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

from src.core.search_modes import SearchMode, get_mode_from_string
from src.services.crawl.crawl4ai_client import Crawl4AIClient
from src.services.document.dockling_processor import DocklingProcessor
from src.services.embedding.embedding_service import EmbeddingService
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient
from src.utils.language_detector import detect_language, get_language_name
from src.utils.query_normalizer import normalize_query
from src.utils.temporal_validator import TemporalValidator

# =============================================================================
# Pydantic Models for Structured Output
# =============================================================================


class SubQuery(BaseModel):
    """Decomposed sub-query with intent and priority.

    Attributes:
        query: Focused sub-query text (1-200 chars)
        intent: Query intent classification (definition/factual/opinion)
        priority: Execution priority (1=highest, 5=lowest)
        temporal_scope: Time filter (recent/past_year/past_month/any)
        specific_year: Specific year mentioned (e.g., 2022, 2023) - overrides temporal_scope
        language: Query language ISO code (en/es/fr/de) for region-specific results
    """

    query: str = Field(..., min_length=1, max_length=200)
    intent: str = Field(..., pattern=r"^(definition|factual|opinion)$")
    priority: int = Field(ge=1, le=5)
    temporal_scope: str = Field(
        default="any",
        pattern=r"^(recent|past_year|past_month|past_week|any)$",
        description="Time filter: recent (past month), past_year, past_month, past_week, any"
    )
    specific_year: int | None = Field(
        default=None,
        ge=1990,
        le=2030,
        description="Specific year if mentioned (e.g., 2022, 2023). Overrides temporal_scope."
    )
    language: str = Field(
        default="en",
        pattern=r"^(en|es|fr|de)$",
        description="Query language: en (English), es (Spanish), fr (French), de (German)"
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
        embedding_service: Embedding service for semantic reranking
        max_sources: Maximum number of sources to return (default: 20)
        timeout: Search timeout in seconds (default: 60.0)
        enable_crawling: Whether to crawl URLs for full content (default: True)
        max_crawl_urls: Maximum URLs to crawl for content (default: 5)
        enable_reranking: Whether to use semantic reranking (default: True)
        rerank_weight: Weight for semantic score in final ranking (default: 0.6)
    """

    llm_client: OpenRouterClient
    tracer: LangfuseTracer
    db: AsyncSession
    searxng_client: httpx.AsyncClient
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

        # Log search configuration
        if deps.serperdev_api_key and deps.serperdev_api_key.strip():
            logger.info(f"SearchAgent initialized with SerperDev (primary) + SearxNG (fallback)")
        else:
            logger.info(f"SearchAgent initialized with SearxNG only (no SerperDev key)")
        
        logger.info(f"✅ Temporal validation enabled with post-retrieval filtering")

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
        logger.info(f"🧩 QUERY DECOMPOSITION START")
        logger.info(f"📥 Input query (raw): '{query}'")
        
        # Normalize query for consistency
        normalized_query = normalize_query(query)
        logger.info(f"📥 Input query (normalized): '{normalized_query}'")
        
        # Detect language for better search results
        detected_lang = detect_language(query)
        lang_name = get_language_name(detected_lang)
        logger.info(f"🌍 Detected language: {lang_name} ({detected_lang})")

        # Use OpenRouter LLM directly with JSON mode for structured decomposition
        system_prompt = """You are a query decomposition expert. Break down user queries into focused sub-queries.

Guidelines:
- Simple queries (1 topic): Return 1-2 sub-queries
- Complex queries (multiple topics): Return 2-4 sub-queries  
- Each sub-query should be specific and searchable
- Intent types: "factual" (facts/data), "definition" (what is X), "opinion" (views/analysis)
- Priority: 1 (most important) to 5 (least important)

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
Response:
{
  "sub_queries": [
    {"query": "What are AI agents?", "intent": "definition", "priority": 1, "temporal_scope": "any", "specific_year": null}
  ]
}

Query: "Recent news about Microsoft Azure"
Response:
{
  "sub_queries": [
    {"query": "Microsoft Azure recent news 2025", "intent": "factual", "priority": 1, "temporal_scope": "recent", "specific_year": null}
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
                {"role": "user", "content": f"Query: {query}\n\nDecompose this into sub-queries."}
            ]
            
            # ============ CRITICAL LOG: LLM INPUT ============
            logger.info(f"🤖 LLM CALL: Query Decomposition")
            logger.info(f"📤 Model: meta-llama/llama-4-maverick:free")
            logger.info(f"📤 Temperature: 0.3, Max Tokens: 500")
            logger.info(f"📤 Messages count: {len(messages)}")
            logger.info(f"📤 System prompt length: {len(system_prompt)} chars")
            logger.info(f"📤 User message: '{messages[1]['content'][:200]}...'")
            
            # Use Llama 4 Maverick (free model) via OpenRouter
            # Note: OpenRouterClient is initialized with a default model,
            # but we can override by temporarily changing it
            original_model = self.deps.llm_client.model
            self.deps.llm_client.model = "meta-llama/llama-4-maverick:free"  # FREE tier
            
            response = await self.deps.llm_client.chat(
                messages=messages,
                temperature=0.3,
                max_tokens=500,
                response_format={"type": "json_object"},  # Force JSON output
            )
            
            # Restore original model
            self.deps.llm_client.model = original_model
            
            # ============ CRITICAL LOG: LLM RESPONSE ============
            content = response["content"].strip()
            logger.info(f"� LLM RESPONSE received")
            logger.info(f"📥 Response length: {len(content)} chars")
            logger.info(f"📥 Raw response:\n{content}")
            
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
            
            return decomposition.sub_queries
            
        except Exception as e:
            logger.error(f"❌ Query decomposition failed: {e}, using fallback")
            # Fallback: treat as single factual query
            
            # Extract specific year from query (2020-2030 range)
            import re
            year_pattern = r'\b(20[2-3][0-9])\b'  # Matches 2020-2039
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
            
            return [SubQuery(
                query=query,
                intent="factual",
                priority=1,
                temporal_scope=temporal_scope,
                specific_year=specific_year,
                language=detected_lang
            )]

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
            temporal_info = f"temporal: {sub_query.temporal_scope}"
            if sub_query.specific_year:
                temporal_info += f", year: {sub_query.specific_year}"
            
            # ============ CRITICAL LOG: SEARCH API INPUT ============
            logger.info(f"🔍 SEARCH API CALL: SerperDev")
            logger.info(f"📤 Query: '{sub_query.query}'")
            logger.info(f"📤 Language: {sub_query.language}")
            logger.info(f"📤 Temporal: {temporal_info}")
            
            try:
                # Build SerperDev request with temporal filtering and language
                search_params = {
                    "q": sub_query.query,
                    "num": 10,
                    "gl": sub_query.language,  # Language/region parameter
                }
                
                # Priority 1: Specific year mentioned (e.g., "2022", "2023")
                if sub_query.specific_year:
                    # Use Google's custom date range: cd_min (start date) and cd_max (end date)
                    # Format: cdr:1,cd_min:MM/DD/YYYY,cd_max:MM/DD/YYYY
                    year = sub_query.specific_year
                    # Search entire year: Jan 1 to Dec 31
                    search_params["tbs"] = f"cdr:1,cd_min:1/1/{year},cd_max:12/31/{year}"
                    logger.info(f"  📅 Filtering: Specific year {year} (Jan 1 - Dec 31)")
                
                # Priority 2: Relative time filters (past week/month/year/recent)
                elif sub_query.temporal_scope == "past_week":
                    search_params["tbs"] = "qdr:w"
                    logger.info(f"  📅 Filtering: Past week")
                elif sub_query.temporal_scope == "past_month" or sub_query.temporal_scope == "recent":
                    search_params["tbs"] = "qdr:m"
                    logger.info(f"  📅 Filtering: Past month (recent)")
                elif sub_query.temporal_scope == "past_year":
                    search_params["tbs"] = "qdr:y"
                    logger.info(f"  📅 Filtering: Past year")
                else:
                    logger.info(f"  📅 No time filter (any)")
                
                logger.info(f"📤 Search params: {search_params}")
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "https://google.serper.dev/search",
                        headers={
                            "X-API-KEY": self.deps.serperdev_api_key,
                            "Content-Type": "application/json",
                        },
                        json=search_params,
                        timeout=self.timeout,
                    )

                    # ============ CRITICAL LOG: SEARCH API RESPONSE ============
                    logger.info(f"📥 SEARCH API RESPONSE")
                    logger.info(f"📥 Status: {response.status_code}")

                    if response.status_code == 200:
                        data = response.json()
                        organic = data.get("organic", [])

                        logger.info(f"📥 Results count: {len(organic)}")
                        logger.info(f"✅ SerperDev SUCCESS for: {sub_query.query}")
                        
                        # Log sample results
                        for i, r in enumerate(organic[:3], 1):
                            logger.info(
                                f"  [{i}] {r.get('title', 'No title')[:60]}... | "
                                f"URL: {r.get('link', 'No URL')[:80]}"
                            )

                        if len(organic) > 0:
                            sources = [
                                SearchSource(
                                    title=r.get("title", ""),
                                    url=r.get("link", ""),
                                    snippet=r.get("snippet", ""),
                                    relevance=0.8,  # SerperDev has good quality
                                    source_type="web",
                                )
                                for r in organic
                            ]
                            logger.info(f"📦 Returning {len(sources)} SearchSource objects")
                            return sources
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

    def _is_document_url(self, url: str) -> bool:
        """Check if URL points to a document (PDF, DOCX, etc.).

        Args:
            url: URL to check

        Returns:
            True if URL is a document, False otherwise
        """
        url_lower = url.lower()
        doc_extensions = ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt']
        
        # Check file extension in path
        for ext in doc_extensions:
            if ext in url_lower:
                return True
        
        # Check for common PDF URL patterns
        if 'pdf' in url_lower or 'download' in url_lower or 'arxiv.org/pdf' in url_lower:
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
                    filename = source.url.split('/')[-1]
                    if '?' in filename:
                        filename = filename.split('?')[0]
                    if not any(ext in filename.lower() for ext in ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt']):
                        filename += '.pdf'  # Default to PDF if no extension
                    
                    # Process document with Dockling
                    processed_doc = await self.deps.document_processor.process_document_bytes(
                        content=response.content,
                        filename=filename,
                        source_url=source.url
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
                    logger.info(
                        f"✅ Crawled {source.url}: {len(source.content)} chars"
                    )
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
                )

                # Prepare documents for reranking (use content if available, else snippet)
                documents = [
                    (s.content if s.content else s.snippet)
                    for s in filtered
                ]

                # Get semantic scores from cross-encoder
                rerank_results = await self.deps.embedding_service.rerank(
                    query=original_query,
                    documents=documents,
                )

                # Map semantic scores back to sources
                for idx, score in rerank_results:
                    filtered[idx].semantic_score = score

                    # Compute final score as weighted combination
                    # final_score = (1 - w) * relevance + w * semantic_score
                    relevance_weight = 1.0 - self.deps.rerank_weight
                    filtered[idx].final_score = (
                        relevance_weight * filtered[idx].relevance
                        + self.deps.rerank_weight * score
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

        # ============ CRITICAL LOG: ANSWER GENERATION INPUT ============
        logger.info(f"💬 ANSWER GENERATION START")
        logger.info(f"📥 Query: '{query}'")
        logger.info(f"📥 Sources: {len(sources)} total, using top 7")
        logger.info(f"📥 Context length: {len(context)} chars")
        
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

Write a detailed answer with full explanations for everything:"""

        # ============ CRITICAL LOG: LLM CALL FOR ANSWER ============
        logger.info(f"🤖 LLM CALL: Answer Generation")
        logger.info(f"📤 Model: meta-llama/llama-4-maverick:free")
        logger.info(f"📤 Temperature: 0.7, Max Tokens: 2048")
        logger.info(f"📤 Prompt length: {len(prompt)} chars")
        logger.info(f"📤 Prompt preview: {prompt[:500]}...")

        try:
            # Use Llama 4 Maverick (free model) via OpenRouter
            original_model = self.deps.llm_client.model
            self.deps.llm_client.model = "meta-llama/llama-4-maverick:free"  # FREE tier
            
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
                logger.info(f"📥 Answer preview: {answer[:300]}...")
                logger.info(f"✅ ANSWER GENERATION COMPLETE")
                return answer
            else:
                logger.warning("⚠️ LLM response format unexpected, using fallback")
                logger.warning(f"Response type: {type(response)}, keys: {response.keys() if isinstance(response, dict) else 'N/A'}")
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
        
        logger.info(
            "Starting search with mode",
            query=query,
            mode=search_mode.value,
            max_sources=config.max_sources,
            timeout=config.timeout,
        )

        start_time = time.time()

        # Apply mode configuration
        original_max_sources = self.max_sources
        original_enable_reranking = self.deps.enable_reranking
        original_max_crawl_urls = self.deps.max_crawl_urls
        
        self.max_sources = config.max_sources
        self.deps.enable_reranking = config.enable_reranking
        
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
                strict_filtering=False  # Penalize, don't remove
            )
            
            logger.info(f"✅ TEMPORAL VALIDATION COMPLETE")
            logger.info(f"📊 Output: {len(validated_sources)} sources after validation")

            # 4. Rank results (reranking controlled by mode config)
            ranked_sources = await self.rank_results(validated_sources, query)

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
