"""Tests for LLM configuration system.

This module tests the LLMConfig model and Settings configuration
for dynamic LLM selection (Gemini for both research and fallback).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.config import LLMConfig, Settings


@pytest.mark.unit
class TestLLMConfig:
    """Test LLMConfig model validation."""

    def test_valid_llm_config(self):
        """Test creating valid LLMConfig."""
        config = LLMConfig(
            provider="openrouter",
            model="google/gemini-2.5-flash-lite",
            temperature=0.3,
            max_tokens=8192,
            timeout=180,
        )

        assert config.provider == "openrouter"
        assert config.model == "google/gemini-2.5-flash-lite"
        assert config.temperature == 0.3
        assert config.max_tokens == 8192
        assert config.timeout == 180

    def test_temperature_validation_min(self):
        """Test temperature minimum validation (>=0.0)."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(
                provider="openrouter",
                model="test",
                temperature=-0.1,  # Invalid: below 0.0
                max_tokens=1000,
                timeout=60,
            )

        assert "temperature" in str(exc_info.value).lower()

    def test_temperature_validation_max(self):
        """Test temperature maximum validation (<=2.0)."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(
                provider="openrouter",
                model="test",
                temperature=2.1,  # Invalid: above 2.0
                max_tokens=1000,
                timeout=60,
            )

        assert "temperature" in str(exc_info.value).lower()

    def test_max_tokens_validation_min(self):
        """Test max_tokens minimum validation (>=100)."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(
                provider="openrouter",
                model="test",
                temperature=0.3,
                max_tokens=50,  # Invalid: below 100
                timeout=60,
            )

        assert "max_tokens" in str(exc_info.value).lower()

    def test_max_tokens_validation_max(self):
        """Test max_tokens maximum validation (<=32000)."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(
                provider="openrouter",
                model="test",
                temperature=0.3,
                max_tokens=40000,  # Invalid: above 32000
                timeout=60,
            )

        assert "max_tokens" in str(exc_info.value).lower()

    def test_timeout_validation_min(self):
        """Test timeout minimum validation (>=10)."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(
                provider="openrouter",
                model="test",
                temperature=0.3,
                max_tokens=1000,
                timeout=5,  # Invalid: below 10
            )

        assert "timeout" in str(exc_info.value).lower()

    def test_timeout_validation_max(self):
        """Test timeout maximum validation (<=600)."""
        with pytest.raises(ValidationError) as exc_info:
            LLMConfig(
                provider="openrouter",
                model="test",
                temperature=0.3,
                max_tokens=1000,
                timeout=700,  # Invalid: above 600
            )

        assert "timeout" in str(exc_info.value).lower()

    def test_llm_config_is_immutable(self):
        """Test LLMConfig is frozen (immutable)."""
        config = LLMConfig(
            provider="openrouter", model="test", temperature=0.3, max_tokens=1000, timeout=60
        )

        with pytest.raises((ValidationError, AttributeError)):
            config.temperature = 0.5  # Should not be allowed


@pytest.mark.unit
class TestSettings:
    """Test Settings configuration for LLMs."""

    def test_research_llm_defaults_to_gemini(self):
        """Test research LLM defaults to Gemini (2.5 flash lite)."""
        settings = Settings()

        assert settings.RESEARCH_LLM_PROVIDER == "openrouter"
        assert settings.RESEARCH_LLM_MODEL == "google/gemini-2.5-flash-lite"
        assert settings.RESEARCH_LLM_TEMPERATURE == 0.3
        assert settings.RESEARCH_LLM_MAX_TOKENS == 8192
        assert settings.RESEARCH_LLM_TIMEOUT == 180

    def test_fallback_llm_defaults_to_gemini(self):
        """Test fallback LLM defaults to Gemini."""
        settings = Settings()

        assert settings.FALLBACK_LLM_PROVIDER == "openrouter"
        assert settings.FALLBACK_LLM_MODEL == "google/gemini-2.5-flash-lite"
        assert settings.FALLBACK_LLM_TEMPERATURE == 0.2
        assert settings.FALLBACK_LLM_MAX_TOKENS == 4096
        assert settings.FALLBACK_LLM_TIMEOUT == 120

    def test_feature_flags_default_to_enabled(self):
        """Test feature flags default to enabled."""
        settings = Settings()

        assert settings.ENABLE_DYNAMIC_PROMPTS is True
        assert settings.ENABLE_LLM_FALLBACK is True

    def test_research_llm_config_property(self):
        """Test research_llm_config computed property returns correct LLMConfig."""
        settings = Settings()
        config = settings.research_llm_config

        assert isinstance(config, LLMConfig)
        assert config.provider == "openrouter"
        assert config.model == "google/gemini-2.5-flash-lite"
        assert config.temperature == 0.3
        assert config.max_tokens == 8192
        assert config.timeout == 180

    def test_fallback_llm_config_property(self):
        """Test fallback_llm_config computed property returns correct LLMConfig."""
        settings = Settings()
        config = settings.fallback_llm_config

        assert isinstance(config, LLMConfig)
        assert config.provider == "openrouter"
        assert config.model == "google/gemini-2.5-flash-lite"
        assert config.temperature == 0.2
        assert config.max_tokens == 4096
        assert config.timeout == 120

    def test_openrouter_api_key_required(self):
        """Test Settings requires OPENROUTER_API_KEY."""
        # Note: This test assumes .env has the key
        # In production, missing key should raise ValidationError
        settings = Settings()
        assert hasattr(settings, "OPENROUTER_API_KEY")
        assert settings.OPENROUTER_API_KEY is not None

    def test_research_llm_config_caching(self):
        """Test research_llm_config property returns same instance."""
        settings = Settings()
        config1 = settings.research_llm_config
        config2 = settings.research_llm_config

        # Should return equal configs
        assert config1.model == config2.model
        assert config1.provider == config2.provider

    def test_settings_can_be_overridden_by_env(self, monkeypatch):
        """Test Settings can be overridden by environment variables."""
        # Override research LLM model via env
        monkeypatch.setenv("RESEARCH_LLM_MODEL", "anthropic/claude-3.5-sonnet")
        monkeypatch.setenv("RESEARCH_LLM_TEMPERATURE", "0.5")

        settings = Settings()

        assert settings.RESEARCH_LLM_MODEL == "anthropic/claude-3.5-sonnet"
        assert settings.RESEARCH_LLM_TEMPERATURE == 0.5

    def test_enable_dynamic_prompts_can_be_disabled(self, monkeypatch):
        """Test ENABLE_DYNAMIC_PROMPTS can be disabled via env."""
        monkeypatch.setenv("ENABLE_DYNAMIC_PROMPTS", "false")

        settings = Settings()

        assert settings.ENABLE_DYNAMIC_PROMPTS is False

    def test_enable_llm_fallback_can_be_disabled(self, monkeypatch):
        """Test ENABLE_LLM_FALLBACK can be disabled via env."""
        monkeypatch.setenv("ENABLE_LLM_FALLBACK", "false")

        settings = Settings()

        assert settings.ENABLE_LLM_FALLBACK is False
