"""Integration tests for LLM Factory.

Tests that factory works with real configuration and creates actual clients.
"""

from __future__ import annotations

import pytest

from src.services.llm import LLMFactory, get_fallback_llm, get_research_llm
from src.services.llm.openrouter_client import OpenRouterClient


@pytest.mark.integration
class TestLLMFactoryIntegration:
    """Integration tests for LLM factory with real config."""

    def setup_method(self):
        """Clear cache before each test."""
        LLMFactory.clear_cache()

    def teardown_method(self):
        """Clear cache after each test."""
        LLMFactory.clear_cache()

    def test_get_research_llm_creates_real_client(self):
        """Test get_research_llm creates actual OpenRouterClient."""
        client = get_research_llm()

        # Should be OpenRouterClient instance
        assert isinstance(client, OpenRouterClient)

        # Should use Gemini model
        assert "gemini" in client.model.lower()

    def test_get_fallback_llm_creates_real_client(self):
        """Test get_fallback_llm creates actual OpenRouterClient."""
        client = get_fallback_llm()

        # Should be OpenRouterClient instance
        assert isinstance(client, OpenRouterClient)

        # Should use Gemini model
        assert "gemini" in client.model.lower()

    def test_clients_are_cached(self):
        """Test that clients are cached on repeated calls."""
        # Get research client twice
        client1 = get_research_llm()
        client2 = get_research_llm()

        # Should be same instance
        assert client1 is client2

        # Get fallback client twice
        fallback1 = get_fallback_llm()
        fallback2 = get_fallback_llm()

        # Should be same instance
        assert fallback1 is fallback2

        # Research and fallback should be different
        assert client1 is not fallback1

    def test_clear_cache_works(self):
        """Test that clearing cache creates new clients."""
        # Get client
        client1 = get_research_llm()

        # Clear cache
        LLMFactory.clear_cache()

        # Get client again
        client2 = get_research_llm()

        # Should be different instances
        assert client1 is not client2

    def test_research_client_has_correct_config(self):
        """Test research client uses correct configuration."""
        client = get_research_llm()

        # Verify model and timeout
        assert client.model == "google/gemini-2.5-flash-lite"
        assert client.timeout == 180  # Research timeout

    def test_fallback_client_has_correct_config(self):
        """Test fallback client uses correct configuration."""
        client = get_fallback_llm()

        # Verify model and timeout
        assert client.model == "google/gemini-2.5-flash-lite"
        assert client.timeout == 120  # Fallback timeout
