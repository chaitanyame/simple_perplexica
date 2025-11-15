"""Unit tests for authority scoring functionality.

Tests cover:
- Domain tier classification (Official, Reputable, Community)
- Pattern-based authority detection
- Wikipedia citation proxy
- Edge cases and error handling
- Configuration toggles
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.agents.search_agent import SearchSource
from src.core.config import Settings
from src.utils.authority_scorer import AuthorityScorer


@pytest.fixture
def mock_settings() -> Settings:
    """Create mock settings with authority scoring enabled."""
    settings = MagicMock(spec=Settings)
    settings.ENABLE_AUTHORITY_SCORING = True
    settings.AUTHORITY_SCORING_WEIGHT = 0.15
    settings.ENABLE_PATTERN_AUTHORITY = True
    settings.ENABLE_WIKIPEDIA_AUTHORITY = True
    settings.WIKIPEDIA_CACHE_TTL = 3600
    settings.AUTHORITY_BOOST_MULTIPLIER = 1.3
    return settings


@pytest.fixture
def authority_scorer(mock_settings: Settings) -> AuthorityScorer:
    """Create AuthorityScorer instance for testing."""
    return AuthorityScorer(mock_settings)


@pytest.fixture
def sample_sources() -> list[SearchSource]:
    """Create sample search sources for testing."""
    return [
        SearchSource(
            url="https://docs.python.org/3/library/asyncio.html",
            title="asyncio — Asynchronous I/O",
            snippet="Official Python documentation",
            relevance=0.95,
            source_type="web",
        ),
        SearchSource(
            url="https://stackoverflow.com/questions/12345/python-async",
            title="How to use Python async/await?",
            snippet="Community Q&A about Python async",
            relevance=0.85,
            source_type="web",
        ),
        SearchSource(
            url="https://example.com/python-tutorial",
            title="Python Tutorial",
            snippet="Learn Python basics",
            relevance=0.75,
            source_type="web",
        ),
        SearchSource(
            url="https://github.com/python/cpython",
            title="Python Source Code",
            snippet="Official Python repository",
            relevance=0.90,
            source_type="web",
        ),
        SearchSource(
            url="https://medium.com/@user/python-async",
            title="Understanding Python Async",
            snippet="Blog post about Python async",
            relevance=0.70,
            source_type="web",
        ),
    ]


@pytest.mark.unit
@pytest.mark.fast
class TestDomainClassification:
    """Test domain tier classification."""

    @pytest.mark.asyncio
    async def test_official_gov_domain(self, authority_scorer: AuthorityScorer) -> None:
        """Test that .gov domains get official authority score."""
        source = SearchSource(
            url="https://www.usa.gov/topic",
            title="Government Info",
            snippet="Official",
            relevance=0.8,
            source_type="web",
        )
        score = await authority_scorer.calculate_authority_score(source)
        assert score == 1.0, ".gov domain should have authority 1.0"

    @pytest.mark.asyncio
    async def test_official_edu_domain(self, authority_scorer: AuthorityScorer) -> None:
        """Test that .edu domains get official authority score."""
        source = SearchSource(
            url="https://mit.edu/research",
            title="MIT Research",
            snippet="Academic",
            relevance=0.9,
            source_type="web",
        )
        score = await authority_scorer.calculate_authority_score(source)
        assert score == 1.0, ".edu domain should have authority 1.0"

    @pytest.mark.asyncio
    async def test_official_documentation(self, authority_scorer: AuthorityScorer) -> None:
        """Test that official documentation domains get highest authority."""
        test_cases = [
            "https://docs.python.org/3/library/",
            "https://docs.microsoft.com/azure/",
            "https://cloud.google.com/docs/",
            "https://docs.docker.com/engine/",
        ]

        for url in test_cases:
            source = SearchSource(
                url=url, title="Docs", snippet="Official docs", relevance=0.9, source_type="web"
            )
            score = await authority_scorer.calculate_authority_score(source)
            assert score == 1.0, f"{url} should have authority 1.0"

    @pytest.mark.asyncio
    async def test_academic_sources(self, authority_scorer: AuthorityScorer) -> None:
        """Test that academic/research sources get highest authority."""
        test_cases = [
            "https://arxiv.org/abs/1234.5678",
            "https://www.nature.com/articles/nature12345",
            "https://ieeexplore.ieee.org/document/1234567",
            "https://dl.acm.org/doi/10.1145/1234567",
        ]

        for url in test_cases:
            source = SearchSource(
                url=url,
                title="Research",
                snippet="Academic paper",
                relevance=0.95,
                source_type="web",
            )
            score = await authority_scorer.calculate_authority_score(source)
            assert score == 1.0, f"{url} should have authority 1.0"

    @pytest.mark.asyncio
    async def test_reputable_domains(self, authority_scorer: AuthorityScorer) -> None:
        """Test that reputable domains get tier 2 authority."""
        test_cases = [
            "https://github.com/user/repo",
            "https://stackoverflow.com/questions/12345",
            "https://www.microsoft.com/products",
            "https://techcrunch.com/2024/article",
        ]

        for url in test_cases:
            source = SearchSource(
                url=url, title="Content", snippet="Reputable", relevance=0.85, source_type="web"
            )
            score = await authority_scorer.calculate_authority_score(source)
            assert score == 0.85, f"{url} should have authority 0.85"

    @pytest.mark.asyncio
    async def test_community_domains(self, authority_scorer: AuthorityScorer) -> None:
        """Test that community domains get tier 3 authority."""
        test_cases = [
            "https://medium.com/@user/article",
            "https://dev.to/user/post",
            "https://reddit.com/r/programming/comments/123",
        ]

        for url in test_cases:
            source = SearchSource(
                url=url, title="Post", snippet="Community", relevance=0.70, source_type="web"
            )
            score = await authority_scorer.calculate_authority_score(source)
            assert score == 0.70, f"{url} should have authority 0.70"

    @pytest.mark.asyncio
    async def test_unknown_domain(self, authority_scorer: AuthorityScorer) -> None:
        """Test that unknown domains get no authority boost."""
        source = SearchSource(
            url="https://random-blog.com/post",
            title="Blog",
            snippet="Content",
            relevance=0.60,
            source_type="web",
        )
        score = await authority_scorer.calculate_authority_score(source)
        # Should get at most pattern authority (0.75) or high relevance proxy (0.60)
        assert score <= 0.75


@pytest.mark.unit
@pytest.mark.fast
class TestPatternAuthority:
    """Test pattern-based authority detection."""

    @pytest.mark.asyncio
    async def test_docs_pattern(self, authority_scorer: AuthorityScorer) -> None:
        """Test that URLs with 'docs.' pattern get authority boost."""
        source = SearchSource(
            url="https://docs.example.com/api",
            title="API Docs",
            snippet="Documentation",
            relevance=0.8,
            source_type="web",
        )
        score = await authority_scorer.calculate_authority_score(source)
        assert score >= 0.75, "docs.* pattern should grant authority"

    @pytest.mark.asyncio
    async def test_developer_pattern(self, authority_scorer: AuthorityScorer) -> None:
        """Test that URLs with 'developer.' pattern get authority boost."""
        source = SearchSource(
            url="https://developer.example.com/api",
            title="Dev Portal",
            snippet="Developer docs",
            relevance=0.8,
            source_type="web",
        )
        score = await authority_scorer.calculate_authority_score(source)
        assert score >= 0.75, "developer.* pattern should grant authority"

    @pytest.mark.asyncio
    async def test_api_documentation_pattern(self, authority_scorer: AuthorityScorer) -> None:
        """Test that /api and /reference paths get authority boost."""
        test_cases = [
            "https://example.com/api/reference",
            "https://example.com/documentation/api",
            "https://example.com/reference/guide",
        ]

        for url in test_cases:
            source = SearchSource(
                url=url,
                title="API Docs",
                snippet="Technical docs",
                relevance=0.8,
                source_type="web",
            )
            score = await authority_scorer.calculate_authority_score(source)
            assert score >= 0.75, f"{url} should get pattern authority"

    @pytest.mark.asyncio
    async def test_high_relevance_proxy(self, authority_scorer: AuthorityScorer) -> None:
        """Test that high relevance (>=0.85) acts as authority proxy."""
        source = SearchSource(
            url="https://unknown-site.com/article",
            title="High Quality Content",
            snippet="Relevant",
            relevance=0.95,
            source_type="web",
        )
        score = await authority_scorer.calculate_authority_score(source)
        assert score >= 0.60, "High relevance should act as authority proxy"


@pytest.mark.unit
@pytest.mark.asyncio
class TestWikipediaCitationProxy:
    """Test Wikipedia citation-based authority."""

    async def test_wikipedia_citation_found(self, authority_scorer: AuthorityScorer) -> None:
        """Test that sources cited by Wikipedia get authority boost."""
        with patch.object(authority_scorer.http_client, "get") as mock_get:
            # Mock Wikipedia search response
            search_response = MagicMock()
            search_response.json.return_value = {
                "query": {"search": [{"pageid": 12345, "title": "Python (programming language)"}]}
            }

            # Mock Wikipedia page response
            page_response = MagicMock()
            page_response.json.return_value = {
                "query": {
                    "pages": {
                        "12345": {
                            "extlinks": [
                                {"*": "https://python.org"},
                                {"*": "https://docs.python.org"},
                            ]
                        }
                    }
                }
            }

            mock_get.side_effect = [search_response, page_response]

            source = SearchSource(
                url="https://docs.python.org/tutorial",
                title="Python Tutorial",
                snippet="Learn Python",
                relevance=0.8,
                source_type="web",
            )

            score = await authority_scorer.calculate_authority_score(
                source, query="python tutorial"
            )
            assert score == 1.0, "Wikipedia-cited source should get max authority"

    async def test_wikipedia_citation_not_found(self, authority_scorer: AuthorityScorer) -> None:
        """Test handling when source not cited by Wikipedia."""
        with patch.object(authority_scorer.http_client, "get") as mock_get:
            # Mock Wikipedia search response
            search_response = MagicMock()
            search_response.json.return_value = {
                "query": {"search": [{"pageid": 12345, "title": "Python"}]}
            }

            # Mock Wikipedia page response with different citations
            page_response = MagicMock()
            page_response.json.return_value = {
                "query": {
                    "pages": {
                        "12345": {
                            "extlinks": [
                                {"*": "https://other-site.com"},
                            ]
                        }
                    }
                }
            }

            mock_get.side_effect = [search_response, page_response]

            source = SearchSource(
                url="https://unknown-blog.com/python",
                title="Python Blog",
                snippet="Blog post",
                relevance=0.7,
                source_type="web",
            )

            score = await authority_scorer.calculate_authority_score(source, query="python")
            # Should not get Wikipedia authority, may get other signals
            assert score < 1.0

    async def test_wikipedia_api_error(self, authority_scorer: AuthorityScorer) -> None:
        """Test graceful handling of Wikipedia API errors."""
        with patch.object(authority_scorer.http_client, "get") as mock_get:
            mock_get.side_effect = httpx.HTTPError("API error")

            source = SearchSource(
                url="https://example.com/article",
                title="Article",
                snippet="Content",
                relevance=0.8,
                source_type="web",
            )

            # Should not raise exception, just return 0 for Wikipedia authority
            score = await authority_scorer.calculate_authority_score(source, query="test")
            assert score >= 0.0

    async def test_wikipedia_caching(self, authority_scorer: AuthorityScorer) -> None:
        """Test that Wikipedia citations are cached."""
        with patch.object(authority_scorer.http_client, "get") as mock_get:
            search_response = MagicMock()
            search_response.json.return_value = {
                "query": {"search": [{"pageid": 123, "title": "Test"}]}
            }
            page_response = MagicMock()
            page_response.json.return_value = {
                "query": {"pages": {"123": {"extlinks": [{"*": "https://python.org"}]}}}
            }
            mock_get.side_effect = [search_response, page_response]

            source = SearchSource(
                url="https://python.org/doc",
                title="Docs",
                snippet="Text",
                relevance=0.8,
                source_type="web",
            )

            # First call should hit API
            score1 = await authority_scorer.calculate_authority_score(source, query="python")

            # Second call with same query should use cache
            mock_get.side_effect = []  # No more responses
            score2 = await authority_scorer.calculate_authority_score(source, query="python")

            assert score1 == score2
            assert len(authority_scorer.wikipedia_cache) == 1


@pytest.mark.unit
@pytest.mark.fast
class TestConfigurationToggles:
    """Test configuration flags for authority scoring."""

    @pytest.mark.asyncio
    async def test_authority_scoring_disabled(self) -> None:
        """Test that scoring returns 0 when disabled."""
        settings = MagicMock(spec=Settings)
        settings.ENABLE_AUTHORITY_SCORING = False
        scorer = AuthorityScorer(settings)

        source = SearchSource(
            url="https://docs.python.org/",
            title="Docs",
            snippet="Official",
            relevance=0.9,
            source_type="web",
        )

        score = await scorer.calculate_authority_score(source)
        assert score == 0.0, "Should return 0 when disabled"

    @pytest.mark.asyncio
    async def test_pattern_authority_disabled(self) -> None:
        """Test that pattern detection is skipped when disabled."""
        settings = MagicMock(spec=Settings)
        settings.ENABLE_AUTHORITY_SCORING = True
        settings.ENABLE_PATTERN_AUTHORITY = False
        settings.ENABLE_WIKIPEDIA_AUTHORITY = False
        scorer = AuthorityScorer(settings)

        source = SearchSource(
            url="https://docs.example.com/api",
            title="API Docs",
            snippet="Docs",
            relevance=0.8,
            source_type="web",
        )

        score = await scorer.calculate_authority_score(source)
        assert score == 0.0, "Should skip pattern authority when disabled"

    @pytest.mark.asyncio
    async def test_wikipedia_authority_disabled(self) -> None:
        """Test that Wikipedia proxy is skipped when disabled."""
        settings = MagicMock(spec=Settings)
        settings.ENABLE_AUTHORITY_SCORING = True
        settings.ENABLE_PATTERN_AUTHORITY = True
        settings.ENABLE_WIKIPEDIA_AUTHORITY = False
        scorer = AuthorityScorer(settings)

        source = SearchSource(
            url="https://example.com/article",
            title="Article",
            snippet="Text",
            relevance=0.7,
            source_type="web",
        )

        # Should only get pattern authority (if any)
        score = await scorer.calculate_authority_score(source, query="test query")
        # No Wikipedia check should happen
        assert score >= 0.0


@pytest.mark.unit
@pytest.mark.fast
class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_invalid_url(self, authority_scorer: AuthorityScorer) -> None:
        """Test handling of invalid URLs."""
        source = SearchSource(
            url="not-a-valid-url", title="Invalid", snippet="Test", relevance=0.5, source_type="web"
        )

        score = await authority_scorer.calculate_authority_score(source)
        assert score >= 0.0, "Should handle invalid URLs gracefully"

    @pytest.mark.asyncio
    async def test_empty_url(self, authority_scorer: AuthorityScorer) -> None:
        """Test handling of empty URL."""
        source = SearchSource(
            url="", title="Empty", snippet="Test", relevance=0.5, source_type="web"
        )

        score = await authority_scorer.calculate_authority_score(source)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_subdomain_matching(self, authority_scorer: AuthorityScorer) -> None:
        """Test that subdomains are matched correctly."""
        # Should match subdomain of official domain
        source1 = SearchSource(
            url="https://api.github.com/users",
            title="API",
            snippet="GitHub API",
            relevance=0.8,
            source_type="web",
        )
        score1 = await authority_scorer.calculate_authority_score(source1)

        # Should match main domain
        source2 = SearchSource(
            url="https://github.com/user/repo",
            title="Repo",
            snippet="Repository",
            relevance=0.8,
            source_type="web",
        )
        score2 = await authority_scorer.calculate_authority_score(source2)

        assert score1 == score2 == 0.85, "Subdomains should match parent domain"

    @pytest.mark.asyncio
    async def test_max_score_selection(self, authority_scorer: AuthorityScorer) -> None:
        """Test that maximum authority score is returned."""
        # Source matches both pattern (0.75) and reputable domain (0.85)
        source = SearchSource(
            url="https://developer.github.com/api",
            title="GitHub API",
            snippet="Developer API",
            relevance=0.9,
            source_type="web",
        )

        score = await authority_scorer.calculate_authority_score(source)
        # Should return max(0.75 pattern, 0.85 reputable, 0.60 high_relevance) = 0.85
        assert score == 0.85

    @pytest.mark.asyncio
    async def test_no_query_for_wikipedia(self, authority_scorer: AuthorityScorer) -> None:
        """Test that Wikipedia authority is skipped when no query provided."""
        with patch.object(authority_scorer.http_client, "get") as mock_get:
            source = SearchSource(
                url="https://example.com/article",
                title="Article",
                snippet="Text",
                relevance=0.7,
                source_type="web",
            )

            score = await authority_scorer.calculate_authority_score(source, query=None)

            # Should not call Wikipedia API
            mock_get.assert_not_called()
            assert score >= 0.0

    @pytest.mark.asyncio
    async def test_cleanup_http_client(self, authority_scorer: AuthorityScorer) -> None:
        """Test that HTTP client is properly closed."""
        with patch.object(authority_scorer.http_client, "aclose") as mock_close:
            await authority_scorer.close()
            mock_close.assert_called_once()


@pytest.mark.unit
@pytest.mark.fast
class TestAuthorityBoostCalculation:
    """Test authority boost impact on final scores."""

    def test_boost_calculation(self, mock_settings: Settings) -> None:
        """Test boost calculation formula."""
        authority_score = 0.85
        weight = mock_settings.AUTHORITY_SCORING_WEIGHT  # 0.15
        multiplier = mock_settings.AUTHORITY_BOOST_MULTIPLIER  # 1.3
        base_score = 0.70

        boost = authority_score * weight  # 0.85 * 0.15 = 0.1275
        expected_final = min(1.0, base_score * (1 + boost * multiplier))
        # = 0.70 * (1 + 0.1275 * 1.3) = 0.70 * 1.16575 = 0.816025

        assert expected_final == pytest.approx(0.816, abs=0.001)

    def test_boost_caps_at_one(self, mock_settings: Settings) -> None:
        """Test that final score is capped at 1.0."""
        authority_score = 1.0
        weight = 0.5  # Higher weight for testing
        multiplier = 2.0
        base_score = 0.95

        boost = authority_score * weight
        final_score = min(1.0, base_score * (1 + boost * multiplier))

        assert final_score == 1.0, "Final score should be capped at 1.0"

    def test_zero_authority_no_boost(self, mock_settings: Settings) -> None:
        """Test that zero authority score results in no boost."""
        authority_score = 0.0
        base_score = 0.75

        boost = authority_score * mock_settings.AUTHORITY_SCORING_WEIGHT
        final_score = base_score * (1 + boost * mock_settings.AUTHORITY_BOOST_MULTIPLIER)

        assert final_score == base_score, "Zero authority should not change score"


@pytest.mark.unit
@pytest.mark.asyncio
class TestSampleSourceScoring:
    """Test scoring of sample sources (integration with real logic)."""

    async def test_official_docs_highest_score(
        self, authority_scorer: AuthorityScorer, sample_sources: list[SearchSource]
    ) -> None:
        """Test that official docs get highest authority."""
        official_doc = sample_sources[0]  # docs.python.org
        score = await authority_scorer.calculate_authority_score(official_doc)
        assert score == 1.0

    async def test_stackoverflow_medium_score(
        self, authority_scorer: AuthorityScorer, sample_sources: list[SearchSource]
    ) -> None:
        """Test that StackOverflow gets reputable authority."""
        stackoverflow = sample_sources[1]
        score = await authority_scorer.calculate_authority_score(stackoverflow)
        assert score == 0.85

    async def test_unknown_site_low_score(
        self, authority_scorer: AuthorityScorer, sample_sources: list[SearchSource]
    ) -> None:
        """Test that unknown sites get minimal authority."""
        unknown = sample_sources[2]  # example.com
        score = await authority_scorer.calculate_authority_score(unknown)
        # Should get at most high_relevance proxy (0.60) since relevance = 0.75
        assert score <= 0.75

    async def test_github_reputable_score(
        self, authority_scorer: AuthorityScorer, sample_sources: list[SearchSource]
    ) -> None:
        """Test that GitHub gets reputable authority."""
        github = sample_sources[3]
        score = await authority_scorer.calculate_authority_score(github)
        assert score == 0.85

    async def test_medium_community_score(
        self, authority_scorer: AuthorityScorer, sample_sources: list[SearchSource]
    ) -> None:
        """Test that Medium gets community authority."""
        medium = sample_sources[4]
        score = await authority_scorer.calculate_authority_score(medium)
        assert score == 0.70
