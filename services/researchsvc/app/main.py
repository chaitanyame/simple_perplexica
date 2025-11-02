"""
Research Service - FastAPI application for AI-powered content generation.

This service uses CrewAI with multiple agents to research topics and generate
comprehensive blog posts. It integrates with OpenRouter for LLM capabilities
and SerperDev for web search.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.models import HealthResponse
from app.routers import generate

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger.info("Starting Research Service...")
    logger.info(f"OpenRouter Model: {settings.openrouter_model}")
    logger.info(f"Server: {settings.host}:{settings.port}")

    yield

    # Shutdown
    logger.info("Shutting down Research Service...")


# Create FastAPI application
app = FastAPI(
    title="Research Service",
    description="AI-powered content generation using multi-agent research system",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(generate.router, prefix="/api", tags=["content generation"])


@app.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    """
    return HealthResponse(status="ok", service="researchsvc", version="1.0.0")


@app.get("/health", response_model=HealthResponse)
async def health():
    """
    Detailed health check endpoint.
    """
    return HealthResponse(status="ok", service="researchsvc", version="1.0.0")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=True)
