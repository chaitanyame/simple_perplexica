"""Tests for claim extraction from synthesized text.

TDD Phase: RED - Tests written before implementation.
Target: 6 test cases for claim extraction functionality.
"""

from __future__ import annotations

import pytest

from src.utils.claim_grounder import Claim, ClaimExtractor


class TestSimpleClaimExtraction:
    """Test extraction of simple factual claims from text."""

    def test_extract_single_sentence_claim(self):
        """Test extracting a single factual sentence as a claim.
        
        Given: Text with one factual sentence
        When: Extracting claims
        Then: Returns one claim with the sentence text
        """
        extractor = ClaimExtractor()
        text = "Python 3.11 was released in October 2022."
        
        claims = extractor.extract_claims(text)
        
        assert len(claims) == 1
        assert "Python 3.11" in claims[0].text
        assert "October 2022" in claims[0].text
        assert claims[0].claim_id is not None

    def test_extract_multiple_sentence_claims(self):
        """Test extracting multiple sentences as separate claims.
        
        Given: Text with three factual sentences
        When: Extracting claims
        Then: Returns three separate claims
        """
        extractor = ClaimExtractor()
        text = """FastAPI is a modern web framework. It supports async operations. 
        The framework was created by Sebastián Ramírez."""
        
        claims = extractor.extract_claims(text)
        
        assert len(claims) == 3
        assert any("FastAPI" in c.text for c in claims)
        assert any("async" in c.text for c in claims)
        assert any("Sebastián Ramírez" in c.text for c in claims)
        # Each claim should have unique ID
        claim_ids = [c.claim_id for c in claims]
        assert len(claim_ids) == len(set(claim_ids))

    def test_extract_claim_with_numbers_and_dates(self):
        """Test extracting claims containing numerical data and dates.
        
        Given: Text with specific numbers, percentages, and dates
        When: Extracting claims
        Then: Preserves exact numerical values in claims
        """
        extractor = ClaimExtractor()
        text = "LangChain 0.1.0 released on January 15, 2024 with 50% faster execution."
        
        claims = extractor.extract_claims(text)
        
        assert len(claims) >= 1
        claim_text = " ".join(c.text for c in claims)
        # Verify exact numbers preserved
        assert "0.1.0" in claim_text
        assert "January 15, 2024" in claim_text or "2024" in claim_text
        assert "50%" in claim_text


class TestComplexClaimExtraction:
    """Test extraction of complex or compound claims."""

    def test_extract_claims_with_existing_citations(self):
        """Test handling text that already has citation markers [1], [2].
        
        Given: Text with inline citation markers like [1], [2]
        When: Extracting claims
        Then: Preserves or extracts citation markers with claims
        """
        extractor = ClaimExtractor()
        text = "Azure AI Search provides vector search [1]. It uses embeddings for semantic ranking [2]."
        
        claims = extractor.extract_claims(text)
        
        assert len(claims) == 2
        # Citations should be preserved or tracked
        assert any("[1]" in c.text or c.citation_markers == ["1"] for c in claims)
        assert any("[2]" in c.text or c.citation_markers == ["2"] for c in claims)

    def test_filter_non_factual_sentences(self):
        """Test filtering out meta-commentary and non-factual sentences.
        
        Given: Text with mix of factual claims and meta-commentary
        When: Extracting claims
        Then: Filters out questions, meta-statements, conversational phrases
        """
        extractor = ClaimExtractor()
        text = """Let me explain the key features. First, the system uses neural networks. 
        What does this mean? It means the model learns from data. 
        In summary, we covered the main points."""
        
        claims = extractor.extract_claims(text)
        
        # Should extract factual claims, filter meta-commentary
        claim_texts = [c.text.lower() for c in claims]
        # Factual claims should be included
        assert any("neural networks" in text for text in claim_texts)
        assert any("learns from data" in text for text in claim_texts)
        # Meta-commentary should be filtered
        assert not any("let me explain" in text for text in claim_texts)
        assert not any("in summary" in text for text in claim_texts)


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_extract_from_empty_text(self):
        """Test extracting claims from empty text.
        
        Given: Empty string
        When: Extracting claims
        Then: Returns empty list without error
        """
        extractor = ClaimExtractor()
        
        claims = extractor.extract_claims("")
        
        assert claims == []

    def test_extract_from_single_word(self):
        """Test extracting from very short text (single word).
        
        Given: Text with only one word
        When: Extracting claims
        Then: Returns empty list (too short to be a claim)
        """
        extractor = ClaimExtractor()
        
        claims = extractor.extract_claims("Python")
        
        # Single word is not a complete factual claim
        assert len(claims) == 0

    def test_extract_preserves_whitespace_and_formatting(self):
        """Test that extraction preserves important whitespace.
        
        Given: Text with specific formatting (newlines, spaces)
        When: Extracting claims
        Then: Normalizes whitespace but preserves sentence structure
        """
        extractor = ClaimExtractor()
        text = "FastAPI   supports\n\nPython 3.7+."
        
        claims = extractor.extract_claims(text)
        
        assert len(claims) >= 1
        # Whitespace normalized (no multiple spaces/newlines)
        assert "  " not in claims[0].text
        assert "\n\n" not in claims[0].text
        # Content preserved
        assert "FastAPI" in claims[0].text
        assert "Python 3.7+" in claims[0].text
