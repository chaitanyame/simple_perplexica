"""
Rate limiting middleware using slowapi.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request, Response
from fastapi.responses import JSONResponse
import os


def get_rate_limit_key(request: Request) -> str:
    """
    Get the key for rate limiting.
    Uses X-Forwarded-For header if available (for proxy scenarios),
    otherwise falls back to remote address.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


# Create limiter instance with custom key function
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[os.getenv("RATE_LIMIT_DEFAULT", "100/hour")],
    storage_uri=os.getenv("RATE_LIMIT_STORAGE", "memory://"),
    # Optional: use Redis for distributed rate limiting
    # storage_uri="redis://localhost:6379",
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded
) -> Response:
    """Custom handler for rate limit exceeded errors."""
    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": f"Too many requests. Please try again later.",
            "retry_after": exc.detail,
        },
        headers={"Retry-After": str(exc.detail)},
    )
