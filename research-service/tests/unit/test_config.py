"""Tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from src.core.config import Settings


def test_settings_with_defaults():
    """Test settings initialization with default values."""
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/dbname",
            "OPENROUTER_API_KEY": "test_openrouter_key",
            "LANGFUSE_PUBLIC_KEY": "test_public_key",
            "LANGFUSE_SECRET_KEY": "test_secret_key",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        # Required fields
        assert str(settings.DATABASE_URL) == "postgresql+asyncpg://user:pass@localhost/dbname"
        assert settings.OPENROUTER_API_KEY == "test_openrouter_key"
        assert settings.LANGFUSE_PUBLIC_KEY == "test_public_key"
        assert settings.LANGFUSE_SECRET_KEY == "test_secret_key"

        # Defaults
        assert str(settings.REDIS_URL) == "redis://localhost:6379/0"
        assert settings.OPENROUTER_BASE_URL == "https://openrouter.ai/api/v1"
        assert settings.LANGFUSE_HOST == "https://cloud.langfuse.com"
        assert settings.SEARXNG_BASE_URL == "http://localhost:8080"
        assert settings.SERPER_API_KEY is None


def test_settings_research_pipeline_defaults():
    """Test research pipeline configuration defaults."""
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/dbname",
            "OPENROUTER_API_KEY": "test_key",
            "LANGFUSE_PUBLIC_KEY": "test_public",
            "LANGFUSE_SECRET_KEY": "test_secret",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        assert settings.RESEARCH_MAX_ITERATIONS == 3
        assert settings.RESEARCH_CRAWL_DEPTH == 2
        assert settings.RESEARCH_MAX_PAGES_PER_URL == 5
        assert settings.RESEARCH_TIMEOUT_SECONDS == 300


def test_settings_search_mode_defaults():
    """Test search mode configuration defaults."""
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/dbname",
            "OPENROUTER_API_KEY": "test_key",
            "LANGFUSE_PUBLIC_KEY": "test_public",
            "LANGFUSE_SECRET_KEY": "test_secret",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        assert settings.SEARCH_MAX_QUERIES == 4
        assert settings.SEARCH_MAX_SOURCES == 20


def test_settings_research_mode_defaults():
    """Test research mode configuration defaults."""
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/dbname",
            "OPENROUTER_API_KEY": "test_key",
            "LANGFUSE_PUBLIC_KEY": "test_public",
            "LANGFUSE_SECRET_KEY": "test_secret",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        assert settings.RESEARCH_MAX_SOURCES == 80
        assert settings.RESEARCH_SECTION_SOURCES == 10


def test_settings_embedding_defaults():
    """Test embedding configuration defaults."""
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/dbname",
            "OPENROUTER_API_KEY": "test_key",
            "LANGFUSE_PUBLIC_KEY": "test_public",
            "LANGFUSE_SECRET_KEY": "test_secret",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        assert settings.EMBEDDING_MODEL == "sentence-transformers/all-MiniLM-L6-v2"
        assert settings.EMBEDDING_DIMENSION == 384


def test_settings_llm_models_defaults():
    """Test LLM model configuration defaults."""
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/dbname",
            "OPENROUTER_API_KEY": "test_key",
            "LANGFUSE_PUBLIC_KEY": "test_public",
            "LANGFUSE_SECRET_KEY": "test_secret",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        assert settings.LLM_MODEL == "anthropic/claude-3.5-sonnet"
        assert settings.PLANNING_MODEL == "anthropic/claude-3.5-sonnet"


def test_settings_api_defaults():
    """Test API configuration defaults."""
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/dbname",
            "OPENROUTER_API_KEY": "test_key",
            "LANGFUSE_PUBLIC_KEY": "test_public",
            "LANGFUSE_SECRET_KEY": "test_secret",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        assert settings.API_HOST == "0.0.0.0"
        assert settings.API_PORT == 8001
        assert settings.API_WORKERS == 4
        assert settings.API_RATE_LIMIT == "10/minute"


def test_settings_logging_defaults():
    """Test logging configuration defaults."""
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/dbname",
            "OPENROUTER_API_KEY": "test_key",
            "LANGFUSE_PUBLIC_KEY": "test_public",
            "LANGFUSE_SECRET_KEY": "test_secret",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        assert settings.LOG_LEVEL == "INFO"
        assert settings.LOG_FORMAT == "json"
        assert settings.DEBUG is False


def test_settings_custom_values():
    """Test settings with custom environment values."""
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql+asyncpg://custom:pass@custom-host:5433/custom_db",
            "REDIS_URL": "redis://custom-redis:6380/1",
            "OPENROUTER_API_KEY": "custom_openrouter",
            "LANGFUSE_PUBLIC_KEY": "custom_public",
            "LANGFUSE_SECRET_KEY": "custom_secret",
            "RESEARCH_MAX_ITERATIONS": "5",
            "SEARCH_MAX_QUERIES": "8",
            "EMBEDDING_DIMENSION": "768",
            "API_PORT": "9000",
            "LOG_LEVEL": "DEBUG",
            "DEBUG": "true",
        },
        clear=True,
    ):
        settings = Settings(_env_file=None)

        assert "custom-host" in str(settings.DATABASE_URL)
        assert "custom-redis" in str(settings.REDIS_URL)
        assert settings.OPENROUTER_API_KEY == "custom_openrouter"
        assert settings.RESEARCH_MAX_ITERATIONS == 5
        assert settings.SEARCH_MAX_QUERIES == 8
        assert settings.EMBEDDING_DIMENSION == 768
        assert settings.API_PORT == 9000
        assert settings.LOG_LEVEL == "DEBUG"
        assert settings.DEBUG is True


def test_settings_missing_required_field():
    """Test that missing required fields raise validation error."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(Exception):  # ValidationError from Pydantic
            Settings(_env_file=None)
