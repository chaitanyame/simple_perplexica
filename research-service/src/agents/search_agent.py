"""SearchAgent implementation using Pydantic AI.

The SearchAgent coordinates intelligent search workflows:
- Query decomposition (complex → focused sub-queries)
- Search coordination (parallel multi-source execution)
- Result ranking (relevance scoring and quality filtering)
- Source deduplication and validation

Architecture:
    Uses Pydantic AI Agent framework with:
    - Dependency injection for LLM, DB, HTTP clients
    - Structured output validation via Pydantic models
    - Tool-based workflow (decompose → coordinate → rank)
    - Langfuse tracing for observability
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

import json
import httpx
from src.core.circuit_breaker import CircuitBreaker
from pydantic import BaseModel, Field
from pydantic_ai import ModelRetry
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.search_modes import SearchMode, get_mode_from_string
from src.core.config import settings
from src.services.crawl.crawl4ai_client import Crawl4AIClient
from src.services.document.dockling_processor import DocklingProcessor
from src.services.embedding.embedding_service import EmbeddingService
from src.services.embedding.semantic_reranker import (
    RecencyConfig,
    RerankingConfig,
    SemanticReranker,
)
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient
from src.services.search.searxng_client import SearxNGClient
from src.utils.language_detector import detect_language, get_language_name
from src.utils.query_normalizer import normalize_query
from src.utils.temporal_validator import TemporalValidator
from src.utils.claim_grounder import ClaimGrounder
from src.utils.response_validator import ResponseValidator, ResponseQuality
from src.models.citation import Citation
from src.agents.decomposition_validator import DecompositionValidator
from src.services.search.perplexity_search import perplexity_search

# =============================================================================
# Pydantic Models for Structured Output
# =============================================================================


class SubQuery(BaseModel):
    """Decomposed sub-query with intent and priority.

    Attributes:
        query: Focused sub-query text (1-500 chars, can be longer for structured prompts)
        intent: Query intent classification (definition/factual/opinion)
        priority: Execution priority (1=highest, 5=lowest)
        temporal_scope: Time filter (recent/past_year/past_month/any)
        specific_year: Specific year mentioned (e.g., 2022, 2023) - overrides temporal_scope
        language: Query language ISO code (en/es/fr/de) for region-specific results
    """

    query: str = Field(..., min_length=1, max_length=500)
    intent: str = Field(..., pattern=r"^(definition|factual|opinion)$")
    priority: int = Field(ge=1, le=5)
    temporal_scope: str = Field(
        default="any",
        pattern=r"^(recent|past_year|past_month|past_week|any)$",
        description="Time filter: recent (past month), past_year, past_month, past_week, any",
    )
    specific_year: int | None = Field(
        default=None,
        ge=1990,
        le=2030,
        description="Specific year if mentioned (e.g., 2022, 2023). Overrides temporal_scope.",
    )
    language: str = Field(
        default="en",
        pattern=r"^(en|es|fr|de)$",
        description="Query language: en (English), es (Spanish), fr (French), de (German)",
    )


class SearchSource(BaseModel):
    """Search result source with metadata.

    Attributes:
        title: Source title
        url: Source URL
        snippet: Text excerpt/snippet from search results
        content: Full extracted content from URL (populated by crawling)
        relevance: Relevance score from search API (0.0-1.0)
        semantic_score: Cross-encoder reranking score (0.0-1.0, optional)
        final_score: Combined score for ranking (0.0-1.0)
        source_type: Source classification (web/academic/news)
    """

    title: str
    url: str
    snippet: str
    content: str | None = None  # Full content from crawling
    relevance: float = Field(ge=0.0, le=1.0)
    semantic_score: float | None = Field(default=None, ge=0.0, le=1.0)
    final_score: float = Field(default=0.0, ge=0.0, le=1.0)
    source_type: str = Field(pattern=r"^(web|academic|news)$")

    def model_post_init(self, __context) -> None:
        """Initialize final_score if not provided."""
        if self.final_score == 0.0:
            self.final_score = self.relevance


class QueryDecomposition(BaseModel):
    """Result of query decomposition.

    Attributes:
        sub_queries: List of decomposed sub-queries
    """

    sub_queries: list[SubQuery] = Field(
        ...,
        min_length=1,
        max_length=10,
        description="1-10 focused sub-queries (more for complex structured prompts)",
    )


class SearchOutput(BaseModel):
    """Final search output with all results and metadata.

    Attributes:
        answer: AI-generated answer synthesizing the sources
        sub_queries: List of decomposed sub-queries
        sources: Ranked and filtered search sources
        execution_time: Total execution time in seconds
        confidence: Overall confidence score (0.0-1.0)
        grounding_score: Hallucination detection score (0-1, higher = better)
        hallucination_count: Number of unsupported claims detected
    """

    answer: str = Field(..., min_length=1, description="AI-generated answer")
    sub_queries: list[SubQuery]
    sources: list[SearchSource]
    execution_time: float
    confidence: float = Field(ge=0.0, le=1.0)
    grounding_score: float | None = Field(
        None, ge=0.0, le=1.0, description="Hallucination detection score"
    )
    hallucination_count: int | None = Field(None, ge=0, description="Number of unsupported claims")


# =============================================================================
# Utility Functions
# =============================================================================


def extract_json_from_markdown(content: str) -> str:
    """Extract JSON from markdown code blocks.

    Some LLM models wrap JSON responses in ```json...``` or ```...``` blocks.
    This function extracts the JSON content from such blocks.

    Args:
        content: Raw LLM response text

    Returns:
        Cleaned JSON string
    """
    if not content.startswith("```"):
        return content

    lines = content.split("\n")
    json_lines = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            json_lines.append(line)

    extracted = "\n".join(json_lines).strip()
    logger.info(f"📝 Extracted JSON from markdown code block: {len(extracted)} chars")
    return extracted


# =============================================================================
# Dependency Injection
# =============================================================================


@dataclass
class SearchAgentDeps:
    """SearchAgent dependencies for dependency injection.

    Attributes:
        llm_client: OpenRouter LLM client for AI calls
        tracer: Langfuse tracer for observability
        db: Async SQLAlchemy database session
        searxng_client: HTTP client for SearxNG API
        serperdev_api_key: API key for SerperDev service
        crawl_client: Crawl4AI client for URL content extraction
        embedding_service: Embedding service for semantic reranking
        max_sources: Maximum number of sources to return (default: 20)
        timeout: Search timeout in seconds (default: 60.0)
        enable_crawling: Whether to crawl URLs for full content (default: True)
        max_crawl_urls: Maximum URLs to crawl for content (default: 5)
        enable_reranking: Whether to use semantic reranking (default: True)
        rerank_weight: Weight for semantic score in final ranking (default: 0.6)
        enable_diversity_penalty: Enable diversity penalty to reduce duplicates (default: False)
        enable_recency_boost: Enable recency boost for temporal queries (default: False)
        enable_query_aware: Enable query-aware score adaptations (default: False)
        reranking_config: Advanced reranking configuration (optional)
    """

    llm_client: OpenRouterClient
    tracer: LangfuseTracer
    db: AsyncSession
    # Accept either raw httpx.AsyncClient or SearxNGClient abstraction, or None for serperdev-only mode
    searxng_client: Any | None
    serperdev_api_key: str
    crawl_client: Crawl4AIClient
    document_processor: DocklingProcessor
    embedding_service: EmbeddingService
    max_sources: int = 20
    timeout: float = 60.0
    min_sources: int = 5  # Minimum required sources for valid output
    min_confidence: float = 0.5  # Minimum confidence threshold
    enable_crawling: bool = True  # Enable URL crawling
    max_crawl_urls: int = 5  # Maximum URLs to crawl
    enable_reranking: bool = True  # Enable semantic reranking
    rerank_weight: float = 0.6  # Weight for semantic score (0.0-1.0)
    # Enhanced reranking configuration
    enable_diversity_penalty: bool = (
        True  # Enable diversity penalty (deduplication) - ENABLED BY DEFAULT for better quality
    )
    enable_recency_boost: bool = False  # Enable recency boost for temporal queries
    enable_query_aware: bool = False  # Enable query-aware score adaptations
    reranking_config: RerankingConfig | None = None  # Advanced reranking config


# =============================================================================
# SearchAgent Implementation
# =============================================================================


class SearchAgent:
    """Intelligent search coordination agent using Pydantic AI.

    The SearchAgent orchestrates complex search workflows by:
    1. Decomposing queries into focused sub-queries
    2. Coordinating parallel searches across multiple sources
    3. Ranking results by relevance and quality
    4. Validating output meets quality criteria

    Example:
        >>> deps = SearchAgentDeps(
        ...     llm_client=client,
        ...     tracer=tracer,
        ...     db=session,
        ...     searxng_client=http_client,
        ...     serperdev_api_key="key"
        ... )
        >>> agent = SearchAgent(deps=deps)
        >>> result = await agent.run("What are AI agents?")
        >>> print(f"Found {len(result.sources)} sources")
    """

    def __init__(self, deps: SearchAgentDeps) -> None:
        """Initialize SearchAgent with dependencies.

        Args:
            deps: SearchAgentDeps with all required dependencies
        """
        self.deps = deps
        self.max_sources = deps.max_sources
        self.timeout = deps.timeout
        self.temporal_validator = TemporalValidator()
        self.response_validator = ResponseValidator(
            min_tokens=settings.MIN_ANSWER_TOKENS, min_sources=2
        )

        # Log search configuration
        # SearxNG is now the primary search backend; SerperDev acts as a fallback when available
        if deps.serperdev_api_key and deps.serperdev_api_key.strip():
            logger.info("SearchAgent initialized with SearxNG (primary) + SerperDev (fallback)")
        else:
            logger.info(
                "SearchAgent initialized with SearxNG (primary, no SerperDev key available)"
            )

        logger.info(f"✅ Temporal validation enabled with post-retrieval filtering")
        logger.info(f"✅ Cascading fallback enabled: SearxNG → SerperDev → Perplexity")

    async def decompose_query(self, query: str) -> list[SubQuery]:
        """Decompose complex query into focused sub-queries using Pydantic AI.

        Args:
            query: Complex user query to decompose

        Returns:
            List of SubQuery objects with intent and priority

        Example:
            >>> sub_queries = await agent.decompose_query(
            ...     "What are AI agents and how do they work?"
            ... )
            >>> print(len(sub_queries))
            2
        """
        logger.info(f"🧩 QUERY DECOMPOSITION + EXPANSION START")
        logger.info(f"📥 Input query (raw): '{query}'")
        logger.info(
            f"🔄 Query Expansion: LLM-based term expansion enabled (20-30% broader coverage)"
        )

        # Normalize query for consistency
        normalized_query = normalize_query(query)
        logger.info(f"📥 Input query (normalized): '{normalized_query}'")

        # Detect language for better search results
        detected_lang = detect_language(query)
        lang_name = get_language_name(detected_lang)
        logger.info(f"🌍 Detected language: {lang_name} ({detected_lang})")

        # Use OpenRouter LLM directly with JSON mode for structured decomposition
        system_prompt = """You are a query decomposition expert. Break down user queries into focused sub-queries with intelligent term expansion.

Guidelines:
- Simple queries (1 topic): Return 1-2 sub-queries
- Complex queries (multiple topics): Return 2-4 sub-queries  
- Each sub-query should be specific and searchable
- Intent types: "factual" (facts/data), "definition" (what is X), "opinion" (views/analysis)
- Priority: 1 (most important) to 5 (least important)

QUERY EXPANSION (20-30% Better Coverage):
- Detect ambiguous terms and expand with context:
  * "AI" → include "artificial intelligence", "machine learning" in separate sub-queries
  * "Python" → clarify "Python programming language" vs "python snake" based on context
  * "Apple" → specify "Apple Inc." vs "apple fruit" based on context
  
- Add synonyms and related terms for key concepts:
  * "dangerous" → include "risky", "harmful", "threatening" variations
  * "trends" → include "developments", "changes", "evolution"
  * "COVID vaccine" → include "coronavirus vaccination", "immunization"
  
- Expand technical abbreviations:
  * "ML" → "machine learning"
  * "NLP" → "natural language processing"
  * "GPU" → "graphics processing unit"
  
- Generate sub-queries with term variations for broader coverage:
  * Original: "Is AI dangerous?"
  * Expanded: ["AI safety risks", "artificial intelligence dangers", "machine learning threats"]

EXPANSION RULES:
- Keep 1 sub-query with original terms (for exact matches)
- Add 1-2 sub-queries with expanded/synonym terms (for broader coverage)
- Maintain query intent while expanding
- Don't over-expand simple, unambiguous queries

Temporal Detection (CRITICAL - Extract ANY year mentioned):
- If query mentions SPECIFIC YEAR (2022, 2023, 2024, etc.):
  * Set "specific_year": [year as integer]
  * Keep that year in sub-query text
  * Set temporal_scope to "any"
  
- If query has "latest"/"recent"/"new" (no specific year):
  * Set temporal_scope: "recent" 
  * Add current year (2025) to sub-query
  * Set specific_year: null
  
- If query has "past month"/"last month":
  * Set temporal_scope: "past_month"
  * Set specific_year: null
  
- If query has "past week"/"this week":
  * Set temporal_scope: "past_week"
  * Set specific_year: null
  
