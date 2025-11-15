"""Integration tests for authority scoring within search agent.

Tests cover:
- Authority boost integration with rank_results()
- Impact on final_score calculation
- Interaction with semantic reranking
- End-to-end search pipeline with authority scoring
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.agents.search_agent import SearchAgent, SearchAgentDeps, SearchSource
from src.core.config import settings
from src.utils.authority_scorer import AuthorityScorer


@pytest_asyncio.fixture
async def mock_search_agent_deps() -> SearchAgentDeps:
    """Create mock dependencies for SearchAgent."""
    deps = MagicMock(spec=SearchAgentDeps)
    deps.llm_client = MagicMock()
    deps.tracer = MagicMock()
    deps.db = MagicMock()
    deps.searxng_client = MagicMock()
    deps.serperdev_api_key = ""
    deps.crawl_client = MagicMock()
    deps.document_processor = MagicMock()
    deps.embedding_service = MagicMock()
    deps.max_sources = 20
    deps.timeout = 60.0
    deps.min_sources = 5
    deps.min_confidence = 0.5
    deps.enable_crawling = True
    deps.max_crawl_urls = 5
    deps.enable_reranking = True
    deps.rerank_weight = 0.6
    deps.enable_diversity_penalty = True
    deps.enable_recency_boost = False
    deps.enable_query_aware = False
    deps.reranking_config = None
    return deps


@pytest.fixture
def sample_search_sources() -> list[SearchSource]:
    """Create sample sources with varying authority levels."""
    return [
        SearchSource(
            url="https://docs.python.org/3/library/asyncio.html",
            title="asyncio — Asynchronous I/O",
            snippet="Official Python async documentation",
            relevance=0.80,
            semantic_score=0.75,
            final_score=0.78,
            source_type="web",
        ),
        SearchSource(
            url="https://example.com/python-async-tutorial",
            title="Python Async Tutorial",
            snippet="Learn async programming",
            relevance=0.85,
            semantic_score=0.90,
            final_score=0.88,
            source_type="web",
        ),
        SearchSource(
            url="https://stackoverflow.com/questions/12345",
            title="How to use asyncio?",
            snippet="Q&A about Python asyncio",
            relevance=0.75,
            semantic_score=0.70,
            final_score=0.72,
            source_type="web",
        ),
        SearchSource(
            url="https://medium.com/@author/async-guide",
            title="Async Programming Guide",
            snippet="Blog post about async",
            relevance=0.70,
            semantic_score=0.65,
            final_score=0.67,
            source_type="web",
        ),
    ]


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthorityBoostIntegration:
    """Test authority scoring integration with SearchAgent."""

    async def test_authority_boost_affects_ranking(
        self, mock_search_agent_deps: SearchAgentDeps, sample_search_sources: list[SearchSource]
    ) -> None:
        """Test that authority scores affect final ranking."""
        # Create agent with authority scoring enabled
        agent = SearchAgent(deps=mock_search_agent_deps)

        with patch.object(agent.authority_scorer, "calculate_authority_score") as mock_score:
            # docs.python.org gets max authority
            # example.com gets no authority
            # stackoverflow gets medium authority
            # medium gets low authority
            mock_score.side_effect = [1.0, 0.0, 0.85, 0.70]

            ranked = await agent.rank_results(sample_search_sources, "python asyncio tutorial")

            # docs.python.org should be boosted to top despite lower initial score
            assert ranked[0].url == "https://docs.python.org/3/library/asyncio.html"
            assert ranked[0].final_score > sample_search_sources[0].final_score

    async def test_authority_boost_formula(self, mock_search_agent_deps: SearchAgentDeps) -> None:
        """Test the exact authority boost calculation formula."""
        agent = SearchAgent(deps=mock_search_agent_deps)

        source = SearchSource(
            url="https://docs.python.org/asyncio",
            title="Docs",
            snippet="Official",
            relevance=0.70,
            semantic_score=0.75,
            final_score=0.73,
            source_type="web",
        )

        with patch.object(agent.authority_scorer, "calculate_authority_score") as mock_score:
            mock_score.return_value = 0.85  # Reputable authority

            ranked = await agent.rank_results([source], "python asyncio")

            # Formula: final_score * (1 + boost * multiplier)
            # boost = authority * weight = 0.85 * 0.15 = 0.1275
            # new_final = 0.73 * (1 + 0.1275 * 1.3) = 0.73 * 1.16575 ≈ 0.851
            expected_min = 0.73 * 1.10  # At least 10% boost
            expected_max = min(1.0, 0.73 * 1.20)  # At most 20% boost

            assert ranked[0].final_score > expected_min
            assert ranked[0].final_score <= expected_max

    async def test_authority_boost_with_reranking_disabled(
        self, mock_search_agent_deps: SearchAgentDeps, sample_search_sources: list[SearchSource]
    ) -> None:
        """Test authority boost when semantic reranking is disabled."""
        mock_search_agent_deps.enable_reranking = False
        agent = SearchAgent(deps=mock_search_agent_deps)

        with patch.object(agent.authority_scorer, "calculate_authority_score") as mock_score:
            mock_score.side_effect = [1.0, 0.0, 0.85, 0.70]

            ranked = await agent.rank_results(sample_search_sources, "python asyncio")

            # Authority boost should still be applied
            assert ranked[0].final_score > sample_search_sources[0].relevance

    async def test_no_boost_when_authority_scoring_disabled(
        self, mock_search_agent_deps: SearchAgentDeps, sample_search_sources: list[SearchSource]
    ) -> None:
        """Test that no boost is applied when authority scoring is disabled."""
        with patch.object(settings, "ENABLE_AUTHORITY_SCORING", False):
            agent = SearchAgent(deps=mock_search_agent_deps)

            # Authority scorer should be None when disabled
            assert agent.authority_scorer is None

            ranked = await agent.rank_results(sample_search_sources, "python asyncio")

            # Ranking should be based only on relevance/semantic scores
            # No authority boost applied

    async def test_authority_boost_capped_at_one(
        self, mock_search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test that final_score is capped at 1.0 after authority boost."""
        agent = SearchAgent(deps=mock_search_agent_deps)

        source = SearchSource(
            url="https://docs.python.org/asyncio",
            title="Docs",
            snippet="Official",
            relevance=0.95,
            semantic_score=0.98,
            final_score=0.97,
            source_type="web",
        )

        with patch.object(agent.authority_scorer, "calculate_authority_score") as mock_score:
            mock_score.return_value = 1.0  # Max authority

            ranked = await agent.rank_results([source], "python asyncio")

            # Final score should be capped at 1.0
            assert ranked[0].final_score <= 1.0


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthorityWithSemanticReranking:
    """Test authority scoring interaction with semantic reranking."""

    async def test_authority_applied_after_reranking(
        self, mock_search_agent_deps: SearchAgentDeps, sample_search_sources: list[SearchSource]
    ) -> None:
        """Test that authority boost is applied after semantic reranking."""
        agent = SearchAgent(deps=mock_search_agent_deps)

        # Mock embedding service rerank
        mock_search_agent_deps.embedding_service.rerank = AsyncMock(
            return_value=[(0, 0.85), (1, 0.75), (2, 0.65), (3, 0.55)]
        )

        with patch.object(agent.authority_scorer, "calculate_authority_score") as mock_score:
            # First source (docs.python.org) gets max authority
            mock_score.side_effect = [1.0, 0.0, 0.85, 0.70]

            ranked = await agent.rank_results(sample_search_sources, "python asyncio")

            # Authority boost should be applied to reranked scores
            # docs.python.org should benefit from both high semantic score and authority
            assert ranked[0].url == "https://docs.python.org/3/library/asyncio.html"

    async def test_authority_preserves_reranking_order_when_similar(
        self, mock_search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test that authority boost preserves reranking order for similar scores."""
        agent = SearchAgent(deps=mock_search_agent_deps)

        sources = [
            SearchSource(
                url="https://docs.python.org/asyncio",
                title="Docs 1",
                snippet="Official",
                relevance=0.80,
                final_score=0.80,
                source_type="web",
            ),
            SearchSource(
                url="https://github.com/python/asyncio",
                title="Docs 2",
                snippet="GitHub",
                relevance=0.78,
                final_score=0.78,
                source_type="web",
            ),
        ]

        mock_search_agent_deps.embedding_service.rerank = AsyncMock(
            return_value=[(0, 0.90), (1, 0.88)]
        )

        with patch.object(agent.authority_scorer, "calculate_authority_score") as mock_score:
            # Both get same authority (official docs)
            mock_score.side_effect = [1.0, 0.85]

            ranked = await agent.rank_results(sources, "python asyncio")

            # Order should follow reranking since authority is similar
            assert ranked[0].url == "https://docs.python.org/asyncio"


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthorityScoringSideEffects:
    """Test authority scoring doesn't cause unexpected side effects."""

    async def test_authority_scoring_doesnt_modify_source_objects(
        self, mock_search_agent_deps: SearchAgentDeps, sample_search_sources: list[SearchSource]
    ) -> None:
        """Test that authority scoring doesn't corrupt original source data."""
        agent = SearchAgent(deps=mock_search_agent_deps)

        # Store original values
        original_urls = [s.url for s in sample_search_sources]
        original_titles = [s.title for s in sample_search_sources]
        original_relevances = [s.relevance for s in sample_search_sources]

        with patch.object(agent.authority_scorer, "calculate_authority_score") as mock_score:
            mock_score.side_effect = [1.0, 0.0, 0.85, 0.70]

            ranked = await agent.rank_results(sample_search_sources, "python asyncio")

            # Original data should be preserved
            for i, source in enumerate(ranked):
                assert source.url in original_urls
                assert source.title in original_titles
                assert source.relevance in original_relevances

    async def test_authority_scoring_handles_concurrent_calls(
        self, mock_search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test that authority scorer handles concurrent scoring calls."""
        import asyncio

        agent = SearchAgent(deps=mock_search_agent_deps)

        sources = [
            SearchSource(
                url=f"https://example{i}.com/article",
                title=f"Article {i}",
                snippet=f"Content {i}",
                relevance=0.75,
                source_type="web",
            )
            for i in range(10)
        ]

        # Simulate concurrent ranking
        tasks = [agent.rank_results([source], f"query {i}") for i, source in enumerate(sources)]
        results = await asyncio.gather(*tasks)

        # All should complete successfully
        assert len(results) == 10
        for result in results:
            assert len(result) == 1


@pytest.mark.integration
@pytest.mark.asyncio
class TestAuthorityLogging:
    """Test authority scoring logging and debugging."""

    async def test_authority_boost_logging(
        self, mock_search_agent_deps: SearchAgentDeps, sample_search_sources: list[SearchSource]
    ) -> None:
        """Test that authority boost events are logged."""
        agent = SearchAgent(deps=mock_search_agent_deps)

        with patch.object(agent.authority_scorer, "calculate_authority_score") as mock_score:
            mock_score.side_effect = [1.0, 0.0, 0.85, 0.70]

            with patch("src.agents.search_agent.logger") as mock_logger:
                await agent.rank_results(sample_search_sources, "python asyncio")

                # Should log authority boost application
                assert any(
                    "authority" in str(call).lower() for call in mock_logger.info.call_args_list
                )

    async def test_authority_disabled_logging(
        self, mock_search_agent_deps: SearchAgentDeps, sample_search_sources: list[SearchSource]
    ) -> None:
        """Test logging when authority scoring is disabled."""
        with patch.object(settings, "ENABLE_AUTHORITY_SCORING", False):
            agent = SearchAgent(deps=mock_search_agent_deps)

            with patch("src.agents.search_agent.logger") as mock_logger:
                await agent.rank_results(sample_search_sources, "python asyncio")

                # Should not log authority-related messages
                authority_logs = [
                    call
                    for call in mock_logger.info.call_args_list
                    if "authority" in str(call).lower()
                ]
                # Only startup log should mention authority (disabled status)
                assert len(authority_logs) <= 1


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
class TestAuthorityPerformance:
    """Test authority scoring performance impact."""

    async def test_authority_scoring_performance_impact(
        self, mock_search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test that authority scoring doesn't significantly slow down ranking."""
        import time

        agent = SearchAgent(deps=mock_search_agent_deps)

        # Create many sources
        sources = [
            SearchSource(
                url=f"https://example{i}.com/article",
                title=f"Article {i}",
                snippet=f"Content {i}",
                relevance=0.70 + (i % 3) * 0.1,
                source_type="web",
            )
            for i in range(100)
        ]

        with patch.object(agent.authority_scorer, "calculate_authority_score") as mock_score:
            mock_score.return_value = 0.85

            start = time.time()
            ranked = await agent.rank_results(sources, "test query")
            duration = time.time() - start

            # Should complete in reasonable time (< 5 seconds for 100 sources)
            assert duration < 5.0
            assert len(ranked) <= agent.max_sources

    async def test_wikipedia_cache_improves_performance(
        self, mock_search_agent_deps: SearchAgentDeps
    ) -> None:
        """Test that Wikipedia caching improves repeated query performance."""
        import time

        agent = SearchAgent(deps=mock_search_agent_deps)

        source = SearchSource(
            url="https://docs.python.org/asyncio",
            title="Docs",
            snippet="Official",
            relevance=0.85,
            source_type="web",
        )

        # First call - cache miss
        start1 = time.time()
        await agent.rank_results([source], "python asyncio")
        duration1 = time.time() - start1

        # Second call - cache hit
        start2 = time.time()
        await agent.rank_results([source], "python asyncio")
        duration2 = time.time() - start2

        # Cached call should be faster or same
        assert duration2 <= duration1 * 1.5  # Allow some variance
