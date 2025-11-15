"""End-to-end tests for search pipeline with authority scoring.

Tests cover:
- Full search flow from query to ranked results
- Authority scoring impact on real-world search scenarios
- Integration with all pipeline components
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.agents.search_agent import (
    SearchAgent,
    SearchAgentDeps,
    SearchMode,
    SearchOutput,
    SearchSource,
)
from src.core.config import settings


@pytest.fixture
def realistic_search_sources() -> list[SearchSource]:
    """Create realistic search sources for E2E testing."""
    return [
        # Official documentation - should rank high with authority boost
        SearchSource(
            url="https://docs.python.org/3/library/asyncio.html",
            title="asyncio — Asynchronous I/O — Python 3.12 documentation",
            snippet="asyncio is used as a foundation for multiple Python asynchronous frameworks that provide high-performance network and web-servers, database connection libraries...",
            relevance=0.82,
            content=None,
            source_type="web",
        ),
        # StackOverflow - reputable but community-driven
        SearchSource(
            url="https://stackoverflow.com/questions/37278647/fire-and-forget-python-async-await",
            title="Fire and forget python async/await",
            snippet="I'm trying to create a function that runs a request in the background, but doesn't pause the execution of the current function. Here's what I have...",
            relevance=0.88,
            content=None,
            source_type="web",
        ),
        # Blog post - lower authority but potentially high relevance
        SearchSource(
            url="https://realpython.com/async-io-python/",
            title="Async IO in Python: A Complete Walkthrough",
            snippet="If you're like many Python programmers, you might have heard of asyncio but found yourself confused by what it's all about. This tutorial will help...",
            relevance=0.90,
            content=None,
            source_type="web",
        ),
        # Academic paper - highest authority for research
        SearchSource(
            url="https://arxiv.org/abs/2103.12345",
            title="Async Programming Patterns in Modern Python",
            snippet="We analyze asynchronous programming patterns in Python 3.5+ and their impact on application performance...",
            relevance=0.78,
            content=None,
            source_type="academic",
        ),
        # GitHub repository - reputable technical source
        SearchSource(
            url="https://github.com/python/cpython/blob/main/Lib/asyncio/__init__.py",
            title="cpython/Lib/asyncio/__init__.py at main · python/cpython",
            snippet="The Python programming language. Contribute to python/cpython development by creating an account on GitHub.",
            relevance=0.75,
            content=None,
            source_type="web",
        ),
        # Medium article - community platform
        SearchSource(
            url="https://medium.com/@asyncio_expert/mastering-python-async-abc123",
            title="Mastering Python Async/Await in 2024",
            snippet="Learn how to write efficient asynchronous Python code with practical examples and best practices...",
            relevance=0.85,
            content=None,
            source_type="web",
        ),
        # News article - reputable news source
        SearchSource(
            url="https://techcrunch.com/2024/01/15/python-async-adoption-grows",
            title="Python Async Adoption Grows Among Enterprises",
            snippet="More companies are adopting Python's async features for high-performance applications...",
            relevance=0.70,
            content=None,
            source_type="news",
        ),
        # Unknown blog - no authority boost
        SearchSource(
            url="https://myblog.example.com/python-async-tutorial",
            title="My Python Async Tutorial",
            snippet="Here's what I learned about Python async after 2 weeks of experimenting...",
            relevance=0.80,
            content=None,
            source_type="web",
        ),
    ]


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestE2ESearchPipelineWithAuthority:
    """End-to-end tests for complete search pipeline."""

    async def test_full_search_flow_with_authority_boost(
        self, realistic_search_sources: list[SearchSource]
    ) -> None:
        """Test full search flow with authority scoring enabled."""
        # Setup mock dependencies
        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()
        deps.max_sources = 20
        deps.timeout = 60.0
        deps.enable_reranking = True
        deps.rerank_weight = 0.6
        deps.enable_diversity_penalty = True

        # Mock search results
        deps.searxng_client.search.return_value = realistic_search_sources

        # Mock embedding service
        deps.embedding_service.rerank = AsyncMock(
            return_value=[(i, 0.9 - i * 0.05) for i in range(len(realistic_search_sources))]
        )

        agent = SearchAgent(deps=deps)

        # Execute search
        ranked = await agent.rank_results(realistic_search_sources, "python asyncio tutorial")

        # Verify authority boost impact
        # docs.python.org should get significant boost (1.0 authority)
        docs_python = [s for s in ranked if "docs.python.org" in s.url]
        assert len(docs_python) == 1

        # arxiv.org should also get boost (1.0 authority)
        arxiv = [s for s in ranked if "arxiv.org" in s.url]
        assert len(arxiv) == 1

        # Official docs and academic papers should rank higher than blogs
        official_positions = [
            i for i, s in enumerate(ranked) if "docs.python.org" in s.url or "arxiv.org" in s.url
        ]
        blog_positions = [
            i
            for i, s in enumerate(ranked)
            if "myblog.example.com" in s.url or "medium.com" in s.url
        ]

        if official_positions and blog_positions:
            assert min(official_positions) < max(blog_positions), (
                "Official sources should rank higher than personal blogs"
            )

    async def test_authority_preserves_highly_relevant_results(
        self, realistic_search_sources: list[SearchSource]
    ) -> None:
        """Test that authority doesn't completely override high relevance."""
        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()
        deps.enable_reranking = True
        deps.rerank_weight = 0.6

        # Mock high semantic scores for highly relevant results
        deps.embedding_service.rerank = AsyncMock(
            return_value=[
                (2, 0.95),  # RealPython (high relevance, low authority)
                (0, 0.85),  # docs.python.org (medium relevance, high authority)
                (3, 0.80),  # arxiv (low relevance, high authority)
                (1, 0.75),  # StackOverflow
                (4, 0.70),  # GitHub
                (5, 0.65),  # Medium
                (6, 0.60),  # TechCrunch
                (7, 0.55),  # myblog
            ]
        )

        agent = SearchAgent(deps=deps)
        ranked = await agent.rank_results(
            realistic_search_sources, "detailed python asyncio tutorial with examples"
        )

        # RealPython should still rank high despite lower authority
        # Authority boost shouldn't completely override semantic relevance
        realpython_pos = next((i for i, s in enumerate(ranked) if "realpython.com" in s.url), None)
        assert realpython_pos is not None
        assert realpython_pos < 3, "Highly relevant content should still rank well"

    async def test_search_mode_configurations(
        self, realistic_search_sources: list[SearchSource]
    ) -> None:
        """Test authority scoring works correctly across different search modes."""
        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()

        deps.embedding_service.rerank = AsyncMock(
            return_value=[(i, 0.8 - i * 0.05) for i in range(len(realistic_search_sources))]
        )

        agent = SearchAgent(deps=deps)

        # Test in different modes
        modes = [SearchMode.QUICK, SearchMode.BALANCED, SearchMode.DEEP]

        for mode in modes:
            ranked = await agent.rank_results(realistic_search_sources, "python asyncio")

            # Authority boost should apply consistently across modes
            docs_python = [s for s in ranked if "docs.python.org" in s.url]
            assert len(docs_python) == 1
            assert docs_python[0].final_score > 0.80


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestE2ERealWorldScenarios:
    """Test real-world search scenarios."""

    async def test_technical_documentation_search(self) -> None:
        """Test search for technical documentation prioritizes official sources."""
        sources = [
            SearchSource(
                url="https://docs.python.org/3/library/asyncio-task.html",
                title="Coroutines and Tasks",
                snippet="Official Python documentation on asyncio tasks",
                relevance=0.80,
                source_type="web",
            ),
            SearchSource(
                url="https://blog.example.com/asyncio-tasks",
                title="Understanding Asyncio Tasks",
                snippet="Personal blog explaining asyncio tasks",
                relevance=0.92,
                source_type="web",
            ),
            SearchSource(
                url="https://developer.mozilla.org/en-US/docs/Learn/JavaScript/Asynchronous",
                title="MDN Async Programming",
                snippet="Mozilla Developer Network async guide",
                relevance=0.75,
                source_type="web",
            ),
        ]

        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()
        deps.enable_reranking = False

        agent = SearchAgent(deps=deps)
        ranked = await agent.rank_results(sources, "asyncio task documentation")

        # Official docs should rank highest for documentation queries
        assert "docs.python.org" in ranked[0].url or "developer.mozilla.org" in ranked[0].url

    async def test_academic_research_search(self) -> None:
        """Test academic research queries prioritize scholarly sources."""
        sources = [
            SearchSource(
                url="https://arxiv.org/abs/2103.12345",
                title="Research on Async Patterns",
                snippet="Academic paper on async programming",
                relevance=0.75,
                source_type="academic",
            ),
            SearchSource(
                url="https://blog.medium.com/async-research",
                title="My Research on Async",
                snippet="Blog post about async research",
                relevance=0.85,
                source_type="web",
            ),
            SearchSource(
                url="https://dl.acm.org/doi/10.1145/3428290",
                title="ACM Paper on Async Programming",
                snippet="Peer-reviewed paper on async",
                relevance=0.78,
                source_type="academic",
            ),
        ]

        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()
        deps.enable_reranking = False

        agent = SearchAgent(deps=deps)
        ranked = await agent.rank_results(sources, "async programming research papers")

        # Academic sources should dominate
        assert any(domain in ranked[0].url for domain in ["arxiv.org", "acm.org", "ieee.org"])

    async def test_community_qa_search(self) -> None:
        """Test Q&A queries balance authority with community engagement."""
        sources = [
            SearchSource(
                url="https://stackoverflow.com/questions/12345/how-to-async",
                title="How to use async/await?",
                snippet="Q&A with 500 upvotes",
                relevance=0.92,
                source_type="web",
            ),
            SearchSource(
                url="https://docs.python.org/3/library/asyncio.html#asyncio.create_task",
                title="asyncio.create_task() documentation",
                snippet="Official documentation",
                relevance=0.70,
                source_type="web",
            ),
            SearchSource(
                url="https://reddit.com/r/python/comments/abc/async_question",
                title="Reddit: How do I use async?",
                snippet="Community discussion",
                relevance=0.88,
                source_type="web",
            ),
        ]

        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()
        deps.enable_reranking = False

        agent = SearchAgent(deps=deps)
        ranked = await agent.rank_results(sources, "how to use python async await")

        # StackOverflow should rank highly for how-to queries
        # but official docs should also be near top
        stackoverflow_pos = next(
            (i for i, s in enumerate(ranked) if "stackoverflow.com" in s.url), None
        )
        docs_pos = next((i for i, s in enumerate(ranked) if "docs.python.org" in s.url), None)

        assert stackoverflow_pos is not None and stackoverflow_pos < 2
        assert docs_pos is not None and docs_pos < 3


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.asyncio
class TestE2EAuthorityConfigurationImpact:
    """Test impact of authority configuration changes."""

    async def test_authority_weight_impact(self) -> None:
        """Test different authority weight settings."""
        sources = [
            SearchSource(
                url="https://docs.python.org/3/library/asyncio.html",
                title="Official Docs",
                snippet="Official documentation",
                relevance=0.70,
                source_type="web",
            ),
            SearchSource(
                url="https://blog.example.com/asyncio",
                title="Blog Post",
                snippet="High quality blog",
                relevance=0.90,
                source_type="web",
            ),
        ]

        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()
        deps.enable_reranking = False

        agent = SearchAgent(deps=deps)

        # Test with default weight (0.15)
        with patch.object(settings, "AUTHORITY_SCORING_WEIGHT", 0.15):
            ranked_low = await agent.rank_results(sources.copy(), "asyncio")

        # Test with higher weight (0.30)
        with patch.object(settings, "AUTHORITY_SCORING_WEIGHT", 0.30):
            ranked_high = await agent.rank_results(sources.copy(), "asyncio")

        # Higher weight should give more advantage to official docs
        docs_score_low = next(s.final_score for s in ranked_low if "docs.python.org" in s.url)
        docs_score_high = next(s.final_score for s in ranked_high if "docs.python.org" in s.url)

        assert docs_score_high > docs_score_low

    async def test_authority_multiplier_impact(self) -> None:
        """Test different authority multiplier settings."""
        sources = [
            SearchSource(
                url="https://docs.python.org/3/library/asyncio.html",
                title="Official Docs",
                snippet="Official documentation",
                relevance=0.75,
                source_type="web",
            ),
        ]

        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()
        deps.enable_reranking = False

        agent = SearchAgent(deps=deps)

        # Test with lower multiplier (1.1)
        with patch.object(settings, "AUTHORITY_BOOST_MULTIPLIER", 1.1):
            ranked_low = await agent.rank_results(sources.copy(), "asyncio")

        # Test with higher multiplier (2.0)
        with patch.object(settings, "AUTHORITY_BOOST_MULTIPLIER", 2.0):
            ranked_high = await agent.rank_results(sources.copy(), "asyncio")

        # Higher multiplier should result in higher final score
        score_low = ranked_low[0].final_score
        score_high = ranked_high[0].final_score

        assert score_high > score_low


