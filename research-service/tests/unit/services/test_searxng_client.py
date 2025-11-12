"""Unit tests for `SearxNGClient`.

These tests mock the internal HTTP layer to verify:
    - Settings exposes SEARXNG_BASE_URL
    - Basic search result normalization
    - Categories parameter mapping
    - Non-200 status handling
    - Timeout & unexpected exception handling
    - Limit enforcement
    - Query params include q & format=json
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from pydantic import BaseModel

from src.core.config import settings
from src.services.search.searxng_client import SearxNGClient


class DummyResponse(BaseModel):
    status_code: int
    json_data: dict[str, Any]

    def json(self) -> dict[str, Any]:  # mimic httpx.Response
        return self.json_data


@pytest.mark.unit
def test_settings_has_searxng_base_url() -> None:
    assert hasattr(settings, "SEARXNG_BASE_URL")
    assert settings.SEARXNG_BASE_URL.startswith("http")


@pytest.mark.unit
def test_searxng_client_class_exists() -> None:
    client = SearxNGClient(base_url="http://example.com")
    assert client.base_url == "http://example.com"


@pytest.mark.asyncio
async def test_searxng_client_search_basic(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SearxNGClient(base_url="http://example.com")

    async def fake_get(path: str, params: dict[str, Any], timeout: float):  # type: ignore[override]
        assert path == "/search"
        assert params["q"] == "python"
        assert params["format"] == "json"
        return DummyResponse(status_code=200, json_data={
            "results": [
                {"title": "Python", "url": "https://python.org", "content": "Official site"},
                {"title": "Docs", "url": "https://docs.python.org", "content": "Documentation"},
            ]
        })

    monkeypatch.setattr(client, "_get", fake_get)
    results = await client.search("python", limit=5)
    assert len(results) == 2
    assert {"title", "url", "content"}.issubset(results[0].keys())


@pytest.mark.asyncio
async def test_searxng_client_includes_optional_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SearxNGClient(base_url="http://example.com")

    async def fake_get(path: str, params: dict[str, Any], timeout: float):  # type: ignore[override]
        assert "categories" in params
        assert params["categories"] == "news,science"
        return DummyResponse(status_code=200, json_data={"results": []})

    monkeypatch.setattr(client, "_get", fake_get)
    results = await client.search("python", categories=["news", "science"])
    assert results == []


@pytest.mark.asyncio
async def test_searxng_client_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SearxNGClient(base_url="http://example.com")

    async def fake_get(path: str, params: dict[str, Any], timeout: float):  # type: ignore[override]
        return DummyResponse(status_code=503, json_data={"error": "service unavailable"})

    monkeypatch.setattr(client, "_get", fake_get)
    results = await client.search("python")
    assert results == []


@pytest.mark.asyncio
async def test_searxng_client_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SearxNGClient(base_url="http://example.com")

    async def fake_get(path: str, params: dict[str, Any], timeout: float):  # type: ignore[override]
        raise asyncio.TimeoutError()

    monkeypatch.setattr(client, "_get", fake_get)
    results = await client.search("python")
    assert results == []


@pytest.mark.asyncio
async def test_searxng_client_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SearxNGClient(base_url="http://example.com")

    async def fake_get(path: str, params: dict[str, Any], timeout: float):  # type: ignore[override]
        return DummyResponse(status_code=200, json_data={
            "results": [
                {"title": f"T{i}", "url": f"u{i}", "content": "c"} for i in range(20)
            ]
        })

    monkeypatch.setattr(client, "_get", fake_get)
    results = await client.search("python", limit=7)
    assert len(results) == 7


@pytest.mark.asyncio
async def test_searxng_client_unexpected_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SearxNGClient(base_url="http://example.com")

    async def fake_get(path: str, params: dict[str, Any], timeout: float):  # type: ignore[override]
        raise RuntimeError("boom")

    monkeypatch.setattr(client, "_get", fake_get)
    results = await client.search("python")
    assert results == []



@pytest.mark.asyncio
async def test_searxng_client_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    """Timeout should raise TimeoutError or return empty list depending on design."""
    if SearxNGClient is None:
        pytest.skip("SearxNGClient not implemented yet")

    async def mock_get(self, path: str, params: dict, timeout: float) -> httpx.Response:  # type: ignore
        raise httpx.TimeoutException("Request timed out")

    client = SearxNGClient(base_url="http://localhost:8080")
    monkeypatch.setattr(SearxNGClient, "_get", mock_get)

    results = await client.search("timeout", limit=5)
    assert results == []  # Graceful handling


@pytest.mark.asyncio
async def test_searxng_client_non_200(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-200 HTTP status should return empty list and not raise."""
    if SearxNGClient is None:
        pytest.skip("SearxNGClient not implemented yet")

    async def mock_get(self, path: str, params: dict, timeout: float) -> httpx.Response:  # type: ignore
        class DummyResponse:
            status_code = 500
            def json(self_inner):  # noqa: ANN001
                return {"error": "server"}
        return DummyResponse()  # type: ignore

    client = SearxNGClient(base_url="http://localhost:8080")
    monkeypatch.setattr(SearxNGClient, "_get", mock_get)

    results = await client.search("error", limit=5)
    assert results == []


