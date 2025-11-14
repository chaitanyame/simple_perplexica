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
        assert path.endswith("/search")
        assert params["q"] == "python"
        assert params["format"] == "json"
        return DummyResponse(
            status_code=200,
            json_data={
                "results": [
                    {"title": "Python", "url": "https://python.org", "content": "Official site"},
                    {"title": "Docs", "url": "https://docs.python.org", "content": "Documentation"},
                ]
            },
        )

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
async def test_searxng_client_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    client = SearxNGClient(base_url="http://example.com")

    async def fake_get(path: str, params: dict[str, Any], timeout: float):  # type: ignore[override]
        return DummyResponse(
            status_code=200,
            json_data={
                "results": [{"title": f"T{i}", "url": f"u{i}", "content": "c"} for i in range(20)]
            },
        )

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


# EOF
