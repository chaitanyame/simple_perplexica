"""Tests for LLM client factory.

This module tests the LLMFactory class which creates and caches
LLM clients based on configuration.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.core.config import LLMConfig
from src.services.llm.llm_factory import LLMFactory, get_fallback_llm, get_research_llm


@pytest.mark.unit
class TestLLMFactory:
    """Test LLMFactory client creation and caching."""

    def setup_method(self):
        """Clear factory cache before each test."""
        LLMFactory.clear_cache()

    def teardown_method(self):
        """Clear factory cache after each test."""
        LLMFactory.clear_cache()

    def test_create_client_for_openrouter(self):
        """Test factory creates OpenRouterClient for openrouter provider."""
        config = LLMConfig(
            provider="openrouter",
            model="google/gemini-2.5-flash-lite",
            temperature=0.3,
            max_tokens=8192,
            timeout=180,
        )

        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client = LLMFactory.create_client(config)

            # Verify OpenRouterClient was instantiated
            mock_client.assert_called_once()
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["model"] == "google/gemini-2.5-flash-lite"
            assert call_kwargs["timeout"] == 180
            # Note: temperature and max_tokens are passed to chat() method, not constructor
            assert client is mock_instance

    def test_create_client_uses_correct_model(self):
        """Test factory passes correct model to client."""
        config = LLMConfig(
            provider="openrouter",
            model="google/gemini-2.5-flash-lite",
            temperature=0.2,
            max_tokens=4096,
            timeout=120,
        )

        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            LLMFactory.create_client(config)

            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["model"] == "google/gemini-2.5-flash-lite"

    def test_create_client_raises_error_for_unknown_provider(self):
        """Test factory raises ValueError for unknown provider."""
        config = LLMConfig(
            provider="unknown_provider",
            model="test-model",
            temperature=0.3,
            max_tokens=1000,
            timeout=60,
        )

        with pytest.raises(ValueError, match="Unknown provider"):
            LLMFactory.create_client(config)

    def test_factory_caches_clients(self):
        """Test factory caches clients for same config."""
        config = LLMConfig(
            provider="openrouter",
            model="google/gemini-2.5-flash-lite",
            temperature=0.3,
            max_tokens=8192,
            timeout=180,
        )

        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # First call - creates client
            client1 = LLMFactory.create_client(config)
            assert mock_client.call_count == 1

            # Second call - returns cached client
            client2 = LLMFactory.create_client(config)
            assert mock_client.call_count == 1  # Not called again

            # Should be same instance
            assert client1 is client2

    def test_factory_creates_different_clients_for_different_models(self):
        """Test factory creates separate clients for different models."""
        config1 = LLMConfig(
            provider="openrouter",
            model="google/gemini-2.5-flash-lite",
            temperature=0.3,
            max_tokens=8192,
            timeout=180,
        )

        config2 = LLMConfig(
            provider="openrouter",
            model="google/gemini-2.0-flash-lite-001",
            temperature=0.2,
            max_tokens=4096,
            timeout=120,
        )

        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_client.side_effect = [MagicMock(), MagicMock()]

            client1 = LLMFactory.create_client(config1)
            client2 = LLMFactory.create_client(config2)

            # Should create two separate clients
            assert mock_client.call_count == 2
            assert client1 is not client2

    def test_clear_cache_removes_all_clients(self):
        """Test clear_cache removes all cached clients."""
        config = LLMConfig(
            provider="openrouter",
            model="google/gemini-2.5-flash-lite",
            temperature=0.3,
            max_tokens=8192,
            timeout=180,
        )

        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_client.return_value = MagicMock()

            # Create client - should be cached
            LLMFactory.create_client(config)
            assert mock_client.call_count == 1

            # Clear cache
            LLMFactory.clear_cache()

            # Create again - should create new client
            LLMFactory.create_client(config)
            assert mock_client.call_count == 2

    def test_cache_key_includes_provider_and_model(self):
        """Test cache key is based on provider and model."""
        # Same model, same provider -> cached
        config1 = LLMConfig(
            provider="openrouter",
            model="google/gemini-2.5-flash-lite",
            temperature=0.3,
            max_tokens=8192,
            timeout=180,
        )

        # Same model, same provider, different params -> still cached
        config2 = LLMConfig(
            provider="openrouter",
            model="google/gemini-2.5-flash-lite",
            temperature=0.5,  # Different temperature
            max_tokens=4096,  # Different max_tokens
            timeout=120,  # Different timeout
        )

        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_client.return_value = MagicMock()

            client1 = LLMFactory.create_client(config1)
            client2 = LLMFactory.create_client(config2)

            # Should use cached client (same provider:model key)
            assert mock_client.call_count == 1
            assert client1 is client2


@pytest.mark.unit
class TestLLMFactoryHelpers:
    """Test helper functions for getting specific LLMs."""

    def setup_method(self):
        """Clear factory cache before each test."""
        LLMFactory.clear_cache()

    def teardown_method(self):
        """Clear factory cache after each test."""
        LLMFactory.clear_cache()

    def test_get_research_llm_returns_gemini_client(self):
        """Test get_research_llm returns Gemini client."""
        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client = get_research_llm()

            # Verify correct model and timeout (temperature/max_tokens go to chat())
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["model"] == "google/gemini-2.5-flash-lite"
            assert call_kwargs["timeout"] == 180

    def test_get_fallback_llm_returns_gemini_client(self):
        """Test get_fallback_llm returns Gemini client."""
        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client = get_fallback_llm()

            # Verify correct model and timeout (temperature/max_tokens go to chat())
            call_kwargs = mock_client.call_args.kwargs
            assert call_kwargs["model"] == "google/gemini-2.5-flash-lite"
            assert call_kwargs["timeout"] == 120

    def test_get_research_llm_caches_client(self):
        """Test get_research_llm returns cached client on multiple calls."""
        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client1 = get_research_llm()
            client2 = get_research_llm()

            # Should create client only once
            assert mock_client.call_count == 1
            assert client1 is client2

    def test_get_fallback_llm_caches_client(self):
        """Test get_fallback_llm returns cached client on multiple calls."""
        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            client1 = get_fallback_llm()
            client2 = get_fallback_llm()

            # Should create client only once
            assert mock_client.call_count == 1
            assert client1 is client2

    def test_research_and_fallback_are_different_clients(self):
        """Test research and fallback LLMs are separate clients."""
        with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
            mock_client.side_effect = [MagicMock(), MagicMock()]

            research_client = get_research_llm()
            fallback_client = get_fallback_llm()

            # Should create two separate clients
            assert mock_client.call_count == 2
            assert research_client is not fallback_client

    def test_helper_functions_use_settings(self):
        """Test helper functions read from settings."""
        with patch("src.services.llm.llm_factory.settings") as mock_settings:
            mock_research_config = LLMConfig(
                provider="openrouter",
                model="custom/research-model",
                temperature=0.4,
                max_tokens=16000,
                timeout=240,
            )
            mock_settings.research_llm_config = mock_research_config

            with patch("src.services.llm.llm_factory.OpenRouterClient") as mock_client:
                mock_client.return_value = MagicMock()

                get_research_llm()

                call_kwargs = mock_client.call_args.kwargs
                assert call_kwargs["model"] == "custom/research-model"
                assert call_kwargs["timeout"] == 240
                # Note: temperature and max_tokens are in config but passed to chat() method
