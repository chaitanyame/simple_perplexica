import httpx
import os
from typing import List, Dict, Optional
import logging
import spacy
import re
from functools import lru_cache
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
# Tunables via environment
SEARXNG_ENGINES = os.getenv(
    "SEARXNG_ENGINES", ""
)  # e.g. "google,bing,duckduckgo,brave"
SEARXNG_CATEGORIES = os.getenv("SEARXNG_CATEGORIES", "general,news,it")
SEARXNG_TIME_RANGE_DEFAULT = os.getenv(
    "SEARXNG_TIME_RANGE", ""
)  # day|week|month|year or ''
SEARXNG_LANGUAGE_DEFAULT = os.getenv("SEARXNG_LANGUAGE", "en")
SEARXNG_PAGES = int(
    os.getenv("SEARXNG_PAGES", "1")
)  # number of pages to fetch per query
SEARXNG_BACKFILL_ENABLED = os.getenv("SEARXNG_BACKFILL_ENABLED", "true").lower() in (
    "1",
    "true",
    "yes",
)
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_spacy_model():
    """Load spacy model once and cache it"""
    try:
        return spacy.load("en_core_web_sm")
    except OSError:
        logger.warning(
            "SpaCy model not found. Install with: python -m spacy download en_core_web_sm"
        )
        return None


def _detect_recency_need(query: str) -> Optional[str]:
    """Detect if query needs recent results using NLP analysis.

    Uses SpaCy for entity recognition and linguistic analysis to identify
    temporal intent more intelligently than keyword matching.

    Returns:
        'day' for today/yesterday, 'week' for this week, 'month' for this month, or None
    """
    if not query:
        return None

    nlp = _load_spacy_model()
    if nlp is None:
        # Fallback to simple keyword matching if SpaCy not available
        return _detect_recency_fallback(query)

    doc = nlp(query)

    # Check for explicit DATE entities recognized by SpaCy
    for ent in doc.ents:
        if ent.label_ == "DATE":
            text_lower = ent.text.lower()
            # Day-level temporal entities
            if any(
                term in text_lower
                for term in ["today", "yesterday", "tonight", "now", "just now"]
            ):
                return "day"
            # Week-level
            if any(term in text_lower for term in ["this week", "week", "weekly"]):
                return "week"
            # Month-level
            if any(term in text_lower for term in ["this month", "month", "monthly"]):
                return "month"

    # Check for temporal modifiers (adjectives that imply recency)
    temporal_adjectives = {
        "latest",
        "breaking",
        "recent",
        "current",
        "new",
        "live",
        "developing",
    }
    news_context_words = {
        "news",
        "update",
        "updates",
        "event",
        "events",
        "development",
        "developments",
        "story",
        "stories",
        "report",
        "reports",
    }

    for token in doc:
        if token.text.lower() in temporal_adjectives:
            # Check if this temporal adjective modifies a news/event context
            # Look at token's children and head in dependency tree
            related_words = {child.text.lower() for child in token.children}
            related_words.add(token.head.text.lower())

            if related_words & news_context_words:
                return "day"  # Latest news/breaking updates → day filter

    return None


