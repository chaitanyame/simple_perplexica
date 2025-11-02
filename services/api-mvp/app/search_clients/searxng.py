import httpx
import os
from typing import List, Dict, Optional
import logging
import spacy
from functools import lru_cache

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
        'd' for day (today/yesterday), 'w' for week, 'm' for month, or None
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
                return "d"
            # Week-level
            if any(term in text_lower for term in ["this week", "week", "weekly"]):
                return "w"
            # Month-level
            if any(term in text_lower for term in ["this month", "month", "monthly"]):
                return "m"

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
                return "d"  # Latest news/breaking updates → day filter

    return None


def _detect_recency_fallback(query: str) -> Optional[str]:
    """Fallback keyword matching when SpaCy is unavailable"""
    ql = query.lower()

    # Day-level recency
    day_terms = ["today", "yesterday", "breaking", "just now", "tonight", "latest"]
    if any(term in ql for term in day_terms):
        return "d"

    # Week-level recency
    week_terms = ["this week", "past week", "last week", "recent"]
    if any(term in ql for term in week_terms):
        return "w"

    # Month-level recency
    month_terms = ["this month", "past month", "last month"]
    if any(term in ql for term in month_terms):
        return "m"

    if "current" in ql or "now" in ql:
        return "d"

    return None


async def search(
    query: str,
    engines: Optional[List[str]] = None,
    language: Optional[str] = None,
) -> List[Dict]:
    """Search via SearxNG with automatic time-range filtering for recency queries."""
    url = f"{SEARXNG_URL}/search"
    params = {"q": query, "format": "json"}

    # Add time_range if query suggests recency
    time_range = _detect_recency_need(query)
    if time_range:
        params["time_range"] = time_range
        logger.info(
            f"SpaCy detected temporal intent: time_range={time_range} for query: {query}"
        )

    if engines:
        params["engines"] = ",".join(engines)
    if language:
        params["language"] = language
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
        return results
