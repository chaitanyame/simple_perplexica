"""Unit tests for SearchAgent - RED phase (tests written FIRST).

Test Coverage:
- Agent initialization
- Query decomposition (simple/complex)
- Intent classification
- Search coordination (parallel execution, deduplication, timeout)
- Result ranking (relevance scoring, quality filtering)
- Output validation (min sources, confidence threshold)
- Full workflow integration
"""

import uuid
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.search_agent import (
    SearchAgent,
    SearchAgentDeps,
    SearchOutput,
    SearchSource,
    SubQuery,
)
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient


@pytest.fixture
def mock_llm_client() -> OpenRouterClient:
    """Mock OpenRouter LLM client."""
    client = MagicMock(spec=OpenRouterClient)
    client.chat = AsyncMock()
    return client


@pytest.fixture
def mock_tracer() -> LangfuseTracer:
    """Mock Langfuse tracer."""
    tracer = MagicMock(spec=LangfuseTracer)
    tracer.trace_llm_call = AsyncMock()
    return tracer


@pytest.fixture
def mock_searxng_client() -> httpx.AsyncClient:
    """Mock SearxNG HTTP client."""
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get = AsyncMock()
    return client


@pytest.fixture
def search_agent_deps(
    mock_llm_client: OpenRouterClient,
    mock_tracer: LangfuseTracer,
    mock_searxng_client: httpx.AsyncClient,
    async_session: AsyncSession,
) -> SearchAgentDeps:
    """Create SearchAgent dependencies for testing."""
    return SearchAgentDeps(
        llm_client=mock_llm_client,
        tracer=mock_tracer,
        db=async_session,
        searxng_client=mock_searxng_client,
        serperdev_api_key="test_serperdev_key",
        max_sources=20,
        timeout=60.0,
    )