- If query has "past year":
  * Set temporal_scope: "past_year"
  * Set specific_year: null
  
- No time keywords:
  * Set temporal_scope: "any"
  * Set specific_year: null

Examples:

Query: "What are AI agents?"
Response (with expansion):
{
  "sub_queries": [
    {"query": "What are AI agents?", "intent": "definition", "priority": 1, "temporal_scope": "any", "specific_year": null},
    {"query": "artificial intelligence agents definition", "intent": "definition", "priority": 2, "temporal_scope": "any", "specific_year": null}
  ]
}

Query: "Recent news about Microsoft Azure"
Response:
{
  "sub_queries": [
    {"query": "Microsoft Azure recent news 2025", "intent": "factual", "priority": 1, "temporal_scope": "recent", "specific_year": null}
  ]
}

Query: "Is AI dangerous?"
Response (with expansion - demonstrates ambiguity detection):
{
  "sub_queries": [
    {"query": "Is AI dangerous?", "intent": "opinion", "priority": 1, "temporal_scope": "any", "specific_year": null},
    {"query": "artificial intelligence safety risks", "intent": "factual", "priority": 1, "temporal_scope": "any", "specific_year": null},
    {"query": "machine learning threats and concerns", "intent": "opinion", "priority": 2, "temporal_scope": "any", "specific_year": null}
  ]
}

Query: "GitHub Universe 2023 announcements"
Response:
{
  "sub_queries": [
    {"query": "GitHub Universe 2023 announcements", "intent": "factual", "priority": 1, "temporal_scope": "any", "specific_year": 2023}
  ]
}

Query: "AI developments in 2022"
Response:
{
  "sub_queries": [
    {"query": "AI developments 2022", "intent": "factual", "priority": 1, "temporal_scope": "any", "specific_year": 2022}
  ]
}

Query: "Python trends 2020 vs 2024"
Response:
{
  "sub_queries": [
    {"query": "Python trends 2020", "intent": "factual", "priority": 1, "temporal_scope": "any", "specific_year": 2020},
    {"query": "Python trends 2024", "intent": "factual", "priority": 1, "temporal_scope": "any", "specific_year": 2024}
  ]
}

