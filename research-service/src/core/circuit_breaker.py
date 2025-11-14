"""Circuit breaker for external service calls.

Implements the Circuit Breaker pattern to prevent cascading failures
by temporarily blocking calls to failing services.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable
import random


class CircuitState(Enum):
    """Circuit breaker states.

    CLOSED: Normal operation, calls pass through
    OPEN: Service failing, calls rejected immediately
    HALF_OPEN: Testing recovery, limited calls allowed
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Circuit breaker for fault tolerance.

    Prevents cascading failures by opening circuit after threshold failures,
    then periodically testing recovery with HALF_OPEN state.

    Example:
        >>> breaker = CircuitBreaker(failure_threshold=5, timeout=60.0)
        >>> result = await breaker.call(external_api_func, arg1, kwarg1="value")

    Attributes:
        failure_threshold: Number of failures before opening circuit
        timeout: Seconds before testing recovery (HALF_OPEN)
    """

    failure_threshold: int = 5
    timeout: float = 60.0  # Seconds

    state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    failure_count: int = field(default=0, init=False)
    last_failure_time: datetime | None = field(default=None, init=False)

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Function result if successful

        Raises:
            Exception: If circuit open or function fails

        Example:
            >>> breaker = CircuitBreaker(failure_threshold=3)
            >>> result = await breaker.call(api_client.search, "query")
        """
        # Check if should transition from OPEN to HALF_OPEN
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker open - service unavailable")

        try:
            # Call the function
            result = await func(*args, **kwargs)

            # Success - reset circuit
            self._on_success()
            return result

        except Exception as e:
            # Failure - increment count and possibly open circuit
            self._on_failure()
            raise e

    async def call_with_retries(
        self,
        func: Callable,
        *args: Any,
        retries: int = 3,
        backoff_base: float = 0.5,
        backoff_factor: float = 2.0,
        fallback: Callable[[], Any] | None = None,
        jitter: bool = True,
        **kwargs: Any,
    ) -> Any:
        """Execute function with circuit breaker, retries and optional fallback.

        This preserves the existing behavior of ``call`` while adding a minimal,
        non-breaking API for callers that want controlled retries and a fallback.

        Args:
            func: Async function to call
            *args: Positional args for func
            retries: Max retries on failure (default 3)
            backoff_base: Initial delay in seconds (default 0.5)
            backoff_factor: Exponential multiplier (default 2.0)
            fallback: Optional 0-arg callable to produce a fallback result
            jitter: Whether to add jitter to delays (default True)
            **kwargs: Keyword args for func

        Returns:
            Result of func or fallback result if provided when exhausted/open

        Raises:
            Exception: Last error if no fallback is provided
        """
        # Use the same OPEN/HALF_OPEN rules as call()
        delay = backoff_base
        attempts = retries + 1  # initial attempt + retries

        for attempt in range(attempts):
            # If circuit is OPEN, see if we can switch to HALF_OPEN or fail fast
            if self.state == CircuitState.OPEN and not self._should_attempt_reset():
                if fallback is not None:
                    return fallback()
                raise Exception("Circuit breaker open - service unavailable")

            if self.state == CircuitState.OPEN and self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except Exception as e:
                self._on_failure()
                is_last = attempt >= attempts - 1
                if is_last:
                    if fallback is not None:
                        return fallback()
                    raise e
                # Backoff before next retry
                await self._sleep(delay, jitter=jitter)
                delay *= backoff_factor

    async def _sleep(self, delay: float, jitter: bool = True) -> None:
        """Async sleep helper with optional jitter."""
        actual = delay * (1.0 + random.random()) if jitter else delay
        await asyncio.sleep(actual)

    def _on_success(self) -> None:
        """Handle successful call - reset state to CLOSED."""
        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        """Handle failed call - increment count and possibly OPEN circuit."""
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

    def _should_attempt_reset(self) -> bool:
        """Check if timeout elapsed to test recovery.

        Returns:
            True if enough time has passed to try HALF_OPEN state
        """
        if not self.last_failure_time:
            return True

        elapsed = datetime.utcnow() - self.last_failure_time
        return elapsed >= timedelta(seconds=self.timeout)
