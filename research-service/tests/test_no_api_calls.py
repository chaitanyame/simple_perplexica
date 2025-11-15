"""Verify that tests do not make real API calls to DeepSeek/OpenRouter."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
def test_openrouter_client_is_mocked():
    """Verify OpenRouterClient is mocked globally."""
    from src.services.llm.openrouter_client import OpenRouterClient

    # Try to create a client - should be mocked
    client = OpenRouterClient(api_key="test")

    # Verify it's a mock
    assert isinstance(client, MagicMock) or hasattr(client, "_mock_name"), (
        "OpenRouterClient is not mocked - real API calls possible!"
    )


@pytest.mark.unit
async def test_llm_factory_uses_mocked_clients():
    """Verify LLM factory returns mocked clients."""
    from src.services.llm.llm_factory import get_research_llm

    client = await get_research_llm()

    # Check that chat method exists and won't make real calls
    assert hasattr(client, "chat"), "Client missing chat method"

    # Try calling chat - should not make real API call
    result = await client.chat(messages=[{"role": "user", "content": "test"}], stream=False)

    # Should return mocked response
    assert result is not None
    assert isinstance(result, dict)


@pytest.mark.integration
def test_run_tests_bat_prevents_api_calls():
    """Verify run_tests.bat environment variables prevent real API calls."""
    # Check that test environment variables are set
    assert os.getenv("OPENROUTER_API_KEY") in ["test", None], (
        "Real API key detected in test environment!"
    )

    assert os.getenv("RESEARCH_LLM_MODEL") in ["test", None], (
        "Real LLM model configured in test environment!"
    )

    assert os.getenv("SYNTHESIS_LLM_MODEL") in ["test", None], (
        "Real synthesis model configured in test environment!"
    )


@pytest.mark.integration
async def test_config_uses_test_models():
    """Verify Settings uses test models during tests."""
    from src.core.config import settings

    # Check that we're using test configuration
    assert settings.OPENROUTER_API_KEY == "test", (
        f"Real API key in settings: {settings.OPENROUTER_API_KEY[:10]}..."
    )

    # Models should be test or free-tier
    print(f"RESEARCH_LLM_MODEL: {settings.RESEARCH_LLM_MODEL}")
    print(f"FALLBACK_LLM_MODEL: {settings.FALLBACK_LLM_MODEL}")

    # If models are configured, they should be test models
    if settings.RESEARCH_LLM_MODEL != "test":
        assert ":free" in settings.RESEARCH_LLM_MODEL.lower(), (
            f"Non-free model detected: {settings.RESEARCH_LLM_MODEL}"
        )


from unittest.mock import patch, MagicMock
import pytest


@pytest.mark.unit
def test_httpx_client_is_mocked():
    """Verify httpx client is mocked globally."""
    import httpx

    # Attempt to make a request - should fail if not mocked
    with pytest.raises(Exception):
        # This should not actually make a network call
        client = httpx.Client()
        response = client.get("https://openrouter.ai/api/v1/chat/completions")
        assert response.status_code == 200, "Real network call detected!"


@pytest.mark.unit
def test_openrouter_client_is_mocked():
    """Verify OpenRouterClient is mocked globally."""
    from src.services.llm.openrouter_client import OpenRouterClient

    # Try to create a client - should be mocked
    client = OpenRouterClient(api_key="test")

    # Verify it's a mock
    assert isinstance(client, MagicMock) or hasattr(client, "_mock_name"), (
        "OpenRouterClient is not mocked - real API calls possible!"
    )


@pytest.mark.unit
async def test_llm_factory_uses_mocked_clients():
    """Verify LLM factory returns mocked clients."""
    from src.services.llm.llm_factory import get_research_llm

    client = await get_research_llm()

    # Check that chat method exists and won't make real calls
    assert hasattr(client, "chat"), "Client missing chat method"

    # Try calling chat - should not make real API call
    result = await client.chat(messages=[{"role": "user", "content": "test"}], stream=False)

    # Should return mocked response
    assert result is not None
    assert isinstance(result, dict)


@pytest.mark.unit
async def test_no_network_calls_in_search_agent():
    """Verify SearchAgent doesn't make network calls during tests."""
    from src.agents.search_agent import SearchAgent, SearchAgentDeps
    from unittest.mock import AsyncMock, MagicMock

    with patch("httpx.AsyncClient.post") as mock_post:
        # Setup mocked dependencies
        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = AsyncMock()
        deps.llm_client.chat = AsyncMock(
            return_value={"choices": [{"message": {"content": "Mocked response"}}]}
        )
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = AsyncMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = AsyncMock()

        # Create agent
        agent = SearchAgent(deps=deps)

        # Verify mock_post was never called with OpenRouter URL
        mock_post.assert_not_called()


@pytest.mark.integration
def test_run_tests_bat_prevents_api_calls():
    """Verify run_tests.bat environment variables prevent real API calls."""
    import os

    # Check that test environment variables are set
    assert os.getenv("OPENROUTER_API_KEY") in ["test", None], (
        "Real API key detected in test environment!"
    )

    assert os.getenv("RESEARCH_LLM_MODEL") in ["test", None], (
        "Real LLM model configured in test environment!"
    )

    assert os.getenv("SYNTHESIS_LLM_MODEL") in ["test", None], (
        "Real synthesis model configured in test environment!"
    )


@pytest.mark.integration
async def test_config_uses_test_models():
    """Verify Settings uses test models during tests."""
    from src.core.config import settings

    # Check that we're using test configuration
    assert settings.OPENROUTER_API_KEY == "test", (
        f"Real API key in settings: {settings.OPENROUTER_API_KEY[:10]}..."
    )

    # Models should be test or free-tier
    print(f"RESEARCH_LLM_MODEL: {settings.RESEARCH_LLM_MODEL}")
    print(f"FALLBACK_LLM_MODEL: {settings.FALLBACK_LLM_MODEL}")

    # If models are configured, they should be test models
    if settings.RESEARCH_LLM_MODEL != "test":
        assert ":free" in settings.RESEARCH_LLM_MODEL.lower(), (
            f"Non-free model detected: {settings.RESEARCH_LLM_MODEL}"
        )
