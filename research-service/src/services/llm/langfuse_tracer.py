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
        self._host: str | None = None

        if not enabled:
            logger.info("Langfuse tracing disabled")
            return

        try:
            from langfuse import Langfuse

            eff_public = (public_key or settings.LANGFUSE_PUBLIC_KEY or "").strip()
            eff_secret = (secret_key or settings.LANGFUSE_SECRET_KEY or "").strip()
            eff_host = (host or settings.LANGFUSE_BASE_URL or "").strip()

            if not eff_public or not eff_secret:
                # Missing credentials: disable tracing explicitly for clarity
                logger.warning(
                    "Langfuse disabled: missing credentials",
                    has_public=bool(eff_public),
                    has_secret=bool(eff_secret),
                    host=eff_host,
                )
                self.enabled = False
                self.langfuse_client = None
                return

            self.langfuse_client = Langfuse(
                public_key=eff_public,
                secret_key=eff_secret,
                host=eff_host,
            )
            self._host = eff_host or None
            logger.info(
                "Langfuse tracer initialized",
                host=eff_host,
                has_public=True,
                has_secret=True,
            )
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

    def get_trace_id(self, trace: Any | None = None) -> str | None:
        """Return the current trace id (if available).

        Args:
            trace: Optional explicit trace object (as returned by trace_context)

        Returns:
            Trace id string or None
        """
        try:
            t = trace or self.current_trace
            if t is None:
                return None
            # Common attribute name in Langfuse client
            tid = getattr(t, "id", None)
            if tid is None:
                return None
            return str(tid)
        except Exception:
            return None

    def get_trace_url(self, trace: Any | None = None) -> str | None:
        """Return a URL to view the trace in Langfuse (best-effort).

        Tries client helper if available, otherwise constructs a fallback URL
        using configured host and the trace id.
        """
        try:
            t = trace or self.current_trace
            if t is None:
                return None
            tid = self.get_trace_id(t)
            if not tid:
                return None
            # Prefer client helper if present
            if self.langfuse_client and hasattr(self.langfuse_client, "get_trace_url"):
                try:
                    return self.langfuse_client.get_trace_url(tid)  # type: ignore[attr-defined]
                except Exception:
                    pass
            if self._host:
                base = self._host.rstrip("/")
                # Fallback path (may vary by Langfuse version)
                return f"{base}/traces/{tid}"
            return None
        except Exception:
            return None

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
