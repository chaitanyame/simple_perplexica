import os
import inspect
import httpx
from dataclasses import dataclass
from typing import List, Dict, Set, Optional

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.openai import OpenAIModel

from ..utils.http_client import get_http_client


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

# Web search response system prompt (fully aligned with Perplexica's detailed style):
# - Comprehensive instructions for blog-style, engaging responses
# - Enforces strict citation requirements with [n] notation
# - Emphasizes depth, clarity, and professional structure
WEBSEARCH_RESPONSE_PROMPT = """You are Perplexica, an AI model skilled in web search and crafting detailed, engaging, and well-structured answers. You excel at summarizing web pages and extracting relevant information to create professional, blog-style responses.

Your task is to provide answers that are:
- **Informative and relevant**: Thoroughly address the user's query using the given context.
- **Well-structured**: Include clear headings and subheadings, and use a professional tone to present information concisely and logically.
- **Engaging and detailed**: Write responses that read like a high-quality blog post, including extra details and relevant insights.
- **Cited and credible**: Use inline citations with [number] notation to refer to the context source(s) for each fact or detail included.
- **Explanatory and Comprehensive**: Strive to explain the topic in depth, offering detailed analysis, insights, and clarifications wherever applicable.

### Formatting Instructions
- **Structure**: Use a well-organized format with proper headings (e.g., "## Overview" or "## Key Features"). Present information in paragraphs or concise bullet points where appropriate.
- **Tone and Style**: Maintain a neutral, journalistic tone with engaging narrative flow. Write as though you're crafting an in-depth article for a professional audience.
- **Markdown Usage**: Format your response with Markdown for clarity. Use headings, subheadings, bold text, and italicized words as needed to enhance readability.
- **Length and Depth**: Provide comprehensive coverage of the topic. Avoid superficial responses and strive for depth without unnecessary repetition. Expand on technical or complex topics to make them easier to understand for a general audience.
- **No main heading/title**: Start your response directly with the introduction unless asked to provide a specific title.
- **Conclusion or Summary**: Include a concluding paragraph that synthesizes the provided information or suggests potential next steps, where appropriate.

### Citation Requirements
- Cite every single fact, statement, or sentence using [number] notation corresponding to the source from the provided context.
- Integrate citations naturally at the end of sentences or clauses as appropriate. For example, "The Eiffel Tower is one of the most visited landmarks in the world[1]."
- Ensure that **every sentence in your response includes at least one citation**, even when information is inferred or connected to general knowledge available in the provided context.
- Use multiple sources for a single detail if applicable, such as, "Paris is a cultural hub, attracting millions of visitors annually[1][2]."
- Always prioritize credibility and accuracy by linking all statements back to their respective context sources.
- Avoid citing unsupported assumptions or personal interpretations; if no source supports a statement, clearly indicate the limitation.

### Special Instructions
- If the query involves technical, historical, or complex topics, provide detailed background and explanatory sections to ensure clarity.
- If the user provides vague input or if relevant information is missing, explain what additional details might help refine the search.
- If no relevant information is found, say: "Hmm, sorry I could not find any relevant information on this topic. Would you like me to search again or ask something else?" Be transparent about limitations and suggest alternatives or ways to reframe the query.

### User Instructions
These instructions are shared by the user and not by the system. You will have to follow them but give them less priority than the above instructions. If the user has provided specific instructions or preferences, incorporate them into your response while adhering to the overall guidelines.
{systemInstructions}

### Context
<context>
{context}
</context>

### Conversation History
{chat_history}

Current date & time in ISO format (UTC timezone) is: {date}.

### Response Guidelines
- Begin with a brief introduction summarizing the topic or query.
- Follow with detailed sections under clear headings, covering all aspects of the query if possible.
- Provide explanations or historical context as needed to enhance understanding.
- End with a conclusion or overall perspective if relevant.
- Remember: Every sentence must have at least one citation [n] from the context above.
"""


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

    OPTIMIZATION: Uses Redis caching to avoid redundant embedding API calls (75% cost savings)

    Returns a list of vectors, matching the order of inputs. If an error occurs, raises.
    """
    if not texts:
        return []
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")

    embed_model = model or OPENROUTER_EMBEDDING_MODEL

    # Try to get from cache first
    from ..utils.cache import cache_embeddings_get, cache_embeddings_set

    cached = await cache_embeddings_get(texts, embed_model)
    if cached is not None:
        return cached

    # Cache miss - call API
    payload = {
        "model": embed_model,
        "input": texts,
    }
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    client = get_http_client()
    resp = await client.post(
        f"{OPENROUTER_BASE_URL}/embeddings", json=payload, headers=headers, timeout=60
    )
    resp.raise_for_status()
    data = resp.json()
    # OpenAI-compatible response: { data: [ { embedding: [...], index: 0 }, ... ] }
    out: List[List[float]] = []
    for item in data.get("data", []):
        emb = item.get("embedding")
        if isinstance(emb, list):
            out.append([float(v) for v in emb])

        # Cache the result
        await cache_embeddings_set(texts, embed_model, out)

        # Ensure length matches input count when possible
        return out


async def decide_search_and_rewrite(
    query: str,
    history: Optional[List[List[str]]] = None,
    focus_mode: Optional[str] = None,
) -> DecisionOutput:
    """Decide if search is needed and produce an optimized standalone query.

    Mirrors Perplexica behavior with few-shot examples:
    - Greetings/simple writing -> need_search=false
    - Questions -> need_search=true with optimized query
    - URL references -> extract links and question
    """
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not configured")

    os.environ.setdefault("OPENAI_API_KEY", OPENROUTER_API_KEY)
    os.environ.setdefault("OPENAI_BASE_URL", OPENROUTER_BASE_URL)
    model = OpenAIModel(OPENROUTER_MODEL)

    instructions = """You are an AI question rephraser and search decider.

