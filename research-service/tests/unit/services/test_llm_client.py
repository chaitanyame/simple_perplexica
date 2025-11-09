"""Tests for OpenRouter LLM client.

Test Driven Development (TDD) - RED Phase
These tests define the expected behavior before implementation.

Patterns inspired by:
- Alibaba-NLP/DeepResearch: Retry with exponential backoff, error handling
- bytedance/deer-flow: OpenAI-compatible client patterns, token management
"""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import httpx
import pytest
from openai import APIError, APITimeoutError, RateLimitError
from openai.types.chat import ChatCompletion, ChatCompletionChunk, ChatCompletionMessage
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_chunk import Choice as ChunkChoice
from openai.types.chat.chat_completion_chunk import ChoiceDelta
from openai.types.completion_usage import CompletionUsage


def _create_mock_request():
    """Create a mock request for OpenAI exceptions."""
    return httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def _create_mock_response(status_code: int = 500):
    """Create a mock response for OpenAI exceptions."""
    return httpx.Response(status_code, request=_create_mock_request())


def _create_api_error(message: str, status_code: int | None = None):
    """Create a properly initialized APIError."""
    request = _create_mock_request()
    body = {"error": {"message": message}}
    error = APIError(message, request=request, body=body)
    if status_code:
        error.status_code = status_code
    return error


def _create_rate_limit_error(message: str):
    """Create a properly initialized RateLimitError."""
    response = _create_mock_response(429)
    body = {"error": {"message": message}}
    return RateLimitError(message, response=response, body=body)


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    client = MagicMock()
    client.chat = MagicMock()
    client.chat.completions = MagicMock()
    return client


@pytest.fixture
def mock_chat_response():
    """Create a mock successful chat response."""
    return ChatCompletion(
        id="chatcmpl-test123",
        object="chat.completion",
        created=1234567890,
        model="anthropic/claude-3.5-sonnet",
        choices=[
            Choice(
                index=0,
                message=ChatCompletionMessage(role="assistant", content="Test response from LLM"),
                finish_reason="stop",
            )
        ],
        usage=CompletionUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
    )


@pytest.fixture
def mock_stream_chunks():
    """Create mock streaming response chunks."""
    return [
        ChatCompletionChunk(
            id="chatcmpl-test123",
            object="chat.completion.chunk",
            created=1234567890,
            model="anthropic/claude-3.5-sonnet",
            choices=[
                ChunkChoice(
                    index=0,
                    delta=ChoiceDelta(role="assistant", content="Test "),
                    finish_reason=None,
                )
            ],
        ),
        ChatCompletionChunk(
            id="chatcmpl-test123",
            object="chat.completion.chunk",
            created=1234567890,
            model="anthropic/claude-3.5-sonnet",
            choices=[
                ChunkChoice(index=0, delta=ChoiceDelta(content="response"), finish_reason=None)
            ],
        ),
        ChatCompletionChunk(
            id="chatcmpl-test123",
            object="chat.completion.chunk",
            created=1234567890,
            model="anthropic/claude-3.5-sonnet",
            choices=[ChunkChoice(index=0, delta=ChoiceDelta(content=""), finish_reason="stop")],
        ),
    ]


class TestOpenRouterClientInitialization:
    """Test OpenRouterClient initialization and configuration."""

    def test_client_initialization_with_defaults(self):
        """Test client initializes with default configuration from settings."""
        from src.services.llm.openrouter_client import OpenRouterClient

        client = OpenRouterClient()

        assert client.base_url == "https://openrouter.ai/api/v1"
        assert client.model == "anthropic/claude-3.5-sonnet"
        assert client.max_retries == 10
        assert client.timeout == 60.0

    def test_client_initialization_with_custom_params(self):
        """Test client initializes with custom parameters."""
        from src.services.llm.openrouter_client import OpenRouterClient

        client = OpenRouterClient(
            api_key="custom-key",
            model="anthropic/claude-3-opus",
            max_retries=5,
            timeout=120.0,
        )

        assert client.model == "anthropic/claude-3-opus"
        assert client.max_retries == 5
        assert client.timeout == 120.0

    def test_client_requires_api_key(self):
        """Test client raises error if API key is not provided."""
        from src.services.llm.openrouter_client import OpenRouterClient

        with patch("src.services.llm.openrouter_client.settings") as mock_settings:
            mock_settings.OPENROUTER_API_KEY = None

            with pytest.raises(ValueError, match="API key is required"):
                OpenRouterClient()


