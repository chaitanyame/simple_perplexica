from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import json
from ..models import SearchRequest, SearchResponse, Source, FocusMode, OptimizationMode
from ..search_clients import searxng as searx_client
from ..search_clients import serperdev as serper_client
from ..providers import openrouter
import math
from typing import List, Dict

router = APIRouter()


FOCUS_MODE_ENGINES = {
    FocusMode.webSearch: {"searchWeb": True, "engines": []},
    FocusMode.academicSearch: {
        "searchWeb": True,
        "engines": ["arxiv", "google scholar", "pubmed"],
    },
    FocusMode.writingAssistant: {"searchWeb": False, "engines": []},
    FocusMode.wolframAlphaSearch: {"searchWeb": True, "engines": ["wolframalpha"]},
    FocusMode.youtubeSearch: {"searchWeb": True, "engines": ["youtube"]},
    FocusMode.redditSearch: {"searchWeb": True, "engines": ["reddit"]},
}

# Rerank defaults mirrored from src/lib/search/index.ts
RERANK_DEFAULTS = {
    FocusMode.webSearch: {"rerank": True, "threshold": 0.3},
    FocusMode.academicSearch: {"rerank": True, "threshold": 0.0},
    FocusMode.writingAssistant: {"rerank": True, "threshold": 0.0},
    FocusMode.wolframAlphaSearch: {"rerank": False, "threshold": 0.0},
    FocusMode.youtubeSearch: {"rerank": True, "threshold": 0.3},
    FocusMode.redditSearch: {"rerank": True, "threshold": 0.3},
}


async def get_sources(query: str, focus_mode: FocusMode):
    """Fetch sources via SearxNG primary, SerperDev fallback - matching Perplexica."""
    cfg = FOCUS_MODE_ENGINES.get(focus_mode, {"searchWeb": True, "engines": []})
    # Always perform web search regardless of focusMode configuration
    try:
        results = await searx_client.search(
            query, engines=cfg["engines"], language="en"
        )
        if results:
            return results
    except Exception:
        pass
    # Fallback to SerperDev
    try:
        return await serper_client.search(query)
    except Exception:
        return []


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def rerank_sources(
    query: str,
    sources: List[Dict],
    embedding_model_key: str | None,
    focus_mode: FocusMode,
    optimization: OptimizationMode,
) -> List[Dict]:
    # Decide if we rerank
    defaults = RERANK_DEFAULTS.get(focus_mode, {"rerank": True, "threshold": 0.3})
    if not defaults["rerank"] or optimization == OptimizationMode.speed:
        return sources

    # If speed optimization, still do light rerank like TS speed path: only embed query and use existing doc embeddings if available.
    # Here we embed all doc snippets (short, capped) + query for correctness; can optimize later.
    try:
        if not sources:
            return sources
        # Build texts to embed: query once, each source content (fallback to title)
        doc_texts = []
        for s in sources:
            content = s.get("pageContent") or s.get("title") or ""
            # limit length to keep costs bounded
            doc_texts.append(content[:1000])
        # First index 0 reserved for query
        inputs = [query] + doc_texts
        vectors = await openrouter.embed_texts(inputs, model=embedding_model_key)
        if not vectors or len(vectors) != len(inputs):
            return sources
        qv = vectors[0]
        sims = []
        for i, s in enumerate(sources):
            dv = vectors[i + 1]
            sim = _cosine_similarity(qv, dv)
            sims.append({"i": i, "sim": sim})
        threshold = float(defaults.get("threshold", 0.0))
        # Filter and sort
        ranked = [x for x in sims if x["sim"] > threshold]
        if not ranked:
            # if all are below threshold, just sort all by sim
            ranked = sims
        ranked.sort(key=lambda x: x["sim"], reverse=True)
        return [sources[x["i"]] for x in ranked]
    except Exception:
        # On any embedding error, return original order
        return sources


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    # pydantic handles validation for query/focusMode
    # Focus mode engine settings are ignored since we force search for all queries
    # Decide if search is needed and possibly rewrite the query
    try:
        decision = await openrouter.decide_search_and_rewrite(
            req.query, req.history, getattr(req.focusMode, "value", str(req.focusMode))
        )
    except Exception:
        # Graceful fallback if LLM decisioning fails (e.g., rate limit)
        class _D:  # light shim to avoid import cycle
            need_search = True
            optimized_query = req.query
            links = []

        decision = _D()

    # Force search for all queries: prefer optimized query if provided
    effective_query = decision.optimized_query or req.query
    sources = []
    # Seed with user-provided links if any
    link_sources = [
        {"title": url, "url": url, "pageContent": ""} for url in (decision.links or [])
    ]
    fetched = await get_sources(effective_query, req.focusMode)
    sources = link_sources + (fetched or [])
    # If no sources are available, proceed gracefully with empty sources.

    # Rerank with embeddings if configured
    if sources:
        embedding_key = req.embeddingModel.key if req.embeddingModel else None
        sources = await rerank_sources(
            effective_query, sources, embedding_key, req.focusMode, req.optimizationMode
        )

    # Decide caps based on optimization mode
    if req.optimizationMode == OptimizationMode.speed:
        max_docs = 15
        context_chars = 600
    elif req.optimizationMode == OptimizationMode.quality:
        max_docs = 20
        context_chars = 1200
    else:
        max_docs = 15
        context_chars = 800

    if req.stream:

        async def event_stream():
            # init
            yield json.dumps({"type": "init", "data": "Stream connected"}) + "\n"
            # normalize
            norm_sources = [
                {
                    "title": s.get("title", ""),
                    "url": s.get("url", ""),
                    "pageContent": s.get("pageContent"),
                }
                for s in sources[:max_docs]
            ]
            yield json.dumps({"type": "sources", "data": norm_sources}) + "\n"

            # synthesize in one go (chunking can be added later)
            message = await openrouter.synthesize_answer(
                effective_query,
                sources[:max_docs],
                req.systemInstructions,
                req.history,
                context_chars,
            )
            yield json.dumps({"type": "response", "data": message}) + "\n"
            yield json.dumps({"type": "done"}) + "\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    # Non-streaming
    message = await openrouter.synthesize_answer(
        effective_query,
        sources[:max_docs],
        req.systemInstructions,
        req.history,
        context_chars,
    )
    norm_sources = [
        Source(
            title=s.get("title", ""),
            url=s.get("url", ""),
            pageContent=s.get("pageContent"),
        )
        for s in sources[:max_docs]
    ]
    return SearchResponse(message=message, sources=norm_sources)
