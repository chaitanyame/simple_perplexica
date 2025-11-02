import os
import pytest


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
def test_validation_empty_query(client):
    resp = client.post("/api/search", json={"query": " ", "focusMode": "webSearch"})
    assert resp.status_code == 422


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
def test_writing_assistant_no_web_sources(client, monkeypatch):
    from app.routers import search as search_router

    # Ensure get_sources returns [] and does not trigger 502 for writingAssistant
    async def fake_get_sources(query, focus_mode):
        return []

    async def fake_synthesize_answer(
        query, sources, system, history=None, context_chars: int = 800
    ):
        return "Answer text"

    monkeypatch.setattr(search_router, "get_sources", fake_get_sources)
    monkeypatch.setattr(
        search_router.openrouter, "synthesize_answer", fake_synthesize_answer
    )

    resp = client.post(
        "/api/search", json={"query": "hello", "focusMode": "writingAssistant"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "Answer text"
    assert data["sources"] == []
