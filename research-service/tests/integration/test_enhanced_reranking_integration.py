"""Integration test for enhanced semantic reranking in SearchAgent.

Tests that the enhanced reranking features (diversity, recency, query-aware)
are properly integrated and can be toggled via SearchAgentDeps configuration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.search_agent import SearchAgent, SearchAgentDeps
from src.services.embedding.semantic_reranker import RerankingConfig, RecencyConfig


def create_mock_deps(**overrides):
    """Create a fully mocked SearchAgentDeps with all required attributes."""
    mock_deps = MagicMock(spec=SearchAgentDeps)
    
    # Set all required attributes with defaults
    mock_deps.llm_client = AsyncMock()
    mock_deps.tracer = MagicMock()
    mock_deps.db = AsyncMock()
    mock_deps.searxng_client = AsyncMock()
    mock_deps.serperdev_api_key = "test_key"
    mock_deps.crawl_client = AsyncMock()
    mock_deps.document_processor = AsyncMock()
    mock_deps.embedding_service = AsyncMock()
    mock_deps.max_sources = 20
    mock_deps.timeout = 60.0
    mock_deps.min_sources = 5
    mock_deps.min_confidence = 0.5
    mock_deps.enable_crawling = True
    mock_deps.max_crawl_urls = 5
    mock_deps.enable_reranking = True
    mock_deps.rerank_weight = 0.6
    mock_deps.enable_diversity_penalty = False
    mock_deps.enable_recency_boost = False
    mock_deps.enable_query_aware = False
    mock_deps.reranking_config = None
    
    # Apply overrides
    for key, value in overrides.items():
        setattr(mock_deps, key, value)
    
    return mock_deps


@pytest.mark.asyncio
async def test_enhanced_reranking_disabled_by_default():
    """Test that enhanced reranking is disabled by default (backward compatibility)."""
    # Create mock with reranking enabled but enhancements disabled
    mock_embedding_service = AsyncMock()
    mock_embedding_service.rerank = AsyncMock(return_value=[
        (0, 0.9),
        (1, 0.7),
        (2, 0.5),
    ])
    
    mock_deps = create_mock_deps(
        enable_reranking=True,
        enable_diversity_penalty=False,
        enable_recency_boost=False,
        enable_query_aware=False,
        embedding_service=mock_embedding_service,
    )
    
    agent = SearchAgent(deps=mock_deps)
    
    # Create mock sources
    from src.agents.search_agent import SearchSource
    sources = [
        SearchSource(title="A", url="http://a.com", snippet="Test A", relevance=0.8, source_type="web"),
        SearchSource(title="B", url="http://b.com", snippet="Test B", relevance=0.7, source_type="web"),
        SearchSource(title="C", url="http://c.com", snippet="Test C", relevance=0.6, source_type="web"),
    ]
    
    # Rank sources
    ranked = await agent.rank_results(sources, "test query")
    
    # Should use standard reranking (not enhanced)
    assert mock_embedding_service.rerank.called
    assert len(ranked) == 3


@pytest.mark.asyncio
async def test_enhanced_reranking_with_diversity():
    """Test that diversity penalty can be enabled."""
    # Mock embedding service with diversity support
    mock_embedding_service = AsyncMock()
    mock_embedding_service.rerank = AsyncMock(return_value=[
        (0, 0.9),
        (1, 0.85),
    ])
    mock_embedding_service.embed_batch = AsyncMock(return_value=[
        [0.1] * 384,  # Mock 384D embedding
        [0.2] * 384,
    ])
    
    mock_deps = create_mock_deps(
        enable_reranking=True,
        enable_diversity_penalty=True,
        enable_recency_boost=False,
        enable_query_aware=False,
        reranking_config=None,
        embedding_service=mock_embedding_service,
    )
    
    agent = SearchAgent(deps=mock_deps)
    
    from src.agents.search_agent import SearchSource
    sources = [
        SearchSource(title="A", url="http://a.com", snippet="Machine learning basics", relevance=0.9, source_type="web"),
        SearchSource(title="B", url="http://b.com", snippet="Machine learning fundamentals", relevance=0.85, source_type="web"),
    ]
    
    # Should not crash with diversity enabled
    ranked = await agent.rank_results(sources, "machine learning")
    assert len(ranked) == 2


@pytest.mark.asyncio
async def test_enhanced_reranking_with_query_aware():
    """Test that query-aware reranking can be enabled."""
    mock_embedding_service = AsyncMock()
    mock_embedding_service.rerank = AsyncMock(return_value=[
        (0, 0.9),
        (1, 0.7),
    ])
    
    mock_deps = create_mock_deps(
        enable_reranking=True,
        enable_diversity_penalty=False,
        enable_recency_boost=False,
        enable_query_aware=True,
        reranking_config=None,
        embedding_service=mock_embedding_service,
    )
    
    agent = SearchAgent(deps=mock_deps)
    
    from src.agents.search_agent import SearchSource
    sources = [
        SearchSource(title="A", url="http://a.com", snippet="Short answer", relevance=0.9, source_type="web"),
        SearchSource(title="B", url="http://b.com", snippet="Long detailed explanation" * 20, relevance=0.8, source_type="web"),
    ]
    
    # Should not crash with query-aware enabled
    ranked = await agent.rank_results(sources, "What is AI?")
    assert len(ranked) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
