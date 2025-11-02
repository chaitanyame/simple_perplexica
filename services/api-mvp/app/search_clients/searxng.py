import httpx
import os
from typing import List, Dict, Optional
import logging
import spacy
from functools import lru_cache
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
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
    params = {"q": query, "format": "json"}

    # Add time_range if query suggests recency
    # BUT: Skip time filtering for "trending" queries since trending pages are already time-filtered
    query_lower = query.lower()
    is_trending_query = any(
        term in query_lower
        for term in ["trending", "popular", "top repositories", "most starred"]
    )

    time_range = None if is_trending_query else _detect_recency_need(query)
    if time_range:
        params["time_range"] = time_range
        logger.info(
            f"SpaCy detected temporal intent: time_range={time_range} for query: {query}"
        )
    elif is_trending_query:
        logger.info(
            f"Detected trending query, skipping time_range filter to preserve trending pages: {query}"
        )

    if engines:
        params["engines"] = ",".join(engines)
    if language:
        params["language"] = language

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            # Normalize to a list of {title, url, pageContent}
            results = []
            for item in data.get("results", []):
                results.append(
                    {
                        "title": item.get("title") or item.get("source") or "",
                        "url": item.get("url", ""),
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
                    "time_range": time_range,
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
