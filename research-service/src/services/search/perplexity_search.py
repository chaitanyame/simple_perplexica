"""Standalone Perplexity search functions.

Provides simple interface for Perplexity AI searches without
requiring SearchAgent integration.
"""

from __future__ import annotations

import logging
from typing import Any

from ...core.config import settings
from ...core.circuit_breaker import CircuitBreaker
from .perplexity_client import PerplexityClient, PerplexityResponse, PerplexityError

logger = logging.getLogger(__name__)

# Global instances (initialized on first use)
_perplexity_client: PerplexityClient | None = None
_circuit_breaker: CircuitBreaker | None = None


def get_perplexity_client() -> PerplexityClient:
    """Get or create Perplexity client singleton.

    Returns:
        PerplexityClient instance

    Raises:
        ValueError: If PERPLEXITY_API_KEY not configured
    """
    global _perplexity_client

    if _perplexity_client is None:
        if not settings.PERPLEXITY_API_KEY:
            raise ValueError("PERPLEXITY_API_KEY not configured in .env")

        _perplexity_client = PerplexityClient(
            api_key=settings.PERPLEXITY_API_KEY, model=settings.PERPLEXITY_MODEL
        )
        logger.info(f"✅ Perplexity client initialized: {settings.PERPLEXITY_MODEL}")

    return _perplexity_client


def get_circuit_breaker() -> CircuitBreaker:
    """Get or create circuit breaker singleton.

    Returns:
        CircuitBreaker instance
    """
    global _circuit_breaker

    if _circuit_breaker is None:
        _circuit_breaker = CircuitBreaker(
            failure_threshold=settings.PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD,
            timeout=float(settings.PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT),
        )
        logger.info(
            f"✅ Circuit breaker initialized: "
            f"threshold={settings.PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD}, "
            f"timeout={settings.PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT}s"
        )

    return _circuit_breaker


async def perplexity_search(
    query: str,
    search_recency_filter: str = "month",
    search_domain_filter: list[str] | None = None,
    temperature: float = 0.2,
) -> dict[str, Any]:
    """Execute Perplexity AI search with circuit breaker protection.

    Args:
        query: Search query
        search_recency_filter: Recency filter (month, week, day, hour)
        search_domain_filter: Optional domain whitelist (e.g., ["arxiv.org"])
        temperature: Response creativity (0.0-1.0, default 0.2 for precision)

    Returns:
        Dict with:
            - content: Formatted text with [1], [2] citation markers
            - citations: List of citation dicts with index, url, mention_count
            - source: "perplexity"
            - model: Model used (e.g., "sonar-pro")

    Raises:
        PerplexityError: If search fails after retries
        ValueError: If API key not configured

    Example:
        >>> result = await perplexity_search("What are AI agents?")
        >>> print(result["content"])
        AI agents are autonomous software [1]. They perceive and act [2].
        >>> print(result["citations"])
        [{"index": 1, "url": "https://...", "mention_count": 1}, ...]
    """
    client = get_perplexity_client()
    breaker = get_circuit_breaker()

    try:
        logger.info(f"🔍 Perplexity search: {query[:50]}...")

        def _fallback() -> dict[str, Any]:
            # Minimal, non-breaking fallback payload
            return {
                "content": "Perplexity is temporarily unavailable. Returning no-op result.",
                "citations": [],
                "source": "perplexity-fallback",
                "model": settings.PERPLEXITY_MODEL,
                "ready_to_display": True,
                "query": query,
            }

        response: PerplexityResponse | dict[str, Any] = await breaker.call_with_retries(
            client.search,
            query=query,
            search_recency_filter=search_recency_filter,
            search_domain_filter=search_domain_filter,
            temperature=temperature,
            retries=3,
            backoff_base=0.5,
            backoff_factor=2.0,
            fallback=_fallback,
        )
        # Safe logging regardless of fallback or normal response
        if isinstance(response, dict):
            citations_count = len(response.get("citations", []))
            content_len = len(response.get("content", ""))
        else:
            citations_count = len(response.citations)
            content_len = len(response.content)

        logger.info(f"✅ Perplexity completed: {citations_count} citations, {content_len} chars")

        if isinstance(response, dict):
            # Fallback path already returns a dict in the expected format
            return response
        else:
            return {
                "content": response.content,
                "citations": [
                    {
                        "index": c.index,
                        "url": c.url,
                        "mention_count": c.mention_count,
                        "title": f"Source {c.index}",  # Perplexity doesn't provide titles
                    }
                    for c in response.citations
                ],
                "source": "perplexity",
                "model": response.model,
                "ready_to_display": True,  # No additional processing needed
                "query": query,
            }

    except Exception as e:
        logger.error(f"❌ Perplexity search failed: {e}")
        raise PerplexityError(f"Search failed: {e}") from e


async def perplexity_research_search(
    query: str, domain_filter: list[str] | None = None
) -> dict[str, Any]:
    """Execute research-focused Perplexity search.

    Optimized for academic/research queries with longer context.

    Args:
        query: Research query
        domain_filter: Optional domains (e.g., ["arxiv.org", "github.com"])

    Returns:
        Search result dict with content and citations
    """
    return await perplexity_search(
        query=query,
        search_recency_filter="month",  # Broader time range for research
        search_domain_filter=domain_filter,
        temperature=0.1,  # Lower temperature for precision
    )


async def perplexity_news_search(query: str) -> dict[str, Any]:
    """Execute news-focused Perplexity search.

    Optimized for current events and recent news.

    Args:
        query: News query

    Returns:
        Search result dict with recent content
    """
    return await perplexity_search(
        query=query,
        search_recency_filter="day",  # Recent news only
        temperature=0.2,
    )