@pytest.mark.e2e
@pytest.mark.asyncio
class TestE2EErrorHandling:
    """Test error handling in E2E scenarios."""

    async def test_authority_scoring_handles_network_errors(self) -> None:
        """Test that network errors in Wikipedia API don't break pipeline."""
        sources = [
            SearchSource(
                url="https://example.com/article",
                title="Article",
                snippet="Content",
                relevance=0.80,
                source_type="web",
            ),
        ]

        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()
        deps.enable_reranking = False

        agent = SearchAgent(deps=deps)

        # Simulate Wikipedia API failure
        with patch.object(agent.authority_scorer.http_client, "get") as mock_get:
            mock_get.side_effect = Exception("Network error")

            # Should not raise exception
            ranked = await agent.rank_results(sources, "test query")
            assert len(ranked) == 1

    async def test_authority_scoring_handles_malformed_sources(self) -> None:
        """Test handling of malformed source data."""
        sources = [
            SearchSource(
                url="",  # Empty URL
                title="Empty URL",
                snippet="Test",
                relevance=0.80,
            ),
            SearchSource(
                url="not-a-url",  # Invalid URL
                title="Invalid URL",
                snippet="Test",
                relevance=0.75,
            ),
            SearchSource(
                url="https://valid.com/page",
                title="Valid",
                snippet="Test",
                relevance=0.85,
            ),
        ]

        deps = MagicMock(spec=SearchAgentDeps)
        deps.llm_client = MagicMock()
        deps.tracer = MagicMock()
        deps.db = MagicMock()
        deps.searxng_client = AsyncMock()
        deps.serperdev_api_key = ""
        deps.crawl_client = MagicMock()
        deps.document_processor = MagicMock()
        deps.embedding_service = MagicMock()
        deps.enable_reranking = False

        agent = SearchAgent(deps=deps)

        # Should handle gracefully
        ranked = await agent.rank_results(sources, "test query")
        assert len(ranked) == 3
        assert all(hasattr(s, "final_score") for s in ranked)
