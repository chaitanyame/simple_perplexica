"""
Correlation ID middleware for request tracing.
"""

import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add correlation ID to all requests for distributed tracing.

    - Extracts correlation ID from X-Correlation-ID header if present
    - Generates new UUID if not present
    - Adds correlation ID to response headers
    - Injects correlation ID into all log records for the request
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state for access in route handlers
        request.state.correlation_id = correlation_id

        # Create a log filter to inject correlation ID into all logs
        log_filter = CorrelationIdFilter(correlation_id)

        # Add filter to root logger
        root_logger = logging.getLogger()
        root_logger.addFilter(log_filter)

        try:
            # Log request start
            logger.info(
                f"Request started",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "query_params": str(request.query_params),
                    "client_host": request.client.host if request.client else None,
                    "correlation_id": correlation_id,
                },
            )

            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers["X-Correlation-ID"] = correlation_id

            # Log request completion
            logger.info(
                f"Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "correlation_id": correlation_id,
                },
            )

            return response

        except Exception as e:
            # Log error with correlation ID
            logger.error(
                f"Request failed: {str(e)}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "correlation_id": correlation_id,
                },
                exc_info=True,
            )
            raise

        finally:
            # Remove filter
            root_logger.removeFilter(log_filter)


class CorrelationIdFilter(logging.Filter):
    """Logging filter to inject correlation ID into all log records."""

    def __init__(self, correlation_id: str):
        super().__init__()
        self.correlation_id = correlation_id

    def filter(self, record):
        record.correlation_id = self.correlation_id
        return True