CRITICAL RULES:
1. ALWAYS extract specific years (2022, 2023, 2024, etc.) and set specific_year field
2. KEEP the year in the sub-query text (don't remove it)
3. specific_year overrides temporal_scope for search filtering
4. Only use "recent" temporal_scope when NO specific year mentioned

Respond with valid JSON only."""

        try:
            import json

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}\n\nDecompose this into sub-queries."},
            ]

            # ============ CRITICAL LOG: LLM INPUT ============
            logger.info(f"🤖 LLM CALL: Query Decomposition")
            logger.info(f"📤 Model: meta-llama/llama-4-maverick:free")
            logger.info(f"📤 Temperature: 0.3, Max Tokens: 500")
            logger.info(f"📤 Messages count: {len(messages)}")
            logger.info(f"📤 System prompt length: {len(system_prompt)} chars")
            logger.info(f"📤 User message: '{messages[1]['content'][:200]}...'")

            # Use configured research model (Gemini) via OpenRouter
            # Note: OpenRouterClient is initialized with a default model,
            # but we can override by temporarily changing it
            original_model = self.deps.llm_client.model
            self.deps.llm_client.model = settings.RESEARCH_LLM_MODEL

            response = await self.deps.llm_client.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=500,
            )

            # Restore original model
            self.deps.llm_client.model = original_model

            # ============ CRITICAL LOG: LLM RESPONSE ============
            content = response["content"].strip()
            logger.info(f"� LLM RESPONSE received")
            logger.info(f"📥 Response length: {len(content)} chars")
            logger.info(f"📥 Raw response:\n{content}")

            # Extract JSON from markdown code blocks if present
            content = extract_json_from_markdown(content)

            # Parse JSON response
            data = json.loads(content)
            logger.info(f"✅ JSON parsing successful")
            logger.info(f"✅ Parsed data keys: {list(data.keys())}")

            # Validate and convert to SubQuery objects
            decomposition = QueryDecomposition(**data)

            # Add detected language to all sub-queries
            for sq in decomposition.sub_queries:
                sq.language = detected_lang

            logger.info(f"🎯 DECOMPOSITION COMPLETE: {len(decomposition.sub_queries)} sub-queries")

            for i, sq in enumerate(decomposition.sub_queries, 1):
                logger.info(
                    f"  [{i}] Query: '{sq.query}' | "
                    f"Intent: {sq.intent} | "
                    f"Priority: {sq.priority} | "
                    f"Temporal: {sq.temporal_scope} | "
                    f"Year: {sq.specific_year or 'N/A'} | "
                    f"Lang: {sq.language}"
                )

            # ============ QUALITY VALIDATION ============
            validator = DecompositionValidator(
                coverage_threshold=0.7,
                redundancy_threshold=0.85,
                min_quality_score=0.6,
                max_retries=1,
            )

            quality_score = await validator.evaluate_quality(
                original_query=normalized_query, sub_queries=decomposition.sub_queries
            )

            # Log quality metrics
            metrics = quality_score.to_dict()
            logger.info(f"📊 DECOMPOSITION QUALITY METRICS:")
            logger.info(f"  Coverage: {metrics['coverage_score']:.2f}")
            logger.info(f"  Redundancy: {metrics['redundancy_score']:.2f}")
            logger.info(f"  Completeness: {metrics['completeness']}")
            logger.info(f"  Overall Score: {metrics['overall_score']:.2f}")
            logger.info(f"  Passes Threshold: {metrics['passes_threshold']}")
            if metrics["issues"]:
                logger.warning(f"  Issues: {', '.join(metrics['issues'])}")

            # Trace to Langfuse if available
            if hasattr(self.deps, "tracer") and self.deps.tracer and self.deps.tracer.current_trace:
                try:
                    # Add quality metrics to trace context
                    self.deps.tracer.current_trace.update(
                        metadata={
                            "decomposition_quality": metrics,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to log quality metrics to Langfuse: {e}")

            # If quality is poor, log warning but continue (no retry for now)
            if not quality_score.passes_threshold:
                logger.warning(
                    f"⚠️ Low quality decomposition (score: {quality_score.overall_score:.2f}). "
                    f"Issues: {', '.join(quality_score.issues)}"
                )
                # Future enhancement: Implement retry with improved prompt
                # For now, we proceed with the decomposition

            return decomposition.sub_queries

        except Exception as e:
            logger.error(f"❌ Query decomposition failed: {e}, using fallback")
            # Fallback: treat as single factual query

            # Extract specific year from query (2020-2030 range)
            import re

            year_pattern = r"\b(20[2-3][0-9])\b"  # Matches 2020-2039
            year_match = re.search(year_pattern, query)
            specific_year = int(year_match.group(1)) if year_match else None

            # Detect temporal keywords
            temporal_keywords = ["latest", "recent", "new", "now", "current", "today"]
            has_temporal_intent = any(kw in query.lower() for kw in temporal_keywords)

            # Determine temporal scope (specific year takes priority)
            if specific_year:
                temporal_scope = "any"  # Year filtering handles it
                logger.info(f"  Fallback detected specific year: {specific_year}")
            elif has_temporal_intent:
                temporal_scope = "recent"
                logger.info(f"  Fallback detected temporal keywords: recent")
            else:
                temporal_scope = "any"
                logger.info(f"  Fallback: no temporal filtering")

            # Truncate query if too long (fallback for structured prompts)
            fallback_query = query[:480] + "..." if len(query) > 480 else query
            if len(query) > 480:
                logger.warning(f"⚠️ Query truncated for fallback: {len(query)} -> 480 chars")

            return [
                SubQuery(
                    query=fallback_query,
                    intent="factual",
                    priority=1,
                    temporal_scope=temporal_scope,
                    specific_year=specific_year,
                    language=detected_lang,
                )
            ]

    async def coordinate_search(self, sub_queries: list[SubQuery]) -> list[SearchSource]:
        """Coordinate parallel searches across multiple sources.

        Args:
            sub_queries: List of sub-queries to search

        Returns:
            Combined and deduplicated search results

        Raises:
            httpx.TimeoutException: Handled gracefully, returns partial results

        Example:
            >>> sources = await agent.coordinate_search(sub_queries)
            >>> print(f"Found {len(sources)} unique sources")
        """
        logger.info(f"🔄 Coordinating search for {len(sub_queries)} sub-queries")
        for i, sq in enumerate(sub_queries, 1):
            logger.info(f"  [{i}] {sq.query}")

        results: list[SearchSource] = []
        seen_urls: set[str] = set()

        # Execute searches in parallel
        search_tasks = [self._search_source(sq) for sq in sub_queries]

        try:
            logger.info(f"⏳ Executing {len(search_tasks)} search tasks in parallel...")
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            logger.info(f"📥 Got {len(search_results)} search results back")

            # Flatten and deduplicate results
            for idx, result in enumerate(search_results):
                if isinstance(result, Exception):
                    logger.error(f"  Search task {idx + 1} failed with exception: {result}")
                elif isinstance(result, list):
                    logger.info(f"  Search task {idx + 1} returned {len(result)} sources")
                    for source in result:
                        if source.url not in seen_urls:
                            seen_urls.add(source.url)
                            results.append(source)
                else:
                    logger.warning(
                        f"  Search task {idx + 1} returned unexpected type: {type(result)}"
                    )

        except Exception as e:
            # Gracefully handle timeouts/errors, return partial results
            logger.error(f"❌ Exception during search coordination: {e}")

        logger.info(f"✅ Coordination complete: {len(results)} unique sources found")
        return results

    async def _search_source(self, sub_query: SubQuery) -> list[SearchSource]:
        """Search using SearxNG (primary) with fallback to SerperDev.

        Order:
            1. Detect year-specific queries → Route to SerperDev for precise filtering
            2. Attempt SearxNG (preferred per spec)
            3. If SearxNG fails or returns no usable results, try SerperDev (if key)
        """
        # -----------------------------
        # OPTION A: Year-Specific Routing to SerperDev
        # -----------------------------
        if (
            sub_query.specific_year is not None
            and self.deps.serperdev_api_key
            and self.deps.serperdev_api_key.strip()
        ):
            logger.info(
                "📅 Year-specific query detected → Routing to SerperDev for precise filtering",
                query=sub_query.query,
                year=sub_query.specific_year,
            )

            try:
                year = sub_query.specific_year
                search_params = {
                    "q": sub_query.query,
                    "num": 10,
                    "gl": sub_query.language,
                    "tbs": f"cdr:1,cd_min:1/1/{year},cd_max:12/31/{year}",  # Precise year filter
                }

                async def _do_serper() -> httpx.Response:
                    async with httpx.AsyncClient() as client:
                        return await client.post(
                            "https://google.serper.dev/search",
                            headers={
                                "X-API-KEY": self.deps.serperdev_api_key,
                                "Content-Type": "application/json",
                            },
                            json=search_params,
                            timeout=self.timeout,
                        )

                # Use circuit breaker
                serper_cb = getattr(self, "_serper_cb", None)
                if serper_cb is None:
                    serper_cb = CircuitBreaker(
                        failure_threshold=settings.PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD,
                        timeout=float(settings.PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT),
                    )
                    self._serper_cb = serper_cb

                response = await serper_cb.call_with_retries(
                    _do_serper,
                    retries=3,
                    backoff_base=0.5,
                    backoff_factor=2.0,
                    fallback=lambda: None,
                )

                if response and response.status_code == 200:
                    data = response.json()
                    organic = data.get("organic", [])
                    if organic:
                        logger.info(
                            "✅ SerperDev year-specific success", count=len(organic), year=year
                        )
                        return [
                            SearchSource(
                                title=r.get("title", ""),
                                url=r.get("link", ""),
                                snippet=r.get("snippet", ""),
                                relevance=0.85,  # Higher relevance for precise temporal match
                                source_type="web",
                            )
                            for r in organic
                        ]
                    else:
                        logger.warning(
                            "SerperDev year-specific returned 0 results, falling back to SearxNG"
                        )
                else:
                    logger.warning("SerperDev year-specific failed, falling back to SearxNG")
            except Exception as e:
                logger.error(f"SerperDev year-specific error: {e}, falling back to SearxNG")

        # -----------------------------
        # Primary: SearxNG
        # -----------------------------
        logger.info("🌐 SearxNG primary search", query=sub_query.query)
        try:
            # Support both wrapper client and raw httpx.AsyncClient
            if isinstance(self.deps.searxng_client, SearxNGClient):
                # Map temporal_scope to SearxNG time_range when possible
                time_range_map = {
                    "past_week": "week",
                    "past_month": "month",
                    "recent": "month",  # Use month for "recent" to catch events from past 4 weeks
                    "past_year": "year",
                }
                time_range = None
                if sub_query.specific_year is not None:
                    # SearxNG does not have direct year filter; leave None (handled downstream)
                    time_range = None
                else:
                    time_range = time_range_map.get(sub_query.temporal_scope)

                # AUTO-DETECT NEWS QUERIES: If query contains "news" and no temporal scope,
                # default to recent news (past week) to avoid old/irrelevant results
                if time_range is None and sub_query.temporal_scope == "any":
                    if any(
                        keyword in sub_query.query.lower()
                        for keyword in ["news", "latest", "current", "recent", "today", "update"]
                    ):
                        time_range = "week"  # Default to past week for news queries
                        logger.info(
                            f"📰 Auto-detected news query, filtering to past week",
                            query=sub_query.query,
                        )

                # First attempt
                categories = getattr(settings, "SEARXNG_DEFAULT_CATEGORIES", ["general"])
                engines = getattr(settings, "SEARXNG_DEFAULT_ENGINES", []) or None
                searx_results = await self.deps.searxng_client.search(
                    sub_query.query,
                    limit=10,
                    categories=categories,
                    engines=engines,
                    language=sub_query.language,
                    time_range=time_range,
                    safesearch=getattr(settings, "SEARXNG_SAFESEARCH", 1),
                )
                if searx_results:
                    logger.info("✅ SearxNG success (primary attempt)", count=len(searx_results))
                    return [
                        SearchSource(
                            title=r.get("title", "") if isinstance(r, dict) else "",
                            url=r.get("url", "") if isinstance(r, dict) else "",
                            snippet=r.get("content", "") if isinstance(r, dict) else "",
                            relevance=0.7,
                            source_type="web",
                        )
                        for r in searx_results
                        if r is not None and isinstance(r, dict)
                    ]
                logger.warning("SearxNG returned 0 results (primary); evaluating retry conditions")

                # Year heuristic attempt: if a specific year exists, try broad 'year' range
                if sub_query.specific_year is not None:
                    logger.info("🔁 SearxNG retry (year heuristic)", year=sub_query.specific_year)
                    searx_year_results = await self.deps.searxng_client.search(
                        sub_query.query,
                        limit=10,
                        categories=categories,
                        engines=engines,
                        language=sub_query.language,
                        time_range="year",
                        safesearch=getattr(settings, "SEARXNG_SAFESEARCH", 1),
                    )
                    if searx_year_results:
                        logger.info(
                            "✅ SearxNG success (year heuristic)", count=len(searx_year_results)
                        )
                        return [
                            SearchSource(
                                title=r.get("title", "") if isinstance(r, dict) else "",
                                url=r.get("url", "") if isinstance(r, dict) else "",
                                snippet=r.get("content", "") if isinstance(r, dict) else "",
                                relevance=0.7,
                                source_type="web",
                            )
                            for r in searx_year_results
                            if r is not None and isinstance(r, dict)
                        ]
                    else:
                        logger.warning("SearxNG year heuristic yielded 0 results")

                # Expanded retry: drop language restriction & add broader categories if missing
                expanded_categories = sorted(set(list(categories) + ["general", "news"]))
                logger.info("🔁 SearxNG retry (expanded scope)", categories=expanded_categories)
                searx_retry_results = await self.deps.searxng_client.search(
                    sub_query.query,
                    limit=10,
                    categories=expanded_categories,
                    engines=engines,
                    language=None,  # remove language filter to broaden
                    time_range=None,
                    safesearch=getattr(settings, "SEARXNG_SAFESEARCH", 1),
                )
                if searx_retry_results:
                    logger.info(
                        "✅ SearxNG success (expanded retry)", count=len(searx_retry_results)
                    )
                    return [
                        SearchSource(
                            title=r.get("title", "") if isinstance(r, dict) else "",
                            url=r.get("url", "") if isinstance(r, dict) else "",
                            snippet=r.get("content", "") if isinstance(r, dict) else "",
                            relevance=0.65,  # Slightly lower relevance due to broadened scope
                            source_type="web",
                        )
                        for r in searx_retry_results
                        if r is not None and isinstance(r, dict)
                    ]
                else:
                    logger.warning(
                        "SearxNG expanded retry returned 0 results; proceeding to fallback"
                    )
            else:  # Raw httpx client path
                # Raw client path - build params manually
                params = {
                    "q": sub_query.query,
                    "format": "json",
                    "language": sub_query.language,
                }
                # Temporal mapping as above
                time_range_map = {
                    "past_week": "week",
                    "past_month": "month",
                    "recent": "month",
                    "past_year": "year",
                }
                if sub_query.specific_year is None:
                    tr = time_range_map.get(sub_query.temporal_scope)
                    if tr:
                        params["time_range"] = tr
                cats = getattr(settings, "SEARXNG_DEFAULT_CATEGORIES", ["general"])
                if cats:
                    params["categories"] = ",".join(cats)
                engines = getattr(settings, "SEARXNG_DEFAULT_ENGINES", [])
                if engines:
                    params["engines"] = ",".join(engines)
                params["safesearch"] = getattr(settings, "SEARXNG_SAFESEARCH", 1)

                response = await self.deps.searxng_client.get(
                    "/search", params=params, timeout=self.timeout
                )
                logger.info("SearxNG response status", status=response.status_code)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", []) if data else []
                    if results:
                        logger.info("✅ SearxNG success", count=len(results))
                        return [
                            SearchSource(
                                title=r.get("title", "") if isinstance(r, dict) else "",
                                url=r.get("url", "") if isinstance(r, dict) else "",
                                snippet=r.get("content", "") if isinstance(r, dict) else "",
                                relevance=0.7,
                                source_type="web",
                            )
                            for r in results
                            if r is not None and isinstance(r, dict)
                        ]
                    else:
                        logger.warning("SearxNG returned 0 results; will consider fallback")
                else:
                    logger.warning("SearxNG non-200", status=response.status_code)
        except httpx.TimeoutException:
            logger.warning("SearxNG timeout", query=sub_query.query)
        except httpx.ConnectError as e:
            logger.error("SearxNG connect error", error=str(e))
        except Exception as e:
            logger.error("SearxNG unexpected error", error=str(e))

        # -----------------------------
        # Fallback: SerperDev
        # -----------------------------
        if not (self.deps.serperdev_api_key and self.deps.serperdev_api_key.strip()):
            logger.warning("No SerperDev API key available; returning empty results")
            return []

        temporal_info = f"temporal: {sub_query.temporal_scope}"
        if sub_query.specific_year:
            temporal_info += f", year: {sub_query.specific_year}"
        logger.info("↩️ Fallback to SerperDev", query=sub_query.query, temporal=temporal_info)

        try:
            search_params = {
                "q": sub_query.query,
                "num": 10,
                "gl": sub_query.language,
            }
            if sub_query.specific_year:
                year = sub_query.specific_year
                search_params["tbs"] = f"cdr:1,cd_min:1/1/{year},cd_max:12/31/{year}"
            elif sub_query.temporal_scope == "past_week":
                search_params["tbs"] = "qdr:w"
            elif sub_query.temporal_scope in {"past_month", "recent"}:
                search_params["tbs"] = "qdr:m"
            elif sub_query.temporal_scope == "past_year":
                search_params["tbs"] = "qdr:y"

            async def _do_serper() -> httpx.Response:
                async with httpx.AsyncClient() as client:
                    return await client.post(
                        "https://google.serper.dev/search",
                        headers={
                            "X-API-KEY": self.deps.serperdev_api_key,
                            "Content-Type": "application/json",
                        },
                        json=search_params,
                        timeout=self.timeout,
                    )

            # Use a circuit breaker with retries and exponential backoff
            # Reuse the Perplexity CB thresholds for now
            serper_cb = getattr(self, "_serper_cb", None)
            if serper_cb is None:
                serper_cb = CircuitBreaker(
                    failure_threshold=settings.PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD,
                    timeout=float(settings.PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT),
                )
                setattr(self, "_serper_cb", serper_cb)

            response = await serper_cb.call_with_retries(
                _do_serper,
                retries=3,
                backoff_base=0.5,
                backoff_factor=2.0,
                fallback=lambda: None,
            )

            logger.info("SerperDev response status", status=response.status_code)
            if response.status_code == 200:
                data = response.json()
                organic = data.get("organic", [])
                if organic:
                    logger.info("✅ SerperDev success", count=len(organic))
                    return [
                        SearchSource(
                            title=r.get("title", ""),
                            url=r.get("link", ""),
                            snippet=r.get("snippet", ""),
                            relevance=0.8,
                            source_type="web",
                        )
                        for r in organic
                    ]
                else:
                    logger.warning("SerperDev returned 0 results")
            elif response is not None:
                logger.warning("SerperDev non-200", status=response.status_code)
        except Exception as e:
            logger.error("SerperDev error", error=str(e))

        return []

    async def enrich_sources_with_content(self, sources: list[SearchSource]) -> list[SearchSource]:
        """Enrich search sources by crawling URLs for full content.

        Args:
            sources: Search sources with snippets

        Returns:
            Same sources enriched with full content from crawling

        Example:
            >>> enriched = await agent.enrich_sources_with_content(sources)
            >>> assert enriched[0].content is not None
        """
        if not self.deps.enable_crawling:
            logger.info("⏭️  URL crawling disabled, skipping content enrichment")
            return sources

        # Select top URLs to crawl (by relevance)
        urls_to_crawl = sources[: self.deps.max_crawl_urls]
        logger.info(f"🌐 Crawling {len(urls_to_crawl)} URLs for full content extraction")

        # Crawl URLs in parallel
        crawl_tasks = []
        for source in urls_to_crawl:
            crawl_tasks.append(self._crawl_single_url(source))

        results = await asyncio.gather(*crawl_tasks, return_exceptions=True)

        # Count successful crawls
        success_count = sum(
            1
            for r, source in zip(results, urls_to_crawl)
            if not isinstance(r, Exception) and source.content
        )
        logger.info(f"✅ Successfully crawled {success_count}/{len(urls_to_crawl)} URLs")

        return sources

    def _is_document_url(self, url: str) -> bool:
        """Check if URL points to a document (PDF, DOCX, etc.).

        Args:
            url: URL to check

        Returns:
            True if URL is a document, False otherwise
        """
        url_lower = url.lower()
        doc_extensions = [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"]

        # Check file extension in path
        for ext in doc_extensions:
            if ext in url_lower:
                return True

        # Check for common PDF URL patterns
        if "pdf" in url_lower or "download" in url_lower or "arxiv.org/pdf" in url_lower:
            return True

        return False

    async def _crawl_single_url(self, source: SearchSource) -> SearchSource:
        """Crawl a single URL and update source with content.

        Routes to appropriate processor:
        - PDF/DOCX/etc → DocklingProcessor for structured extraction
        - Regular web pages → Crawl4AI for HTML crawling

        Args:
            source: Search source to enrich

        Returns:
            Same source with content field populated
        """
        try:
            # Check if this is a document URL
            if self._is_document_url(source.url):
                logger.info(f"� Processing document: {source.url}")

                # Download document content
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(source.url, follow_redirects=True)
                    response.raise_for_status()

                    # Extract filename from URL or Content-Disposition
                    filename = source.url.split("/")[-1]
                    if "?" in filename:
                        filename = filename.split("?")[0]
                    if not any(
                        ext in filename.lower()
                        for ext in [".pdf", ".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt"]
                    ):
                        filename += ".pdf"  # Default to PDF if no extension

                    # Process document with Dockling
                    processed_doc = await self.deps.document_processor.process_document_bytes(
                        content=response.content, filename=filename, source_url=source.url
                    )

                    # Use processed markdown content
                    source.content = processed_doc.content[:10000]  # Limit to 10K chars
                    logger.info(
                        f"✅ Processed document {source.url}: {len(source.content)} chars, "
                        f"{len(processed_doc.chunks)} chunks"
                    )

            else:
                # Regular web page - use Crawl4AI
                logger.info(f"�🕷️  Crawling web page: {source.url}")
                crawled_page = await self.deps.crawl_client.crawl_url(
                    url=source.url,
                    word_count_threshold=50,  # Filter out short/nav blocks
                )

                if crawled_page.success and crawled_page.markdown:
                    # Use markdown content (cleaner than HTML)
                    source.content = crawled_page.markdown[:10000]  # Limit to 10K chars
                    logger.info(f"✅ Crawled {source.url}: {len(source.content)} chars")
                else:
                    logger.warning(
                        f"⚠️  Crawl failed for {source.url}: {crawled_page.error_message}"
                    )

        except Exception as e:
            logger.error(f"❌ Error processing {source.url}: {e}")

        return source

    async def rank_results(
        self, sources: list[SearchSource], original_query: str
    ) -> list[SearchSource]:
        """Rank and filter results by relevance with optional semantic reranking.

        Args:
            sources: Raw search results
            original_query: User's original question

        Returns:
            Top-ranked sources (up to max_sources), filtered by quality

        Example:
            >>> ranked = await agent.rank_results(sources, "AI agents")
            >>> assert ranked[0].final_score >= ranked[-1].final_score
        """
        if not sources:
            return []

        # Filter low-quality results (relevance < 0.5)
        filtered = [s for s in sources if s.relevance >= 0.5]

        if not filtered:
            return []

        # Apply semantic reranking if enabled
        if self.deps.enable_reranking:
            try:
                logger.info(
                    "Applying semantic reranking",
                    query=original_query,
                    num_candidates=len(filtered),
                    diversity_enabled=self.deps.enable_diversity_penalty,
                    recency_enabled=self.deps.enable_recency_boost,
                    query_aware_enabled=self.deps.enable_query_aware,
                )

                # Prepare documents for reranking (use content if available, else snippet)
                documents = [(s.content if s.content else s.snippet) for s in filtered]

                # Check if enhanced reranking is enabled
                use_enhanced = (
                    self.deps.enable_diversity_penalty
                    or self.deps.enable_recency_boost
                    or self.deps.enable_query_aware
                )

                if use_enhanced:
                    # Use enhanced semantic reranking
                    # Build reranking config
                    config = self.deps.reranking_config or RerankingConfig(
                        diversity_penalty=0.3 if self.deps.enable_diversity_penalty else 0.0,
                        query_aware=self.deps.enable_query_aware,
                        recency_config=RecencyConfig(
                            enabled=self.deps.enable_recency_boost,
                            weight=0.3,
                            adaptive=True,
                        ),
                    )

                    reranker = SemanticReranker(
                        embedding_service=self.deps.embedding_service,
                        config=config,
                    )

                    # Apply enhanced reranking based on enabled features
                    if self.deps.enable_diversity_penalty and not self.deps.enable_recency_boost:
                        rerank_results = await reranker.rerank_with_diversity(
                            query=original_query,
                            documents=documents,
                        )
                    elif self.deps.enable_recency_boost and not self.deps.enable_diversity_penalty:
                        # Need DocumentWithMetadata for recency
                        from src.services.embedding.semantic_reranker import DocumentWithMetadata

                        docs_with_meta = [
                            DocumentWithMetadata(
                                content=doc,
                                published_at=filtered[i].published_at
                                if hasattr(filtered[i], "published_at")
                                else None,
                            )
                            for i, doc in enumerate(documents)
                        ]
                        rerank_results = await reranker.rerank_with_recency(
                            query=original_query,
                            documents=docs_with_meta,
                        )
                    elif self.deps.enable_query_aware:
                        rerank_results = await reranker.rerank_with_query_awareness(
                            query=original_query,
                            documents=documents,
                        )
                    else:
                        # Multiple features enabled - use query awareness as primary
                        rerank_results = await reranker.rerank_with_query_awareness(
                            query=original_query,
                            documents=documents,
                        )

                    logger.info(
                        "Enhanced semantic reranking applied",
                        method="diversity"
                        if self.deps.enable_diversity_penalty
                        else ("recency" if self.deps.enable_recency_boost else "query_aware"),
                    )
                else:
                    # Use standard cross-encoder reranking
                    rerank_results = await self.deps.embedding_service.rerank(
                        query=original_query,
                        documents=documents,
                    )

                # Map semantic scores back to sources
                for idx, score in rerank_results:
                    filtered[idx].semantic_score = score

                    # Compute final score as weighted combination
                    # final_score = (1 - w) * relevance + w * semantic_score + authority_weight * authority
                    relevance_weight = 1.0 - self.deps.rerank_weight
                    filtered[idx].final_score = (
                        relevance_weight * filtered[idx].relevance + self.deps.rerank_weight * score
                    )

                logger.info(
                    "Semantic reranking complete",
                    reranked_count=len(rerank_results),
                )

            except Exception as e:
                logger.warning(
                    "Semantic reranking failed, falling back to relevance",
                    error=str(e),
                )
                # Fallback: use relevance as final_score
                for source in filtered:
                    source.final_score = source.relevance
        else:
            # No reranking: use relevance as final_score
            for source in filtered:
                source.final_score = source.relevance

        # Sort by final_score (descending)
        filtered.sort(key=lambda s: s.final_score, reverse=True)

        # Return top max_sources
        return filtered[: self.max_sources]

    # =========================================================================
    # Content-Type Detection and Analysis (Phase 2)
    # =========================================================================

    def _analyze_source_composition(self, sources: list[SearchSource]) -> dict:
        """Analyze the composition of sources to detect content types.

        Examines sources to determine:
        - Ratio of academic vs news vs technical content
        - Authority levels (official, third-party, news outlets)
        - Document types (web pages, PDFs, code repos, arxiv papers)

        Args:
            sources: List of SearchSource objects

        Returns:
            Dictionary with composition metrics:
                - academic_ratio: float (0.0-1.0)
                - news_ratio: float (0.0-1.0)
                - technical_ratio: float (0.0-1.0)
                - authority_score: float (0.0-1.0)
                - has_code_samples: bool
                - has_official_docs: bool
                - primary_type: str ("academic", "news", "technical", "general", "mixed")
        """
        if not sources:
            return {
                "academic_ratio": 0.0,
                "news_ratio": 0.0,
                "technical_ratio": 0.0,
                "authority_score": 0.5,
                "has_code_samples": False,
                "has_official_docs": False,
                "primary_type": "general",
            }

        # Count source types
        academic_count = 0
        news_count = 0
        technical_count = 0
        authority_sources = 0

        # Keywords for detection
        academic_keywords = [
            "arxiv",
            "research",
            "study",
            "paper",
            "journal",
            "university",
            "scholar",
            "academic",
            "thesis",
            "dissertation",
            "proceedings",
        ]
        news_keywords = [
            "news",
            "article",
            "today",
            "breaking",
            "latest",
            "report",
            "announcement",
            "press release",
            "statement",
        ]
        technical_keywords = [
            "github",
            "documentation",
            "api",
            "code",
            "repository",
            "library",
            "framework",
            "sdk",
            "tutorial",
            "guide",
            "python",
            "javascript",
            "typescript",
            "java",
            "rust",
            "go",
            "example",
        ]
        official_domains = [
            "github.com/official",
            "docs.microsoft.com",
            "cloud.google.com",
            "aws.amazon.com",
            "docs.",
            ".org/docs",
            "developer.",
        ]

        # Analyze each source
        for source in sources:
            url_lower = source.url.lower()
            title_lower = source.title.lower()
            snippet_lower = source.snippet.lower() if source.snippet else ""
            combined = f"{title_lower} {snippet_lower} {url_lower}"

            # Check for academic content
            if any(kw in combined for kw in academic_keywords) or "arxiv" in url_lower:
                academic_count += 1

            # Check for news content
            if any(kw in combined for kw in news_keywords) or source.source_type == "news":
                news_count += 1

            # Check for technical content
            if any(kw in combined for kw in technical_keywords) or source.source_type == "academic":
                technical_count += 1

            # Check for official/authoritative sources
            if any(domain in url_lower for domain in official_domains):
                authority_sources += 1

        total = len(sources)
        academic_ratio = academic_count / total if total > 0 else 0.0
        news_ratio = news_count / total if total > 0 else 0.0
        technical_ratio = technical_count / total if total > 0 else 0.0
        authority_score = (authority_sources + sum(1 for s in sources if s.relevance > 0.8)) / (
            total * 2
        )

        # Determine primary type
        ratios = {
            "academic": academic_ratio,
            "news": news_ratio,
            "technical": technical_ratio,
        }
        primary_type = max(ratios, key=ratios.get) if max(ratios.values()) > 0.3 else "general"

        # Check for code samples in content
        has_code_samples = any("```" in (s.content or "") for s in sources)
        has_official_docs = authority_score > 0.3

        return {
            "academic_ratio": academic_ratio,
            "news_ratio": news_ratio,
            "technical_ratio": technical_ratio,
            "authority_score": min(authority_score, 1.0),
            "has_code_samples": has_code_samples,
            "has_official_docs": has_official_docs,
            "primary_type": primary_type if max(ratios.values()) > 0.2 else "mixed",
        }

    def _detect_any_comparison(self, query: str) -> dict[str, bool]:
        """Detect if query is comparing multiple items (generic comparison detection).

        Works for any type of comparison:
        - Cloud providers: AWS vs Azure vs GCP
        - Programming languages: Python vs JavaScript
        - Frameworks: React vs Vue
        - Databases: PostgreSQL vs MongoDB
        - Tools: Docker vs Kubernetes
        - And anything else being compared

        Args:
            query: User's search query

        Returns:
            Dictionary with detected comparison info:
            {
                "is_comparison": bool,
                "items": list[str],  # Items being compared
                "item_count": int,
                "comparison_type": str,  # "cloud_provider", "programming", "generic"
                "provider_info": dict  # Special cloud provider details if applicable
            }

        Example:
            >>> result = agent._detect_any_comparison("Compare Python and JavaScript")
            >>> result["is_comparison"]
            True
            >>> result["items"]
            ["python", "javascript"]
            >>> result["item_count"]
            2
        """
        query_lower = query.lower()

        # First, check for cloud provider comparison (special case for better formatting)
        cloud_provider_info = self._detect_provider_comparison(query)
        if cloud_provider_info["is_comparison"]:
            return {
                "is_comparison": True,
                "items": cloud_provider_info["providers"],
                "item_count": cloud_provider_info["provider_count"],
                "comparison_type": "cloud_provider",
                "provider_info": cloud_provider_info,
            }

        # Generic comparison detection for any items
        comparison_keywords = ["vs", "versus", "compare", "comparison", "difference", "between"]
        has_comparison_keyword = any(kw in query_lower for kw in comparison_keywords)

        # Extract potential items from the query by looking for common separators
        items = []
        if has_comparison_keyword:
            # Split by comparison keywords to extract items
            import re

            # Replace comparison keywords with delimiter for splitting
            temp_query = query_lower
            for kw in comparison_keywords:
                temp_query = temp_query.replace(kw, "|")

            # Split and clean items
            potential_items = [item.strip() for item in temp_query.split("|")]

            # Filter out empty items and very short items (likely noise)
            items = [
                item
                for item in potential_items
                if item and len(item) > 2 and item not in ["and", "or", "the"]
            ]

            # Remove overly long items (likely full clauses, not just items being compared)
            items = [item for item in items if len(item) < 100]

        # It's a comparison if we found 2+ distinct items with comparison keyword
        is_comparison = has_comparison_keyword and len(items) >= 2

        return {
            "is_comparison": is_comparison,
            "items": items,
            "item_count": len(items),
            "comparison_type": "generic",
            "provider_info": {},
        }

    def _detect_provider_comparison(self, query: str) -> dict[str, bool]:
        """Detect if query is comparing multiple cloud providers.

        Identifies cloud provider mentions to ensure balanced coverage:
        - AWS / Amazon Web Services
        - Azure / Microsoft Azure
        - GCP / Google Cloud Platform / Google Cloud
        - Other providers (Oracle, Alibaba, etc.)

        Args:
            query: User's search query

        Returns:
            Dictionary with detected providers:
            {
                "is_comparison": bool,
                "providers": list[str],
                "aws": bool,
                "azure": bool,
                "gcp": bool,
                "other_providers": list[str]
            }

        Example:
            >>> result = agent._detect_provider_comparison("Compare AWS and Azure")
            >>> result["is_comparison"]
            True
            >>> result["providers"]
            ["aws", "azure"]
        """
        query_lower = query.lower()

        # Provider detection patterns
        providers_detected = {
            "aws": any(
                term in query_lower for term in ["aws", "amazon web services", "amazon aws"]
            ),
            "azure": any(term in query_lower for term in ["azure", "microsoft azure"]),
            "gcp": any(
                term in query_lower for term in ["gcp", "google cloud", "google cloud platform"]
            ),
        }

        # Other cloud providers
        other_keywords = ["oracle cloud", "alibaba cloud", "ibm cloud", "digital ocean", "linode"]
        other_providers = [p for p in other_keywords if p in query_lower]

        # Detect if this is a comparison query
        comparison_keywords = [
            "vs",
            "versus",
            "compare",
            "comparison",
            "difference",
            "between",
            "and",
        ]
        is_comparison = any(kw in query_lower for kw in comparison_keywords)

        # Count detected providers
        detected_count = sum(1 for v in providers_detected.values() if v)

        # It's a comparison if multiple providers OR explicit comparison keyword + any provider
        is_comparison = (
            is_comparison and detected_count >= 2 or (detected_count > 1 and not is_comparison)
        )

        providers_list = [p for p, detected in providers_detected.items() if detected]
        providers_list.extend(other_providers)

        return {
            "is_comparison": is_comparison,
            "providers": providers_list,
            "aws": providers_detected["aws"],
            "azure": providers_detected["azure"],
            "gcp": providers_detected["gcp"],
            "other_providers": other_providers,
            "provider_count": len(providers_list),
        }

    def _get_balanced_coverage_instructions(self, comparison_info: dict) -> str:
        """Build instructions for balanced multi-item comparison coverage.

        Works for ANY comparison (cloud providers, programming languages, frameworks, etc.)
        Ensures equal representation and prevents quality-based bias from suppressing items.

        Args:
            comparison_info: Dictionary from _detect_any_comparison()
                           Also supports legacy format from _detect_provider_comparison()

        Returns:
            Coverage balancing instruction string

        Example:
            >>> info = {"is_comparison": True, "items": ["python", "javascript"], "item_count": 2}
            >>> instructions = agent._get_balanced_coverage_instructions(info)
            >>> "equal coverage" in instructions.lower()
            True
        """
        # Handle both new and legacy formats
        is_comparison = comparison_info.get("is_comparison", False)

        # Determine which format we're dealing with
        if "item_count" in comparison_info:
            # New generic format from _detect_any_comparison()
            item_count = comparison_info.get("item_count", 0)
            items = comparison_info.get("items", [])
            comparison_type = comparison_info.get("comparison_type", "generic")
        else:
            # Legacy format from _detect_provider_comparison()
            item_count = comparison_info.get("provider_count", 0)
            items = comparison_info.get("providers", [])
            comparison_type = "cloud_provider"

        if not is_comparison or item_count < 2:
            return ""

        target_coverage = 1.0 / item_count

        # Build item-specific sections
        item_sections = []

        if comparison_type == "cloud_provider":
            # Special handling for cloud providers with known names
            provider_info = comparison_info.get("provider_info", {})
            if provider_info.get("aws"):
                item_sections.append(
                    "AWS: Include all announcements, features, services, and tools mentioned"
                )
            if provider_info.get("azure"):
                item_sections.append(
                    "Azure: Include all announcements, features, services, and tools mentioned"
                )
            if provider_info.get("gcp"):
                item_sections.append(
                    "Google Cloud: Include all announcements, features, services, and tools mentioned"
                )

            for other in provider_info.get("other_providers", []):
                item_sections.append(
                    f"{other.title()}: Include all announcements and updates mentioned"
                )
        else:
            # Generic items - just include all with standard requirements
            for item in items:
                # Capitalize properly
                item_display = " ".join(word.capitalize() for word in item.split())
                item_sections.append(
                    f"{item_display}: Include all specific information, features, and details mentioned"
                )

        # Determine plural form for items
        item_type = "items" if len(items) > 1 else "item"
        items_display = ", ".join(
            [item.upper() if len(item) <= 10 else item.title() for item in items]
        )

        instructions = f"""
MULTI-ITEM BALANCED COVERAGE REQUIREMENT:
This query compares {item_count} {item_type}: {items_display}

EQUAL REPRESENTATION MANDATE:
- Allocate approximately {target_coverage:.0%} of coverage to each {item_type.rstrip("s")}
- Include all specific information, features, and details for each item
- Do NOT deprioritize any item due to source quality, specificity, or citation differences
- Each item section should be roughly equal in detail and length

ITEM-SPECIFIC REQUIREMENTS:
{chr(10).join("- " + section for section in item_sections)}

COVERAGE BALANCE CHECK:
Before finalizing the answer, verify:
[OK] Each item has substantial dedicated coverage
[OK] No item is reduced to a single generic line
[OK] All specific features/details are represented proportionally
[OK] Information items are balanced across all mentioned items

DO NOT USE INVERTED PYRAMID FOR ITEM ORDERING
- Instead, organize by item (one section per item)
- Within each item, use inverted pyramid for features/announcements
"""
        return instructions

    def _build_content_type_instructions(self, composition: dict) -> str:
        """Build content-type-specific instructions based on source composition.

        Args:
            composition: Dictionary from _analyze_source_composition()

        Returns:
            String with specialized instructions for the detected content type
        """
        instructions = ""

        # Academic content instructions
        if composition["academic_ratio"] > 0.4:
            instructions += """
ACADEMIC CONTENT INSTRUCTIONS:
- Use formal, scholarly tone
- Include author (year) format for citations: "Smith et al. (2024) [1]"
- Explain research methodology when discussing findings
- Distinguish between empirical findings and theoretical hypotheses
- Include sample sizes and statistical significance when available
- Reference datasets and experimental conditions
- Note limitations of studies where mentioned
- Use precise terminology (avoid overgeneralization)
- Format: "The research shows [finding] (n=XXX, p<0.05) [citation]"
"""

        # News content instructions
        if composition["news_ratio"] > 0.3:
            instructions += """
NEWS CONTENT INSTRUCTIONS:
- Lead with most recent and significant developments (inverted pyramid)
- Include exact dates and timestamps: "On November 12, 2024 [1]"
- Distinguish breaking news from analysis/opinion pieces: "Breaking: ..." vs "Analysis: ..."
- Mark updates to stories: "Updated: [date]"
- Use chronological ordering for event narratives
- Separate fact from opinion: "The company announced X [1]. Analysts believe Y [2]."
- Include direct quotes from official sources when relevant
- Note if information is developing/preliminary
"""

        # Technical content instructions
        if composition["technical_ratio"] > 0.3 or composition["has_code_samples"]:
            instructions += """
TECHNICAL CONTENT INSTRUCTIONS:
- Format code snippets with language specification:
  ```python
  code_here()
  ```
- Include version requirements: "Requires version X.Y+ or Python 3.8+"
- List prerequisites and dependencies clearly
- Number installation/setup steps: "1. Step, 2. Step..."
- Include platform compatibility: "Works on: Linux, macOS, Windows"
- Add warnings for breaking changes or deprecated features
- Include error handling examples
- Provide working examples with expected output
- Note performance characteristics when relevant
"""

        # Official documentation instructions
        if composition["has_official_docs"]:
            instructions += """
OFFICIAL DOCUMENTATION PRIORITY:
- Prioritize official documentation sources [cite first]
- Note: "According to official documentation [1], feature X..."
- Defer to official specs for accurate information
- Clearly mark community-provided information
- Verify information against official sources when conflicting info exists
"""

        return instructions

    def _get_format_instructions(self, composition: dict) -> str:
        """Get formatting instructions based on source types.

        Args:
            composition: Dictionary from _analyze_source_composition()

        Returns:
            String with formatting guidelines
        """
        formatting = "\nFORMATTING GUIDELINES:"

        # Academic formatting
        if composition["academic_ratio"] > 0.4:
            formatting += "\n- Use formal paragraph structure (avoid lists where possible)"
            formatting += "\n- Include methodology, findings, implications sections"
            formatting += "\n- Use 'research indicates', 'studies show', 'evidence suggests'"

        # News formatting
        if composition["news_ratio"] > 0.3:
            formatting += "\n- Use headline style for major announcements"
            formatting += "\n- Use bullet points for breaking updates"
            formatting += "\n- Include date after each fact: 'X announced on [date] [cite]'"
            formatting += "\n- Use subheadings for different newsworthy items"

        # Technical formatting
        if composition["technical_ratio"] > 0.3 or composition["has_code_samples"]:
            formatting += "\n- Preserve code examples exactly as shown"
            formatting += "\n- Use 'Note:', 'Warning:', 'Tip:' for important information"
            formatting += "\n- Format file paths and commands in monospace: `path/to/file`"
            formatting += "\n- Include version numbers with all references"

        return formatting

    # =========================================================================
    # Phase 3 Task 7: Observability & Monitoring
    # =========================================================================

    def _log_response_metrics(
        self,
        query: str,
        grounding_score: float | None,
        hallucination_count: int | None,
        total_claims: int,
        content_type: str,
        language: str,
        citation_quality: float | None,
        confidence_scores: dict[str, float] | None,
        execution_time: float,
    ) -> None:
        """Log comprehensive response metrics for observability.

        Captures all Phase 1-3 metrics in structured format for monitoring,
        debugging, and analytics.

        Args:
            query: User's query
            grounding_score: Hallucination detection score (0-1)
            hallucination_count: Number of unsupported claims
            total_claims: Total number of extracted claims
            content_type: Detected content type (academic/news/technical)
            language: Detected language (en/es/fr/de)
            citation_quality: Average citation quality score (0-1)
            confidence_scores: Dict of confidence scores
            execution_time: Total execution time (seconds)

        Example:
            >>> agent._log_response_metrics(
            ...     query="What is AI?",
            ...     grounding_score=0.87,
            ...     hallucination_count=1,
            ...     total_claims=10,
            ...     content_type="technical",
            ...     language="en",
            ...     citation_quality=0.91,
            ...     confidence_scores={"overall_confidence": 0.85},
            ...     execution_time=2.5
            ... )
        """
        # Structured logging of all metrics
        logger.info("=" * 80)
        logger.info("PHASE 3: COMPREHENSIVE RESPONSE METRICS")
        logger.info("=" * 80)

        # Query and content information
        logger.info(f"Query: {query[:100]}")
        logger.info(f"Content-Type: {content_type}")
        logger.info(f"Language: {language}")
        logger.info(f"Execution Time: {execution_time:.2f}s")

        # Phase 1: Hallucination Detection Metrics
        logger.info("\n--- PHASE 1: HALLUCINATION DETECTION ---")
        logger.info(
            f"Grounding Score: {grounding_score:.2f}/1.0"
            if grounding_score is not None
            else "Grounding Score: N/A"
        )
        logger.info(
            f"Hallucination Count: {hallucination_count}/{total_claims}"
            if hallucination_count is not None
            else "Hallucination Count: N/A"
        )
        if hallucination_count is not None and total_claims > 0:
            hallucination_rate = hallucination_count / total_claims
            logger.info(f"Hallucination Rate: {hallucination_rate:.1%}")

        # Phase 3 Task 1: Citation Quality Metrics
        logger.info("\n--- PHASE 3 TASK 1: CITATION QUALITY ---")
        logger.info(
            f"Average Citation Quality: {citation_quality:.2f}/1.0"
            if citation_quality is not None
            else "Average Citation Quality: N/A"
        )

        # Phase 3 Task 5: Confidence Scoring Metrics
        logger.info("\n--- PHASE 3 TASK 5: CONFIDENCE SCORING ---")
        if confidence_scores:
            for score_type, score_value in confidence_scores.items():
                readable_name = score_type.replace("_", " ").title()
                logger.info(f"{readable_name}: {score_value:.2f}/1.0")
        else:
            logger.info("Confidence Scores: N/A")

        logger.info("=" * 80)

    # =========================================================================
    # Phase 3 Task 5: Response Confidence Scoring
    # =========================================================================

    def _calculate_response_confidence(
        self,
        grounding_score: float | None,
        content_type: str,
        hallucination_count: int | None,
        total_claims: int,
    ) -> dict[str, float]:
        """Calculate response confidence scores with per-type metrics.

        Confidence calculation:
        - Overall: (grounding × 0.5) + (type_authority × 0.3) + (anti_hallucination × 0.2)
        - Type-specific scores adjust for content category strengths

        Args:
            grounding_score: Overall grounding/hallucination detection score (0-1)
            content_type: Detected content type (academic/news/technical)
            hallucination_count: Number of unsupported claims
            total_claims: Total number of extracted claims

        Returns:
            Dictionary with confidence scores:
            - overall_confidence: 0-1 overall confidence
            - academic_confidence: 0-1 if academic content
            - news_freshness_confidence: 0-1 if news content
            - technical_accuracy_confidence: 0-1 if technical content

        Example:
            >>> confidence = agent._calculate_response_confidence(0.85, "technical", 1, 10)
            >>> print(f"Overall: {confidence['overall_confidence']:.2f}")
            Overall: 0.83
        """
        # Handle missing values
        if grounding_score is None:
            grounding_score = 0.7  # Default neutral score

        # Calculate hallucination rate
        hallucination_rate = 0.0
        if hallucination_count is not None and total_claims > 0:
            hallucination_rate = hallucination_count / total_claims

        # Authority score (placeholder - could be enhanced with citation authority)
        authority_score = 0.85  # Default authority assumption

        # Anti-hallucination component (1 - hallucination_rate)
        anti_hallucination_score = 1.0 - min(hallucination_rate, 1.0)

        # Overall confidence calculation
        overall_confidence = (
            grounding_score * 0.5 + authority_score * 0.3 + anti_hallucination_score * 0.2
        )
        overall_confidence = min(overall_confidence, 1.0)

        confidence_dict = {"overall_confidence": overall_confidence}

        # Type-specific confidence scores
        if content_type == "academic":
            # Academic: Higher confidence from grounding + formality
            academic_confidence = min(grounding_score * 1.1, 1.0)
            confidence_dict["academic_confidence"] = academic_confidence

        elif content_type == "news":
            # News: Freshness matters more than grounding
            # Assume recent sources have better freshness
            news_freshness = overall_confidence * 0.95  # Slight discount for recency risk
            confidence_dict["news_freshness_confidence"] = news_freshness

        elif content_type == "technical":
            # Technical: Accuracy from grounding + authority
            technical_accuracy = grounding_score * 0.7 + authority_score * 0.3
            confidence_dict["technical_accuracy_confidence"] = min(technical_accuracy, 1.0)

        return confidence_dict

    # =========================================================================
    # Phase 3: Language-Specific Adaptation Methods
    # =========================================================================

    def _build_language_specific_instructions(self, language: str) -> str:
        """Build language-specific LLM instructions for adapted responses.

        Supports: English, Spanish, French, German

        Each language has specific conventions for:
        - Citation formats
        - Number and date formatting
        - Formal tone and voice
        - Sentence structure preferences

        Args:
            language: ISO 639-1 language code (en, es, fr, de)

        Returns:
            Language-adapted instruction string for LLM prompt injection

        Example:
            >>> instructions = agent._build_language_specific_instructions("es")
            >>> "español" in instructions.lower()
            True
        """
        language_instructions = {
            "en": """ENGLISH-SPECIFIC WRITING CONVENTIONS:
- Use active voice primarily, passive voice for emphasis
- Citation format: Author (Year) [reference]
- Numbers: Use commas for thousands (e.g., 1,000; 1.5 million)
- Dates: Month Day, Year format (e.g., November 12, 2024)
- Sentence structure: Clear topic sentences followed by supporting details
- Contractions acceptable in semi-formal writing
- Use specific examples and concrete evidence""",
            "es": """CONVENCIONES DE ESCRITURA EN ESPAOL:
- Usar voz activa preferentemente
- Formato de citas: Autor (Ao) [referencia]
- Nmeros: Usar puntos para miles (p. ej., 1.000; 1,5 millones)
- Fechas: Formato Da de Mes de Ao (p. ej., 12 de noviembre de 2024)
- Estructura: Oraciones temticas claras con detalles de apoyo
- Evitar construcciones pasivas cuando sea posible
- Usar ejemplos especficos de fuentes confiables""",
            "fr": """CONVENTIONS D'CRITURE EN FRANAIS:
- Utiliser la voix active de prfrence
- Format de citation: Auteur (Anne) [rfrence]
- Nombres: Utiliser des espaces pour les milliers (p. ex., 1 000 ; 1,5 million)
- Dates: Format Jour Mois Anne (p. ex., 12 novembre 2024)
- Structure: Phrases thmatiques claires avec dtails de soutien
- Viter les constructions passives quand possible
- Inclure des exemples spcifiques de sources fiables""",
            "de": """DEUTSCHSPRACHIGE SCHREIBKONVENTIONEN:
- Aktive Stimme bevorzugt verwenden
- Zitierformat: Autor (Jahr) [Referenz]
- Zahlen: Punkte fr Tausender (z. B., 1.000; 1,5 Millionen)
- Daten: Datumsformat Tag. Monat Jahr (z. B., 12. November 2024)
- Struktur: Klare Themenstze mit untersttzenden Details
- Passivkonstruktionen vermeiden, wenn mglich
- Spezifische Beispiele aus zuverlssigen Quellen einbinden""",
        }

        return language_instructions.get(language, language_instructions["en"])

    # =========================================================================
    # Response Templates for Different Query Types
    # =========================================================================

    def _get_response_template(self, sub_queries: list[SubQuery], query: str) -> str:
        """Select appropriate response template based on query intent and keywords.

        Args:
            sub_queries: List of decomposed sub-queries with intent
            query: Original query text

        Returns:
            Template structure string to guide answer generation
        """
        # Determine primary intent from first sub-query
        primary_intent = sub_queries[0].intent if sub_queries else "factual"

        # Check for comparative keywords (override intent)
        comparative_keywords = [
            "vs",
            "versus",
            "compare",
            "comparison",
            "difference between",
            "similar to",
            "unlike",
        ]
        if any(kw in query.lower() for kw in comparative_keywords):
            return self._get_comparative_template()

        # Check for analytical keywords (override intent)
        analytical_keywords = [
            "analyze",
            "trends",
            "outlook",
            "implications",
            "impact",
            "effect",
            "causes",
        ]
        if any(kw in query.lower() for kw in analytical_keywords):
            return self._get_analytical_template()

        # Use intent-based templates
        if primary_intent == "definition":
            return self._get_definition_template()
        elif primary_intent == "opinion":
            return self._get_analytical_template()
        else:  # factual
            return self._get_factual_template()

    def _get_definition_template(self) -> str:
        """Template for definition queries (what is X?)."""
        return """
RESPONSE STRUCTURE FOR DEFINITION:
1. **Core Definition** - Start with a clear, concise definition
2. **Key Characteristics** - List 3-5 important features or properties
3. **How It Works** - Explain the mechanism or process if applicable
4. **Context & Background** - Provide historical context or origin
5. **Related Concepts** - Mention similar or related terms
6. **Practical Applications** - Show how it's used in practice

FORMATTING:
- Use clear section headers
- Number key characteristics and applications
- Include specific examples with citations
- Keep definition in opening paragraph to ~100 words
"""

    def _get_factual_template(self) -> str:
        """Template for factual queries (who, what, when, where)."""
        return """
RESPONSE STRUCTURE FOR FACTUAL INFORMATION:
1. **Overview** - Brief summary of the topic (1-2 sentences)
2. **Key Facts** - Organize by category or chronologically
   - Group related facts together
   - Include: Who, What, When, Where, Why, How
   - Use specific numbers, dates, percentages
3. **Timeline** (if temporal) - List major events/milestones chronologically
4. **Current Status** (if recent query) - Latest information as of today
5. **Significance** - Why these facts matter

FORMATTING:
- Use numbered lists for facts organized by category
- Format dates as "Month DD, YYYY" for clarity
- Include specific metrics and percentages
- Each bullet point should be a complete thought with details
"""

    def _get_comparative_template(self) -> str:
        """Template for comparative queries (X vs Y)."""
        return """
RESPONSE STRUCTURE FOR COMPARATIVE ANALYSIS:
1. **Introduction** - State what's being compared (A and B)
2. **Similarities** - What A and B have in common
   - List 2-4 key similarities with explanations
3. **Key Differences** - Create a comparison breakdown:
   | Aspect | Option A | Option B |
   |--------|----------|----------|
   | Feature 1 | Details | Details |
   | Feature 2 | Details | Details |
4. **Strengths & Weaknesses** - For each option
5. **Use Case Recommendations** - When to choose A vs B
   - Scenario 1: Choose A because...
   - Scenario 2: Choose B because...

FORMATTING:
- Use consistent comparison structure
- Include a comparison table for easy reference
- Highlight key differentiators in bold
- Provide real-world scenarios for each option
"""

    def _get_analytical_template(self) -> str:
        """Template for analytical queries (trends, impact, analysis)."""
        return """
RESPONSE STRUCTURE FOR ANALYTICAL CONTENT:
1. **Background & Context** - Set up the topic
   - What is the current situation?
   - Why is this important?
2. **Landscape Analysis** - Describe the current state
   - Key players or factors involved
   - Market conditions or context
3. **Key Trends & Patterns** - Main observations (3-5 trends)
   - Trend 1: Description with evidence and citations
   - Trend 2: Description with evidence and citations
4. **Underlying Causes** - Why these trends exist
5. **Implications & Outlook** - What this means
   - Short-term impacts
   - Long-term outlook
   - Potential challenges or opportunities
6. **Conclusion** - Synthesis and key takeaways

FORMATTING:
- Use evidence-based language ("data shows", "research indicates")
- Include specific examples with citations
- Distinguish facts from analysis clearly
- Use forward-looking language for implications
"""

    async def generate_answer(
        self, query: str, sources: list[SearchSource], sub_queries: list[SubQuery] | None = None
    ) -> tuple[str, float | None, int | None]:
        """Generate AI answer based on search sources.

        Args:
            query: User's original query
            sources: Retrieved and ranked sources
            sub_queries: Optional sub-queries for intent-based templating

        Returns:
            Tuple of (answer, grounding_score, hallucination_count)
            - answer: AI-generated answer synthesizing the sources
            - grounding_score: Hallucination detection score (0-1)
            - hallucination_count: Number of unsupported claims

        Example:
            >>> answer, grounding, hallucinations = await agent.generate_answer("What are AI agents?", sources)
            >>> assert len(answer) > 100
        """
        if not sources:
            return (
                "I couldn't find enough information to answer your question. Please try rephrasing your query.",
                None,
                None,
            )

        # Build context from sources
        context_parts = []
        for idx, source in enumerate(sources[:7], 1):  # Use top 7 sources
            # Use full content if available, otherwise fall back to snippet
            content_text = source.content if source.content else source.snippet
            # Limit content length per source (max 8000 chars to capture full articles)
            content_text = content_text[:8000] if len(content_text) > 8000 else content_text

            context_parts.append(
                f"[{idx}] {source.title}\nContent: {content_text}\nURL: {source.url}\n"
            )
        context = "\n".join(context_parts)

        # Log content enrichment stats
        enriched_count = sum(1 for s in sources[:7] if s.content)
        logger.info(
            f"📊 Using {enriched_count}/7 sources with full content, {7 - enriched_count} with snippets only"
        )

        # ============ CRITICAL LOG: ANSWER GENERATION INPUT ============
        logger.info(f"💬 ANSWER GENERATION START")
        logger.info(f"📥 Query: '{query}'")
        logger.info(f"📥 Sources: {len(sources)} total, using top 7")
        logger.info(f"📥 Context length: {len(context)} chars")

        # Get response template based on query intent
        response_template = ""
        if sub_queries:
            response_template = self._get_response_template(sub_queries, query)
            logger.info(f"📋 Using query-specific response template")

        # ========== PHASE 2: CONTENT-TYPE ANALYSIS ==========
        # Analyze source composition to adapt response style
        composition = self._analyze_source_composition(sources[:7])
        logger.info(
            f"📊 Source composition: {composition['primary_type']} (academic={composition['academic_ratio']:.0%}, news={composition['news_ratio']:.0%}, technical={composition['technical_ratio']:.0%})"
        )

        # Build content-type-specific instructions
        content_type_instructions = self._build_content_type_instructions(composition)
        format_instructions = self._get_format_instructions(composition)

        if content_type_instructions:
            logger.info(f"📝 Content-type instructions: {len(content_type_instructions)} chars")
        if format_instructions:
            logger.info(f"📝 Format instructions: {len(format_instructions)} chars")

        # ========== BALANCED COVERAGE DETECTION (ANY COMPARISON) ==========
        # Detect any comparison queries (cloud providers, languages, frameworks, etc.)
        # and ensure equal balanced coverage for all items
        comparison_info = self._detect_any_comparison(query)
        balanced_coverage_instructions = self._get_balanced_coverage_instructions(comparison_info)

        if comparison_info["is_comparison"]:
            comparison_type = comparison_info.get("comparison_type", "generic")
            items = comparison_info.get("items", [])
            item_count = comparison_info.get("item_count", 0)

            if comparison_type == "cloud_provider":
                logger.info(
                    f"🔍 Cloud provider comparison detected: {', '.join([p.upper() for p in items])}"
                )
            else:
                logger.info(
                    f"🔍 Multi-item comparison detected: {', '.join([item.title() for item in items])}"
                )

            logger.info(f"📊 Items being compared: {item_count}")
            if balanced_coverage_instructions:
                logger.info(
                    f"📝 Balanced coverage instructions: {len(balanced_coverage_instructions)} chars"
                )

        # ========== PHASE 3 TASK 2: MULTI-LINGUAL ADAPTATION ==========
        # Detect language and build language-specific instructions
        detected_language = sub_queries[0].language if sub_queries else "en"
        language_instructions = self._build_language_specific_instructions(detected_language)
        language_name = get_language_name(detected_language)
        logger.info(f"🌐 Detected language: {language_name} ({detected_language})")
        logger.info(f"📝 Language-specific instructions: {len(language_instructions)} chars")

        # Build prompt for answer generation
        prompt = f"""You are a helpful search assistant. Answer the user's question by extracting and explaining SPECIFIC information from the search results.

User Question: {query}

Search Results:
{context}

MANDATORY REQUIREMENTS:

1. EXTRACT SPECIFIC DETAILS - For EVERY point you make, include:
   ✓ Exact names, products, services, features mentioned in sources
   ✓ Specific numbers, dates, percentages, metrics
   ✓ Direct facts and statements from the sources
   ✗ NO generic statements like "continues to evolve" or "recent updates"
   ✗ NO meta-commentary about "the search results show..."
   
   ⚠️ CRITICAL: DO NOT DESCRIBE THE WEBSITES OR WHAT THEY COVER!
   
   ABSOLUTELY FORBIDDEN - DO NOT WRITE THESE PATTERNS:
   ✗ "ThePrint provides coverage of..." 
   ✗ "CNBC TV18 reports on business news..."
   ✗ "Fox News includes a category for..."
   ✗ "Reuters offers news about..."
   ✗ "Website X covers topics like A, B, C..."
   ✗ "Platform Y is providing insightful analyses..."
   ✗ "Source Z functions as digital platform for..."
   
   IF THE SOURCE ONLY DESCRIBES WEBSITE FEATURES/CATEGORIES:
   → SKIP IT ENTIRELY! Say "No specific news events found in sources"
   
   ONLY WRITE ABOUT ACTUAL EVENTS/FACTS:
   ✓ RIGHT: "India's GDP grew 7.8% in Q2 2024 [1]"
   ✓ RIGHT: "Microsoft announced Azure AI updates on Nov 10, 2024 [2]"
   ✓ RIGHT: "Prime Minister Modi met with US President on Nov 8, 2024 [3]"
   ✓ RIGHT: "Indian rupee weakened to 83.2 against dollar on Nov 11 [4]"

2. EXPLAIN EVERY ITEM - When listing products, services, or features:
   ✗ BAD: "Azure AI Foundry, Azure AI Search, Azure OpenAI [7]"
   ✓ GOOD: 
     "- Azure AI Foundry: Platform for building AI applications [7]
      - Azure AI Search: Vector search and retrieval service [7]
      - Azure OpenAI: Access to GPT-4 and other models [7]"
   
   RULE: Never just list names - always add what they do/are

3. MORE EXAMPLES:
   ✗ BAD: "Growth of 31% [1], stock up 17.9% [1]"
   ✓ GOOD: "Azure cloud revenue grew 31% year-over-year [1], contributing to Microsoft's stock price increase of 17.9% year-to-date [1], driven by enterprise cloud adoption"
   
   ✗ BAD: "Microsoft Ignite 2025 on November 17-21 [2]"
   ✓ GOOD: "Microsoft Ignite 2025 will take place November 17-21, 2025 [2], featuring keynotes on Azure AI capabilities, hands-on labs for developers, and announcements of new cloud services [2]"

4. STRUCTURE with numbered sections and bullet points with descriptions

5. CITE EVERYTHING with [number] after each fact

6. 500+ words - extract and EXPLAIN more details, don't just list

7. NO apologizing or hedging

8. Add context from sources for every claim - "what", "why", "how", "when"

MULTI-SOURCE SYNTHESIS STRATEGY:

1. TRIANGULATION - When multiple sources discuss the same topic:
   ✓ "According to both Microsoft [1] and industry analysts [2][3], Azure revenue grew 31% year-over-year"
   ✗ "Azure revenue grew [1]"

2. CONFLICT RESOLUTION - When sources disagree:
   ✓ "Microsoft reports 31% growth [1], while independent analysis suggests 28-33% [2],
      with the discrepancy likely due to different accounting methods [2]"
   ✗ Ignoring contradictions or cherry-picking one source

3. CHRONOLOGICAL SYNTHESIS - For evolving topics:
   ✓ "Initially announced in March 2024 [1], the feature was enhanced in June [2] and
      reached general availability in October 2024 [3]"
   ✗ Presenting timeline out of order

4. COMPLEMENTARY INTEGRATION - Combining different aspects:
   ✓ "Azure AI Foundry provides the development platform [1], while Azure AI Search
      handles retrieval [2], and Azure OpenAI delivers the language models [3],
      creating an integrated RAG solution [1][2][3]"
   ✗ Listing features separately without integration

5. PRIMARY vs SECONDARY SOURCES - Distinguish authority:
   ✓ "Microsoft's official documentation states [1], which is corroborated by third-party
      testing [2][3]"
   ✗ Treating all sources with equal weight

{response_template}

CONTENT-TYPE ADAPTATION:
Based on the sources provided, adapt your response style accordingly:
{content_type_instructions}{format_instructions}

LANGUAGE-SPECIFIC CONVENTIONS:
{language_instructions}

{balanced_coverage_instructions}

Write a detailed answer with full explanations for everything:"""

        # ============ CRITICAL LOG: LLM CALL FOR ANSWER ============
        logger.info(f"🤖 LLM CALL: Answer Generation")
        logger.info(f"📤 Model: google/gemini-2.5-flash-lite (final answer generation)")
        logger.info(f"📤 Temperature: 0.7, Max Tokens: 2048")
        logger.info(f"📤 Prompt length: {len(prompt)} chars")

        # ============ FULL PROMPT LOGGING ============
        logger.info("=" * 80)
        logger.info("� FULL LLM INPUT (SEARCH - ANSWER GENERATION)")
        logger.info("=" * 80)
        logger.info(prompt)
        logger.info("=" * 80)

        try:
            # Use synthesis model for final answer generation (if configured)
            from src.core.config import settings

            original_model = self.deps.llm_client.model
            if settings.SYNTHESIS_LLM_MODEL:
                self.deps.llm_client.model = settings.SYNTHESIS_LLM_MODEL
                logger.info(f"Using synthesis model: {settings.SYNTHESIS_LLM_MODEL}")

            response = await self.deps.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048,  # Allow longer, more detailed responses
            )

            # Restore original model
            self.deps.llm_client.model = original_model

            # ============ CRITICAL LOG: LLM RESPONSE ============
            logger.info(f"📥 LLM RESPONSE received")

            # Extract answer from response
            if isinstance(response, dict) and "content" in response:
                answer = response["content"].strip()
                word_count = len(answer.split())
                logger.info(f"📥 Answer length: {len(answer)} chars, {word_count} words")

                # ============ FULL RESPONSE LOGGING ============
                logger.info("=" * 80)
                logger.info("📥 FULL LLM OUTPUT (SEARCH - ANSWER)")
                logger.info("=" * 80)
                logger.info(answer)
                logger.info("=" * 80)

                # ========== TASK 1: HALLUCINATION DETECTION ==========
                grounding_score = None
                hallucination_count = None

                try:
                    # Convert sources to citations for grounding check
                    citations = [
                        Citation(
                            source_id=str(i),
                            title=source.title,
                            url=source.url,
                            excerpt=source.content if source.content else source.snippet,
                            relevance=source.relevance,
                        )
                        for i, source in enumerate(sources[:7], 1)
                    ]

                    # Initialize claim grounder and run grounding analysis
                    claim_grounder = ClaimGrounder(
                        embedding_service=self.deps.embedding_service,
                        grounding_threshold=0.6,
                        similarity_threshold=0.7,
                    )

                    grounding_result = await claim_grounder.ground_synthesis(answer, citations)
                    grounding_score = grounding_result.overall_grounding
                    hallucination_count = grounding_result.hallucination_count

                    # Safety check for claims
                    if not grounding_result.claims:
                        logger.warning(
                            "⚠️ No claims extracted from answer, skipping hallucination detection"
                        )
                        grounding_result.claims = []

                    logger.info(f"✅ HALLUCINATION DETECTION COMPLETE")
                    logger.info(f"📊 Grounding Score: {grounding_score:.2f}/1.0")
                    logger.info(
                        f"📊 Hallucination Count: {hallucination_count}/{len(grounding_result.claims)} claims"
                    )

                    # ========== TWO-PASS SYNTHESIS: REGENERATION IF NEEDED ==========
                    if grounding_result.hallucination_count > 0 and grounding_result.claims:
                        hallucination_rate = grounding_result.hallucination_count / len(
                            grounding_result.claims
                        )

                        # Get configurable threshold from settings (default: 10%)
                        from src.core.config import settings

                        hallucination_threshold = settings.HALLUCINATION_THRESHOLD

                        logger.info(
                            f"📊 Hallucination Detection: {hallucination_rate:.1%} rate "
                            f"(threshold: {hallucination_threshold:.1%})"
                        )

                        # Trigger regeneration if above threshold
                        if hallucination_rate > hallucination_threshold:
                            logger.warning(
                                f"⚠️ High hallucination rate detected: {hallucination_rate:.1%} > {hallucination_threshold:.1%} - TRIGGERING REGENERATION"
                            )

                            # Identify hallucinated claims for correction
                            hallucinated_claims = [
                                claim for claim in grounding_result.claims if not claim.is_grounded
                            ]

                            logger.info(f"🔄 PASS 2: REGENERATING with DeepSeek R1 (free)")
                            logger.info(
                                f"📝 Correcting {len(hallucinated_claims)} unsupported claims"
                            )

                            # Build correction prompt with explicit unsupported claims
                            correction_context = "\n\n".join(
                                [
                                    f"**UNSUPPORTED CLAIM {i + 1}**: {claim.text}\n"
                                    f"Grounding Score: {claim.grounding_score:.2f} (threshold: 0.6)\n"
                                    f"Supporting Sources: {len(claim.supporting_sources)} found"
                                    for i, claim in enumerate(
                                        hallucinated_claims[:5]
                                    )  # Top 5 worst
                                ]
                            )

                            regeneration_prompt = f"""You are a fact-checking editor. The draft answer below contains unsupported claims.

**ORIGINAL QUERY**: {query}

**DRAFT ANSWER** (contains hallucinations):
{answer}

**UNSUPPORTED CLAIMS** (must be corrected or removed):
{correction_context}

**VERIFIED SOURCES** (use ONLY these):
{chr(10).join([f"[{i + 1}] {s.title} - {s.content[:300]}..." for i, s in enumerate(sources[:7])])}

**INSTRUCTIONS**:
1. Remove or rewrite each unsupported claim
2. Use ONLY information from verified sources
3. Add explicit citations [1], [2], etc.
4. If a claim cannot be verified, say "Sources do not provide information about..."
5. Maintain the same tone and structure as the original
6. Keep the answer comprehensive but factual

Generate the corrected answer:"""

                            try:
                                # Use Gemini 2.0 Flash for hallucination correction (more reliable than DeepSeek R1)
                                regeneration_response = await self._run_llm_chat(
                                    messages=[{"role": "user", "content": regeneration_prompt}],
                                    temperature=0.3,  # Lower for accuracy
                                    max_tokens=2048,
                                    model_override="google/gemini-2.0-flash-exp:free",  # Gemini for regeneration
                                )

                                if (
                                    isinstance(regeneration_response, dict)
                                    and "content" in regeneration_response
                                ):
                                    corrected_answer = regeneration_response["content"].strip()

                                    # Verify improvement by re-grounding
                                    corrected_grounding = await claim_grounder.ground_synthesis(
                                        corrected_answer, citations
                                    )

                                    # Check if re-grounding was successful
                                    if corrected_grounding and corrected_grounding.claims:
                                        improvement = (
                                            grounding_result.hallucination_count
                                            - corrected_grounding.hallucination_count
                                        )

                                        if improvement > 0:
                                            logger.info(
                                                f"✅ REGENERATION SUCCESSFUL: Reduced hallucinations by {improvement}"
                                            )
                                            logger.info(
                                                f"📊 New Grounding Score: {corrected_grounding.overall_grounding:.2f} "
                                                f"(was {grounding_score:.2f})"
                                            )

                                            # Use corrected answer
                                            answer = corrected_answer
                                            grounding_score = corrected_grounding.overall_grounding
                                            hallucination_count = (
                                                corrected_grounding.hallucination_count
                                            )
                                            grounding_result = corrected_grounding
                                        else:
                                            logger.warning(
                                                "⚠️ Regeneration did not improve quality - keeping original"
                                            )
                                    else:
                                        logger.warning(
                                            "⚠️ Regeneration grounding failed, keeping original"
                                        )

                            except Exception as regen_error:
                                logger.error(f"❌ Regeneration failed: {regen_error}")
                                logger.info("Continuing with original answer")
                        else:
                            logger.info(
                                f"✓ Hallucination rate within acceptable range: {hallucination_rate:.1%} <= {hallucination_threshold:.1%}"
                            )

                    # ========== PHASE 3 TASK 1: CITATION QUALITY VERIFICATION ==========
                    # Grade citation authority levels
                    for citation in citations:
                        citation.authority_level = claim_grounder._grade_citation_authority(
                            citation
                        )

                    logger.info(f"📊 Citation Authority Grading Complete")
                    authority_breakdown = {}
                    for citation in citations:
                        authority_breakdown[citation.authority_level] = (
                            authority_breakdown.get(citation.authority_level, 0) + 1
                        )
                    logger.info(f"📊 Authority Distribution: {authority_breakdown}")

                    # Calculate citation quality for each claim
                    if grounding_result.claims:
                        for claim in grounding_result.claims:
                            claim.citation_quality_score = (
                                await claim_grounder.calculate_citation_quality(claim, citations)
                            )
                            # Set best citation authority level
                            if claim.supporting_sources:
                                best_citation = next(
                                    (
                                        c
                                        for c in citations
                                        if c.source_id == claim.supporting_sources[0]
                                    ),
                                    None,
                                )
                                if best_citation:
                                    claim.citation_authority_level = best_citation.authority_level

                        logger.info(f"✅ CITATION QUALITY VERIFICATION COMPLETE")
                        avg_quality = (
                            sum(c.citation_quality_score for c in grounding_result.claims)
                            / len(grounding_result.claims)
                            if grounding_result.claims
                            else 0
                        )
                        logger.info(f"📊 Average Citation Quality: {avg_quality:.2f}/1.0")

                        # Reorder claims by citation quality
                        reordered_claims = claim_grounder._reorder_claims_by_citation_quality(
                            grounding_result.claims
                        )
                        if reordered_claims != grounding_result.claims:
                            logger.info(
                                f"📊 Reordered {len(reordered_claims)} claims by citation quality"
                            )
                            best_citation_authority = (
                                reordered_claims[0].citation_authority_level
                                if reordered_claims
                                else "unknown"
                            )
                            logger.info(f"📊 Best claim authority: {best_citation_authority}")

                    # ========== PHASE 3 TASK 5: CONFIDENCE SCORING ==========
                    # Calculate response confidence with per-type metrics
                    total_claims = len(grounding_result.claims)
                    confidence_scores = self._calculate_response_confidence(
                        grounding_score=grounding_score,
                        content_type=composition["primary_type"],
                        hallucination_count=hallucination_count,
                        total_claims=total_claims,
                    )

                    logger.info(f"✅ CONFIDENCE SCORING COMPLETE")
                    logger.info(
                        f"📊 Overall Confidence: {confidence_scores['overall_confidence']:.2f}/1.0"
                    )

                    # Log type-specific confidence
                    for score_type, score_value in confidence_scores.items():
                        if score_type != "overall_confidence":
                            logger.info(
                                f"📊 {score_type.replace('_', ' ').title()}: {score_value:.2f}/1.0"
                            )

                except Exception as e:
                    logger.warning(f"⚠️ Hallucination detection failed: {e}")
                    logger.info(
                        "Continuing with answer generation (hallucination metrics unavailable)"
                    )

                logger.info(f"✅ ANSWER GENERATION COMPLETE")
                return (answer, grounding_score, hallucination_count)
            else:
                logger.warning("⚠️ LLM response format unexpected, using fallback")
                logger.warning(
                    f"Response type: {type(response)}, keys: {response.keys() if isinstance(response, dict) else 'N/A'}"
                )
                fallback_answer = self._generate_fallback_answer(query, sources)
                return (fallback_answer, None, None)

        except Exception as e:
            logger.error(f"❌ Error generating answer: {e}")
            fallback_answer = self._generate_fallback_answer(query, sources)
            return (fallback_answer, None, None)

    def _generate_fallback_answer(self, query: str, sources: list[SearchSource]) -> str:
        """Generate a simple fallback answer if LLM fails.

        Args:
            query: User's query
            sources: Retrieved sources

        Returns:
            Simple concatenated answer from snippets
        """
        if not sources:
            return "No information found."

        # Combine top 3 snippets
        snippets = [s.snippet for s in sources[:3]]
        answer = f"Based on the search results:\n\n{' '.join(snippets)}"
        return answer

    # =========================================================================
    # Cascading Fallback Strategy (SearxNG → SerperDev → Perplexity)
    # =========================================================================

    async def _execute_search_tier(
        self, tier: str, query: str, sub_queries: list[SubQuery], mode: SearchMode
    ) -> tuple[str, list[SearchSource], float | None, int | None]:
        """Execute search in a specific tier.

        Args:
            tier: Search tier ("searxng", "serperdev", "perplexity")
            query: Original user query
            sub_queries: Decomposed sub-queries
            mode: Search mode configuration

        Returns:
            Tuple of (answer, sources, grounding_score, hallucination_count)
        """
        logger.info(f"🔍 Tier {tier.upper()}: Starting search")

        if tier == "perplexity":
            # Tier 3: Perplexity - returns ready-to-use answer
            return await self._execute_perplexity_fallback(query)

        # Tier 1 (searxng) or Tier 2 (serperdev): Execute normal search pipeline
        raw_sources = await self.coordinate_search(sub_queries)

        logger.info(f"📊 Tier {tier.upper()}: Got {len(raw_sources)} raw sources")

        # Enrich with content if enabled
        if mode.config.enable_crawling:
            enriched_sources = await self.enrich_sources_with_content(raw_sources)
        else:
            enriched_sources = raw_sources

        # Temporal validation
        target_year = None
        temporal_scope = "any"
        for sq in sub_queries:
            if sq.specific_year:
                target_year = sq.specific_year
                break
            elif sq.temporal_scope != "any":
                temporal_scope = sq.temporal_scope

        validated_sources = self.temporal_validator.filter_and_rerank_sources(
            sources=enriched_sources,
            target_year=target_year,
            temporal_scope=temporal_scope,
            strict_filtering=False,
        )

        # Rank results
        ranked_sources = await self.rank_results(validated_sources, query)

        # Generate answer
        answer, grounding_score, hallucination_count = await self.generate_answer(
            query, ranked_sources, sub_queries
        )

        logger.info(
            f"✅ Tier {tier.upper()}: Generated answer "
            f"({len(answer)} chars, {len(ranked_sources)} sources)"
        )

        return answer, ranked_sources, grounding_score, hallucination_count

    async def _execute_perplexity_fallback(
        self, query: str
    ) -> tuple[str, list[SearchSource], float | None, int | None]:
        """Execute Perplexity as ultimate fallback.

        Args:
            query: User query

        Returns:
            Tuple of (answer, sources, grounding_score, hallucination_count)
        """
        logger.info("🚨 TIER 3 - PERPLEXITY FALLBACK")

        try:
            # Call Perplexity API
            result = await perplexity_search(query)

            # Extract answer and convert citations to SearchSource
            answer = result.get("content", "")
            citations = result.get("citations", [])

            # Convert Perplexity citations to SearchSource format
            sources = []
            for idx, url in enumerate(citations[:10], 1):
                sources.append(
                    SearchSource(
                        title=f"Source {idx}",
                        url=url,
                        snippet=f"From Perplexity search",
                        content="",
                        relevance=0.9,
                        source_type="perplexity",
                    )
                )

            logger.info(
                f"✅ Perplexity fallback success: {len(answer)} chars, {len(sources)} citations"
            )

            return answer, sources, None, None

        except Exception as e:
            logger.error(f"❌ Perplexity fallback failed: {e}")

            # Ultimate fallback: minimal answer
            fallback_answer = (
                "I apologize, but all search sources are currently unavailable. "
                "Please try again in a moment."
            )
            return fallback_answer, [], None, None

    def _check_answer_quality(
        self, answer: str, sources: list[SearchSource], tier: str
    ) -> ResponseQuality:
        """Check if answer meets quality thresholds.

        Args:
            answer: Generated answer
            sources: Sources used
            tier: Search tier name (for logging)

        Returns:
            ResponseQuality assessment
        """
        quality = self.response_validator.validate(answer=answer, source_count=len(sources))

        logger.info(
            f"📊 Tier {tier.upper()} Quality Check: "
            f"sufficient={quality.is_sufficient}, "
            f"tokens={quality.token_count}, "
            f"confidence={quality.confidence_score:.2f}"
        )

        if not quality.is_sufficient:
            logger.warning(
                f"⚠️ Tier {tier.upper()} quality issues: {', '.join([i.value for i in quality.issues])}"
            )

        return quality

    async def _generate_answer_with_fallback(
        self,
        query: str,
        sub_queries: list[SubQuery],
        initial_sources: list[SearchSource],
        mode: SearchMode,
    ) -> tuple[str, list[SearchSource], float | None, int | None]:
        """Generate answer with cascading fallback strategy.

        Tier 1: SearxNG (already executed) → Generate answer → Check quality
        Tier 2: SerperDev → Generate answer → Check quality
        Tier 3: Perplexity → Use Perplexity's answer directly

        Args:
            query: User query
            sub_queries: Decomposed sub-queries
            initial_sources: Sources from Tier 1 (SearxNG)
            mode: Search mode

        Returns:
            Tuple of (answer, sources, grounding_score, hallucination_count)
        """
        logger.info("🔄 CASCADING FALLBACK: Starting quality-based search cascade")

        # Tier 1: Try with existing SearxNG sources
        answer, grounding_score, hallucination_count = await self.generate_answer(
            query, initial_sources, sub_queries
        )

        quality = self._check_answer_quality(answer, initial_sources, "searxng")

        if quality.is_sufficient:
            logger.info("✅ TIER 1 (SearxNG) - Quality sufficient, using this answer")
            return answer, initial_sources, grounding_score, hallucination_count

        # Tier 2: Fallback to SerperDev if available
        if self.deps.serperdev_api_key and self.deps.serperdev_api_key.strip():
            logger.warning(
                f"⚠️ TIER 1 failed quality check (tokens={quality.token_count}, "
                f"issues={[i.value for i in quality.issues]}), trying TIER 2 (SerperDev)"
            )

            try:
                (
                    answer,
                    sources,
                    grounding_score,
                    hallucination_count,
                ) = await self._execute_search_tier(
                    tier="serperdev", query=query, sub_queries=sub_queries, mode=mode
                )

                quality = self._check_answer_quality(answer, sources, "serperdev")

                if quality.is_sufficient:
                    logger.info("✅ TIER 2 (SerperDev) - Quality sufficient, using this answer")
                    return answer, sources, grounding_score, hallucination_count

            except Exception as e:
                logger.error(f"❌ TIER 2 (SerperDev) failed: {e}")

        # Tier 3: Ultimate fallback to Perplexity if enabled
        if settings.PERPLEXITY_AS_FALLBACK and settings.PERPLEXITY_API_KEY:
            logger.warning(
                f"⚠️ TIER 2 failed or unavailable, trying TIER 3 (Perplexity) - ultimate fallback"
            )

            try:
                (
                    answer,
                    sources,
                    grounding_score,
                    hallucination_count,
                ) = await self._execute_perplexity_fallback(query=query)

                logger.info("✅ TIER 3 (Perplexity) - Ultimate fallback used")
                return answer, sources, grounding_score, hallucination_count

            except Exception as e:
                logger.error(f"❌ TIER 3 (Perplexity) failed: {e}")

        # All tiers failed - return best available answer (Tier 1)
        logger.warning(
            "⚠️ All fallback tiers exhausted, returning TIER 1 answer despite quality issues"
        )
        return answer, initial_sources, grounding_score, hallucination_count

    async def validate_output(self, output: SearchOutput) -> SearchOutput:
        """Validate search output meets quality criteria.

        Args:
            output: SearchOutput to validate

        Returns:
            Validated SearchOutput

        Raises:
            ModelRetry: If output doesn't meet quality criteria
        """
        # Validate minimum sources requirement
        if len(output.sources) < self.deps.min_sources:
            raise ModelRetry(
                f"Need at least {self.deps.min_sources} sources, got {len(output.sources)}"
            )

        # Validate minimum confidence threshold
        if output.confidence < self.deps.min_confidence:
            raise ModelRetry(
                f"Confidence {output.confidence:.2f} below minimum {self.deps.min_confidence:.2f}"
            )

        return output

    async def run(
        self,
        query: str,
        mode: SearchMode | str | None = None,
    ) -> SearchOutput:
        """Execute full search workflow with configurable mode.

        Args:
            query: User's search query
            mode: Search mode (SPEED/BALANCED/DEEP) or mode string or None (defaults to BALANCED)

        Returns:
            SearchOutput with results, metadata

        Example:
            >>> result = await agent.run("What are AI agents?", mode=SearchMode.DEEP)
            >>> print(f"Confidence: {result.confidence:.2f}")
            >>> print(f"Sources: {len(result.sources)}")
        """
        import time

        # Parse mode
        if isinstance(mode, str):
            search_mode = get_mode_from_string(mode)
        elif mode is None:
            search_mode = SearchMode.BALANCED
        else:
            search_mode = mode

        config = search_mode.config

        # Auto-enable recency boost for news/current event queries
        is_news_query = any(
            keyword in query.lower()
            for keyword in ["news", "latest", "current", "recent", "today", "update", "breaking"]
        )

        logger.info(
            "Starting search with mode",
            query=query,
            mode=search_mode.value,
            max_sources=config.max_sources,
            timeout=config.timeout,
            news_query=is_news_query,
        )

        start_time = time.time()

        # Apply mode configuration
        original_max_sources = self.max_sources
        original_enable_reranking = self.deps.enable_reranking
        original_max_crawl_urls = self.deps.max_crawl_urls
        original_enable_recency_boost = self.deps.enable_recency_boost

        self.max_sources = config.max_sources
        self.deps.enable_reranking = config.enable_reranking

        # Auto-enable recency boost for news queries to rank recent content higher
        if is_news_query and not self.deps.enable_recency_boost:
            self.deps.enable_recency_boost = True
            logger.info("📰 Auto-enabled recency boost for news query")

        # Adjust max_crawl_urls based on mode for better performance
        # BALANCED: crawl top 5 (half of sources) for speed
        # DEEP: crawl all sources for comprehensiveness
        if search_mode == SearchMode.BALANCED:
            self.deps.max_crawl_urls = min(5, config.max_sources // 2)
        elif search_mode == SearchMode.DEEP:
            self.deps.max_crawl_urls = config.max_sources
        # SPEED doesn't crawl, so no need to set

        try:
            # 1. Decompose query
            sub_queries = await self.decompose_query(query)

            # 2. Coordinate search
            raw_sources = await self.coordinate_search(sub_queries)

            # 3. Enrich sources with full content (crawl URLs) - only if enabled by mode
            if config.enable_crawling:
                enriched_sources = await self.enrich_sources_with_content(raw_sources)
            else:
                # SPEED mode: skip crawling, use snippets only
                logger.info("Crawling disabled by mode, using snippets only")
                enriched_sources = raw_sources

            # 3.5. Temporal validation (post-retrieval filtering - Big Tech approach)
            logger.info(f"🕒 TEMPORAL VALIDATION START")
            logger.info(f"📊 Input: {len(enriched_sources)} sources before validation")

            # Extract temporal intent from sub_queries
            target_year = None
            temporal_scope = "any"

            for sq in sub_queries:
                if sq.specific_year:
                    target_year = sq.specific_year
                    logger.info(f"  Detected target year: {target_year}")
                    break
                elif sq.temporal_scope != "any":
                    temporal_scope = sq.temporal_scope
                    logger.info(f"  Detected temporal scope: {temporal_scope}")

            # Apply temporal validation (penalize mismatched sources)
            validated_sources = self.temporal_validator.filter_and_rerank_sources(
                sources=enriched_sources,
                target_year=target_year,
                temporal_scope=temporal_scope,
                strict_filtering=False,  # Penalize, don't remove
            )

            logger.info(f"✅ TEMPORAL VALIDATION COMPLETE")
            logger.info(f"📊 Output: {len(validated_sources)} sources after validation")

            # 4. Rank results (reranking controlled by mode config)
            ranked_sources = await self.rank_results(validated_sources, query)

            # 5. Generate answer with cascading fallback if enabled
            if settings.ENABLE_CASCADING_FALLBACK:
                (
                    answer,
                    ranked_sources,
                    grounding_score,
                    hallucination_count,
                ) = await self._generate_answer_with_fallback(
                    query=query,
                    sub_queries=sub_queries,
                    initial_sources=ranked_sources,
                    mode=search_mode,
                )
            else:
                # Standard answer generation without fallback
                answer, grounding_score, hallucination_count = await self.generate_answer(
                    query, ranked_sources, sub_queries
                )

            execution_time = time.time() - start_time

            # 6. Build output
            output = SearchOutput(
                answer=answer,
                sub_queries=sub_queries,
                sources=ranked_sources,
                execution_time=execution_time,
                confidence=0.8,  # Default confidence
                grounding_score=grounding_score,
                hallucination_count=hallucination_count,
            )

            # 7. Validate output
            output = await self.validate_output(output)

            logger.info(
                "Search complete",
                mode=search_mode.value,
                num_sources=len(ranked_sources),
                execution_time=execution_time,
            )

            return output

        finally:
            # Restore original settings
            self.max_sources = original_max_sources
            self.deps.enable_reranking = original_enable_reranking
            self.deps.max_crawl_urls = original_max_crawl_urls
            self.deps.enable_recency_boost = original_enable_recency_boost