class TestSearchAgentInitialization:
    """Test SearchAgent initialization and setup."""

    def test_search_agent_initialization(self, search_agent_deps: SearchAgentDeps) -> None:
        """Test that SearchAgent initializes with correct dependencies.

        Given: Valid SearchAgentDeps
        When: Creating a SearchAgent instance
        Then: Agent is initialized with correct configuration
        """
        agent = SearchAgent(deps=search_agent_deps)

        assert agent is not None
        assert agent.deps == search_agent_deps
        assert agent.max_sources == 20
        assert agent.timeout == 60.0

    def test_search_agent_initialization_custom_params(
        self, search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test SearchAgent initialization with custom parameters.

        Given: SearchAgentDeps with custom max_sources and timeout
        When: Creating a SearchAgent instance
        Then: Agent uses custom parameters
        """
        custom_deps = SearchAgentDeps(
            llm_client=search_agent_deps.llm_client,
            tracer=search_agent_deps.tracer,
            db=search_agent_deps.db,
            searxng_client=search_agent_deps.searxng_client,
            serperdev_api_key="test_key",
            max_sources=50,
            timeout=120.0,
        )

        agent = SearchAgent(deps=custom_deps)

        assert agent.max_sources == 50
        assert agent.timeout == 120.0


class TestQueryDecomposition:
    """Test query decomposition functionality."""

    @pytest.mark.asyncio
    async def test_decompose_simple_query(self, search_agent_deps: SearchAgentDeps) -> None:
        """Test decomposition of a simple query into a single sub-query.

        Given: A SearchAgent with mocked LLM
        When: Decomposing a simple query
        Then: Returns a single focused sub-query
        """
        agent = SearchAgent(deps=search_agent_deps)

        # Mock LLM response
        search_agent_deps.llm_client.chat.return_value = {
            "sub_queries": [{"query": "what is AI", "intent": "definition", "priority": 1}]
        }

        result = await agent.decompose_query("What is AI?")

        assert len(result) == 1
        assert isinstance(result[0], SubQuery)
        assert result[0].query == "what is AI"
        assert result[0].intent == "definition"
        assert result[0].priority == 1

    @pytest.mark.asyncio
    async def test_decompose_complex_query(self, search_agent_deps: SearchAgentDeps) -> None:
        """Test decomposition of complex query into multiple sub-queries.

        Given: A SearchAgent with mocked LLM
        When: Decomposing a complex multi-part query
        Then: Returns multiple focused sub-queries with priorities
        """
        agent = SearchAgent(deps=search_agent_deps)

        # Mock LLM response with multiple sub-queries
        search_agent_deps.llm_client.chat.return_value = {
            "sub_queries": [
                {"query": "what are AI agents", "intent": "definition", "priority": 1},
                {
                    "query": "how do AI agents work",
                    "intent": "factual",
                    "priority": 2,
                },
                {
                    "query": "AI agent use cases",
                    "intent": "factual",
                    "priority": 3,
                },
            ]
        }

        result = await agent.decompose_query(
            "What are AI agents and how do they work? What are some use cases?"
        )

        assert len(result) == 3
        assert all(isinstance(sq, SubQuery) for sq in result)
        assert result[0].intent == "definition"
        assert result[1].intent == "factual"
        assert result[0].priority < result[1].priority < result[2].priority

    @pytest.mark.asyncio
    async def test_decompose_query_with_intent_classification(
        self, search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test intent classification in query decomposition.

        Given: A SearchAgent with mocked LLM
        When: Decomposing queries with different intents
        Then: Each sub-query has correct intent classification
        """
        agent = SearchAgent(deps=search_agent_deps)

        # Mock LLM response with mixed intents
        search_agent_deps.llm_client.chat.return_value = {
            "sub_queries": [
                {"query": "define machine learning", "intent": "definition", "priority": 1},
                {
                    "query": "best ML frameworks",
                    "intent": "opinion",
                    "priority": 2,
                },
                {
                    "query": "how ML algorithms work",
                    "intent": "factual",
                    "priority": 3,
                },
            ]
        }

        result = await agent.decompose_query(
            "What is machine learning? Which frameworks are best? How do the algorithms work?"
        )

        intents = [sq.intent for sq in result]
        assert "definition" in intents
        assert "opinion" in intents
        assert "factual" in intents


class TestSearchCoordination:
    """Test search coordination across multiple sources."""

    @pytest.mark.asyncio
    async def test_coordinate_search_parallel_execution(
        self, search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test parallel search execution across multiple sources.

        Given: A SearchAgent with multiple sub-queries
        When: Coordinating search across SearxNG and SerperDev
        Then: Searches are executed in parallel and results combined
        """
        agent = SearchAgent(deps=search_agent_deps)

        sub_queries = [
            SubQuery(query="AI agents", intent="definition", priority=1),
            SubQuery(query="agent frameworks", intent="factual", priority=2),
        ]

        # Mock search responses
        mock_searxng_response = MagicMock()
        mock_searxng_response.status_code = 200
        mock_searxng_response.json.return_value = {
            "results": [
                {
                    "title": "AI Agents Overview",
                    "url": "https://example.com/ai-agents",
                    "content": "AI agents are...",
                }
            ]
        }

        search_agent_deps.searxng_client.get.return_value = mock_searxng_response

        results = await agent.coordinate_search(sub_queries)

        assert len(results) > 0
        assert all(isinstance(r, SearchSource) for r in results)
        # Verify parallel execution (both sources called)
        assert search_agent_deps.searxng_client.get.call_count >= len(sub_queries)

    @pytest.mark.asyncio
    async def test_coordinate_search_deduplication(
        self, search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test deduplication of search results by URL.

        Given: A SearchAgent with overlapping search results
        When: Coordinating search across multiple sources
        Then: Duplicate URLs are removed, keeping highest relevance
        """
        agent = SearchAgent(deps=search_agent_deps)

        sub_queries = [SubQuery(query="AI", intent="definition", priority=1)]

        # Mock responses with duplicate URLs
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "AI Overview 1",
                    "url": "https://example.com/ai",  # Duplicate URL
                    "content": "AI is...",
                },
                {
                    "title": "AI Overview 2",
                    "url": "https://example.com/ai",  # Duplicate URL
                    "content": "Artificial Intelligence...",
                },
                {
                    "title": "ML Basics",
                    "url": "https://example.com/ml",  # Unique URL
                    "content": "Machine learning...",
                },
            ]
        }

        search_agent_deps.searxng_client.get.return_value = mock_response

        results = await agent.coordinate_search(sub_queries)

        # Check deduplication
        urls = [r.url for r in results]
        assert len(urls) == len(set(urls)), "Duplicate URLs should be removed"
        assert "https://example.com/ai" in urls
        assert "https://example.com/ml" in urls

    @pytest.mark.asyncio
    async def test_coordinate_search_timeout_handling(
        self, search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test graceful timeout handling in search coordination.

        Given: A SearchAgent with timeout configured
        When: A search source times out
        Then: Returns partial results without raising exception
        """
        agent = SearchAgent(deps=search_agent_deps)

        sub_queries = [SubQuery(query="AI", intent="definition", priority=1)]

        # Mock timeout for one source
        search_agent_deps.searxng_client.get.side_effect = httpx.TimeoutException("Request timeout")

        # Should not raise, returns empty or partial results
        results = await agent.coordinate_search(sub_queries)

        assert isinstance(results, list)
        # Timeout handled gracefully (empty results acceptable)


class TestResultRanking:
    """Test result ranking and filtering."""

    @pytest.mark.asyncio
    async def test_rank_results_by_relevance(self, search_agent_deps: SearchAgentDeps) -> None:
        """Test ranking of results by relevance score.

        Given: A SearchAgent with unranked search results
        When: Ranking results by relevance to query
        Then: Results are sorted by descending relevance score
        """
        agent = SearchAgent(deps=search_agent_deps)

        sources = [
            SearchSource(
                title="Low Relevance",
                url="https://example.com/low",
                snippet="Generic content",
                relevance=0.5,  # Changed to 0.5 to pass filtering threshold
                source_type="web",
            ),
            SearchSource(
                title="High Relevance",
                url="https://example.com/high",
                snippet="Highly relevant AI agents content",
                relevance=0.9,
                source_type="academic",
            ),
            SearchSource(
                title="Medium Relevance",
                url="https://example.com/med",
                snippet="Some AI content",
                relevance=0.6,
                source_type="web",
            ),
        ]

        ranked = await agent.rank_results(sources, "AI agents")

        # Check descending order (all 3 sources should pass filtering)
        assert len(ranked) == 3
        assert ranked[0].relevance >= ranked[1].relevance >= ranked[2].relevance
        assert ranked[0].title == "High Relevance"
        assert ranked[2].title == "Low Relevance"

    @pytest.mark.asyncio
    async def test_rank_results_quality_filtering(self, search_agent_deps: SearchAgentDeps) -> None:
        """Test filtering of low-quality results.

        Given: A SearchAgent with mixed quality results
        When: Ranking results with quality threshold
        Then: Low-quality sources are filtered out
        """
        agent = SearchAgent(deps=search_agent_deps)

        sources = [
            SearchSource(
                title="High Quality",
                url="https://example.com/high",
                snippet="Well-sourced AI agents content",
                relevance=0.9,
                source_type="academic",
            ),
            SearchSource(
                title="Low Quality",
                url="https://example.com/low",
                snippet="Spam content",
                relevance=0.1,  # Below threshold
                source_type="web",
            ),
        ]

        ranked = await agent.rank_results(sources, "AI agents")

        # Low quality filtered (relevance < 0.5 threshold)
        assert all(r.relevance >= 0.5 for r in ranked)
        assert len(ranked) < len(sources)


class TestOutputValidation:
    """Test SearchAgent output validation."""

    @pytest.mark.asyncio
    async def test_output_validation_min_sources(self, search_agent_deps: SearchAgentDeps) -> None:
        """Test validation of minimum source count.

        Given: A SearchAgent configured with min_sources requirement
        When: Output has fewer sources than minimum
        Then: Validation raises ModelRetry to prompt retry
        """
        agent = SearchAgent(deps=search_agent_deps)

        # Output with insufficient sources (< 5 minimum)
        output = SearchOutput(
            sub_queries=[SubQuery(query="AI", intent="definition", priority=1)],
            sources=[
                SearchSource(
                    title="Source 1",
                    url="https://example.com/1",
                    snippet="Content",
                    relevance=0.8,
                    source_type="web",
                )
            ],  # Only 1 source
            execution_time=1.5,
            confidence=0.7,
        )

        # Should raise ModelRetry
        with pytest.raises(Exception):  # Replace with actual ModelRetry import
            await agent.validate_output(output)

    @pytest.mark.asyncio
    async def test_output_validation_confidence_threshold(
        self, search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test validation of confidence threshold.

        Given: A SearchAgent with confidence threshold
        When: Output confidence is below threshold
        Then: Validation raises ModelRetry
        """
        agent = SearchAgent(deps=search_agent_deps)

        # Output with low confidence (< 0.5 threshold)
        output = SearchOutput(
            sub_queries=[SubQuery(query="AI", intent="definition", priority=1)],
            sources=[
                SearchSource(
                    title=f"Source {i}",
                    url=f"https://example.com/{i}",
                    snippet="Content",
                    relevance=0.8,
                    source_type="web",
                )
                for i in range(6)
            ],  # Sufficient sources
            execution_time=1.5,
            confidence=0.3,  # Below threshold
        )

        # Should raise ModelRetry
        with pytest.raises(Exception):  # Replace with actual ModelRetry import
            await agent.validate_output(output)


class TestSearchAgentFullWorkflow:
    """Test full SearchAgent workflow end-to-end."""

    @pytest.mark.asyncio
    async def test_search_agent_full_workflow(self, search_agent_deps: SearchAgentDeps) -> None:
        """Test complete search workflow from query to ranked results.

        Given: A SearchAgent with all dependencies
        When: Running a complete search query
        Then: Returns SearchOutput with decomposed queries, sources, and metadata
        """
        agent = SearchAgent(deps=search_agent_deps)

        # Mock LLM decomposition
        search_agent_deps.llm_client.chat.return_value = {
            "sub_queries": [
                {"query": "AI agents", "intent": "definition", "priority": 1},
                {"query": "agent frameworks", "intent": "factual", "priority": 2},
            ]
        }

        # Mock search results
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": f"Result {i}",
                    "url": f"https://example.com/{i}",
                    "content": f"Content about AI agents {i}",
                }
                for i in range(10)
            ]
        }
        search_agent_deps.searxng_client.get.return_value = mock_response

        # Execute full workflow
        result = await agent.run("What are AI agents and which frameworks exist?")

        assert isinstance(result, SearchOutput)
        assert len(result.sub_queries) > 0
        assert len(result.sources) >= 5  # Minimum sources
        assert result.confidence >= 0.5  # Minimum confidence
        assert result.execution_time > 0
        assert all(isinstance(s, SearchSource) for s in result.sources)
