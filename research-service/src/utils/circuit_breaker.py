"""Circuit breaker for preventing cascading failures."""

import time
import structlog
from enum import Enum
from typing import Optional

logger = structlog.get_logger()


class CircuitState(str, Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocking requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """
    Circuit breaker to prevent hammering failed services.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Service failed too many times, blocking requests
    - HALF_OPEN: After timeout, testing if service recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 300,
        name: str = "circuit_breaker"
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Consecutive failures before opening
            timeout: Seconds to wait before testing again (half-open)
            name: Circuit breaker name for logging
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.name = name

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

    def is_open(self) -> bool:
        """Check if circuit is open (blocking requests)."""

        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time and \
               (time.time() - self.last_failure_time) > self.timeout:
                # Transition to half-open (test recovery)
                self.state = CircuitState.HALF_OPEN
                logger.info(
                    "circuit_breaker_half_open",
                    name=self.name,
                    message="Testing service recovery"
                )
                return False

            return True

        return False

    def record_success(self):
        """Record successful request."""

        if self.state == CircuitState.HALF_OPEN:
            # Service recovered!
            logger.info(
                "circuit_breaker_closed",
                name=self.name,
                message="Service recovered"
            )

        self.failure_count = 0
        self.state = CircuitState.CLOSED

    def record_failure(self):
        """Record failed request."""

        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                "circuit_breaker_open",
                name=self.name,
                failures=self.failure_count,
                message=f"Circuit opened after {self.failure_count} failures"
            )
        else:
            logger.warning(
                "circuit_breaker_failure",
                name=self.name,
                failures=self.failure_count,
                threshold=self.failure_threshold
            )

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state
