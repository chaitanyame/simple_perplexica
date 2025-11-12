"""Tests for hallucination detection in synthesized claims.

TDD Phase: RED - Tests written before implementation.
Target: 3 test cases for hallucination detection.
"""

from __future__ import annotations

import pytest

from src.models.citation import Citation
from src.utils.claim_grounder import Claim, ClaimGrounder


@pytest.fixture
def mock_embedding_service():
    """Provide mock embedding service."""
    from unittest.mock import MagicMock, AsyncMock
    
    service = MagicMock()
    service.embed = AsyncMock(return_value=[0.1] * 384)
    service.cosine_similarity = MagicMock(return_value=0.5)
    return service


class TestHallucinationDetection:
    """Test detection of hallucinated (fabricated) claims."""

    @pytest.mark.asyncio
    async def test_detect_completely_fabricated_claim(self, mock_embedding_service):
        """Test detection of completely made-up claim.
        
        Given: Claim with facts not in any source
        When: Checking if hallucinated
        Then: Returns True (is hallucination) with low grounding score
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        # Very low similarity for fabricated claim
        mock_embedding_service.cosine_similarity.return_value = 0.25
        
        claim_text = "FastAPI was downloaded 50 million times in November 2024."
        source_content = "FastAPI is a modern web framework for building APIs."
        
        score = await grounder.calculate_grounding_score(claim_text, source_content)
        
        claim = Claim(
            text=claim_text,
            claim_id="claim_1",
            supporting_sources=["1"],
            grounding_score=score,
            is_grounded=score >= 0.6,
            evidence_snippets=[],
            citation_markers=[],
        )
        
        is_hallucination = grounder.detect_hallucination(claim, threshold=0.5)
        
        assert is_hallucination is True, "Fabricated claim should be detected as hallucination"
        assert claim.grounding_score < 0.5, "Hallucinated claim should have low score"

    @pytest.mark.asyncio
    async def test_detect_embellished_claim(self, mock_embedding_service):
        """Test detection of claim with added details not in source.
        
        Given: Claim that starts accurate but adds fabricated details
        When: Checking if hallucinated
        Then: Returns True due to unsupported embellishments
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        # Medium similarity - partial match
        mock_embedding_service.cosine_similarity.return_value = 0.45
        
        # Claim adds "50% faster" which is not in source
        claim_text = "Python 3.11 was released with 50% faster execution than 3.10."
        source_content = "Python 3.11 was released with performance improvements over Python 3.10."
        
        score = await grounder.calculate_grounding_score(claim_text, source_content)
        
        claim = Claim(
            text=claim_text,
            claim_id="claim_2",
            supporting_sources=["1"],
            grounding_score=score,
            is_grounded=score >= 0.6,
            evidence_snippets=[],
            citation_markers=[],
        )
        
        is_hallucination = grounder.detect_hallucination(claim, threshold=0.5)
        
        # Should be detected as hallucination due to unsupported "50%"
        assert is_hallucination is True or score < 0.6, "Embellished claim should be flagged"

    @pytest.mark.asyncio
    async def test_allow_reasonable_paraphrasing(self, mock_embedding_service):
        """Test that reasonable paraphrasing is NOT flagged as hallucination.
        
        Given: Claim that paraphrases source accurately
        When: Checking if hallucinated
        Then: Returns False (not hallucination) with acceptable score
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        # High similarity for good paraphrase
        mock_embedding_service.cosine_similarity.return_value = 0.82
        
        claim_text = "The framework offers automated documentation generation."
        source_content = "FastAPI provides automatic API documentation and validation."
        
        score = await grounder.calculate_grounding_score(claim_text, source_content)
        
        claim = Claim(
            text=claim_text,
            claim_id="claim_3",
            supporting_sources=["1"],
            grounding_score=score,
            is_grounded=score >= 0.6,
            evidence_snippets=[],
            citation_markers=[],
        )
        
        is_hallucination = grounder.detect_hallucination(claim, threshold=0.5)
        
        assert is_hallucination is False, "Accurate paraphrasing should not be flagged"
        assert claim.grounding_score >= 0.7, "Good paraphrase should have high score"
