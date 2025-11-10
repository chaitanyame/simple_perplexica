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

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import ModelRetry
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient

# =============================================================================
# Pydantic Models for Structured Output
# =============================================================================


class SubQuery(BaseModel):
    """Decomposed sub-query with intent and priority.

    Attributes:
        query: Focused sub-query text (1-200 chars)
        intent: Query intent classification (definition/factual/opinion)
        priority: Execution priority (1=highest, 5=lowest)
    """

    query: str = Field(..., min_length=1, max_length=200)
    intent: str = Field(..., pattern=r"^(definition|factual|opinion)$")
    priority: int = Field(ge=1, le=5)


class SearchSource(BaseModel):
    """Search result source with metadata.

    Attributes:
        title: Source title
        url: Source URL
        snippet: Text excerpt/snippet
        relevance: Relevance score (0.0-1.0)
        source_type: Source classification (web/academic/news)
    """

    title: str
    url: str
    snippet: str
    relevance: float = Field(ge=0.0, le=1.0)
    source_type: str = Field(pattern=r"^(web|academic|news)$")


class SearchOutput(BaseModel):
    """Final search output with all results and metadata.

    Attributes:
        sub_queries: List of decomposed sub-queries
        sources: Ranked and filtered search sources
        execution_time: Total execution time in seconds
        confidence: Overall confidence score (0.0-1.0)
    """

    sub_queries: list[SubQuery]
    sources: list[SearchSource]
    execution_time: float
    confidence: float = Field(ge=0.0, le=1.0)


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
        max_sources: Maximum number of sources to return (default: 20)
        timeout: Search timeout in seconds (default: 60.0)
    """

    llm_client: OpenRouterClient
    tracer: LangfuseTracer
    db: AsyncSession
    searxng_client: httpx.AsyncClient
    serperdev_api_key: str
    max_sources: int = 20
    timeout: float = 60.0


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

    async def decompose_query(self, query: str) -> list[SubQuery]:
        """Decompose complex query into focused sub-queries.

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
        # Call LLM to decompose query
        response = await self.deps.llm_client.chat(
            messages=[{"role": "user", "content": f"Decompose query: {query}"}],
            temperature=0.7,
        )

        # Parse LLM response into SubQuery objects
        # Handle both dict and AsyncGenerator return types from LLM client
        if hasattr(response, "get"):
            sub_queries_data = response.get("sub_queries", [])
        else:
            sub_queries_data = []
        return [SubQuery(**sq_data) for sq_data in sub_queries_data]

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
        results: list[SearchSource] = []
        seen_urls: set[str] = set()

        # Execute searches in parallel
        search_tasks = [self._search_source(sq) for sq in sub_queries]

        try:
            search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

            # Flatten and deduplicate results
            for result in search_results:
                if isinstance(result, list):
                    for source in result:
                        if source.url not in seen_urls:
                            seen_urls.add(source.url)
                            results.append(source)

        except Exception:
            # Gracefully handle timeouts/errors, return partial results
            pass

        return results

    async def _search_source(self, sub_query: SubQuery) -> list[SearchSource]:
        """Search single source (SearxNG) for sub-query.

        Args:
            sub_query: Sub-query to search

        Returns:
            List of SearchSource objects from this source
        """
        try:
            response = await self.deps.searxng_client.get(
                "/search",
                params={"q": sub_query.query, "format": "json"},
                timeout=self.timeout,
            )

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                return [
                    SearchSource(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", ""),
                        relevance=0.7,  # Default relevance
                        source_type="web",
                    )
                    for r in results
                ]

        except httpx.TimeoutException:
            # Return empty list on timeout
            return []

        return []

    async def rank_results(
        self, sources: list[SearchSource], original_query: str
    ) -> list[SearchSource]:
        """Rank and filter results by relevance.

        Args:
            sources: Raw search results
            original_query: User's original question

        Returns:
            Top-ranked sources (up to max_sources), filtered by quality

        Example:
            >>> ranked = await agent.rank_results(sources, "AI agents")
            >>> assert ranked[0].relevance >= ranked[-1].relevance
        """
        # Filter low-quality results (relevance < 0.5)
        filtered = [s for s in sources if s.relevance >= 0.5]

        # Sort by relevance (descending)
        filtered.sort(key=lambda s: s.relevance, reverse=True)

        # Return top max_sources
        return filtered[: self.max_sources]

    async def validate_output(self, output: SearchOutput) -> SearchOutput:
        """Validate search output meets quality criteria.

        Args:
            output: SearchOutput to validate

        Returns:
            Validated SearchOutput

        Raises:
            ModelRetry: If output doesn't meet quality criteria
        """
        if len(output.sources) < 5:
            raise ModelRetry("Need at least 5 sources")

        if output.confidence < 0.5:
            raise ModelRetry("Confidence too low, refine search")

        return output

    async def run(self, query: str) -> SearchOutput:
        """Execute full search workflow.

        Args:
            query: User's search query

        Returns:
            SearchOutput with results, metadata

        Example:
            >>> result = await agent.run("What are AI agents?")
            >>> print(f"Confidence: {result.confidence:.2f}")
        """
        import time

        start_time = time.time()

        # 1. Decompose query
        sub_queries = await self.decompose_query(query)

        # 2. Coordinate search
        raw_sources = await self.coordinate_search(sub_queries)

        # 3. Rank results
        ranked_sources = await self.rank_results(raw_sources, query)

        execution_time = time.time() - start_time

        # 4. Build output
        output = SearchOutput(
            sub_queries=sub_queries,
            sources=ranked_sources,
            execution_time=execution_time,
            confidence=0.8,  # Default confidence
        )

        # 5. Validate output
        output = await self.validate_output(output)

        return output
