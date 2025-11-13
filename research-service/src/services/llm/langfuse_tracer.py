"""Langfuse tracing integration for LLM monitoring.

This module provides LangfuseTracer for tracking LLM interactions,
including generations, spans, token usage, and costs.

Features:
- Automatic trace management with context managers
- Generation tracking with token/cost metrics
- Span creation for sub-operations (retries, etc.)
- Error tracking
- Graceful degradation when Langfuse unavailable
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import structlog

from src.core.config import settings

logger = structlog.get_logger(__name__)


class LangfuseTracer:
    """Tracer for LLM interactions using Langfuse.

    Provides context management for traces, generation tracking,
    and span creation for monitoring LLM operations.

    Example:
        >>> tracer = LangfuseTracer()
        >>> with tracer.trace_context(name="search", session_id="123"):
        ...     tracer.track_generation(
        ...         name="decompose_query",
        ...         model="claude-3.5-sonnet",
        ...         input_messages=[{"role": "user", "content": "test"}],
        ...         output="response",
        ...         prompt_tokens=10,
        ...         completion_tokens=20,
        ...         total_tokens=30
        ...     )
    """

    def __init__(
        self,
        public_key: str | None = None,
        secret_key: str | None = None,
        host: str | None = None,
        enabled: bool = True,
    ) -> None:
        """Initialize Langfuse tracer.

        Args:
            public_key: Langfuse public API key (defaults to settings)
            secret_key: Langfuse secret API key (defaults to settings)
            host: Langfuse server URL (defaults to settings)
            enabled: Whether tracing is enabled (defaults to True)
        """
        self.enabled = enabled
        self.current_trace: Any = None
        self.langfuse_client: Any = None

        if not enabled:
            logger.info("Langfuse tracing disabled")
            return

        try:
            from langfuse import Langfuse

            self.langfuse_client = Langfuse(
                public_key=public_key or settings.LANGFUSE_PUBLIC_KEY,
                secret_key=secret_key or settings.LANGFUSE_SECRET_KEY,
                host=host or settings.LANGFUSE_BASE_URL,
            )
            logger.info("Langfuse tracer initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Langfuse client: {e}")
            self.enabled = False
            self.langfuse_client = None

    def create_trace(
        self,
        name: str,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Create a new trace.

        Args:
            name: Name of the trace
            session_id: Optional session ID
            user_id: Optional user ID
            metadata: Optional metadata dictionary

        Returns:
            Trace object or None if tracing disabled
        """
        if not self.enabled or not self.langfuse_client:
            return None

        try:
            self.current_trace = self.langfuse_client.trace(
                name=name,
                session_id=session_id,
                user_id=user_id,
                metadata=metadata or {},
            )
            logger.debug(f"Created trace: {name}")
            return self.current_trace
        except Exception as e:
            logger.warning(f"Failed to create trace: {e}")
            return None

    def end_trace(self) -> None:
        """End the current trace."""
        if not self.enabled or not self.current_trace:
            return

        try:
            self.current_trace.update()
            logger.debug("Ended trace")
        except Exception as e:
            logger.warning(f"Failed to end trace: {e}")
        finally:
            self.current_trace = None

    def track_generation(
        self,
        name: str,
        model: str,
        input_messages: list[dict[str, str]],
        output: str,
        prompt_tokens: int | None = None,
        completion_tokens: int | None = None,
        total_tokens: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Track an LLM generation.

        Args:
            name: Name of the generation
            model: Model name used
            input_messages: Input messages to the LLM
            output: Generated output
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            total_tokens: Total tokens used
            metadata: Optional metadata

        Returns:
            Generation object or None if no active trace
        """
        if not self.enabled or not self.current_trace:
            return None

        try:
            usage = {}
            if prompt_tokens is not None:
                usage["promptTokens"] = prompt_tokens
            if completion_tokens is not None:
                usage["completionTokens"] = completion_tokens
            if total_tokens is not None:
                usage["totalTokens"] = total_tokens

            generation = self.current_trace.generation(
                name=name,
                model=model,
                input=input_messages,
                output=output,
                usage=usage if usage else None,
                metadata=metadata or {},
            )
            logger.debug(f"Tracked generation: {name}")
            return generation
        except Exception as e:
            logger.warning(f"Failed to track generation: {e}")
            return None

    def create_span(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Create a span for a sub-operation.

        Args:
            name: Name of the span
            metadata: Optional metadata

        Returns:
            Span object or None if no active trace
        """
        if not self.enabled or not self.current_trace:
            return None

        try:
            span = self.current_trace.span(
                name=name,
                metadata=metadata or {},
            )
            logger.debug(f"Created span: {name}")
            return span
        except Exception as e:
            logger.warning(f"Failed to create span: {e}")
            return None

    def end_span(self, span: Any) -> None:
        """End a span.

        Args:
            span: Span object to end
        """
        if not self.enabled or span is None:
            return

        try:
            span.end()
            logger.debug("Ended span")
        except Exception as e:
            logger.warning(f"Failed to end span: {e}")

    def track_error(
        self,
        error: Exception,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Track an error in the current trace.

        Args:
            error: Exception that occurred
            metadata: Optional metadata
        """
        if not self.enabled or not self.current_trace:
            return

        try:
            self.current_trace.update(
                metadata={
                    **(metadata or {}),
                    "error": str(error),
                    "error_type": type(error).__name__,
                }
            )
            logger.debug(f"Tracked error: {error}")
        except Exception as e:
            logger.warning(f"Failed to track error: {e}")

    @contextmanager
    def trace_context(
        self,
        name: str,
        session_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Any:
        """Context manager for automatic trace management.

        Args:
            name: Name of the trace
            session_id: Optional session ID
            user_id: Optional user ID
            metadata: Optional metadata

        Yields:
            Trace object

        Example:
            >>> with tracer.trace_context(name="search") as trace:
            ...     # perform operations
            ...     tracer.track_generation(...)
        """
        trace = self.create_trace(
            name=name,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata,
        )
        try:
            yield trace
        finally:
            self.end_trace()

    def flush(self) -> None:
        """Flush pending traces to Langfuse."""
        if not self.enabled or not self.langfuse_client:
            return

        try:
            self.langfuse_client.flush()
            logger.debug("Flushed Langfuse traces")
        except Exception as e:
            logger.warning(f"Failed to flush traces: {e}")