class TestOpenRouterClientChatCompletion:
    """Test non-streaming chat completion."""

    @pytest.mark.asyncio
    async def test_chat_success(self, mock_openai_client, mock_chat_response):
        """Test successful chat completion."""
        from src.services.llm.openrouter_client import OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key")
            messages = [{"role": "user", "content": "Hello"}]

            response = await client.chat(messages=messages, stream=False)

            assert response["content"] == "Test response from LLM"
            assert response["role"] == "assistant"
            assert response["usage"]["total_tokens"] == 30
            assert response["model"] == "anthropic/claude-3.5-sonnet"
            assert response["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_chat_with_system_message(self, mock_openai_client, mock_chat_response):
        """Test chat with system message."""
        from src.services.llm.openrouter_client import OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key")
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"},
            ]

            await client.chat(messages=messages, stream=False)

            # Verify system message was included
            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args[1]["messages"][0]["role"] == "system"
            assert call_args[1]["messages"][1]["role"] == "user"

    @pytest.mark.asyncio
    async def test_chat_with_custom_parameters(self, mock_openai_client, mock_chat_response):
        """Test chat with custom generation parameters."""
        from src.services.llm.openrouter_client import OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key")
            messages = [{"role": "user", "content": "Hello"}]

            await client.chat(
                messages=messages,
                stream=False,
                temperature=0.7,
                max_tokens=1000,
                top_p=0.9,
            )

            call_args = mock_openai_client.chat.completions.create.call_args
            assert call_args[1]["temperature"] == 0.7
            assert call_args[1]["max_tokens"] == 1000
            assert call_args[1]["top_p"] == 0.9


class TestOpenRouterClientStreaming:
    """Test streaming chat completion."""

    @pytest.mark.asyncio
    async def test_chat_streaming_success(self, mock_openai_client, mock_stream_chunks):
        """Test successful streaming chat completion."""
        from src.services.llm.openrouter_client import OpenRouterClient

        # Create async iterator for streaming
        async def mock_stream():
            for chunk in mock_stream_chunks:
                yield chunk

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key")
            messages = [{"role": "user", "content": "Hello"}]

            chunks = []
            stream_response = await client.chat(messages=messages, stream=True)
            async for chunk in stream_response:
                chunks.append(chunk)

            assert len(chunks) == 3
            assert chunks[0]["content"] == "Test "
            assert chunks[1]["content"] == "response"
            assert chunks[2]["finish_reason"] == "stop"

    @pytest.mark.asyncio
    async def test_chat_streaming_full_content(self, mock_openai_client, mock_stream_chunks):
        """Test streaming accumulates full content correctly."""
        from src.services.llm.openrouter_client import OpenRouterClient

        async def mock_stream():
            for chunk in mock_stream_chunks:
                yield chunk

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_stream())

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key")
            messages = [{"role": "user", "content": "Hello"}]

            full_content = ""
            stream_response = await client.chat(messages=messages, stream=True)
            async for chunk in stream_response:
                if chunk.get("content"):
                    full_content += chunk["content"]

            assert full_content == "Test response"


class TestOpenRouterClientErrorHandling:
    """Test error handling and recovery."""

    @pytest.mark.asyncio
    async def test_handles_api_error(self, mock_openai_client):
        """Test handling of API errors."""
        from src.services.llm.openrouter_client import LLMClientError, OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=_create_api_error("API Error occurred")
        )

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key", max_retries=0)
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(LLMClientError, match="Maximum.*retries"):
                await client.chat(messages=messages, stream=False)

    @pytest.mark.asyncio
    async def test_handles_timeout_error(self, mock_openai_client):
        """Test handling of timeout errors."""
        from src.services.llm.openrouter_client import LLMClientError, OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=APITimeoutError("Request timeout")
        )

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key", max_retries=0)
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(LLMClientError, match="Maximum.*retries.*timed out"):
                await client.chat(messages=messages, stream=False)

    @pytest.mark.asyncio
    async def test_handles_rate_limit_error(self, mock_openai_client):
        """Test handling of rate limit errors."""
        from src.services.llm.openrouter_client import LLMClientError, OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=_create_rate_limit_error("Rate limit exceeded")
        )

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key", max_retries=0)
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(LLMClientError, match="Maximum.*retries.*Rate limit"):
                await client.chat(messages=messages, stream=False)


