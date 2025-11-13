"""Configuration management for research service."""

from pydantic import Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database Configuration
    DATABASE_URL: PostgresDsn = Field(
        ..., description="PostgreSQL connection URL with asyncpg driver"
    )

    # Redis Configuration
    REDIS_URL: RedisDsn = Field(
        default=RedisDsn("redis://localhost:6379/0"), description="Redis connection URL"
    )

    # OpenRouter (LLM)
    OPENROUTER_API_KEY: str = Field(..., description="OpenRouter API key")
    OPENROUTER_BASE_URL: str = Field(
        default="https://openrouter.ai/api/v1", description="OpenRouter API base URL"
    )

    # Langfuse (Monitoring)
    LANGFUSE_PUBLIC_KEY: str = Field(..., description="Langfuse public key")
    LANGFUSE_SECRET_KEY: str = Field(..., description="Langfuse secret key")
    LANGFUSE_HOST: str = Field(
        default="https://cloud.langfuse.com", description="Langfuse host URL"
    )

    # Search Services
    SEARXNG_BASE_URL: str = Field(
        default="http://localhost:8080", description="SearxNG instance URL"
    )
    SEARXNG_DEFAULT_CATEGORIES: list[str] = Field(
        default_factory=lambda: ["general", "news"],
        description="Default SearxNG categories (comma separated when sent)",
    )
    SEARXNG_DEFAULT_ENGINES: list[str] = Field(
        default_factory=lambda: ["google", "bing", "duckduckgo"],
        description="Optional default engines (comma separated when sent)",
    )
    SEARXNG_SAFESEARCH: int = Field(
        default=1, ge=0, le=2, description="SearxNG safesearch level: 0=off,1=moderate,2=strict"
    )
    SERPER_API_KEY: str | None = Field(default=None, description="SerperDev API key (optional)")

    # Perplexity AI (Fallback Search)
    PERPLEXITY_API_KEY: str | None = Field(
        default=None, description="Perplexity API key (optional, for fallback search)"
    )
    PERPLEXITY_MODEL: str = Field(
        default="sonar-pro", description="Perplexity model to use (sonar-pro for best research)"
    )
    PERPLEXITY_TIMEOUT: int = Field(
        default=30, ge=5, le=300, description="Perplexity request timeout (seconds)"
    )
    PERPLEXITY_SEARCH_CONTEXT_SIZE: str = Field(
        default="low", description="Perplexity search context size: low, medium, high"
    )
    PERPLEXITY_MAX_RETRIES: int = Field(
        default=2, ge=0, le=5, description="Max retry attempts for Perplexity API"
    )
    PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD: int = Field(
        default=5, ge=1, le=20, description="Failures before circuit breaker opens"
    )
    PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT: int = Field(
        default=300, ge=60, le=3600, description="Seconds before circuit breaker retry"
    )

    # Search Fallback Configuration
    ENABLE_SEARCH_FALLBACK: bool = Field(
        default=True, description="Enable 3-tier search fallback cascade"
    )
    SEARXNG_MIN_RESULTS_THRESHOLD: int = Field(
        default=3, ge=1, le=10, description="Min SearxNG results before fallback to SerperDev"
    )
    SERPERDEV_MIN_RESULTS_THRESHOLD: int = Field(
        default=3, ge=1, le=10, description="Min SerperDev results before fallback to Perplexity"
    )

    # Research Pipeline Settings
    RESEARCH_MAX_ITERATIONS: int = Field(
        default=3, description="Maximum refinement iterations for research mode"
    )
    RESEARCH_CRAWL_DEPTH: int = Field(default=2, description="Maximum depth for URL crawling")
    RESEARCH_MAX_PAGES_PER_URL: int = Field(
        default=5, description="Maximum pages to crawl per starting URL"
    )
    RESEARCH_TIMEOUT_SECONDS: int = Field(
        default=300, description="Maximum time for research pipeline (seconds)"
    )

    # Search Mode Settings
    SEARCH_MAX_QUERIES: int = Field(default=4, description="Maximum sub-queries in search mode")
    SEARCH_MAX_SOURCES: int = Field(
        default=20, description="Maximum sources for search mode synthesis"
    )

    # Research Mode Settings
    RESEARCH_MAX_SOURCES: int = Field(
        default=80, description="Maximum sources for research mode synthesis"
    )
    RESEARCH_SECTION_SOURCES: int = Field(default=10, description="Sources per report section")

    # Embedding Settings
    EMBEDDING_MODEL: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", description="Local embedding model name"
    )
    EMBEDDING_DIMENSION: int = Field(default=384, description="Embedding vector dimension")
    
    # Reranking Settings
    RERANKER_MODEL: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2",
        description="Cross-encoder model for semantic reranking"
    )
    ENABLE_RERANKING: bool = Field(
        default=True,
        description="Enable semantic reranking with cross-encoder"
    )
    RERANK_WEIGHT: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for semantic score in final ranking (0.0-1.0)"
    )

    # LLM Models
    LLM_MODEL: str = Field(
        default="anthropic/claude-3.5-sonnet", description="Primary LLM model for synthesis"
    )
    PLANNING_MODEL: str = Field(
        default="anthropic/claude-3.5-sonnet",
        description="LLM model for planning and decomposition",
    )

    # API Configuration
    API_HOST: str = Field(default="0.0.0.0", description="API host")
    API_PORT: int = Field(default=8001, description="API port")
    API_WORKERS: int = Field(default=4, description="Number of workers")
    API_RATE_LIMIT: str = Field(default="10/minute", description="Rate limit per user")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="json", description="Log format (json/text)")

    # Development
    DEBUG: bool = Field(default=False, description="Debug mode")

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Global settings instance
# Type ignore: Settings() will read from .env file at runtime
settings = Settings()  # type: ignore[call-arg]
