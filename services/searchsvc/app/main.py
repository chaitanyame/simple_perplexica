from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded
from .routers import search, providers
from .logging_config import setup_logging, get_logger
from .middleware.correlation import CorrelationIdMiddleware
from .middleware.rate_limit import limiter, rate_limit_exceeded_handler
import os

# Setup structured logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
setup_logging(LOG_LEVEL)
logger = get_logger(__name__)

app = FastAPI(title="API-only MVP Web Search")

# Add rate limiting state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

# Add correlation ID middleware first (for request tracing)
app.add_middleware(CorrelationIdMiddleware)

# CORS configuration - use environment variable for allowed origins
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:8501,http://localhost:3000,http://localhost:3010",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # Specific domains only
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Specific methods
    allow_headers=["Content-Type", "Authorization", "X-Correlation-ID"],
    max_age=3600,  # Cache preflight requests for 1 hour
)

app.include_router(search.router, prefix="/api")
app.include_router(providers.router, prefix="/api")

logger.info(f"API-only MVP Web Search started with CORS origins: {ALLOWED_ORIGINS}")


@app.get("/")
async def root():
    return {"status": "ok"}
