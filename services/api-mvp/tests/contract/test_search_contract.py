import os
import pytest


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
def test_search_requires_query_and_focus(client):
    resp = client.post("/api/search", json={})
    assert resp.status_code == 422


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
def test_search_success_shape(client, monkeypatch):
    # Mock upstreams to avoid network
    from app.routers import search as search_router

    async def fake_get_sources(query, focus_mode):
        return [
            {
                "title": "Example",
                "url": "https://example.com",
                "pageContent": "Lorem ipsum",
            }
        ]

    async def fake_synthesize_answer(
        query, sources, system, history=None, context_chars: int = 800
    ):
        return "Answer text"

    monkeypatch.setattr(search_router, "get_sources", fake_get_sources)
    monkeypatch.setattr(
        search_router.openrouter, "synthesize_answer", fake_synthesize_answer
    )

    payload = {"query": "hello", "focusMode": "webSearch"}
    resp = client.post("/api/search", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "message" in data and isinstance(data["message"], str)
    assert "sources" in data and isinstance(data["sources"], list)
    assert data["sources"] and "title" in data["sources"][0]
