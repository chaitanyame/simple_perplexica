"""Tests for grounding verification - checking if sources support claims.

TDD Phase: RED - Tests written before implementation.
Target: 6 test cases for grounding verification.
"""

from __future__ import annotations

import pytest

from src.models.citation import Citation
from src.utils.claim_grounder import Claim, ClaimGrounder, GroundingResult


@pytest.fixture
def mock_embedding_service():
    """Provide mock embedding service with controllable similarity scores."""
    from unittest.mock import MagicMock, AsyncMock
    
    service = MagicMock()
    service.embed = AsyncMock(return_value=[0.1] * 384)
    
    # Default to high similarity (grounded)
    service.cosine_similarity = MagicMock(return_value=0.85)
    
    return service


class TestGroundingVerification:
    """Test verification that claims are grounded in sources."""

    @pytest.mark.asyncio
    async def test_verify_fully_grounded_claim(self, mock_embedding_service):
        """Test claim that is fully supported by source.
        
        Given: Claim text that exactly matches source content
        When: Calculating grounding score
        Then: Returns high score (>0.8) and is_grounded=True
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        claim_text = "FastAPI is a modern web framework for Python 3.7+."
        source_content = "FastAPI is a modern, fast web framework for building APIs with Python 3.7+. It provides automatic validation."
        
        score = await grounder.calculate_grounding_score(claim_text, source_content)
        
        assert score >= 0.8, "Exact content match should have high grounding score"
        assert score <= 1.0, "Score should not exceed 1.0"

    @pytest.mark.asyncio
    async def test_verify_partially_grounded_claim(self, mock_embedding_service):
        """Test claim with some facts from source, some missing.
        
        Given: Claim with multiple facts, only some in source
        When: Calculating grounding score
        Then: Returns medium score (0.4-0.7)
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        # Override to medium similarity
        mock_embedding_service.cosine_similarity.return_value = 0.55
        
        claim_text = "Python 3.11 was released in October 2022 with 50% faster execution."
        source_content = "Python 3.11 was released in October 2022. It includes many improvements."
        # Note: source doesn't mention "50% faster"
        
        score = await grounder.calculate_grounding_score(claim_text, source_content)
        
        assert 0.4 <= score <= 0.7, "Partial match should have medium score"

    @pytest.mark.asyncio
    async def test_verify_ungrounded_claim(self, mock_embedding_service):
        """Test claim not supported by source.
        
        Given: Claim about different topic than source
        When: Calculating grounding score
        Then: Returns low score (<0.4) and is_grounded=False
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        # Override to low similarity
        mock_embedding_service.cosine_similarity.return_value = 0.25
        
        claim_text = "Rust is a memory-safe systems programming language."
        source_content = "FastAPI is a modern web framework for Python 3.7+."
        
        score = await grounder.calculate_grounding_score(claim_text, source_content)
        
        assert score < 0.4, "Unrelated content should have low grounding score"

    @pytest.mark.asyncio
    async def test_verify_paraphrased_claim(self, mock_embedding_service):
        """Test claim that paraphrases source (semantic match).
        
        Given: Claim that says same thing as source with different wording
        When: Calculating grounding score
        Then: Returns high score (semantic similarity catches paraphrase)
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        # High semantic similarity despite different wording
        mock_embedding_service.cosine_similarity.return_value = 0.78
        
        claim_text = "The framework offers automatic API documentation and validation."
        source_content = "FastAPI provides automatic API documentation and validation features."
        
        score = await grounder.calculate_grounding_score(claim_text, source_content)
        
        # Hybrid score: 0.7 * 0.78 (semantic) + 0.3 * keyword_overlap ≈ 0.65-0.75
        assert score >= 0.65, "Paraphrased content should still score reasonably high"
        assert score <= 0.85, "Score should reflect some differences in wording"

    @pytest.mark.asyncio
    async def test_verify_numerical_claim_exact_match(self, mock_embedding_service):
        """Test claim with specific numbers requires exact match.
        
        Given: Claim with exact percentage/number
        When: Source has same number
        Then: High score with entity matching boost
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        claim_text = "Performance improved by 50% compared to version 3.10."
        source_content = "Python 3.11 shows 10-60% faster execution compared to Python 3.10, with typical improvements around 50%."
        
        score = await grounder.calculate_grounding_score(claim_text, source_content)
        
        # Should get boost for matching "50%" and "3.10"
        assert score >= 0.75, "Exact number match should boost grounding score"

    @pytest.mark.asyncio
    async def test_confidence_scoring_scale(self, mock_embedding_service):
        """Test that grounding scores are properly scaled 0.0-1.0.
        
        Given: Various claim-source pairs
        When: Calculating grounding scores
        Then: All scores in valid range [0.0, 1.0]
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        test_cases = [
            ("Exact match text", "Exact match text", 0.95),  # Expected high
            ("Similar topic", "Related topic", 0.60),  # Expected medium
            ("Completely different", "Unrelated content", 0.20),  # Expected low
        ]
        
        for claim_text, source_text, expected_similarity in test_cases:
            mock_embedding_service.cosine_similarity.return_value = expected_similarity
            
            score = await grounder.calculate_grounding_score(claim_text, source_text)
            
            assert 0.0 <= score <= 1.0, f"Score {score} out of valid range for: {claim_text}"


