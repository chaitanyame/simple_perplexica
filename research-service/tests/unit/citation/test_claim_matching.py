"""Tests for matching claims to source citations.

TDD Phase: RED - Tests written before implementation.
Target: 5 test cases for claim-to-source matching.
"""

from __future__ import annotations

import pytest

from src.models.citation import Citation
from src.utils.claim_grounder import Claim, ClaimGrounder


@pytest.fixture
def sample_citations() -> list[Citation]:
    """Provide sample citations for testing."""
    return [
        Citation(
            source_id="1",
            title="FastAPI Documentation",
            url="https://fastapi.tiangolo.com/",
            excerpt="FastAPI is a modern, fast web framework for building APIs with Python 3.7+. It provides automatic API documentation and validation.",
            relevance=0.9,
        ),
        Citation(
            source_id="2",
            title="Python 3.11 Release Notes",
            url="https://python.org/downloads/",
            excerpt="Python 3.11 was released in October 2022. Performance improvements include 10-60% faster execution compared to Python 3.10.",
            relevance=0.85,
        ),
        Citation(
            source_id="3",
            title="Machine Learning Guide",
            url="https://ml-guide.example.com/",
            excerpt="Neural networks are computational models inspired by biological neurons. They learn patterns from training data through backpropagation.",
            relevance=0.75,
        ),
    ]


@pytest.fixture
def mock_embedding_service():
    """Provide mock embedding service for testing."""
    from unittest.mock import MagicMock, AsyncMock
    
    service = MagicMock()
    # Mock embed method to return dummy vectors
    service.embed = AsyncMock(return_value=[0.1] * 384)
    # Mock similarity calculation
    service.cosine_similarity = MagicMock(return_value=0.8)
    return service


class TestClaimToSourceMatching:
    """Test matching claims to their supporting sources."""

    @pytest.mark.asyncio
    async def test_match_claim_to_exact_source(self, sample_citations, mock_embedding_service):
        """Test matching a claim to source with exact content.
        
        Given: Claim about FastAPI and sources including FastAPI docs
        When: Matching claim to sources
        Then: Returns FastAPI citation with high confidence (>0.8)
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        claim = Claim(
            text="FastAPI is a modern web framework for Python 3.7+.",
            claim_id="claim_1",
            supporting_sources=[],
            grounding_score=0.0,
            is_grounded=False,
            evidence_snippets=[],
            citation_markers=[],
        )
        
        matches = await grounder.match_claim_to_sources(claim, sample_citations)
        
        # Should match to source 1 (FastAPI docs)
        assert len(matches) > 0
        best_match, confidence = matches[0]
        assert best_match.source_id == "1"
        assert confidence > 0.7  # High confidence for exact match

    @pytest.mark.asyncio
    async def test_match_claim_to_multiple_sources(self, sample_citations, mock_embedding_service):
        """Test claim supported by multiple sources.
        
        Given: General claim about Python that multiple sources mention
        When: Matching to sources
        Then: Returns multiple matches, sorted by confidence
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        claim = Claim(
            text="Python 3.7+ introduced new features for web development.",
            claim_id="claim_2",
            supporting_sources=[],
            grounding_score=0.0,
            is_grounded=False,
            evidence_snippets=[],
            citation_markers=[],
        )
        
        matches = await grounder.match_claim_to_sources(claim, sample_citations)
        
        # Should match to both Python and FastAPI sources
        assert len(matches) >= 2
        # Results sorted by confidence (descending)
        confidences = [conf for _, conf in matches]
        assert confidences == sorted(confidences, reverse=True)

    @pytest.mark.asyncio
    async def test_match_claim_with_entities(self, sample_citations, mock_embedding_service):
        """Test matching using named entities (numbers, dates, products).
        
        Given: Claim with specific version number and date
        When: Matching to sources
        Then: Boosts confidence for source with matching entities
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        claim = Claim(
            text="Python 3.11 was released in October 2022.",
            claim_id="claim_3",
            supporting_sources=[],
            grounding_score=0.0,
            is_grounded=False,
            evidence_snippets=[],
            citation_markers=[],
        )
        
        matches = await grounder.match_claim_to_sources(claim, sample_citations)
        
        # Should strongly match source 2 (Python release notes)
        assert len(matches) > 0
        best_match, confidence = matches[0]
        assert best_match.source_id == "2"
        # High confidence due to matching entities (3.11, October 2022)
        assert confidence > 0.8

    @pytest.mark.asyncio
    async def test_no_matching_source_for_claim(self, sample_citations, mock_embedding_service):
        """Test handling claim with no supporting sources.
        
        Given: Claim about topic not in any source
        When: Matching to sources
        Then: Returns empty list or very low confidence matches
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        # Override mock to return low similarity
        mock_embedding_service.cosine_similarity.return_value = 0.3
        
        claim = Claim(
            text="Rust programming language is memory-safe by default.",
            claim_id="claim_4",
            supporting_sources=[],
            grounding_score=0.0,
            is_grounded=False,
            evidence_snippets=[],
            citation_markers=[],
        )
        
        matches = await grounder.match_claim_to_sources(claim, sample_citations)
        
        # Either empty or all matches below threshold
        if matches:
            assert all(conf < 0.5 for _, conf in matches)

    @pytest.mark.asyncio
    async def test_rank_sources_by_match_quality(self, sample_citations, mock_embedding_service):
        """Test that sources are ranked by match quality.
        
        Given: Claim that partially matches multiple sources
        When: Matching to sources
        Then: Sources ranked by descending confidence score
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        claim = Claim(
            text="Web frameworks enable building APIs efficiently.",
            claim_id="claim_5",
            supporting_sources=[],
            grounding_score=0.0,
            is_grounded=False,
            evidence_snippets=[],
            citation_markers=[],
        )
        
        matches = await grounder.match_claim_to_sources(claim, sample_citations)
        
        assert len(matches) >= 2
        # Verify descending order
        for i in range(len(matches) - 1):
            _, conf1 = matches[i]
            _, conf2 = matches[i + 1]
            assert conf1 >= conf2, "Sources should be ranked by confidence (desc)"
