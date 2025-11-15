"""Configuration management for research service."""

from pydantic import BaseModel, Field, PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseModel):
    """Configuration for a specific LLM.

    Attributes:
        provider: LLM provider (openrouter, openai, etc.)
        model: Model identifier (e.g., 'deepseek/deepseek-r1:free')
        temperature: Sampling temperature (0.0-2.0)
        max_tokens: Maximum tokens to generate (100-32000)
        timeout: Request timeout in seconds (10-600)
    """

    provider: str = Field(..., description="LLM provider (openrouter, openai, etc.)")
    model: str = Field(..., description="Model identifier")
    temperature: float = Field(..., ge=0.0, le=2.0, description="Sampling temperature")
    max_tokens: int = Field(..., ge=100, le=32000, description="Maximum tokens to generate")
    timeout: int = Field(..., ge=10, le=600, description="Request timeout (seconds)")

    model_config = {"frozen": True}  # Make immutable


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
    LANGFUSE_BASE_URL: str = Field(
        default="https://cloud.langfuse.com", description="Langfuse base URL"
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
        description="Cross-encoder model for semantic reranking",
    )
    ENABLE_RERANKING: bool = Field(
        default=True, description="Enable semantic reranking with cross-encoder"
    )
    RERANK_WEIGHT: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Weight for semantic score in final ranking (0.0-1.0)",
    )

    # LLM Models (Legacy - kept for backward compatibility)
    LLM_MODEL: str = Field(
        default="google/gemini-2.5-flash-lite",
        description="Primary LLM model for synthesis (less rate limiting)",
    )
    PLANNING_MODEL: str = Field(
        default="google/gemini-2.5-flash-lite",
        description="LLM model for planning and decomposition (less rate limiting)",
    )

    # ========================================
    # Dynamic LLM Configuration (New)
    # ========================================

    # Research LLM (Primary, User-Facing)
    RESEARCH_LLM_PROVIDER: str = Field(default="openrouter", description="Research LLM provider")
    RESEARCH_LLM_MODEL: str = Field(
        default="google/gemini-2.5-flash-lite",
        description="Research LLM model (Gemini 2.5 Flash Lite - less rate limiting)",
    )
    RESEARCH_LLM_TEMPERATURE: float = Field(
        default=0.3, ge=0.0, le=2.0, description="Research LLM temperature"
    )
    RESEARCH_LLM_MAX_TOKENS: int = Field(
        default=8192, ge=100, le=32000, description="Research LLM max tokens"
    )
    RESEARCH_LLM_TIMEOUT: int = Field(
        default=180, ge=10, le=600, description="Research LLM timeout (R1 needs time for reasoning)"
    )

    # Phase-Specific Token Limits (Optional - falls back to RESEARCH_LLM_MAX_TOKENS)
    DECOMPOSITION_MAX_TOKENS: int | None = Field(
        default=None,
        ge=100,
        le=4096,
        description="Max tokens for query decomposition (falls back to RESEARCH_LLM_MAX_TOKENS if None)",
    )
    SYNTHESIS_MAX_TOKENS: int | None = Field(
        default=None,
        ge=1024,
        le=32768,
        description="Max tokens for answer synthesis (falls back to RESEARCH_LLM_MAX_TOKENS if None)",
    )
    REGENERATION_MAX_TOKENS: int | None = Field(
        default=None,
        ge=1024,
        le=32768,
        description="Max tokens for hallucination regeneration (falls back to RESEARCH_LLM_MAX_TOKENS if None)",
    )

    # Fallback LLM (Secondary)
    FALLBACK_LLM_PROVIDER: str = Field(default="openrouter", description="Fallback LLM provider")
    FALLBACK_LLM_MODEL: str = Field(
        default="google/gemini-2.5-flash-lite",
        description="Fallback LLM model (Gemini 2.5 Lite - less rate limiting)",
    )
    FALLBACK_LLM_TEMPERATURE: float = Field(
        default=0.2, ge=0.0, le=2.0, description="Fallback LLM temperature"
    )
    FALLBACK_LLM_MAX_TOKENS: int = Field(
        default=4096, ge=100, le=32000, description="Fallback LLM max tokens"
    )
    FALLBACK_LLM_TIMEOUT: int = Field(
        default=120, ge=10, le=600, description="Fallback LLM timeout"
    )

    # Synthesis LLM (Optional - for final answer generation)
    # If not set, uses RESEARCH_LLM_MODEL
    SYNTHESIS_LLM_MODEL: str | None = Field(
        default=None,
        description="Optional dedicated model for final synthesis/answer generation (e.g., google/gemini-2.5-flash-lite). If None, uses RESEARCH_LLM_MODEL",
    )

    # Feature Flags
    ENABLE_DYNAMIC_PROMPTS: bool = Field(
        default=True,
        description="Enable dynamic system prompt generation (pure logic, no LLM cost)",
    )
    ENABLE_LLM_FALLBACK: bool = Field(
        default=True, description="Enable fallback to secondary LLM on primary failure"
    )

    # Two-Pass Synthesis Configuration
    HALLUCINATION_THRESHOLD: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Hallucination rate threshold to trigger regeneration (0.1 = 10%)",
    )
    MAX_REGENERATION_PASSES: int = Field(
        default=3, ge=1, le=5, description="Maximum number of regeneration attempts"
    )
    MIN_IMPROVEMENT_THRESHOLD: int = Field(
        default=1,
        ge=0,
        le=10,
        description="Minimum hallucination reduction to accept regenerated answer",
    )

    # ========================================
    # Source Authority Scoring Configuration
    # ========================================
    ENABLE_AUTHORITY_SCORING: bool = Field(
        default=True,
        description="Enable source authority scoring in ranking (pattern-based + Wikipedia)",
    )
    AUTHORITY_SCORING_WEIGHT: float = Field(
        default=0.15,
        ge=0.0,
        le=0.5,
        description="Weight of authority score in final ranking (0.15 = 15%)",
    )
    ENABLE_PATTERN_AUTHORITY: bool = Field(
        default=True,
        description="Enable pattern-based authority detection (*.gov, *.edu, docs.*, etc.)",
    )
    ENABLE_WIKIPEDIA_AUTHORITY: bool = Field(
        default=True, description="Enable Wikipedia citation proxy for query-contextual authority"
    )
    WIKIPEDIA_CACHE_TTL: int = Field(
        default=3600,
        ge=300,
        le=86400,
        description="Wikipedia citation cache TTL in seconds (default: 1 hour)",
    )
    AUTHORITY_BOOST_MULTIPLIER: float = Field(
        default=1.3,
        ge=1.0,
        le=2.0,
        description="Score multiplier for authoritative sources (1.3 = 30% boost)",
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

    # ========================================
    # Computed Properties for LLMConfig
    # ========================================

    @property
    def research_llm_config(self) -> LLMConfig:
        """Get research LLM configuration.

        Returns:
            LLMConfig for primary research LLM (DeepSeek R1)
        """
        return LLMConfig(
            provider=self.RESEARCH_LLM_PROVIDER,
            model=self.RESEARCH_LLM_MODEL,
            temperature=self.RESEARCH_LLM_TEMPERATURE,
            max_tokens=self.RESEARCH_LLM_MAX_TOKENS,
            timeout=self.RESEARCH_LLM_TIMEOUT,
        )

    @property
    def fallback_llm_config(self) -> LLMConfig:
        """Get fallback LLM configuration.

        Returns:
            LLMConfig for fallback LLM (Gemini)
        """
        return LLMConfig(
            provider=self.FALLBACK_LLM_PROVIDER,
            model=self.FALLBACK_LLM_MODEL,
            temperature=self.FALLBACK_LLM_TEMPERATURE,
            max_tokens=self.FALLBACK_LLM_MAX_TOKENS,
            timeout=self.FALLBACK_LLM_TIMEOUT,
        )


# Global settings instance
# Type ignore: Settings() will read from .env file at runtime
settings = Settings()  # type: ignore[call-arg]
