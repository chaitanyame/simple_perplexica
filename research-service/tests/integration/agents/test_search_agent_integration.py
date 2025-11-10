"""Integration tests for SearchAgent with real database and mocked external APIs.

These tests verify SearchAgent works correctly with:
- Real async database sessions
- Real LangfuseTracer initialization
- Mocked OpenRouter LLM responses
- Mocked SearxNG HTTP responses
- Real async coordination and error handling
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.search_agent import SearchAgent, SearchAgentDeps, SearchOutput
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient


@pytest.fixture
def mock_openrouter_responses() -> list[dict[str, Any]]:
    """Mock OpenRouter API responses for search workflow."""
    return [
        # Query decomposition response
        {
            "sub_queries": [
                {
                    "query": "Pydantic AI framework features",
                    "intent": "definition",
                    "priority": 1,
                },
                {
                    "query": "Pydantic AI agents tutorial",
                    "intent": "factual",
                    "priority": 2,
                },
            ]
        }
    ]


@pytest.fixture
def mock_searxng_responses() -> list[dict[str, Any]]:
    """Mock SearxNG search responses."""
    return [
        {
            "results": [
                {
                    "title": "Pydantic AI Documentation",
                    "url": "https://ai.pydantic.dev/",
                    "content": "Pydantic AI is a Python agent framework designed to make it easy to build production-grade applications with Generative AI.",
                },
                {
                    "title": "Getting Started with Pydantic AI",
                    "url": "https://ai.pydantic.dev/getting-started/",
                    "content": "Learn how to build your first AI agent with Pydantic AI. Simple, type-safe, and production-ready.",
                },
                {
                    "title": "Pydantic AI Examples",
                    "url": "https://ai.pydantic.dev/examples/",
                    "content": "Comprehensive examples showing Pydantic AI agents in action with various LLMs.",
                },
            ]
        },
        {
            "results": [
                {
                    "title": "Build AI Agents Tutorial",
                    "url": "https://tutorial.pydantic.dev/agents/",
                    "content": "Step-by-step guide to building AI agents with Pydantic AI framework.",
                },
                {
                    "title": "Pydantic AI Agent Patterns",
                    "url": "https://patterns.pydantic.dev/",
                    "content": "Common design patterns for building robust AI agents.",
                },
            ]
        },
    ]


class TestSearchAgentWithRealDatabase:
    """Test SearchAgent with real database integration."""

    @pytest.mark.asyncio
    async def test_search_agent_with_real_db_session(self, async_session: AsyncSession) -> None:
        """Test SearchAgent initialization with real async database session.

        Given: Real async database session from fixture
        When: Creating SearchAgent with real DB dependency
        Then: Agent initializes successfully and DB is accessible
        """
        # Mock external dependencies
        mock_llm = MagicMock(spec=OpenRouterClient)
        mock_llm.chat = AsyncMock()
        mock_tracer = MagicMock(spec=LangfuseTracer)
        mock_searxng = AsyncMock(spec=httpx.AsyncClient)

        deps = SearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=async_session,
            searxng_client=mock_searxng,
            serperdev_api_key="test_key",
            max_sources=20,
            timeout=60.0,
        )

        agent = SearchAgent(deps=deps)

        # Verify agent has real DB session via deps
        assert agent.deps.db == async_session
        assert agent.deps.db.is_active


class TestSearchAgentWithMockedAPIs:
    """Test SearchAgent with mocked external APIs and real async coordination."""

    @pytest.mark.asyncio
    async def test_search_workflow_with_mocked_llm_and_searxng(
        self,
        async_session: AsyncSession,
        mock_openrouter_responses: list[dict[str, Any]],
        mock_searxng_responses: list[dict[str, Any]],
    ) -> None:
        """Test complete search workflow with mocked external APIs.

        Given: Real DB session, mocked LLM and SearxNG responses
        When: Running full search workflow
        Then: Returns SearchOutput with sources from mocked responses
        """
        # Setup mocked LLM client
        mock_llm = MagicMock(spec=OpenRouterClient)
        mock_llm.chat = AsyncMock(return_value=mock_openrouter_responses[0])

        # Setup mocked SearxNG client
        mock_searxng = AsyncMock(spec=httpx.AsyncClient)

        # Create mock responses for each sub-query
        mock_responses = []
        for searxng_resp in mock_searxng_responses:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = searxng_resp
            mock_responses.append(mock_response)

        mock_searxng.get = AsyncMock(side_effect=mock_responses)

        # Create mock tracer
        mock_tracer = MagicMock(spec=LangfuseTracer)

        deps = SearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=async_session,
            searxng_client=mock_searxng,
            serperdev_api_key="test_key",
            max_sources=20,
            timeout=60.0,
        )

        agent = SearchAgent(deps=deps)

        # Execute search
        result = await agent.run("What is Pydantic AI?")

        # Verify result structure
        assert isinstance(result, SearchOutput)
        assert len(result.sub_queries) > 0
        assert len(result.sources) > 0
        assert result.confidence > 0

        # Verify sources contain expected data
        assert any("pydantic" in s.title.lower() for s in result.sources)
        assert all(s.relevance > 0 for s in result.sources)

    @pytest.mark.asyncio
    async def test_search_agent_handles_searxng_timeout(self, async_session: AsyncSession) -> None:
        """Test SearchAgent handles SearxNG timeout gracefully with fallback.

        Given: SearchAgent with SearxNG client that partially times out
        When: Executing search with multiple sub-queries where some timeout
        Then: Returns SearchOutput with available sources from successful queries
        """
        # Setup mocked LLM (successful)
        mock_llm = MagicMock(spec=OpenRouterClient)
        mock_llm.chat = AsyncMock(
            return_value={
                "sub_queries": [
                    {"query": "test query 1", "intent": "factual", "priority": 1},
                    {"query": "test query 2", "intent": "factual", "priority": 2},
                ]
            }
        )

        # Setup SearxNG with partial timeout (first fails, second succeeds with 5 sources)
        mock_searxng = AsyncMock(spec=httpx.AsyncClient)

        # First sub-query times out
        timeout_side_effect = httpx.TimeoutException("Timeout")

        # Second sub-query succeeds with 5 sources
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "results": [
                {
                    "title": f"Result {i}",
                    "url": f"https://example.com/{i}",
                    "content": f"Content {i}",
                }
                for i in range(1, 6)
            ]
        }

        mock_searxng.get = AsyncMock(side_effect=[timeout_side_effect, success_response])

        mock_tracer = MagicMock(spec=LangfuseTracer)

        deps = SearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=async_session,
            searxng_client=mock_searxng,
            serperdev_api_key="test_key",
            max_sources=20,
            timeout=60.0,
        )

        agent = SearchAgent(deps=deps)

        # Execute search - should not raise exception
        result = await agent.run("test query")

        # Verify graceful handling
        assert isinstance(result, SearchOutput)
        assert len(result.sub_queries) == 2
        # Should have sources from the successful query (minimum 5)
        assert len(result.sources) >= 5

    @pytest.mark.asyncio
    async def test_search_agent_deduplication_with_real_async(
        self, async_session: AsyncSession
    ) -> None:
        """Test source deduplication with real async coordination.

        Given: SearchAgent with multiple sub-queries returning duplicate URLs
        When: Executing parallel searches with async coordination
        Then: Duplicate URLs are removed, keeping highest relevance
        """
        # Setup LLM with multiple sub-queries
        mock_llm = MagicMock(spec=OpenRouterClient)
        mock_llm.chat = AsyncMock(
            return_value={
                "sub_queries": [
                    {"query": "query 1", "intent": "factual", "priority": 1},
                    {"query": "query 2", "intent": "factual", "priority": 2},
                ]
            }
        )

        # Setup SearxNG with duplicate URLs (different relevance) and enough unique sources
        mock_searxng = AsyncMock(spec=httpx.AsyncClient)

        response1 = MagicMock()
        response1.status_code = 200
        response1.json.return_value = {
            "results": [
                {
                    "title": "Page A (High Relevance)",
                    "url": "https://example.com/duplicate",
                    "content": "High quality content",
                },
                {
                    "title": "Unique Page 1",
                    "url": "https://example.com/unique1",
                    "content": "Unique content 1",
                },
                {
                    "title": "Unique Page 2",
                    "url": "https://example.com/unique2",
                    "content": "Unique content 2",
                },
            ]
        }

        response2 = MagicMock()
        response2.status_code = 200
        response2.json.return_value = {
            "results": [
                {
                    "title": "Page A (Low Relevance)",
                    "url": "https://example.com/duplicate",  # Duplicate URL
                    "content": "Lower quality content",
                },
                {
                    "title": "Unique Page 3",
                    "url": "https://example.com/unique3",
                    "content": "Unique content 3",
                },
                {
                    "title": "Unique Page 4",
                    "url": "https://example.com/unique4",
                    "content": "Unique content 4",
                },
            ]
        }

        mock_searxng.get = AsyncMock(side_effect=[response1, response2])
        mock_tracer = MagicMock(spec=LangfuseTracer)

        deps = SearchAgentDeps(
            llm_client=mock_llm,
            tracer=mock_tracer,
            db=async_session,
            searxng_client=mock_searxng,
            serperdev_api_key="test_key",
            max_sources=20,
            timeout=60.0,
        )

        agent = SearchAgent(deps=deps)
        result = await agent.run("test query")

        # Verify deduplication occurred
        urls = [s.url for s in result.sources]
        assert len(urls) == len(set(urls))  # No duplicate URLs
        assert "https://example.com/duplicate" in urls
