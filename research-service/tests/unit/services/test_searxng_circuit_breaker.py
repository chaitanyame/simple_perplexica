"""Unit tests for SearxNGClient circuit-breaker retries and fallback."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest


@pytest.mark.asyncio
async def test_searxng_timeouts_trigger_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.services.search.searxng_client import SearxNGClient, get_search_circuit_breaker

    client = SearxNGClient(base_url="http://example.com")

    # Speed up CB sleeps
    breaker = get_search_circuit_breaker()
    monkeypatch.setattr(breaker, "_sleep", AsyncMock())

    # Count how many GET attempts are made across retries and hosts
    call_counter = {"count": 0}

    async def always_timeout(url: str, params: dict[str, Any], timeout: float) -> httpx.Response:  # type: ignore[override]
        call_counter["count"] += 1
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(client._client, "get", always_timeout)

    results = await client.search("python", limit=5)
    # Fallback should return empty list
    assert results == []
    # Expect at least one attempt per host in a single pass
    assert call_counter["count"] == len(client.fallback_hosts)
