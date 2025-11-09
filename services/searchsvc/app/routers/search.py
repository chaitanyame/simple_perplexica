from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import json
from ..models import (
    SearchRequest,
    SearchResponse,
    Source,
    FocusMode,
    OptimizationMode,
    DecompositionInfo,
    SearchStrategy,
)
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


async def get_sources(query: str, focus_mode):
    """Fetch sources via SearxNG primary, SerperDev fallback - matching Perplexica."""
    # Handle both string and enum focus modes for testing flexibility
    if isinstance(focus_mode, str):
        # Convert string to enum if needed
        focus_mode_value = focus_mode
        try:
            focus_mode = FocusMode(focus_mode)
        except ValueError:
            focus_mode = FocusMode.webSearch
    else:
        focus_mode_value = (
            focus_mode.value if hasattr(focus_mode, "value") else str(focus_mode)
        )

    cfg = FOCUS_MODE_ENGINES.get(focus_mode, {"searchWeb": True, "engines": []})
    # Always perform web search regardless of focusMode configuration

    logger.info(
        "Fetching sources",
        extra={
            "query": query,
            "focus_mode": focus_mode_value,
            "engines": cfg["engines"],
        },
    )

    # TEMPORARY: Skip SearxNG to test SerperDev directly
    logger.info("TEMP: Skipping SearxNG, forcing SerperDev", extra={"query": query})
    # try:
    #     results = await searx_client.search(
    #         query, engines=cfg["engines"], language="en"
    #     )
    #     if results:
    #         logger.info(
    #             "SearxNG search successful",
    #             extra={"query": query, "result_count": len(results)},
    #         )
    #         return results
    # except Exception as e:
    #     logger.warning(
    #         "SearxNG search failed",
    #         extra={"query": query, "error": str(e)},
    #     )

    # Force SerperDev for comparison
    if serper_client.is_available():
        try:
            logger.info("Falling back to SerperDev", extra={"query": query})
            results = await serper_client.search(query)
            logger.info(
                "SerperDev search successful",
                extra={"query": query, "result_count": len(results)},
            )
            return results
        except Exception as e:
            logger.error(
                "SerperDev fallback failed",
                extra={"query": query, "error": str(e)},
                exc_info=True,
            )
    else:
        logger.warning(
            "SerperDev not configured, skipping fallback",
            extra={"query": query},
        )

    logger.error(
        "All search providers failed or unavailable",
        extra={"query": query},
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


def _aggregate_multi_query_results(results: List[Dict]) -> List[Dict]:
    """
    Aggregate multi-query search results with fairness across sub-queries.

    Process:
    0. (If available) Limit per sub-query to reduce dominance and ensure balance
    1. Deduplicate by URL (keep version with longer content)
    2. Prioritize authoritative/official domains (microsoft.com, azure.com, google.com, aws.amazon.com, etc.)
    3. Apply diversity filter (max per domain)
    4. Sort by domain authority and content quality
    5. Limit to support comprehensive data coverage
    """
    if not results:
        return []

    from urllib.parse import urlparse

    # Define authoritative domains that should be prioritized
    AUTHORITATIVE_DOMAINS = {
        # Microsoft ecosystem (TIER 1 - Official)
        "microsoft.com",
        "azure.microsoft.com",
        "azure.com",
        "docs.microsoft.com",
        "techcommunity.microsoft.com",
        "devblogs.microsoft.com",
        "learn.microsoft.com",
        "blogs.microsoft.com",
        "news.microsoft.com",
        # Google Cloud (TIER 1 - Official)
        "cloud.google.com",
        "cloud.google",
        "developers.google.com",
        "cloud.google.com",
        # AWS (TIER 1 - Official)
        "aws.amazon.com",
        "amazonaws.com",
        "docs.aws.amazon.com",
        # Other major tech companies (TIER 1 - Official)
        "oracle.com",
        "ibm.com",
        "salesforce.com",
        "vmware.com",
        "redhat.com",
        # Major tech news (TIER 2 - Reputable news)
        "techcrunch.com",
        "theverge.com",
        "arstechnica.com",
        "zdnet.com",
        "cnet.com",
        "engadget.com",
        "venturebeat.com",
        "infoworld.com",
        "computerworld.com",
        "wired.com",
        "theinformation.com",
        "bloomberg.com",
        "reuters.com",
        "wsj.com",
        "nytimes.com",
        "cnbc.com",
        # Microsoft-focused news sites (TIER 2)
        "windowscentral.com",
        "windowslatest.com",
        "neowin.net",
        "bleepingcomputer.com",
        "webpronews.com",
        "techradar.com",
        "msn.com",
        # Developer resources (TIER 2)
        "github.com",
        "stackoverflow.com",
        "medium.com",
        "dev.to",
        # Financial news with tech coverage (TIER 3)
        "fool.com",
        "morningstar.com",
        "seekingalpha.com",
        "benzinga.com",
    }

    def is_authoritative_domain(url: str) -> bool:
        """Check if URL is from an authoritative domain."""
        try:
            domain = urlparse(url).netloc.lower()
            # Check exact match or subdomain match
            for auth_domain in AUTHORITATIVE_DOMAINS:
                if domain == auth_domain or domain.endswith("." + auth_domain):
                    return True
            return False
        except Exception:
            return False

    working = results

    # Step 0: Fairness per sub-query if tagging is present
    try:
        if any("_query_index" in r for r in results):
            groups: dict[int, list[dict]] = {}
            for r in results:
                idx = int(r.get("_query_index", 1))
                groups.setdefault(idx, []).append(r)

            logger.info(
                "PHASE 0: Query grouping",
                extra={
                    "total_results": len(results),
                    "num_queries": len(groups),
                    "per_query_counts": {k: len(v) for k, v in groups.items()},
                },
            )

            # Sort within each group by rough content quality
            for lst in groups.values():
                lst.sort(key=lambda x: len(x.get("pageContent", "")), reverse=True)

            # Cap per group to avoid any single topic dominating
            cap_per_group = 8
            balanced: list[dict] = []
            for idx in sorted(groups.keys()):
                balanced.extend(groups[idx][:cap_per_group])

            logger.info(
                "PHASE 0: After per-query capping",
                extra={
                    "cap_per_group": cap_per_group,
                    "balanced_count": len(balanced),
                },
            )

            working = balanced
    except Exception:
        # If any error in fairness step, continue with all results
        working = results

    # Step 1: Deduplicate by URL (keep best version)
    url_to_best: dict[str, dict] = {}
    for result in working:
        url = result.get("url", "")
        if not url:
            continue

        if url not in url_to_best:
            url_to_best[url] = result
        else:
            existing = url_to_best[url]
            existing_content_len = len(existing.get("pageContent", ""))
            new_content_len = len(result.get("pageContent", ""))
            if new_content_len > existing_content_len:
                url_to_best[url] = result

    deduplicated = list(url_to_best.values())

    logger.info(
        "PHASE 1: Deduplication completed",
        extra={
            "original_count": len(working),
            "deduplicated_count": len(deduplicated),
            "duplicates_removed": len(working) - len(deduplicated),
        },
    )

    # Step 2: Diversity filter (higher limits for authoritative domains)
    domain_counts: dict[str, int] = {}
    filtered: list[dict] = []

    for result in deduplicated:
        url = result.get("url", "")
        try:
            domain = urlparse(url).netloc
        except Exception:
            domain = "unknown"

        # Authoritative domains get higher cap (20), others get 10
        is_auth = is_authoritative_domain(url)
        max_per_domain = 20 if is_auth else 10

        domain_count = domain_counts.get(domain, 0)
        if domain_count < max_per_domain:
            filtered.append(result)
            domain_counts[domain] = domain_count + 1

    logger.info(
        "PHASE 2: Diversity filter completed",
        extra={
            "input_count": len(deduplicated),
            "filtered_count": len(filtered),
            "unique_domains": len(domain_counts),
            "domain_distribution": domain_counts,
        },
    )

    # Step 3: Prioritize authoritative domains and sort by quality
    # Separate into authoritative and non-authoritative
    authoritative = []
    non_authoritative = []

    for result in filtered:
        url = result.get("url", "")
        if is_authoritative_domain(url):
            authoritative.append(result)
        else:
            non_authoritative.append(result)

    # Sort each group by content quality (length as proxy)
    authoritative.sort(key=lambda x: len(x.get("pageContent", "")), reverse=True)
    non_authoritative.sort(key=lambda x: len(x.get("pageContent", "")), reverse=True)

    # Combine with authoritative sources first
    filtered = authoritative + non_authoritative

    logger.info(
        "PHASE 3: Domain prioritization completed",
        extra={
            "authoritative_count": len(authoritative),
            "non_authoritative_count": len(non_authoritative),
            "authoritative_domains": [
                urlparse(r.get("url", "")).netloc for r in authoritative[:5]
            ],
        },
    )

    # Step 4: Limit to support comprehensive data coverage
    # Keep more results to allow for URL enrichment and final synthesis
    limited = filtered[:50]  # Increased from 10 to support Option 1 comprehensive data

    logger.info(
        "PHASE 4: Multi-query aggregation completed",
        extra={
            "after_sort_count": len(filtered),
            "final_count": len(limited),
            "limit_applied": 50,
        },
    )

    return limited


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
                "optimized_queries": decision.optimized_queries,
                "search_strategy": getattr(decision, "search_strategy", "single"),
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
            optimized_queries = [req.query]
            search_strategy = "single"
            links = []

        decision = _D()

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

    # Multi-query search implementation
    if decision.need_search:
        search_strategy = getattr(decision, "search_strategy", "single")

        if search_strategy == "multi" and len(decision.optimized_queries) > 1:
            # MULTI-QUERY: Execute all queries in parallel and aggregate
            all_results = []
            effective_query = req.query  # Original query for context

            logger.info(
                "Multi-query search initiated",
                extra={
                    "query_count": len(decision.optimized_queries),
                    "queries": decision.optimized_queries,
                },
            )

            # Execute each query and collect results
            for idx, query in enumerate(decision.optimized_queries, 1):
                try:
                    query_results = await get_sources(query, req.focusMode)

                    # Tag results with source query for tracking
                    for result in query_results or []:
                        result["_source_query"] = query
                        result["_query_index"] = idx

                    all_results.extend(query_results or [])

                    logger.info(
                        f"Query {idx} search completed",
                        extra={
                            "query": query,
                            "result_count": len(query_results or []),
                        },
                    )
                except Exception as e:
                    logger.warning(
                        f"Query {idx} failed",
                        extra={"query": query, "error": str(e)},
                    )

            # BACKFILL: Add official domain search for authoritative sources
            # Detect if query mentions specific companies/products
            query_lower = req.query.lower().strip()
            base_query = req.query.strip()
            official_site_query = None

            if any(term in query_lower for term in ["microsoft", "azure"]):
                official_site_query = f"{base_query} site:microsoft.com OR site:azure.com OR site:docs.microsoft.com"
            elif any(term in query_lower for term in ["google cloud", "gcp"]):
                official_site_query = (
                    f"{base_query} site:cloud.google.com OR site:google.com/cloud"
                )
            elif any(term in query_lower for term in ["aws", "amazon web services"]):
                official_site_query = (
                    f"{base_query} site:aws.amazon.com OR site:docs.aws.amazon.com"
                )

            if official_site_query:
                try:
                    logger.info(
                        "Executing official domain backfill query",
                        extra={"query": official_site_query},
                    )
                    official_results = await get_sources(
                        official_site_query, req.focusMode
                    )
                    if official_results:
                        for result in official_results:
                            result["_source_query"] = "official_backfill"
                            result["_query_index"] = 999  # Special marker
                        all_results.extend(official_results)
                        logger.info(
                            "Official domain backfill completed",
                            extra={"backfill_count": len(official_results)},
                        )
                except Exception as e:
                    logger.warning(
                        "Official domain backfill failed",
                        extra={"error": str(e)},
                    )

            # AGGREGATION: Process multi-query results
            fetched = _aggregate_multi_query_results(all_results)

            logger.info(
                "Multi-query aggregation completed",
                extra={
                    "raw_count": len(all_results),
                    "final_count": len(fetched),
                },
            )
        else:
            # SINGLE-QUERY: Use existing behavior
            effective_query = (
                decision.optimized_queries[0]
                if decision.optimized_queries
                else req.query
            )

            logger.info(
                "Single-query search",
                extra={"query": effective_query},
            )

            fetched = await get_sources(effective_query, req.focusMode)
    else:
        fetched = []

    sources = link_sources + (fetched or [])
    # If no sources are available, proceed gracefully with empty sources.

    # ENHANCEMENT: Optionally fetch full content from top search result URLs
    # Fetch URLs in balanced (2 URLs) and quality mode (5 URLs)
    if (
        req.optimizationMode in [OptimizationMode.balanced, OptimizationMode.quality]
        and fetched
    ):
        # Balanced: fetch 5 URLs, Quality: fetch 25 URLs for deep research
        num_urls = 5 if req.optimizationMode == OptimizationMode.balanced else 25
        # Quality mode: 5 chunks per URL for comprehensive coverage
        chunks_per_url = 3 if req.optimizationMode == OptimizationMode.balanced else 5
        top_urls = [s.get("url") for s in fetched[:num_urls] if s.get("url")]

        logger.info(
            "ENRICHMENT PHASE: Starting URL content fetching",
            extra={
                "optimization_mode": req.optimizationMode.value,
                "num_urls_to_fetch": num_urls,
                "chunks_per_url": chunks_per_url,
                "fetched_count": len(fetched),
                "top_urls_count": len(top_urls),
            },
        )

        if top_urls:
            try:
                enriched_docs = await fetch_and_process_urls(
                    top_urls, max_chunks_per_url=chunks_per_url
                )

                logger.info(
                    "ENRICHMENT PHASE: URL content fetched",
                    extra={
                        "enriched_docs_count": len(enriched_docs),
                    },
                )
                # Replace shallow snippets with enriched content for these URLs
                url_to_enriched = {}
                for doc in enriched_docs:
                    url = doc.get("url")
                    if url not in url_to_enriched:
                        url_to_enriched[url] = []
                    url_to_enriched[url].append(doc)

                # Update sources with enriched content
                enriched_sources: list[dict] = []
                for s in sources:
                    s_url = s.get("url")
                    if s_url in url_to_enriched:
                        # Replace with enriched chunks from this URL
                        enriched_sources.extend(url_to_enriched[s_url])
                        del url_to_enriched[s_url]  # avoid duplication
                    else:
                        enriched_sources.append(s)

                logger.info(
                    "ENRICHMENT PHASE: Sources merged",
                    extra={
                        "original_sources_count": len(sources),
                        "enriched_sources_count": len(enriched_sources),
                    },
                )

                # Re-aggregate after enrichment to collapse duplicate chunks per URL
                logger.info("ENRICHMENT PHASE: Starting re-aggregation")
                sources = _aggregate_multi_query_results(enriched_sources)
                logger.info(
                    "ENRICHMENT PHASE: Re-aggregation completed",
                    extra={
                        "sources_after_reaggregation": len(sources),
                    },
                )
            except Exception:
                # Silent fallback - use original sources if enrichment fails
                pass

    # Rerank with embeddings if configured
    if sources:
        logger.info(
            "RERANKING PHASE: Starting",
            extra={"sources_before_rerank": len(sources)},
        )
        embedding_key = req.embeddingModel.key if req.embeddingModel else None
        sources = await rerank_sources(
            effective_query, sources, embedding_key, req.focusMode, req.optimizationMode
        )
        logger.info(
            "RERANKING PHASE: Completed",
            extra={"sources_after_rerank": len(sources)},
        )

    # Decide caps based on optimization mode
    if req.optimizationMode == OptimizationMode.speed:
        max_docs = 15
        context_chars = 600
    elif req.optimizationMode == OptimizationMode.quality:
        max_docs = (
            80  # Increased for deep research (25 URLs × 5 chunks ≈ 125, capped at 80)
        )
        context_chars = 2000
    else:
        max_docs = 20
        context_chars = 1000

    logger.info(
        "SYNTHESIS PHASE: Preparing sources",
        extra={
            "total_sources": len(sources),
            "max_docs": max_docs,
            "sources_to_send": min(len(sources), max_docs),
        },
    )

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

            logger.info(
                "SYNTHESIS PHASE: Sending sources to client",
                extra={
                    "sources_sent": len(norm_sources),
                },
            )

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
    # Attach decomposition metadata so UIs (e.g., Streamlit pipeline demo) can display it
    try:
        decomp = DecompositionInfo(
            strategy=search_strategy
            if "search_strategy" in locals()
            else getattr(decision, "search_strategy", "single"),
            optimized_queries=decision.optimized_queries
            if getattr(decision, "optimized_queries", None)
            else [effective_query],
            query_count=len(
                getattr(decision, "optimized_queries", []) or [effective_query]
            ),
        )
    except Exception:
        # Fallback if anything goes wrong constructing metadata
        decomp = None

    return SearchResponse(message=message, sources=norm_sources, decomposition=decomp)