@pytest.mark.asyncio
async def test_searxng_client_extracts_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Client should cap results to the requested limit."""
    if SearxNGClient is None:
        pytest.skip("SearxNGClient not implemented yet")

    mock_json = {
        "results": [
            {"title": f"Title {i}", "url": f"https://example.com/{i}", "content": "Snippet"}
            for i in range(10)
        ]
    }

    async def mock_get(self, path: str, params: dict, timeout: float) -> httpx.Response:  # type: ignore
        class DummyResponse:
            status_code = 200
            def json(self_inner):  # noqa: ANN001
                return mock_json
        return DummyResponse()  # type: ignore

    client = SearxNGClient(base_url="http://localhost:8080")
    monkeypatch.setattr(SearxNGClient, "_get", mock_get)

    results = await client.search("limit test", limit=5)
    assert len(results) == 5


@pytest.mark.asyncio
async def test_searxng_client_passes_query_params(monkeypatch: pytest.MonkeyPatch) -> None:
    """Client should pass q and format=json params to SearxNG."""
    if SearxNGClient is None:
        pytest.skip("SearxNGClient not implemented yet")

    captured_params = {}

    async def mock_get(self, path: str, params: dict, timeout: float) -> httpx.Response:  # type: ignore
        nonlocal captured_params
        captured_params = params
        class DummyResponse:
            status_code = 200
            def json(self_inner):  # noqa: ANN001
                return {"results": []}
        return DummyResponse()  # type: ignore

    client = SearxNGClient(base_url="http://localhost:8080")
    monkeypatch.setattr(SearxNGClient, "_get", mock_get)

    await client.search("param test", limit=5)
    assert captured_params.get("q") == "param test"
    assert captured_params.get("format") == "json"


@pytest.mark.asyncio
async def test_searxng_client_includes_optional_categories(monkeypatch: pytest.MonkeyPatch) -> None:
    """Client can include categories if provided."""
    if SearxNGClient is None:
        pytest.skip("SearxNGClient not implemented yet")

    captured_params = {}

    async def mock_get(self, path: str, params: dict, timeout: float) -> httpx.Response:  # type: ignore
        nonlocal captured_params
        captured_params = params
        class DummyResponse:
            status_code = 200
            def json(self_inner):  # noqa: ANN001
                return {"results": []}
        return DummyResponse()  # type: ignore

    client = SearxNGClient(base_url="http://localhost:8080")
    monkeypatch.setattr(SearxNGClient, "_get", mock_get)

    await client.search("cats", limit=5, categories=["news", "science"])
    assert captured_params.get("categories") == "news,science"


@pytest.mark.asyncio
async def test_searxng_client_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unexpected exception should result in empty list and not propagate."""
    if SearxNGClient is None:
        pytest.skip("SearxNGClient not implemented yet")

    async def mock_get(self, path: str, params: dict, timeout: float) -> httpx.Response:  # type: ignore
        raise RuntimeError("Unexpected")

    client = SearxNGClient(base_url="http://localhost:8080")
    monkeypatch.setattr(SearxNGClient, "_get", mock_get)

    results = await client.search("exception", limit=5)
    assert results == []

```