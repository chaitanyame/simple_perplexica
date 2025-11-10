"""Integration tests for ResearchAgent with real database and agent coordination.

These tests verify ResearchAgent works correctly with:
- Real async database sessions
- Real SearchAgent coordination (with mocked dependencies)
- Real vector store integration (mocked queries)
- Mocked LLM responses
- Real async workflow orchestration
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.research_agent import (
    Citation,
    ResearchAgent,
    ResearchAgentDeps,
    ResearchOutput,
)
from src.agents.search_agent import (
    SearchAgent,
    SearchAgentDeps,
    SearchOutput,
    SearchSource,
    SubQuery,
)
from src.rag.vector_store_repository import VectorStoreRepository
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient


@pytest.fixture
def mock_search_agent_with_real_output() -> SearchAgent:
    """Mock SearchAgent that returns realistic SearchOutput."""
    agent = MagicMock(spec=SearchAgent)
    agent.run = AsyncMock(
        return_value=SearchOutput(
            sub_queries=[
                SubQuery(
                    query="Pydantic AI architecture",
                    intent="factual",
                    priority=1,
                )
            ],
            sources=[
                SearchSource(
                    title="Pydantic AI Architecture Guide",
                    url="https://ai.pydantic.dev/architecture",
                    snippet="Pydantic AI uses a modular architecture with agents, tools, and models. The framework emphasizes type safety and validation.",
                    relevance=0.95,
                    source_type="academic",
                ),
                SearchSource(
                    title="Building with Pydantic AI",
                    url="https://ai.pydantic.dev/guide",
                    snippet="Learn how to build production-grade AI agents with Pydantic AI. Includes examples and best practices.",
                    relevance=0.88,
                    source_type="web",
                ),
                SearchSource(
                    title="Pydantic AI API Reference",
                    url="https://ai.pydantic.dev/api",
                    snippet="Complete API reference for Pydantic AI agents, dependencies, and tools.",
                    relevance=0.82,
                    source_type="academic",
                ),
                SearchSource(
                    title="Pydantic AI Examples",
                    url="https://ai.pydantic.dev/examples",
                    snippet="Real-world examples of Pydantic AI agents for various use cases.",
                    relevance=0.78,
                    source_type="web",
                ),
                SearchSource(
                    title="Pydantic AI GitHub",
                    url="https://github.com/pydantic/pydantic-ai",
                    snippet="Source code and contributions for Pydantic AI framework.",
                    relevance=0.75,
                    source_type="web",
                ),
            ],
            execution_time=2.5,
            confidence=0.87,
        )
    )
    return agent


@pytest.fixture
def mock_vector_store_with_results() -> VectorStoreRepository:
    """Mock vector store with realistic search results."""
    repo = MagicMock(spec=VectorStoreRepository)
    repo.search_similar = AsyncMock(
        return_value=[
            {
                "id": "doc1",
                "content": "Pydantic AI is a Python agent framework...",
                "similarity": 0.92,
            },
            {
                "id": "doc2",
                "content": "Agents in Pydantic AI use structured outputs...",
                "similarity": 0.85,
            },
        ]
    )
    return repo


class TestResearchAgentWithRealDatabase:
    """Test ResearchAgent with real database integration."""

    @pytest.mark.asyncio
    async def test_research_agent_with_real_db_session(
        self,
        async_session: AsyncSession,
        mock_search_agent_with_real_output: SearchAgent,
        mock_vector_store_with_results: VectorStoreRepository,
    ) -> None:
        """Test ResearchAgent initialization with real async database session.

        Given: Real async database session from fixture
        When: Creating ResearchAgent with real DB dependency
        Then: Agent initializes successfully and DB is accessible
        """
        # Mock LLM client
        mock_llm = MagicMock(spec=OpenRouterClient)
        mock_llm.chat = AsyncMock()

        mock_tracer = MagicMock(spec=LangfuseTracer)

        deps = ResearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=async_session,
            search_agent=mock_search_agent_with_real_output,
            vector_store=mock_vector_store_with_results,
            max_iterations=5,
            timeout=300.0,
        )

        agent = ResearchAgent(deps=deps)

        # Verify agent has real DB session via deps
        assert agent.deps.db == async_session
        assert agent.deps.db.is_active
        assert agent.search_agent is not None


class TestResearchAgentWithSearchAgentCoordination:
    """Test ResearchAgent coordination with SearchAgent."""

    @pytest.mark.asyncio
    async def test_research_workflow_delegates_to_search_agent(
        self,
        async_session: AsyncSession,
        mock_search_agent_with_real_output: SearchAgent,
        mock_vector_store_with_results: VectorStoreRepository,
    ) -> None:
        """Test ResearchAgent delegates evidence gathering to SearchAgent.

        Given: ResearchAgent with SearchAgent dependency
        When: Running research workflow
        Then: SearchAgent is called for evidence gathering
        """
        # Mock LLM responses
        mock_llm = MagicMock(spec=OpenRouterClient)
        mock_llm.chat = AsyncMock(
            side_effect=[
                # Plan generation
                {
                    "steps": [
                        {
                            "step_number": 1,
                            "description": "Research Pydantic AI",
                            "search_query": "what is Pydantic AI",
                            "expected_outcome": "Understanding of framework",
                            "depends_on": [],
                        }
                    ],
                    "estimated_time": 60.0,
                    "complexity": "simple",
                },
                # Synthesis
                {
                    "synthesis": "Pydantic AI is a Python agent framework designed for building production-grade applications with Generative AI. It emphasizes type safety through Pydantic models and provides a modular architecture with agents, tools, and model integrations. The framework is particularly well-suited for applications requiring structured outputs and validation."
                },
            ]
        )

        mock_tracer = MagicMock(spec=LangfuseTracer)

        deps = ResearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=async_session,
            search_agent=mock_search_agent_with_real_output,
            vector_store=mock_vector_store_with_results,
            max_iterations=5,
            timeout=300.0,
        )

        agent = ResearchAgent(deps=deps)
        result = await agent.run("What is Pydantic AI?")

        # Verify SearchAgent was called
        mock_search_agent_with_real_output.run.assert_called()

        # Verify result structure
        assert isinstance(result, ResearchOutput)
        assert len(result.citations) >= 3
        assert len(result.findings) >= 100

    @pytest.mark.asyncio
    async def test_research_agent_citation_deduplication_across_steps(
        self,
        async_session: AsyncSession,
        mock_vector_store_with_results: VectorStoreRepository,
    ) -> None:
        """Test citation deduplication when multiple steps return same URLs.

        Given: Research plan with multiple steps
        When: Steps return overlapping sources
        Then: Citations are deduplicated by URL
        """
        # Create SearchAgent that returns sources with duplicate URLs plus unique sources
        mock_search_agent = MagicMock(spec=SearchAgent)
        mock_search_agent.run = AsyncMock(
            return_value=SearchOutput(
                sub_queries=[SubQuery(query="test", intent="factual", priority=1)],
                sources=[
                    SearchSource(
                        title="Pydantic AI Guide",
                        url="https://ai.pydantic.dev/guide",  # Will be duplicate
                        snippet="Content about Pydantic AI",
                        relevance=0.9,
                        source_type="academic",
                    ),
                    SearchSource(
                        title="Pydantic AI Guide (Updated)",
                        url="https://ai.pydantic.dev/guide",  # Duplicate URL
                        snippet="Updated content about Pydantic AI",
                        relevance=0.85,  # Lower relevance
                        source_type="academic",
                    ),
                    SearchSource(
                        title="Pydantic AI Examples",
                        url="https://ai.pydantic.dev/examples",
                        snippet="Examples",
                        relevance=0.8,
                        source_type="web",
                    ),
                    SearchSource(
                        title="Pydantic AI Tutorial",
                        url="https://ai.pydantic.dev/tutorial",
                        snippet="Tutorial content",
                        relevance=0.75,
                        source_type="web",
                    ),
                    SearchSource(
                        title="Pydantic AI Best Practices",
                        url="https://ai.pydantic.dev/best-practices",
                        snippet="Best practices guide",
                        relevance=0.7,
                        source_type="academic",
                    ),
                ],
                execution_time=1.5,
                confidence=0.8,
            )
        )

        # Mock LLM
        mock_llm = MagicMock(spec=OpenRouterClient)
        mock_llm.chat = AsyncMock(
            side_effect=[
                # Plan
                {
                    "steps": [
                        {
                            "step_number": 1,
                            "description": "Step 1",
                            "search_query": "query 1",
                            "expected_outcome": "outcome",
                            "depends_on": [],
                        }
                    ],
                    "estimated_time": 30.0,
                    "complexity": "simple",
                },
                # Synthesis
                {
                    "synthesis": "Pydantic AI is a modern Python framework for building AI agents with strong typing and validation. It provides comprehensive tooling for production-grade applications."
                },
            ]
        )

        mock_tracer = MagicMock(spec=LangfuseTracer)

        deps = ResearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=async_session,
            search_agent=mock_search_agent,
            vector_store=mock_vector_store_with_results,
            max_iterations=5,
            timeout=300.0,
        )

        agent = ResearchAgent(deps=deps)
        result = await agent.run("Test query")

        # Verify deduplication (5 sources - 1 duplicate = 4 unique citations)
        citation_urls = [c.url for c in result.citations]
        assert len(citation_urls) == len(set(citation_urls))  # No duplicates
        assert len(citation_urls) == 4  # 4 unique URLs after deduplication

        # Verify the guide URL appears once (kept higher relevance version)
        assert citation_urls.count("https://ai.pydantic.dev/guide") == 1
        assert "https://ai.pydantic.dev/examples" in citation_urls
        assert "https://ai.pydantic.dev/tutorial" in citation_urls
        assert "https://ai.pydantic.dev/best-practices" in citation_urls


class TestResearchAgentErrorHandling:
    """Test ResearchAgent error handling with real async flows."""

    @pytest.mark.asyncio
    async def test_research_agent_handles_search_agent_failure(
        self,
        async_session: AsyncSession,
        mock_vector_store_with_results: VectorStoreRepository,
    ) -> None:
        """Test ResearchAgent handles SearchAgent failures gracefully.

        Given: SearchAgent that raises exceptions
        When: ResearchAgent attempts evidence gathering
        Then: Continues with empty sources (graceful degradation)
        """
        # SearchAgent that fails
        mock_search_agent = MagicMock(spec=SearchAgent)
        mock_search_agent.run = AsyncMock(side_effect=Exception("SearchAgent failed"))

        # Mock LLM (will only get plan request, no synthesis due to validation failure)
        mock_llm = MagicMock(spec=OpenRouterClient)
        mock_llm.chat = AsyncMock(
            return_value={
                "steps": [
                    {
                        "step_number": 1,
                        "description": "Step 1",
                        "search_query": "query",
                        "expected_outcome": "outcome",
                        "depends_on": [],
                    }
                ],
                "estimated_time": 30.0,
                "complexity": "simple",
            }
        )

        mock_tracer = MagicMock(spec=LangfuseTracer)

        deps = ResearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=async_session,
            search_agent=mock_search_agent,
            vector_store=mock_vector_store_with_results,
            max_iterations=5,
            timeout=300.0,
        )

        agent = ResearchAgent(deps=deps)

        # Should raise validation error due to insufficient citations
        with pytest.raises(Exception) as exc_info:
            await agent.run("Test query")

        # Verify it's a validation error (not SearchAgent error)
        assert "citation" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_research_agent_validates_output_quality(
        self,
        async_session: AsyncSession,
        mock_vector_store_with_results: VectorStoreRepository,
    ) -> None:
        """Test ResearchAgent validates output meets quality thresholds.

        Given: Research workflow that produces insufficient results
        When: Output validation is performed
        Then: Raises exception for quality threshold violations
        """
        # SearchAgent with insufficient sources
        mock_search_agent = MagicMock(spec=SearchAgent)
        mock_search_agent.run = AsyncMock(
            return_value=SearchOutput(
                sub_queries=[SubQuery(query="test", intent="factual", priority=1)],
                sources=[
                    SearchSource(
                        title="Source 1",
                        url="https://example.com/1",
                        snippet="Content 1",
                        relevance=0.7,
                        source_type="web",
                    )
                ],  # Only 1 source (need >= 3)
                execution_time=1.0,
                confidence=0.6,
            )
        )

        # Mock LLM
        mock_llm = MagicMock(spec=OpenRouterClient)
        mock_llm.chat = AsyncMock(
            side_effect=[
                # Plan
                {
                    "steps": [
                        {
                            "step_number": 1,
                            "description": "Step 1",
                            "search_query": "query",
                            "expected_outcome": "outcome",
                            "depends_on": [],
                        }
                    ],
                    "estimated_time": 30.0,
                    "complexity": "simple",
                },
                # Synthesis (will be called but output will fail validation)
                {"synthesis": "Short findings that don't meet minimum length."},
            ]
        )

        mock_tracer = MagicMock(spec=LangfuseTracer)

        deps = ResearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=async_session,
            search_agent=mock_search_agent,
            vector_store=mock_vector_store_with_results,
            max_iterations=5,
            timeout=300.0,
        )

        agent = ResearchAgent(deps=deps)

        # Should raise validation error
        with pytest.raises(Exception) as exc_info:
            await agent.run("Test query")

        # Verify validation error (insufficient citations or short findings)
        error_msg = str(exc_info.value).lower()
        assert "citation" in error_msg or "finding" in error_msg or "short" in error_msg