class TestOpenRouterClientRetryLogic:
    """Test retry logic with exponential backoff.

    Pattern inspired by Alibaba-NLP/DeepResearch:
    - Exponential backoff: delay = min(delay * 2^n, max_delay) * jitter
    - Jitter: 1.0 + random.random() to avoid thundering herd
    - Max retries: 10 (configurable)
    - Max delay: 300 seconds
    """

    @pytest.mark.asyncio
    async def test_retries_on_transient_error(self, mock_openai_client, mock_chat_response):
        """Test client retries on transient errors."""
        from src.services.llm.openrouter_client import OpenRouterClient

        # Fail twice, then succeed
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[
                _create_api_error("Transient error"),
                _create_api_error("Transient error"),
                mock_chat_response,
            ]
        )

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            with patch("asyncio.sleep", new=AsyncMock()):  # Speed up tests
                client = OpenRouterClient(api_key="test-key", max_retries=5)
                messages = [{"role": "user", "content": "Hello"}]

                response = await client.chat(messages=messages, stream=False)

                assert response["content"] == "Test response from LLM"
                assert mock_openai_client.chat.completions.create.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_with_exponential_backoff(self, mock_openai_client):
        """Test exponential backoff pattern matches DeepResearch implementation."""
        from src.services.llm.openrouter_client import OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=_create_api_error("Always fails")
        )

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            with patch("asyncio.sleep", new=AsyncMock()) as mock_sleep:
                client = OpenRouterClient(api_key="test-key", max_retries=3)
                messages = [{"role": "user", "content": "Hello"}]

                with pytest.raises(Exception):
                    await client.chat(messages=messages, stream=False)

                # Verify exponential backoff was applied
                assert mock_sleep.call_count >= 3
                # Each sleep should be progressively longer (accounting for jitter)
                delays = [call[0][0] for call in mock_sleep.call_args_list]
                assert delays[1] > delays[0]  # Second delay > first delay

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self, mock_openai_client):
        """Test client stops after max retries."""
        from src.services.llm.openrouter_client import LLMClientError, OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=_create_api_error("Always fails")
        )

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            with patch("asyncio.sleep", new=AsyncMock()):
                client = OpenRouterClient(api_key="test-key", max_retries=2)
                messages = [{"role": "user", "content": "Hello"}]

                with pytest.raises(LLMClientError, match="Maximum.*retries"):
                    await client.chat(messages=messages, stream=False)

                assert (
                    mock_openai_client.chat.completions.create.call_count == 3
                )  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_no_retry_on_bad_request(self, mock_openai_client):
        """Test client doesn't retry on 400 Bad Request errors."""
        from src.services.llm.openrouter_client import LLMClientError, OpenRouterClient

        # Simulate 400 Bad Request
        error = _create_api_error("Bad request", status_code=400)
        mock_openai_client.chat.completions.create = AsyncMock(side_effect=error)

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key", max_retries=5)
            messages = [{"role": "user", "content": "Hello"}]

            with pytest.raises(LLMClientError):
                await client.chat(messages=messages, stream=False)

            # Should not retry on 400 errors
            assert mock_openai_client.chat.completions.create.call_count == 1


