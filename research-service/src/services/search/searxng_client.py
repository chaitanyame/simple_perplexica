"""SearxNG client abstraction.

Provides a typed, resilient interface to a local SearxNG instance.

Design goals:
    - Simple async `search()` API returning normalized dicts
    - Graceful handling of timeouts / connection errors (return [])
    - Optional categories parameter (comma separated)
    - Result limiting applied client-side
    - Minimal dependencies (httpx only)

Test alignment:
    - test_settings_has_searxng_base_url: relies on Settings
    - test_searxng_client_class_exists: class must be importable
    - test_searxng_client_search_basic: returns list w/ title,url,content
    - test_searxng_client_handles_empty_results: empty list
    - test_searxng_client_timeout: returns [] on timeout
    - test_searxng_client_non_200: returns [] on non-200
    - test_searxng_client_extracts_limit: caps length
    - test_searxng_client_passes_query_params: sends q & format=json
    - test_searxng_client_includes_optional_categories: categories param
    - test_searxng_client_handles_exception: returns [] on unexpected
"""

from __future__ import annotations

from typing import Any, Sequence

import httpx
import structlog

from ...core.circuit_breaker import CircuitBreaker
from ...core.config import settings

logger = structlog.get_logger(__name__)

_search_circuit_breaker: CircuitBreaker | None = None


def get_search_circuit_breaker() -> CircuitBreaker:
    """Get or create a circuit breaker for search clients.

    Reuse Perplexity CB thresholds for consistency until
    dedicated settings are introduced.
    """
    global _search_circuit_breaker
    if _search_circuit_breaker is None:
        _search_circuit_breaker = CircuitBreaker(
            failure_threshold=settings.PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD,
            timeout=float(settings.PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT),
        )
    return _search_circuit_breaker


class SearxNGClient:
    """Async client for SearxNG search endpoint.

    Args:
        base_url: Base URL to the SearxNG instance (e.g. http://localhost:8080)
        timeout: Per-request timeout in seconds (default 15.0)

    Example:
        >>> client = SearxNGClient(base_url="http://localhost:8080")
        >>> results = await client.search("python news", limit=5, categories=["news"], time_range="week")
        >>> assert results and "title" in results[0]

    Supported parameters (mapped directly to SearxNG API):
        - query (q)
        - categories (comma separated)
        - engines (comma separated)
        - language (language)
        - time_range (day|week|month|year)
        - safesearch (0|1|2)
        - pageno (for pagination)
    """

    def __init__(self, base_url: str, timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        # Fallback hosts we will attempt if primary fails (inside container vs host)
        self.fallback_hosts: list[str] = [
            self.base_url,
            "http://searxng:8080",  # common docker service name
            "http://localhost:8080",
        ]
        # Deduplicate while preserving order
        seen: set[str] = set()
        ordered: list[str] = []
        for h in self.fallback_hosts:
            if h not in seen:
                ordered.append(h)
                seen.add(h)
        self.fallback_hosts = ordered
        self.timeout = timeout
        # Client created per attempt to allow host switching
        self._client = httpx.AsyncClient(timeout=timeout)

    async def close(self) -> None:
        """Close underlying HTTP resources."""
        await self._client.aclose()

    async def _get(self, path: str, params: dict[str, Any], timeout: float) -> httpx.Response:
        """Internal GET wrapper (patched in tests)."""
        return await self._client.get(path, params=params, timeout=timeout)

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        categories: Sequence[str] | None = None,
        engines: Sequence[str] | None = None,
        language: str | None = None,
        time_range: str | None = None,
        safesearch: int = 1,
        pageno: int = 1,
    ) -> list[dict[str, Any]]:
        """Perform a SearxNG search.

        Args:
            query: Search query string
            limit: Maximum number of results to return (default 10)
            categories: Optional sequence of categories (e.g. ["news", "science"])

        Returns:
            List of normalized result dicts: {title,url,content}
        """
        params: dict[str, Any] = {"q": query, "format": "json"}
        if categories:
            params["categories"] = ",".join(categories)
        if engines:
            params["engines"] = ",".join(engines)
        if language:
            params["language"] = language
        if time_range:
            params["time_range"] = time_range
        if safesearch in (0, 1, 2):  # validate
            params["safesearch"] = safesearch
        if pageno > 1:
            params["pageno"] = pageno
        # image_proxy intentionally omitted (not needed yet)
        logger.info(
            "SearxNG query params built", params={k: v for k, v in params.items() if k != "q"}
        )

        async def _do_search() -> list[dict[str, Any]]:
            last_error: str | None = None
            response: httpx.Response | None = None
            for host in self.fallback_hosts:
                try:
                    response = await self._get(
                        f"{host}/search", params=params, timeout=self.timeout
                    )
                    if response.status_code == 200:
                        break  # success
                    else:
                        logger.warning(
                            "SearxNG non-200 on host", host=host, status=response.status_code
                        )
                except httpx.TimeoutException:
                    logger.warning("SearxNG timeout", host=host, query=query)
                    last_error = "timeout"
                except httpx.ConnectError as e:
                    logger.error("SearxNG connection error", host=host, error=str(e))
                    last_error = str(e)
                except Exception as e:  # Unexpected
                    logger.error("SearxNG unexpected error", host=host, error=str(e))
                    last_error = str(e)
            if response is None:
                logger.error("SearxNG all host attempts failed", error=last_error)
                return []

            if response.status_code != 200:
                # After all attempts still non-200
                logger.warning("SearxNG final non-200 status", status=response.status_code)
                return []

            try:
                data = response.json()
            except Exception as e:  # Malformed JSON
                logger.error("SearxNG JSON parse error", error=str(e))
                return []

            raw_results = data.get("results", [])
            if not isinstance(raw_results, list):
                logger.warning("SearxNG results not a list")
                return []

            normalized: list[dict[str, Any]] = []
            for item in raw_results:
                if not isinstance(item, dict):
                    continue
                normalized.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                    }
                )
                if len(normalized) >= limit:
                    break

            return normalized

        breaker = get_search_circuit_breaker()
        return await breaker.call_with_retries(
            _do_search,
            retries=3,
            backoff_base=0.5,
            backoff_factor=2.0,
            fallback=lambda: [],
        )


__all__ = ["SearxNGClient"]
