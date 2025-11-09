"""Tests for Langfuse tracing integration.

Following TDD RED-GREEN-REFACTOR:
- RED: Write tests first (they should fail - module doesn't exist yet)
- GREEN: Implement minimal code to pass tests
- REFACTOR: Clean up while keeping tests green

Test Coverage:
- LangfuseTracer initialization
- Trace context management
- Generation tracking
- Span creation
- Token and cost tracking
- Error handling
- Integration with OpenRouter client
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.schemas import LLMClientError


class TestLangfuseTracerInitialization:
    """Test LangfuseTracer initialization."""

    def test_init_with_default_parameters(self) -> None:
        """Test LangfuseTracer initialization with default parameters."""
        tracer = LangfuseTracer()

        assert tracer.langfuse_client is not None
        assert tracer.enabled is True
        assert tracer.current_trace is None

    def test_init_with_disabled_tracing(self) -> None:
        """Test LangfuseTracer initialization with tracing disabled."""
        tracer = LangfuseTracer(enabled=False)

        assert tracer.langfuse_client is None
        assert tracer.enabled is False
        assert tracer.current_trace is None

    def test_init_with_custom_parameters(self) -> None:
        """Test LangfuseTracer initialization with custom parameters."""
        tracer = LangfuseTracer(
            public_key="test_public_key",
            secret_key="test_secret_key",
            host="https://custom.langfuse.com",
        )

        assert tracer.langfuse_client is not None
        assert tracer.enabled is True


class TestLangfuseTracerTraceManagement:
    """Test trace creation and management."""

    @pytest.fixture
    def tracer(self) -> LangfuseTracer:
        """Create a LangfuseTracer instance with mocked client."""
        with patch("langfuse.Langfuse") as mock_langfuse:
            mock_client = MagicMock()
            mock_langfuse.return_value = mock_client
            tracer = LangfuseTracer()
            tracer.langfuse_client = mock_client
            return tracer

    def test_create_trace(self, tracer: LangfuseTracer) -> None:
        """Test creating a new trace."""
        mock_trace = MagicMock()
        tracer.langfuse_client.trace.return_value = mock_trace

        trace = tracer.create_trace(
            name="test_search",
            session_id="session_123",
            user_id="user_456",
            metadata={"query": "test query"},
        )

        assert trace == mock_trace
        tracer.langfuse_client.trace.assert_called_once()
        assert tracer.current_trace == mock_trace

    def test_create_trace_when_disabled(self) -> None:
        """Test creating trace when tracing is disabled."""
        tracer = LangfuseTracer(enabled=False)

        trace = tracer.create_trace(name="test_search", session_id="session_123")

        assert trace is None
        assert tracer.current_trace is None

    def test_end_trace(self, tracer: LangfuseTracer) -> None:
        """Test ending a trace."""
        mock_trace = MagicMock()
        tracer.current_trace = mock_trace

        tracer.end_trace()

        mock_trace.update.assert_called_once()
        assert tracer.current_trace is None

    def test_end_trace_when_no_active_trace(self, tracer: LangfuseTracer) -> None:
        """Test ending trace when no active trace exists."""
        tracer.current_trace = None

        # Should not raise an error
        tracer.end_trace()

        assert tracer.current_trace is None


class TestLangfuseTracerGenerationTracking:
    """Test LLM generation tracking."""

    @pytest.fixture
    def tracer(self) -> LangfuseTracer:
        """Create a LangfuseTracer instance with mocked trace."""
        with patch("langfuse.Langfuse"):
            tracer = LangfuseTracer()
            mock_trace = MagicMock()
            tracer.current_trace = mock_trace
            return tracer

    def test_track_generation(self, tracer: LangfuseTracer) -> None:
        """Test tracking an LLM generation."""
        mock_generation = MagicMock()
        tracer.current_trace.generation.return_value = mock_generation

        generation = tracer.track_generation(
            name="chat_completion",
            model="claude-3.5-sonnet",
            input_messages=[{"role": "user", "content": "test"}],
            output="response text",
            metadata={"temperature": 0.7},
        )

        assert generation == mock_generation
        tracer.current_trace.generation.assert_called_once()

    def test_track_generation_with_token_usage(self, tracer: LangfuseTracer) -> None:
        """Test tracking generation with token usage."""
        mock_generation = MagicMock()
        tracer.current_trace.generation.return_value = mock_generation

        generation = tracer.track_generation(
            name="chat_completion",
            model="claude-3.5-sonnet",
            input_messages=[{"role": "user", "content": "test"}],
            output="response text",
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
        )

        assert generation == mock_generation
        call_kwargs = tracer.current_trace.generation.call_args[1]
        assert call_kwargs["usage"]["promptTokens"] == 10
        assert call_kwargs["usage"]["completionTokens"] == 20
        assert call_kwargs["usage"]["totalTokens"] == 30

    def test_track_generation_when_no_active_trace(self, tracer: LangfuseTracer) -> None:
        """Test tracking generation when no active trace exists."""
        tracer.current_trace = None

        generation = tracer.track_generation(
            name="chat_completion",
            model="claude-3.5-sonnet",
            input_messages=[{"role": "user", "content": "test"}],
            output="response text",
        )

        assert generation is None

    def test_track_generation_when_disabled(self) -> None:
        """Test tracking generation when tracing is disabled."""
        tracer = LangfuseTracer(enabled=False)

        generation = tracer.track_generation(
            name="chat_completion",
            model="claude-3.5-sonnet",
            input_messages=[{"role": "user", "content": "test"}],
            output="response text",
        )

        assert generation is None


class TestLangfuseTracerSpanTracking:
    """Test span creation for sub-operations."""

    @pytest.fixture
    def tracer(self) -> LangfuseTracer:
        """Create a LangfuseTracer instance with mocked trace."""
        with patch("langfuse.Langfuse"):
            tracer = LangfuseTracer()
            mock_trace = MagicMock()
            tracer.current_trace = mock_trace
            return tracer

    def test_create_span(self, tracer: LangfuseTracer) -> None:
        """Test creating a span for sub-operation."""
        mock_span = MagicMock()
        tracer.current_trace.span.return_value = mock_span

        span = tracer.create_span(name="retry_attempt", metadata={"attempt": 1, "delay": 2.0})

        assert span == mock_span
        tracer.current_trace.span.assert_called_once()

    def test_create_span_when_no_active_trace(self, tracer: LangfuseTracer) -> None:
        """Test creating span when no active trace exists."""
        tracer.current_trace = None

        span = tracer.create_span(name="retry_attempt")

        assert span is None

    def test_end_span(self, tracer: LangfuseTracer) -> None:
        """Test ending a span."""
        mock_span = MagicMock()

        tracer.end_span(mock_span)

        mock_span.end.assert_called_once()

    def test_end_span_with_none(self, tracer: LangfuseTracer) -> None:
        """Test ending span with None value."""
        # Should not raise an error
        tracer.end_span(None)


class TestLangfuseTracerContextManager:
    """Test context manager for automatic trace management."""

    @pytest.fixture
    def tracer(self) -> LangfuseTracer:
        """Create a LangfuseTracer instance."""
        with patch("langfuse.Langfuse"):
            return LangfuseTracer()

    def test_trace_context_manager(self, tracer: LangfuseTracer) -> None:
        """Test using trace as context manager."""
        mock_trace = MagicMock()
        tracer.langfuse_client.trace.return_value = mock_trace

        with tracer.trace_context(name="test_operation", session_id="session_123") as trace:
            assert trace == mock_trace
            assert tracer.current_trace == mock_trace

        # After exiting context, current_trace should be None
        assert tracer.current_trace is None

    def test_trace_context_manager_with_exception(self, tracer: LangfuseTracer) -> None:
        """Test trace context manager handles exceptions."""
        mock_trace = MagicMock()
        tracer.langfuse_client.trace.return_value = mock_trace

        with pytest.raises(ValueError):
            with tracer.trace_context(name="test_operation"):
                assert tracer.current_trace == mock_trace
                raise ValueError("Test error")

        # end_trace should still be called (current_trace cleared)
        assert tracer.current_trace is None


class TestLangfuseTracerErrorHandling:
    """Test error handling in tracer."""

    @pytest.fixture
    def tracer(self) -> LangfuseTracer:
        """Create a LangfuseTracer instance with mocked trace."""
        with patch("langfuse.Langfuse"):
            tracer = LangfuseTracer()
            mock_trace = MagicMock()
            tracer.current_trace = mock_trace
            return tracer

    def test_track_error(self, tracer: LangfuseTracer) -> None:
        """Test tracking an error."""
        error = LLMClientError("Test error")

        tracer.track_error(error, metadata={"context": "test"})

        # Trace should be updated with error information
        tracer.current_trace.update.assert_called()

    def test_track_error_when_no_active_trace(self, tracer: LangfuseTracer) -> None:
        """Test tracking error when no active trace exists."""
        tracer.current_trace = None
        error = LLMClientError("Test error")

        # Should not raise an error
        tracer.track_error(error)

    def test_langfuse_client_failure_doesnt_break_app(self) -> None:
        """Test that Langfuse client failures don't break the application."""
        with patch("langfuse.Langfuse") as mock_langfuse:
            mock_langfuse.side_effect = Exception("Langfuse connection failed")

            # Should not raise exception - tracing should be disabled gracefully
            tracer = LangfuseTracer()
            assert tracer.enabled is False
            assert tracer.langfuse_client is None


