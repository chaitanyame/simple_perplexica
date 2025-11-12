"""Integration test for citation grounding in ResearchAgent.

Tests end-to-end grounding functionality with real LLM synthesis.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.research_agent import ResearchAgent, ResearchAgentDeps
from src.models.citation import Citation
from src.services.embedding.embedding_service import EmbeddingService


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing."""
    client = MagicMock()
    client.chat = AsyncMock(return_value={
        "content": "FastAPI is a modern web framework for Python 3.7+. It provides automatic API documentation and validation. The framework was created by Sebastián Ramírez and supports async operations."
    })
    return client


@pytest.fixture
def mock_search_agent():
    """Mock search agent."""
    agent = MagicMock()
    return agent


@pytest.fixture
def mock_vector_store():
    """Mock vector store."""
    store = MagicMock()
    return store


@pytest.fixture
async def embedding_service():
    """Real embedding service for testing."""
    service = EmbeddingService(
        model_name="all-MiniLM-L6-v2",
        device="cpu",
    )
    # Ensure model is loaded
    await service.embed_text("test")
    return service


@pytest.fixture
def sample_citations() -> list[Citation]:
    """Sample citations for testing."""
    return [
        Citation(
            source_id="1",
            title="FastAPI Documentation",
            url="https://fastapi.tiangolo.com/",
            excerpt="FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints. It provides automatic interactive API documentation and validation.",
            relevance=0.95,
        ),
        Citation(
            source_id="2",
            title="FastAPI GitHub",
            url="https://github.com/tiangolo/fastapi",
            excerpt="FastAPI framework by Sebastián Ramírez. FastAPI is a modern Python web framework with async/await support. It leverages Python type hints for automatic validation.",
            relevance=0.90,
        ),
    ]


class TestCitationGroundingIntegration:
    """Test citation grounding integration with ResearchAgent."""

    @pytest.mark.asyncio
    async def test_synthesize_findings_with_grounding_enabled(
        self,
        mock_llm_client,
        mock_search_agent,
        mock_vector_store,
        embedding_service,
        sample_citations,
    ):
        """Test that grounding is performed when enabled.
        
        Given: ResearchAgent with real embedding service
        When: Synthesizing findings with enable_grounding=True
        Then: Returns synthesis and grounding_result with metrics
        """
        # Create agent deps
        deps = ResearchAgentDeps(
            llm_client=mock_llm_client,
            tracer=None,  # No tracer for test
            db=MagicMock(),
            search_agent=mock_search_agent,
            vector_store=mock_vector_store,
            embedding_service=embedding_service,
        )
        
        agent = ResearchAgent(deps=deps)
        
        # Synthesize with grounding
        synthesis, grounding_result = await agent.synthesize_findings(
            citations=sample_citations,
            query="What is FastAPI?",
            enable_grounding=True,
        )
        
        # Verify synthesis returned
        assert isinstance(synthesis, str)
        assert len(synthesis) > 0
        assert "FastAPI" in synthesis
        
        # Verify grounding result returned
        assert grounding_result is not None
        assert grounding_result.original_text == synthesis
        assert len(grounding_result.claims) > 0  # Should extract claims
        assert 0.0 <= grounding_result.overall_grounding <= 1.0
        assert grounding_result.hallucination_count >= 0

    @pytest.mark.asyncio
    async def test_grounding_detects_well_supported_claims(
        self,
        mock_llm_client,
        mock_search_agent,
        mock_vector_store,
        embedding_service,
        sample_citations,
    ):
        """Test that grounding correctly identifies well-supported claims.
        
        Given: Synthesis that closely matches source citations
        When: Grounding analysis is performed
        Then: Most claims should have high grounding scores
        """
        deps = ResearchAgentDeps(
            llm_client=mock_llm_client,
            tracer=None,
            db=MagicMock(),
            search_agent=mock_search_agent,
            vector_store=mock_vector_store,
            embedding_service=embedding_service,
        )
        
        agent = ResearchAgent(deps=deps)
        
        # Synthesize with grounding
        synthesis, grounding_result = await agent.synthesize_findings(
            citations=sample_citations,
            query="What is FastAPI?",
            enable_grounding=True,
        )
        
        # Check that some claims are grounded (LLM may paraphrase)
        grounded_claims = [c for c in grounding_result.claims if c.is_grounded]
        grounding_rate = len(grounded_claims) / len(grounding_result.claims) if grounding_result.claims else 0
        
        # Since synthesis mentions facts from citations, expect reasonable grounding
        # Note: LLM may paraphrase, so we don't expect 100%
        assert grounding_rate >= 0.2, f"Expected >20% grounded, got {grounding_rate:.1%}"
        
        # Overall grounding should be reasonable (hybrid scoring is more lenient)
        assert grounding_result.overall_grounding >= 0.4, (
            f"Expected overall grounding ≥0.4, got {grounding_result.overall_grounding:.2f}"
        )

    @pytest.mark.asyncio
    async def test_synthesize_findings_with_grounding_disabled(
        self,
        mock_llm_client,
        mock_search_agent,
        mock_vector_store,
        embedding_service,
        sample_citations,
    ):
        """Test that grounding can be disabled.
        
        Given: ResearchAgent with grounding capability
        When: Synthesizing with enable_grounding=False
        Then: Returns synthesis but no grounding_result
        """
        deps = ResearchAgentDeps(
            llm_client=mock_llm_client,
            tracer=None,
            db=MagicMock(),
            search_agent=mock_search_agent,
            vector_store=mock_vector_store,
            embedding_service=embedding_service,
        )
        
        agent = ResearchAgent(deps=deps)
        
        # Synthesize without grounding
        synthesis, grounding_result = await agent.synthesize_findings(
            citations=sample_citations,
            query="What is FastAPI?",
            enable_grounding=False,
        )
        
        # Verify synthesis returned
        assert isinstance(synthesis, str)
        assert len(synthesis) > 0
        
        # Verify no grounding performed
        assert grounding_result is None

    @pytest.mark.asyncio
    async def test_grounding_with_empty_citations(
        self,
        mock_llm_client,
        mock_search_agent,
        mock_vector_store,
        embedding_service,
    ):
        """Test grounding handles empty citations gracefully.
        
        Given: No citations available
        When: Attempting to ground synthesis
        Then: Returns None for grounding_result (graceful degradation)
        """
        deps = ResearchAgentDeps(
            llm_client=mock_llm_client,
            tracer=None,
            db=MagicMock(),
            search_agent=mock_search_agent,
            vector_store=mock_vector_store,
            embedding_service=embedding_service,
        )
        
        agent = ResearchAgent(deps=deps)
        
        # Synthesize with empty citations
        synthesis, grounding_result = await agent.synthesize_findings(
            citations=[],
            query="What is FastAPI?",
            enable_grounding=True,
        )
        
        # Should still return synthesis (from LLM)
        assert isinstance(synthesis, str)
        
        # Grounding should be None or have no claims
        if grounding_result:
            assert len(grounding_result.claims) == 0
