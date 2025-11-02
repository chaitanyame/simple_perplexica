import os
import inspect
import httpx
from dataclasses import dataclass
from typing import List, Dict, Set, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.openai import OpenAIModel


def _env_or_default(name: str, default: str) -> str:
    v = os.getenv(name, None)
    if v is None:
        return default
    v2 = v.strip()
    return v2 if v2 else default


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = _env_or_default(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)
OPENROUTER_MODEL = _env_or_default(
    "OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free"
)
OPENROUTER_EMBEDDING_MODEL = _env_or_default(
    "OPENROUTER_EMBEDDING_MODEL",
    _env_or_default("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
)
LLM_STRUCTURED_OUTPUT = os.getenv("LLM_STRUCTURED_OUTPUT", "false").lower() in (
    "1",
    "true",
    "yes",
)

# Web search response system prompt (aligned with Perplexica style):
# - Injects optional systemInstructions, current date, and numbered context
# - Enforces [n] citations mapped to the numbered sources
WEBSEARCH_RESPONSE_PROMPT = (
    "{systemInstructions}\n\n"
    "You are Perplexica, an AI model skilled in web search and crafting detailed, engaging, and well-structured answers.\n"
    "Use only the provided CONTEXT to answer the USER QUESTION. Do not claim you lack real-time access—summarize what the CONTEXT says. If the answer isn't supported by the context, say you don't know.\n\n"
    "Style and formatting:\n"
    "- Be comprehensive and accurate; write in clear, professional language.\n"
    "- Organize the answer with short section headings when appropriate (e.g., Overview, Key Points, Latest Updates).\n"
    "- Use bullet points for lists and keep paragraphs concise for readability.\n"
    "- Cite 1–3 of the most relevant sources using [n] inline next to the facts they support.\n"
    "- Do NOT add a separate 'Sources'/'References' section; citations must be inline.\n"
    "- If sources conflict, briefly note differing viewpoints.\n"
    "- Today is: {date}\n\n"
    "CONTEXT (numbered sources):\n{context}\n\n"
    "CONVERSATION (if any):\n{chat_history}\n\n"
    "USER QUESTION: Provide a well-structured, thorough answer with inline [n] citations.\n"
)


class AnswerOutput(BaseModel):
    """Structured answer with citations.

    - answer: final response text to return to the client
    - citations: list of source URLs used in the answer
    """

    answer: str = Field(description="Concise answer text for the user.")
    citations: List[str] = Field(
        default_factory=list,
        description="List of citation URLs referenced in the answer.",
    )


class DecisionOutput(BaseModel):
    """Decision and rewritten query for search flow."""

    need_search: bool
    optimized_query: Optional[str] = None
    links: List[str] = Field(default_factory=list)


@dataclass
class AnswerDeps:
    """Dependencies passed into the agent for validation/guardrails."""

    allowed_urls: Set[str]
    require_citations: bool


def _build_agent(system_instructions: str | None, deps: AnswerDeps) -> Agent:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")
    # Configure OpenAI SDK env so PydanticAI's OpenAIModel targets OpenRouter
    os.environ["OPENAI_API_KEY"] = OPENROUTER_API_KEY
    os.environ["OPENAI_BASE_URL"] = OPENROUTER_BASE_URL
    # Use OpenAIModel (non-chat specific) to avoid tool-use routing for models that don't support it
    model = OpenAIModel(OPENROUTER_MODEL)
    system = system_instructions or (
        "You are a helpful search assistant."
        " Answer concisely. When context is provided, cite 1-3 sources only from the provided context URLs."
        " If no context is provided, you may answer without citations."
    )

    if LLM_STRUCTURED_OUTPUT:
        agent = Agent[AnswerDeps, AnswerOutput](
            model,
            deps_type=AnswerDeps,
            output_type=AnswerOutput,
            instructions=system,
        )

        @agent.output_validator
        async def _validate(  # type: ignore[no-redef]
            ctx: RunContext[AnswerDeps], output: AnswerOutput
        ) -> AnswerOutput:  # type: ignore[valid-type]
            # Basic guardrails
            if ctx.deps.require_citations and ctx.deps.allowed_urls:
                if not any(url in ctx.deps.allowed_urls for url in output.citations):
                    raise ModelRetry(
                        "Include at least one citation URL from the provided context sources."
                    )
            if output.citations:
                output.citations = [
                    u
                    for u in output.citations
                    if (not ctx.deps.allowed_urls) or (u in ctx.deps.allowed_urls)
                ][:5]
            if len(output.answer) > 4000:
                output.answer = output.answer[:4000].rstrip() + "…"
            return output

        return agent
    else:
        # Plain-text agent to avoid tool/structured-output requirements
        return Agent[AnswerDeps, str](
            model,
            deps_type=AnswerDeps,
            instructions=system,
        )


async def embed_texts(
    texts: List[str], model: Optional[str] = None
) -> List[List[float]]:
    """Create embeddings for a list of texts using OpenRouter's OpenAI-compatible /embeddings.

    Returns a list of vectors, matching the order of inputs. If an error occurs, raises.
    """
    if not texts:
        return []
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")
    embed_model = model or OPENROUTER_EMBEDDING_MODEL
    # Prefer OpenAI-compatible embeddings endpoint
    payload = {
        "model": embed_model,
        "input": texts,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{OPENROUTER_BASE_URL}/embeddings", json=payload, headers=headers
        )
        resp.raise_for_status()
        data = resp.json()
        # OpenAI-compatible response: { data: [ { embedding: [...], index: 0 }, ... ] }
        out: List[List[float]] = []
        for item in data.get("data", []):
            emb = item.get("embedding")
            if isinstance(emb, list):
                out.append([float(v) for v in emb])
        # Ensure length matches input count when possible
        return out


async def decide_search_and_rewrite(
    query: str,
    history: Optional[List[List[str]]] = None,
    focus_mode: Optional[str] = None,
) -> DecisionOutput:
    """Decide if search is needed and produce an optimized standalone query.

    Mirrors Perplexica behavior: greetings/simple writing -> no search; otherwise rewrite.
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")

    os.environ.setdefault("OPENAI_API_KEY", OPENROUTER_API_KEY)
    os.environ.setdefault("OPENAI_BASE_URL", OPENROUTER_BASE_URL)
    model = OpenAIModel(OPENROUTER_MODEL)

    instructions = (
        "You are an AI question rephraser and search decider. "
        "Given a conversation (optional) and a query, decide if web search is needed. "
        "If the message is a greeting or a simple writing task without factual lookup, set need_search=false. "
        "Otherwise set need_search=true and provide an optimized standalone query. "
        "If the user provided URLs to summarize or reference, include them in links. "
        "Return strictly JSON for fields: need_search (bool), optimized_query (string|null), links (string[])."
    )

    # Flatten history for context
    convo = []
    if history:
        for pair in history:
            if isinstance(pair, list) and len(pair) == 2:
                u, a = pair
                if isinstance(u, str):
                    convo.append(f"User: {u}")
                if isinstance(a, str):
                    convo.append(f"Assistant: {a}")
    convo_text = "\n".join(convo) or "(none)"

    agent = Agent[None, DecisionOutput](
        model,
        output_type=DecisionOutput,
        instructions=instructions,
    )
    prompt = (
        f"Conversation:\n{convo_text}\n\n"
        f"Focus mode: {focus_mode or 'unknown'}\n"
        f"Question: {query}\n"
        "Respond with JSON only."
    )

    try:
        result = agent.run(prompt)  # type: ignore[arg-type]
        if inspect.isawaitable(result):
            result = await result
        output = getattr(result, "output", None)
        if isinstance(output, DecisionOutput):
            return output
        # Attempt to coerce from string
        try:
            import json as _json

            data = _json.loads(str(output) if output is not None else str(result))
            return DecisionOutput(**data)
        except Exception:
            return DecisionOutput(need_search=True, optimized_query=query, links=[])
    except Exception:
        # Graceful fallback on model errors (429, connection, etc.)
        # Simple heuristic: if the query looks like a greeting or trivial writing task, skip search.
        ql = (query or "").strip().lower()
        greetings = {
            "hi",
            "hello",
            "hey",
            "hey there",
            "how are you",
            "good morning",
            "good evening",
        }
        writing_prefixes = ("write ", "draft ", "compose ", "rewrite ", "paraphrase ")
        if ql in greetings or any(ql.startswith(p) for p in writing_prefixes):
            return DecisionOutput(need_search=False, optimized_query=query, links=[])
        return DecisionOutput(need_search=True, optimized_query=query, links=[])


async def synthesize_answer(
    query: str,
    sources: List[Dict],
    system_instructions: str | None = None,
    history: Optional[List[List[str]]] = None,
    context_chars: int = 800,
) -> str:
    # Prepare structured context and deps
    context_lines: List[str] = []
    allowed_urls: Set[str] = set()
    # Number sources to support [n] citations
    for idx, s in enumerate(sources, start=1):
        url = s.get("url", "")
        if url:
            allowed_urls.add(url)
        title = s.get("title", "")
        content = (s.get("pageContent", "") or "")[: max(200, context_chars)]
        context_lines.append(f"[{idx}] {title} ({url}): {content}")
    context = "\n".join(context_lines)

    deps = AnswerDeps(allowed_urls=allowed_urls, require_citations=bool(allowed_urls))
    # Inject Perplexica-style web search response prompt into system instructions
    from datetime import datetime, timezone

    now_iso = datetime.now(timezone.utc).isoformat()
    # Build chat history block
    chat_lines: List[str] = []
    if history:
        for pair in history:
            if isinstance(pair, list) and len(pair) == 2:
                h, a = pair
                if isinstance(h, str):
                    chat_lines.append(f"Human: {h}")
                if isinstance(a, str):
                    chat_lines.append(f"Assistant: {a}")
    chat_history = "\n".join(chat_lines)
    sys_text = WEBSEARCH_RESPONSE_PROMPT.format(
        systemInstructions=system_instructions or "",
        context=context,
        date=now_iso,
        chat_history=chat_history,
    )
    agent = _build_agent(sys_text, deps)

    # Pass only the user query; context/date live in system instructions
    user_input = query

    # Run agent using unified API; Agent.run may be async in current version
    try:
        result = agent.run(user_input, deps=deps)  # type: ignore[arg-type]
        if inspect.isawaitable(result):
            result = await result

        output = getattr(result, "output", None)
        if LLM_STRUCTURED_OUTPUT:
            if isinstance(output, AnswerOutput):
                return output.answer
            return str(output) if output is not None else str(result)
        # Non-structured path: output is a string
        return str(output) if output is not None else str(result)
    except Exception as e:
        # If model rejects tool/structured calls, fallback to plain chat completion
        err_text = str(e)
        if (
            isinstance(e, ModelHTTPError)
            or "tool use" in err_text.lower()
            or "no endpoints found" in err_text.lower()
        ):
            # Use the same system text with context and date for fallback
            system = sys_text
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_input},
            ]
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": OPENROUTER_MODEL,
                            "messages": messages,
                            "tool_choice": "none",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices") or []
                    if choices:
                        msg = choices[0].get("message", {}).get("content", "")
                        return msg or ""
            except httpx.HTTPError:
                return "Sorry, the language model is temporarily rate-limited. Please try again shortly."
        # Re-raise other errors
        raise


async def synthesize_answer_structured(
    query: str,
    sources: List[Dict],
    system_instructions: str | None = None,
    history: Optional[List[List[str]]] = None,
    context_chars: int = 800,
) -> AnswerOutput:
    """Structured variant for future consumers who want citations explicitly."""
    context_lines: List[str] = []
    allowed_urls: Set[str] = set()
    for idx, s in enumerate(sources, start=1):
        url = s.get("url", "")
        if url:
            allowed_urls.add(url)
        title = s.get("title", "")
        content = (s.get("pageContent", "") or "")[: max(200, context_chars)]
        context_lines.append(f"[{idx}] {title} ({url}): {content}")
    context = "\n".join(context_lines)

    deps = AnswerDeps(allowed_urls=allowed_urls, require_citations=bool(allowed_urls))
    from datetime import datetime, timezone

    now_iso = datetime.now(timezone.utc).isoformat()
    chat_lines: List[str] = []
    if history:
        for pair in history:
            if isinstance(pair, list) and len(pair) == 2:
                h, a = pair
                if isinstance(h, str):
                    chat_lines.append(f"Human: {h}")
                if isinstance(a, str):
                    chat_lines.append(f"Assistant: {a}")
    chat_history = "\n".join(chat_lines)
    sys_text = WEBSEARCH_RESPONSE_PROMPT.format(
        systemInstructions=system_instructions or "",
        context=context,
        date=now_iso,
        chat_history=chat_history,
    )
    agent = _build_agent(sys_text, deps)
    user_input = query

    try:
        result = agent.run(user_input, deps=deps)  # type: ignore[arg-type]
        if inspect.isawaitable(result):
            result = await result

        output = getattr(result, "output", None)
        if LLM_STRUCTURED_OUTPUT and isinstance(output, AnswerOutput):
            return output
        # Map to structured form
        return AnswerOutput(
            answer=str(output) if output is not None else str(result), citations=[]
        )
    except Exception as e:
        err_text = str(e)
        if (
            isinstance(e, ModelHTTPError)
            or "tool use" in err_text.lower()
            or "no endpoints found" in err_text.lower()
        ):
            system = sys_text
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": user_input},
            ]
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(
                        f"{OPENROUTER_BASE_URL}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": OPENROUTER_MODEL,
                            "messages": messages,
                            "tool_choice": "none",
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    choices = data.get("choices") or []
                    content = (
                        choices[0].get("message", {}).get("content", "")
                        if choices
                        else ""
                    )
                    return AnswerOutput(answer=content, citations=[])
            except httpx.HTTPError:
                return AnswerOutput(
                    answer="Sorry, the language model is temporarily rate-limited. Please try again shortly.",
                    citations=[],
                )
        raise