class TestLangfuseTracerFlush:
    """Test flushing pending traces."""

    @pytest.fixture
    def tracer(self) -> LangfuseTracer:
        """Create a LangfuseTracer instance with mocked client."""
        with patch("langfuse.Langfuse") as mock_langfuse:
            mock_client = MagicMock()
            mock_langfuse.return_value = mock_client
            tracer = LangfuseTracer()
            tracer.langfuse_client = mock_client
            return tracer

    def test_flush(self, tracer: LangfuseTracer) -> None:
        """Test flushing pending traces."""
        tracer.flush()

        tracer.langfuse_client.flush.assert_called_once()

    def test_flush_when_disabled(self) -> None:
        """Test flushing when tracing is disabled."""
        tracer = LangfuseTracer(enabled=False)

        # Should not raise an error
        tracer.flush()


class TestLangfuseTracerIntegration:
    """Test integration patterns with OpenRouter client."""

    @pytest.fixture
    def tracer(self) -> LangfuseTracer:
        """Create a LangfuseTracer instance."""
        with patch("langfuse.Langfuse"):
            return LangfuseTracer()

    def test_integration_pattern(self, tracer: LangfuseTracer) -> None:
        """Test typical integration pattern with LLM client."""
        with patch.object(tracer, "create_trace") as mock_create:
            with patch.object(tracer, "track_generation") as mock_generation:
                with patch.object(tracer, "end_trace") as mock_end:
                    mock_trace = MagicMock()
                    mock_create.return_value = mock_trace

                    # Simulate LLM call flow
                    with tracer.trace_context(name="search_query", session_id="session_123"):
                        # Track generation
                        tracer.track_generation(
                            name="decompose_query",
                            model="claude-3.5-sonnet",
                            input_messages=[{"role": "user", "content": "test"}],
                            output="sub-query 1, sub-query 2",
                            prompt_tokens=10,
                            completion_tokens=20,
                            total_tokens=30,
                        )

                    mock_create.assert_called_once()
                    mock_generation.assert_called_once()
                    mock_end.assert_called_once()