def _detect_recency_fallback(query: str) -> Optional[str]:
    """Fallback keyword matching when SpaCy is unavailable"""
    ql = query.lower()

    # Day-level recency
    day_terms = ["today", "yesterday", "breaking", "just now", "tonight", "latest"]
    if any(term in ql for term in day_terms):
        return "day"

    # Week-level recency
    week_terms = ["this week", "past week", "last week", "recent"]
    if any(term in ql for term in week_terms):
        return "week"

    # Month-level recency
    month_terms = ["this month", "past month", "last month"]
    if any(term in ql for term in month_terms):
        return "month"

    if "current" in ql or "now" in ql:
        return "day"

    return None


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def search(
    query: str,
    engines: Optional[List[str]] = None,
    language: Optional[str] = None,
) -> List[Dict]:
    """Search via SearxNG with automatic time-range filtering for recency queries.

    Implements retry logic with exponential backoff for transient failures.
    Retries up to 3 times for HTTP errors and timeouts.
    """
    url = f"{SEARXNG_URL}/search"
    base_params = {"format": "json", "safesearch": 0}

    # Add time_range if query suggests recency
    # Special handling for trending queries:
    # - For WEB search: Skip time_range (trending pages are already time-filtered)
    # - For VIDEO/YOUTUBE search: Keep time_range (need recency filter for video results)
    query_lower = query.lower()
    is_trending_query = any(
        term in query_lower
        for term in ["trending", "popular", "top repositories", "most starred"]
    )
    is_video_search = engines and "youtube" in engines

    # Skip time_range only for trending WEB queries (not for video searches)
    should_skip_time_filter = is_trending_query and not is_video_search

    time_range = None if should_skip_time_filter else _detect_recency_need(query)
    if time_range:
        logger.info(
            f"SpaCy detected temporal intent: time_range={time_range} for query: {query}"
        )
    elif should_skip_time_filter:
        logger.info(
            f"Detected trending WEB query, skipping time_range filter to preserve trending pages: {query}"
        )

    # Build base params with env + function args
    effective_language = language or SEARXNG_LANGUAGE_DEFAULT
    effective_engines = (
        engines
        if engines is not None
        else (
            [e.strip() for e in SEARXNG_ENGINES.split(",") if e.strip()]
            if SEARXNG_ENGINES
            else None
        )
    )

    # Assemble configured params
    params_common = dict(base_params)
    params_common["language"] = effective_language
    if SEARXNG_CATEGORIES:
        params_common["categories"] = SEARXNG_CATEGORIES
    if effective_engines:
        params_common["engines"] = ",".join(effective_engines)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            # Paginate across multiple pages if configured
            all_items: List[Dict] = []
            pages = max(1, SEARXNG_PAGES)
            for pageno in range(1, pages + 1):
                page_params = dict(params_common)
                page_params["q"] = query
                page_params["pageno"] = pageno

                # Apply time_range for each page
                page_params_with_time = dict(page_params)
                if time_range:
                    page_params_with_time["time_range"] = time_range
                elif SEARXNG_TIME_RANGE_DEFAULT:
                    page_params_with_time["time_range"] = SEARXNG_TIME_RANGE_DEFAULT

                r = await client.get(url, params=page_params_with_time)
                r.raise_for_status()
                data = r.json()
                all_items.extend(data.get("results", []))

            # Optional site backfill for key vendors if mentioned in query
            if SEARXNG_BACKFILL_ENABLED:
                try:
                    entities = _entities_from_query(query)
                    missing_domains = _missing_canonical_domains(entities, all_items)
                    for dom in missing_domains:
                        backfill_params = dict(params_common)
                        backfill_params["q"] = f"site:{dom} {query}"
                        backfill_params["pageno"] = 1
                        if time_range:
                            backfill_params["time_range"] = time_range
                        elif SEARXNG_TIME_RANGE_DEFAULT:
                            backfill_params["time_range"] = SEARXNG_TIME_RANGE_DEFAULT
                        r2 = await client.get(url, params=backfill_params)
                        if r2.status_code == 200:
                            all_items.extend(r2.json().get("results", []))
                except Exception:
                    # Soft-fail backfill; continue with what we have
                    pass

            # Normalize and dedupe by URL (keep first)
            seen_urls = set()
            results: List[Dict] = []
            for item in all_items:
                u = item.get("url", "")
                if not u or u in seen_urls:
                    continue
                seen_urls.add(u)
                results.append(
                    {
                        "title": item.get("title") or item.get("source") or "",
                        "url": u,
                        "pageContent": item.get("content") or item.get("snippet") or "",
                    }
                )

            # Log top URLs for debugging
            top_urls = [r.get("url") for r in results[:5]]
            logger.info(
                "SearxNG search completed",
                extra={
                    "query": query,
                    "result_count": len(results),
                    "time_range": time_range or SEARXNG_TIME_RANGE_DEFAULT or None,
                    "engines": params_common.get("engines"),
                    "categories": params_common.get("categories"),
                    "pages": pages,
                    "top_5_urls": top_urls,
                },
            )
            return results
    except httpx.HTTPError as e:
        logger.error(
            "SearxNG HTTP error",
            extra={"query": query, "error": str(e), "url": url},
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            "SearxNG search failed",
            extra={"query": query, "error": str(e)},
            exc_info=True,
        )
        raise


# --- Helpers ---

_ENTITY_DOMAINS = {
    "aws": ["aws.amazon.com/blogs", "aws.amazon.com/about-aws/whats-new"],
    "azure": ["azure.microsoft.com/en-us/blog", "cloudblogs.microsoft.com"],
    "gcp": ["cloud.google.com/blog", "cloud.google.com/releases"],
    "google cloud": ["cloud.google.com/blog", "cloud.google.com/releases"],
}


def _entities_from_query(query: str) -> List[str]:
    q = (query or "").lower()
    entities = []
    for name in ["aws", "azure", "gcp", "google cloud"]:
        # Build pattern without backslash escapes in f-string expression
        name_pattern = name.replace(" ", r"\s+")  # allow whitespace variations
        pattern = rf"\b{name_pattern}\b"
        if re.search(pattern, q):
            entities.append(name)
    return entities


def _missing_canonical_domains(entities: List[str], items: List[Dict]) -> List[str]:
    if not entities:
        return []
    urls = [(it.get("url") or "") for it in items]
    missing: List[str] = []
    for e in entities:
        domains = _ENTITY_DOMAINS.get(e, [])
        if not any(any(d in u for d in domains) for u in urls):
            if domains:
                missing.append(domains[0])  # pick primary domain for backfill
    return missing
