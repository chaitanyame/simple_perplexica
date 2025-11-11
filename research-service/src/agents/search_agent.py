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

import structlog

logger = structlog.get_logger(__name__)

import httpx
from pydantic import BaseModel, Field
from pydantic_ai import ModelRetry
from sqlalchemy.ext.asyncio import AsyncSession

from src.services.crawl.crawl4ai_client import Crawl4AIClient
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
        snippet: Text excerpt/snippet from search results
        content: Full extracted content from URL (populated by crawling)
        relevance: Relevance score (0.0-1.0)
        source_type: Source classification (web/academic/news)
    """

    title: str
    url: str
    snippet: str
    content: str | None = None  # Full content from crawling
    relevance: float = Field(ge=0.0, le=1.0)
    source_type: str = Field(pattern=r"^(web|academic|news)$")


class QueryDecomposition(BaseModel):
    """Result of query decomposition.
    
    Attributes:
        sub_queries: List of decomposed sub-queries
    """
    sub_queries: list[SubQuery] = Field(
        ..., 
        min_length=1, 
        max_length=5,
        description="1-5 focused sub-queries"
    )


class SearchOutput(BaseModel):
    """Final search output with all results and metadata.

    Attributes:
        answer: AI-generated answer synthesizing the sources
        sub_queries: List of decomposed sub-queries
        sources: Ranked and filtered search sources
        execution_time: Total execution time in seconds
        confidence: Overall confidence score (0.0-1.0)
    """

    answer: str = Field(..., min_length=1, description="AI-generated answer")
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
        crawl_client: Crawl4AI client for URL content extraction
        max_sources: Maximum number of sources to return (default: 20)
        timeout: Search timeout in seconds (default: 60.0)
        enable_crawling: Whether to crawl URLs for full content (default: True)
        max_crawl_urls: Maximum URLs to crawl for content (default: 5)
    """

    llm_client: OpenRouterClient
    tracer: LangfuseTracer
    db: AsyncSession
    searxng_client: httpx.AsyncClient
    serperdev_api_key: str
    crawl_client: Crawl4AIClient
    max_sources: int = 20
    timeout: float = 60.0
    min_sources: int = 5  # Minimum required sources for valid output
    min_confidence: float = 0.5  # Minimum confidence threshold
    enable_crawling: bool = True  # Enable URL crawling
    max_crawl_urls: int = 5  # Maximum URLs to crawl


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

        # Log search configuration
        if deps.serperdev_api_key and deps.serperdev_api_key.strip():
            logger.info(f"SearchAgent initialized with SerperDev (primary) + SearxNG (fallback)")
        else:
            logger.info(f"SearchAgent initialized with SearxNG only (no SerperDev key)")

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
        logger.info(f"🧩 Decomposing query: {query}")

        # Use OpenRouter LLM directly with JSON mode for structured decomposition
        system_prompt = """You are a query decomposition expert. Break down user queries into focused sub-queries.

Guidelines:
- Simple queries (1 topic): Return 1-2 sub-queries
- Complex queries (multiple topics): Return 2-4 sub-queries  
- Each sub-query should be specific and searchable
- Intent types: "factual" (facts/data), "definition" (what is X), "opinion" (views/analysis)
- Priority: 1 (most important) to 5 (least important)

Examples:
Query: "What are AI agents?"
Response:
{
  "sub_queries": [
    {"query": "What are AI agents?", "intent": "definition", "priority": 1}
  ]
}

Query: "Recent news about Microsoft Azure and AWS"
Response:
{
  "sub_queries": [
    {"query": "Microsoft Azure recent news", "intent": "factual", "priority": 1},
    {"query": "AWS recent news", "intent": "factual", "priority": 2}
  ]
}

Respond with valid JSON only."""

        try:
            import json
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Query: {query}\n\nDecompose this into sub-queries."}
            ]
            
            # Use OpenRouter client directly with JSON mode
            response = await self.deps.llm_client.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},  # Force JSON output
            )
            
            # Parse JSON response
            content = response["content"].strip()
            logger.info(f"📄 Raw LLM response (JSON):\n{content}")
            
            data = json.loads(content)
            logger.info(f"✅ Parsed JSON data: {data}")
            
            # Validate and convert to SubQuery objects
            decomposition = QueryDecomposition(**data)
            logger.info(f"🎯 Successfully decomposed into {len(decomposition.sub_queries)} sub-queries:")
            for i, sq in enumerate(decomposition.sub_queries, 1):
                logger.info(f"  [{i}] Query: '{sq.query}'")
                logger.info(f"      Intent: {sq.intent}, Priority: {sq.priority}")
            return decomposition.sub_queries
            
        except Exception as e:
            logger.error(f"❌ Query decomposition failed: {e}, using fallback")
            # Fallback: treat as single factual query
            return [SubQuery(query=query, intent="factual", priority=1)]

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
                    logger.error(f"  Search task {idx+1} failed with exception: {result}")
                elif isinstance(result, list):
                    logger.info(f"  Search task {idx+1} returned {len(result)} sources")
                    for source in result:
                        if source.url not in seen_urls:
                            seen_urls.add(source.url)
                            results.append(source)
                else:
                    logger.warning(f"  Search task {idx+1} returned unexpected type: {type(result)}")

        except Exception as e:
            # Gracefully handle timeouts/errors, return partial results
            logger.error(f"❌ Exception during search coordination: {e}")

        logger.info(f"✅ Coordination complete: {len(results)} unique sources found")
        return results

    async def _search_source(self, sub_query: SubQuery) -> list[SearchSource]:
        """Search using SerperDev (primary) or SearxNG (fallback).

        Args:
            sub_query: Sub-query to search

        Returns:
            List of SearchSource objects from this source
        """
        # Try SerperDev first if API key is available
        if self.deps.serperdev_api_key and self.deps.serperdev_api_key.strip():
            logger.info(f"🔍 Trying SerperDev for query: {sub_query.query}")
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://google.serper.dev/search",
                        headers={
                            "X-API-KEY": self.deps.serperdev_api_key,
                            "Content-Type": "application/json",
                        },
                        json={"q": sub_query.query, "num": 10},
                        timeout=self.timeout,
                    )

                    logger.info(f"SerperDev response status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        organic = data.get("organic", [])

                        logger.info(
                            f"✅ SerperDev returned {len(organic)} results for: {sub_query.query}"
                        )

                        if len(organic) > 0:
                            return [
                                SearchSource(
                                    title=r.get("title", ""),
                                    url=r.get("link", ""),
                                    snippet=r.get("snippet", ""),
                                    relevance=0.8,  # SerperDev has good quality
                                    source_type="web",
                                )
                                for r in organic
                            ]
                        else:
                            logger.warning("SerperDev returned 0 results, trying SearxNG fallback")
                    else:
                        logger.warning(f"SerperDev returned status {response.status_code}, response: {response.text[:200]}")

            except httpx.HTTPStatusError as e:
                import traceback
                logger.error(f"❌ SerperDev HTTP error: {e.response.status_code}")
                logger.error(f"SerperDev error details: {traceback.format_exc()}")
            except Exception as e:
                import traceback
                logger.error(f"❌ SerperDev exception: {e}. Falling back to SearxNG")
                logger.error(f"SerperDev error details: {traceback.format_exc()}")

        # Fallback to SearxNG
        logger.info(f"🔍 Trying SearxNG fallback for query: {sub_query.query}")
        try:
            response = await self.deps.searxng_client.get(
                "/search",
                params={"q": sub_query.query, "format": "json"},
                timeout=self.timeout,
            )

            logger.info(f"SearxNG response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])

                logger.info(f"✅ SearxNG returned {len(results)} results for: {sub_query.query}")

                return [
                    SearchSource(
                        title=r.get("title", ""),
                        url=r.get("url", ""),
                        snippet=r.get("content", ""),
                        relevance=0.7,
                        source_type="web",
                    )
                    for r in results
                ]
            else:
                logger.warning(f"SearxNG returned status {response.status_code}")

        except httpx.ConnectError as e:
            logger.error(f"Cannot connect to SearxNG: {e}")
        except httpx.TimeoutException:
            logger.warning(f"SearxNG timeout for query: {sub_query.query}")
        except Exception as e:
            logger.error(f"SearxNG error: {e}")

        return []

    async def enrich_sources_with_content(
        self, sources: list[SearchSource]
    ) -> list[SearchSource]:
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
        logger.info(
            f"🌐 Crawling {len(urls_to_crawl)} URLs for full content extraction"
        )

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

    async def _crawl_single_url(self, source: SearchSource) -> SearchSource:
        """Crawl a single URL and update source with content.

        Args:
            source: Search source to enrich

        Returns:
            Same source with content field populated
        """
        try:
            logger.info(f"🕷️  Crawling: {source.url}")
            crawled_page = await self.deps.crawl_client.crawl_url(
                url=source.url,
                word_count_threshold=50,  # Filter out short/nav blocks
            )

            if crawled_page.success and crawled_page.markdown:
                # Use markdown content (cleaner than HTML)
                source.content = crawled_page.markdown[:10000]  # Limit to 10K chars
                logger.info(
                    f"✅ Crawled {source.url}: {len(source.content)} chars"
                )
            else:
                logger.warning(
                    f"⚠️  Crawl failed for {source.url}: {crawled_page.error_message}"
                )

        except Exception as e:
            logger.error(f"❌ Error crawling {source.url}: {e}")

        return source

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

    async def generate_answer(
        self, query: str, sources: list[SearchSource]
    ) -> str:
        """Generate AI answer based on search sources.

        Args:
            query: User's original query
            sources: Retrieved and ranked sources

        Returns:
            AI-generated answer synthesizing the sources

        Example:
            >>> answer = await agent.generate_answer("What are AI agents?", sources)
            >>> assert len(answer) > 100
        """
        if not sources:
            return "I couldn't find enough information to answer your question. Please try rephrasing your query."

        # Build context from sources
        context_parts = []
        for idx, source in enumerate(sources[:7], 1):  # Use top 7 sources
            # Use full content if available, otherwise fall back to snippet
            content_text = source.content if source.content else source.snippet
            # Limit content length per source (max 2000 chars)
            content_text = content_text[:2000] if len(content_text) > 2000 else content_text
            
            context_parts.append(
                f"[{idx}] {source.title}\nContent: {content_text}\nURL: {source.url}\n"
            )
        context = "\n".join(context_parts)
        
        # Log content enrichment stats
        enriched_count = sum(1 for s in sources[:7] if s.content)
        logger.info(f"📊 Using {enriched_count}/7 sources with full content, {7-enriched_count} with snippets only")

        # Build prompt for answer generation
        prompt = f"""You are a helpful search assistant. Based on the search results below, provide a comprehensive answer to the user's question.

User Question: {query}

Search Results:
{context}

Instructions:
- Provide a clear, comprehensive answer based on the search results
- Cite sources using [1], [2], etc. when referencing specific information
- If information is contradictory, mention different perspectives
- Be factual and accurate
- Write in a natural, conversational tone
- If the sources don't fully answer the question, acknowledge that

Answer:"""

        logger.info("🤖 Generating answer from sources using LLM...")

        try:
            response = await self.deps.llm_client.chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
            )

            # Extract answer from response
            if isinstance(response, dict) and "content" in response:
                answer = response["content"].strip()
                logger.info(f"✅ Generated answer ({len(answer)} chars)")
                return answer
            else:
                logger.warning("LLM response format unexpected, using fallback")
                return self._generate_fallback_answer(query, sources)

        except Exception as e:
            logger.error(f"❌ Error generating answer: {e}")
            return self._generate_fallback_answer(query, sources)

    def _generate_fallback_answer(
        self, query: str, sources: list[SearchSource]
    ) -> str:
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

        # 3. Enrich sources with full content (crawl URLs)
        enriched_sources = await self.enrich_sources_with_content(raw_sources)

        # 4. Rank results
        ranked_sources = await self.rank_results(enriched_sources, query)

        # 5. Generate answer from sources
        answer = await self.generate_answer(query, ranked_sources)

        execution_time = time.time() - start_time

        # 6. Build output
        output = SearchOutput(
            answer=answer,
            sub_queries=sub_queries,
            sources=ranked_sources,
            execution_time=execution_time,
            confidence=0.8,  # Default confidence
        )

        # 7. Validate output
        output = await self.validate_output(output)

        return output