class TestOpenRouterClientTokenManagement:
    """Test token counting and usage tracking."""

    @pytest.mark.asyncio
    async def test_tracks_token_usage(self, mock_openai_client, mock_chat_response):
        """Test client tracks token usage from API response."""
        from src.services.llm.openrouter_client import OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key")
            messages = [{"role": "user", "content": "Hello"}]

            response = await client.chat(messages=messages, stream=False)

            assert "usage" in response
            assert response["usage"]["prompt_tokens"] == 10
            assert response["usage"]["completion_tokens"] == 20
            assert response["usage"]["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_estimates_tokens_for_messages(self):
        """Test client can estimate token count for messages."""
        from src.services.llm.openrouter_client import OpenRouterClient

        client = OpenRouterClient(api_key="test-key")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"},
        ]

        token_count = client.estimate_tokens(messages)

        # Should be reasonable estimate (not exact)
        assert token_count > 0
        assert token_count < 100  # Simple messages shouldn't exceed this


class TestOpenRouterClientLogging:
    """Test logging and observability."""

    @pytest.mark.asyncio
    async def test_logs_request_details(self, mock_openai_client, mock_chat_response, caplog):
        """Test client logs request details."""
        import logging

        from src.services.llm.openrouter_client import OpenRouterClient

        caplog.set_level(logging.INFO)
        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key")
            messages = [{"role": "user", "content": "Hello"}]

            await client.chat(messages=messages, stream=False)

            # Check log contains request info
            log_messages = [record.message for record in caplog.records]
            assert any("LLM request" in msg for msg in log_messages)

    @pytest.mark.asyncio
    async def test_logs_retry_attempts(self, mock_openai_client, mock_chat_response, caplog):
        """Test client logs retry attempts."""
        import logging

        from src.services.llm.openrouter_client import OpenRouterClient

        caplog.set_level(logging.WARNING)
        mock_openai_client.chat.completions.create = AsyncMock(
            side_effect=[_create_api_error("Transient"), mock_chat_response]
        )

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            with patch("asyncio.sleep", new=AsyncMock()):
                client = OpenRouterClient(api_key="test-key", max_retries=5)
                messages = [{"role": "user", "content": "Hello"}]

                await client.chat(messages=messages, stream=False)

                # Check log contains retry info
                log_messages = [record.message for record in caplog.records]
                assert any("Retry" in msg or "retry" in msg for msg in log_messages)


class TestOpenRouterClientLangfuseIntegration:
    """Test Langfuse tracing integration with OpenRouter client."""

    @pytest.mark.asyncio
    async def test_chat_with_langfuse_tracer(self, mock_openai_client, mock_chat_response):
        """Test that chat calls are tracked with Langfuse tracer."""
        from unittest.mock import MagicMock

        from src.services.llm.langfuse_tracer import LangfuseTracer
        from src.services.llm.openrouter_client import OpenRouterClient

        # Create mock tracer
        mock_tracer = MagicMock(spec=LangfuseTracer)
        mock_tracer.track_generation = MagicMock()

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            client = OpenRouterClient(api_key="test-key", tracer=mock_tracer)
            messages = [{"role": "user", "content": "Hello"}]

            await client.chat(messages=messages, stream=False)

            # Verify tracer.track_generation was called
            assert mock_tracer.track_generation.called
            call_kwargs = mock_tracer.track_generation.call_args[1]
            assert call_kwargs["name"] == "chat_completion"
            assert call_kwargs["model"] == "anthropic/claude-3.5-sonnet"
            assert call_kwargs["input_messages"] == messages
            assert call_kwargs["output"] == "Test response from LLM"
            assert call_kwargs["prompt_tokens"] == 10
            assert call_kwargs["completion_tokens"] == 20
            assert call_kwargs["total_tokens"] == 30

    @pytest.mark.asyncio
    async def test_chat_without_tracer(self, mock_openai_client, mock_chat_response):
        """Test that chat works without tracer (tracer is optional)."""
        from src.services.llm.openrouter_client import OpenRouterClient

        mock_openai_client.chat.completions.create = AsyncMock(return_value=mock_chat_response)

        with patch(
            "src.services.llm.openrouter_client.AsyncOpenAI", return_value=mock_openai_client
        ):
            # No tracer provided
            client = OpenRouterClient(api_key="test-key")
            messages = [{"role": "user", "content": "Hello"}]

            result = await client.chat(messages=messages, stream=False)

            # Should work fine without tracer
            assert result["content"] == "Test response from LLM"
            assert result["usage"]["total_tokens"] == 30