You will be given a conversation and a follow-up question. You need to:
1. Decide if web search is needed (need_search: true/false)
2. Rephrase the question to be standalone (optimized_query)
3. Extract any URLs mentioned (links array)

Rules:
- If it's a simple greeting (Hi, Hello, How are you) or basic writing task WITHOUT needing facts, set need_search=false and optimized_query="not_needed"
- For factual questions, set need_search=true and create a clear standalone query
- If user asks to summarize a URL or PDF, set optimized_query="summarize" and include the URL in links
- If user references a URL for context, include it in links and create an appropriate question
- Always make queries standalone by including context from conversation history

Return JSON with: need_search (bool), optimized_query (string), links (string[])

Examples:

Query: "What is the capital of France"
Response: {"need_search": true, "optimized_query": "Capital of France", "links": []}

Query: "Hi, how are you?"
Response: {"need_search": false, "optimized_query": "not_needed", "links": []}

Query: "What is Docker?"
Response: {"need_search": true, "optimized_query": "What is Docker", "links": []}

Query: "Can you tell me what is X from https://example.com"
Response: {"need_search": true, "optimized_query": "What is X?", "links": ["https://example.com"]}

Query: "Summarize the content from https://example.com"
Response: {"need_search": true, "optimized_query": "summarize", "links": ["https://example.com"]}

Query: "Write a poem about nature"
Response: {"need_search": false, "optimized_query": "not_needed", "links": []}
"""

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
    """Synthesize answer from sources.

    OPTIMIZATION: Uses Redis caching for LLM responses based on query + context hash
    """
    # Check cache first
    from ..utils.cache import cache_response_get, cache_response_set, hash_context

    context_hash = hash_context(sources, system_instructions)
    cached_response = await cache_response_get(query, context_hash, OPENROUTER_MODEL)
    if cached_response is not None:
        return cached_response

    # Cache miss - prepare structured context and deps
    context_lines: List[str] = []
    allowed_urls: Set[str] = set()
    # Number sources to support [n] citations
    for idx, s in enumerate(sources, start=1):
        url = s.get("url", "")
        if url:
            allowed_urls.add(url)
        title = s.get("title", "")
        # Use full content fetched from URLs instead of truncating
        # context_chars is still useful for controlling snippet-only sources
        full_content = s.get("pageContent", "") or ""
        # Only truncate if it's a short snippet (< 500 chars means it's from search API, not fetched URL)
        if len(full_content) < 500:
            content = full_content[: max(200, context_chars)]
        else:
            # It's fetched content - use it all (already chunked to ~2000 chars by fetch_urls)
            content = full_content
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
        response_text = None
        if LLM_STRUCTURED_OUTPUT:
            if isinstance(output, AnswerOutput):
                response_text = output.answer
            else:
                response_text = str(output) if output is not None else str(result)
        else:
            # Non-structured path: output is a string
            response_text = str(output) if output is not None else str(result)

        # Cache the response before returning
        await cache_response_set(query, context_hash, OPENROUTER_MODEL, response_text)
        return response_text

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
                client = get_http_client()
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
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    msg = choices[0].get("message", {}).get("content", "")
                    # Cache fallback response too
                    if msg:
                        await cache_response_set(
                            query, context_hash, OPENROUTER_MODEL, msg
                        )
                    return msg or ""
            except httpx.HTTPError:
                error_msg = "Sorry, the language model is temporarily rate-limited. Please try again shortly."
                return error_msg
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
                client = get_http_client()
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
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                choices = data.get("choices") or []
                content = (
                    choices[0].get("message", {}).get("content", "") if choices else ""
                )
                return AnswerOutput(answer=content, citations=[])
            except httpx.HTTPError:
                return AnswerOutput(
                    answer="Sorry, the language model is temporarily rate-limited. Please try again shortly.",
                    citations=[],
                )
        raise
