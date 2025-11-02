from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
from ..models import SearchRequest, SearchResponse, Source, FocusMode, OptimizationMode
from ..search_clients import searxng as searx_client
from ..search_clients import serperdev as serper_client
from ..providers import openrouter
from ..utils.fetch_urls import fetch_and_process_urls
from ..logging_config import get_logger
from ..middleware.rate_limit import limiter
import math
from typing import List, Dict
import os

logger = get_logger(__name__)

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

    logger.info(
        "Fetching sources",
        extra={
            "query": query,
            "focus_mode": focus_mode.value,
            "engines": cfg["engines"],
        },
    )

    try:
        results = await searx_client.search(
            query, engines=cfg["engines"], language="en"
        )
        if results:
            logger.info(
                "SearxNG search successful",
                extra={"query": query, "result_count": len(results)},
            )
            return results
    except Exception as e:
        logger.warning(
            "SearxNG search failed, falling back to SerperDev",
            extra={"query": query, "error": str(e)},
        )
    # Fallback to SerperDev
    try:
        results = await serper_client.search(query)
        logger.info(
            "SerperDev search successful",
            extra={"query": query, "result_count": len(results)},
        )
        return results
    except Exception as e:
        logger.error(
            "All search providers failed",
            extra={"query": query, "error": str(e)},
            exc_info=True,
        )
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
        logger.debug(
            "Skipping reranking",
            extra={
                "reason": "speed optimization or focus mode",
                "source_count": len(sources),
            },
        )
        return sources

    # If speed optimization, still do light rerank like TS speed path: only embed query and use existing doc embeddings if available.
    # Here we embed all doc snippets (short, capped) + query for correctness; can optimize later.
    try:
        if not sources:
            return sources

        logger.info(
            "Starting reranking",
            extra={
                "query": query,
                "source_count": len(sources),
                "threshold": defaults.get("threshold"),
            },
        )

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
            logger.warning(
                "Embedding failed, returning original order", extra={"query": query}
            )
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

        logger.info(
            "Reranking completed",
            extra={
                "query": query,
                "original_count": len(sources),
                "ranked_count": len(ranked),
                "top_similarity": ranked[0]["sim"] if ranked else 0,
            },
        )

        return [sources[x["i"]] for x in ranked]
    except Exception as e:
        # On any embedding error, return original order
        logger.error(
            "Reranking failed", extra={"query": query, "error": str(e)}, exc_info=True
        )
        return sources


@router.post("/search", response_model=SearchResponse)
@limiter.limit("10/minute")  # Rate limit: 10 requests per minute per IP
async def search(req: SearchRequest, request: Request):
    # pydantic handles validation for query/focusMode
    # Focus mode engine settings are ignored since we force search for all queries

    logger.info(
        "Search request received",
        extra={
            "query": req.query,
            "focus_mode": req.focusMode.value,
            "optimization_mode": req.optimizationMode.value,
            "chat_history_length": len(req.history) if req.history else 0,
        },
    )

    # Decide if search is needed and possibly rewrite the query
    try:
        decision = await openrouter.decide_search_and_rewrite(
            req.query, req.history, getattr(req.focusMode, "value", str(req.focusMode))
        )
        logger.debug(
            "Decision completed",
            extra={
                "need_search": decision.need_search,
                "optimized_query": decision.optimized_query,
                "links_count": len(decision.links) if decision.links else 0,
            },
        )
    except Exception as e:
        logger.warning(
            "LLM decisioning failed, using fallback",
            extra={"query": req.query, "error": str(e)},
        )

        # Graceful fallback if LLM decisioning fails (e.g., rate limit)
        class _D:  # light shim to avoid import cycle
            need_search = True
            optimized_query = req.query
            links = []

        decision = _D()

    # Force search for all queries: prefer optimized query if provided
    effective_query = decision.optimized_query or req.query
    sources = []

    # Process user-provided or LLM-suggested links by fetching actual content
    link_sources = []
    if decision.links:
        try:
            link_docs = await fetch_and_process_urls(decision.links)
            link_sources = [
                {
                    "title": doc.get("title", ""),
                    "url": doc.get("url", ""),
                    "pageContent": doc.get("pageContent", ""),
                }
                for doc in link_docs
            ]
        except Exception as e:
            # Graceful fallback if URL fetching fails
            link_sources = [
                {"title": url, "url": url, "pageContent": f"Failed to fetch: {str(e)}"}
                for url in decision.links
            ]

    fetched = await get_sources(effective_query, req.focusMode)
    sources = link_sources + (fetched or [])
    # If no sources are available, proceed gracefully with empty sources.

    # ENHANCEMENT: Optionally fetch full content from top search result URLs
    # Fetch URLs in balanced (2 URLs) and quality mode (5 URLs)
    if (
        req.optimizationMode in [OptimizationMode.balanced, OptimizationMode.quality]
        and fetched
    ):
        # Balanced: fetch 2 URLs, Quality: fetch 5 URLs
        num_urls = 2 if req.optimizationMode == OptimizationMode.balanced else 5
        top_urls = [s.get("url") for s in fetched[:num_urls] if s.get("url")]
        if top_urls:
            try:
                enriched_docs = await fetch_and_process_urls(
                    top_urls, max_chunks_per_url=3
                )
                # Replace shallow snippets with enriched content for these URLs
                url_to_enriched = {}
                for doc in enriched_docs:
                    url = doc.get("url")
                    if url not in url_to_enriched:
                        url_to_enriched[url] = []
                    url_to_enriched[url].append(doc)

                # Update sources with enriched content
                enriched_sources = []
                for s in sources:
                    s_url = s.get("url")
                    if s_url in url_to_enriched:
                        # Replace with enriched chunks
                        enriched_sources.extend(url_to_enriched[s_url])
                        del url_to_enriched[s_url]  # avoid duplication
                    else:
                        enriched_sources.append(s)

                sources = enriched_sources
            except Exception:
                # Silent fallback - use original sources if enrichment fails
                pass

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
                req.focusMode.value,
                req.optimizationMode.value,
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
        req.focusMode.value,
        req.optimizationMode.value,
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
