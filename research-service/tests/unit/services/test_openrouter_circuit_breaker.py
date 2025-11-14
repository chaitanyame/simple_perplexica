"""Unit tests for OpenRouterClient circuit-breaker retries and fallback."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_openrouter_fallback_on_persistent_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """When internal retry fails, CB should return fallback payload if enabled."""
    from src.services.llm.openrouter_client import OpenRouterClient, get_llm_circuit_breaker
    from src.core import config as cfg

    # Speed up: disable CB sleep
    breaker = get_llm_circuit_breaker()
    monkeypatch.setattr(breaker, "_sleep", AsyncMock())

    # Ensure fallback is enabled
    monkeypatch.setattr(cfg.settings, "ENABLE_LLM_FALLBACK", True, raising=False)

    # Patch AsyncOpenAI to avoid real network
    with patch("src.services.llm.openrouter_client.AsyncOpenAI", return_value=MagicMock()):
        client = OpenRouterClient(api_key="test-key")

        # Force internal retry path to raise (simulate persistent failure)
        monkeypatch.setattr(client, "_retry_with_backoff", AsyncMock(side_effect=Exception("err")))

        result = await client.chat(messages=[{"role": "user", "content": "hi"}], stream=False)
        assert isinstance(result, dict)
        assert result.get("finish_reason") == "fallback"
        assert result.get("role") == "assistant"


@pytest.mark.asyncio
async def test_openrouter_no_fallback_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """If fallback disabled, CB should re-raise the error after retries."""
    from src.services.llm.openrouter_client import OpenRouterClient, get_llm_circuit_breaker
    from src.core import config as cfg
    from src.services.llm.schemas import LLMClientError

    breaker = get_llm_circuit_breaker()
    monkeypatch.setattr(breaker, "_sleep", AsyncMock())
    monkeypatch.setattr(cfg.settings, "ENABLE_LLM_FALLBACK", False, raising=False)

    with patch("src.services.llm.openrouter_client.AsyncOpenAI", return_value=MagicMock()):
        client = OpenRouterClient(api_key="test-key")
        monkeypatch.setattr(client, "_retry_with_backoff", AsyncMock(side_effect=Exception("err")))

        with pytest.raises(LLMClientError):
            await client.chat(messages=[{"role": "user", "content": "hi"}], stream=False)
