"""
Alternative implementation using LLM for temporal intent detection.
This version uses OpenRouter instead of SpaCy, trading ~50ms latency for zero ML dependencies.

To use this instead of SpaCy:
1. Rename searxng.py to searxng_spacy.py
2. Rename this file to searxng.py
3. No Docker rebuild needed (no new dependencies)
"""

import httpx
import os
from typing import List, Dict, Optional
import logging

SEARXNG_URL = os.getenv("SEARXNG_URL", "http://searxng:8080")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
logger = logging.getLogger(__name__)


async def _detect_recency_via_llm(query: str) -> Optional[str]:
    """Use LLM to detect temporal intent in the query.

    Fast and accurate alternative to SpaCy that uses existing OpenRouter infrastructure.
    """
    if not query or not OPENROUTER_API_KEY:
        return None

    prompt = f"""Analyze this search query for temporal intent: "{query}"

Reply with ONLY one word:
- "day" if the query asks about today, yesterday, breaking news, or very recent events
- "week" if the query asks about this week or recent past week
- "month" if the query asks about this month or past month  
- "none" if the query is about historical events, general topics, or no time constraint

Query: {query}
Classification:"""

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "qwen/qwen-2.5-7b-instruct:free",  # Fast and free
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 10,
                    "temperature": 0.0,
                },
            )
            response.raise_for_status()
            result = response.json()
            classification = result["choices"][0]["message"]["content"].strip().lower()

            # Map response to time_range parameter
            if "day" in classification:
                return "d"
            elif "week" in classification:
                return "w"
            elif "month" in classification:
                return "m"
            else:
                return None

    except Exception as e:
        logger.warning(f"LLM recency detection failed: {e}, using fallback")
        return _detect_recency_fallback(query)


def _detect_recency_fallback(query: str) -> Optional[str]:
    """Fallback keyword matching when LLM fails"""
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
    """Search using SearxNG with intelligent temporal filtering via LLM"""
    if not query:
        return []

    # Detect if we need recent results using LLM
    time_range = await _detect_recency_via_llm(query)

    params = {
        "q": query,
        "format": "json",
    }

    if engines:
        params["engines"] = ",".join(engines)
    if language:
        params["language"] = language
    if time_range:
        params["time_range"] = time_range
        logger.info(
            f"LLM detected temporal intent: time_range={time_range} for query: {query}"
        )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(f"{SEARXNG_URL}/search", params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])

            sources = []
            for result in results:
                sources.append(
                    {
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "pageContent": result.get("content", ""),
                    }
                )
            return sources

    except Exception as e:
        logger.error(f"SearxNG search failed: {e}")
        return []