class TestGroundingSynthesis:
    """Test complete grounding of synthesized text with multiple claims."""

    @pytest.mark.asyncio
    async def test_ground_synthesis_with_multiple_claims(self, mock_embedding_service):
        """Test grounding full synthesis with multiple claims.
        
        Given: Synthesis with 3 claims and supporting citations
        When: Grounding the synthesis
        Then: Returns GroundingResult with all claims analyzed
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        synthesis = """FastAPI is a modern web framework for Python 3.7+. 
        It provides automatic API documentation. 
        The framework supports async operations."""
        
        citations = [
            Citation(
                source_id="1",
                title="FastAPI Docs",
                url="https://fastapi.tiangolo.com/",
                excerpt="FastAPI is a modern, fast web framework for building APIs with Python 3.7+. It provides automatic API documentation and supports async operations.",
                relevance=0.9,
            ),
        ]
        
        result = await grounder.ground_synthesis(synthesis, citations)
        
        assert isinstance(result, GroundingResult)
        assert len(result.claims) >= 2, "Should extract multiple claims"
        assert 0.0 <= result.overall_grounding <= 1.0, "Overall score in valid range"
        assert result.hallucination_count >= 0, "Hallucination count should be non-negative"

    @pytest.mark.asyncio
    async def test_identify_unsupported_claims(self, mock_embedding_service):
        """Test identifying claims below grounding threshold.
        
        Given: Synthesis with mix of grounded and unsupported claims
        When: Grounding with threshold=0.6
        Then: Identifies claims with score < 0.6 as unsupported
        """
        grounder = ClaimGrounder(
            embedding_service=mock_embedding_service,
            grounding_threshold=0.6,
        )
        
        synthesis = """FastAPI is a modern web framework. 
        It was downloaded 10 million times last month."""
        # Second claim (10 million downloads) is fabricated
        
        citations = [
            Citation(
                source_id="1",
                title="FastAPI Docs",
                url="https://fastapi.tiangolo.com/",
                excerpt="FastAPI is a modern web framework for building APIs with Python.",
                relevance=0.9,
            ),
        ]
        
        # First claim should match well, second should not
        call_count = [0]
        def varying_similarity(*args, **kwargs):
            call_count[0] += 1
            # First claim: high similarity, second: low
            return 0.85 if call_count[0] <= 2 else 0.35
        
        mock_embedding_service.cosine_similarity.side_effect = varying_similarity
        
        result = await grounder.ground_synthesis(synthesis, citations)
        
        # Should have at least one unsupported claim
        assert len(result.unsupported_claims) >= 1
        assert result.hallucination_count >= 1
        # Unsupported claims should have low scores
        for claim in result.unsupported_claims:
            assert claim.grounding_score < 0.6
