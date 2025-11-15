"""LLM response quality validator.

Validates if LLM-generated responses meet quality thresholds:
- Token count (minimum length)
- Citation presence
- Content quality (not generic errors)
- Source count adequacy
"""

from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, Field


class QualityIssue(str, Enum):
    """Quality issues that can be detected in responses."""

    TOO_SHORT = "too_short"
    MISSING_CITATIONS = "missing_citations"
    GENERIC_RESPONSE = "generic_response"
    INSUFFICIENT_SOURCES = "insufficient_sources"


class ResponseQuality(BaseModel):
    """Response quality assessment result.

    Attributes:
        is_sufficient: Whether response meets quality thresholds
        token_count: Estimated token count
        has_citations: Whether response contains citations
        confidence_score: Overall quality confidence (0.0-1.0)
        issues: List of detected quality issues
        source_count: Number of sources used
    """

    is_sufficient: bool = Field(..., description="Meets quality thresholds")
    token_count: int = Field(..., ge=0, description="Estimated token count")
    has_citations: bool = Field(..., description="Contains citation markers")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Quality confidence")
    issues: list[QualityIssue] = Field(default_factory=list, description="Quality issues")
    source_count: int = Field(..., description="Number of sources used")


class ResponseValidator:
    """Validates LLM response quality.

    Example:
        >>> validator = ResponseValidator(min_tokens=160)
        >>> quality = validator.validate(answer, source_count=5)
        >>> if not quality.is_sufficient:
        ...     print(f"Quality issues: {quality.issues}")
    """

    # Generic error patterns that indicate poor responses
    GENERIC_ERROR_PATTERNS = [
        r"don't have enough information",
        r"cannot provide an answer",
        r"insufficient (information|data|sources)",
        r"unable to (answer|respond|provide)",
        r"I apologize.*(cannot|unable)",
        r"not enough (context|information|data)",
    ]

    # Citation patterns: [1], (1), Source 1, etc.
    CITATION_PATTERNS = [
        r"\[\d+\]",  # [1], [2], etc.
        r"\(\d+\)",  # (1), (2), etc.
        r"Source \d+",  # Source 1, Source 2, etc.
        r"Reference \d+",  # Reference 1, Reference 2, etc.
    ]

    def __init__(self, min_tokens: int = 160, min_sources: int = 2):
        """Initialize validator.

        Args:
            min_tokens: Minimum token count for sufficient response
            min_sources: Minimum source count required
        """
        self.min_tokens = min_tokens
        self.min_sources = min_sources

    def validate(self, answer: str, source_count: int) -> ResponseQuality:
        """Validate response quality.

        Args:
            answer: LLM-generated answer text
            source_count: Number of sources used

        Returns:
            ResponseQuality assessment with issues flagged
        """
        issues: list[QualityIssue] = []

        # Strip whitespace for analysis
        answer_stripped = answer.strip()

        # 1. Check token count
        token_count = self._estimate_tokens(answer_stripped)
        if token_count < self.min_tokens:
            issues.append(QualityIssue.TOO_SHORT)

        # 2. Check for citations
        has_citations = self._has_citations(answer_stripped)
        if not has_citations and answer_stripped:
            issues.append(QualityIssue.MISSING_CITATIONS)

        # 3. Check for generic error responses
        if self._is_generic_error(answer_stripped):
            issues.append(QualityIssue.GENERIC_RESPONSE)

        # 4. Check source count
        if source_count < self.min_sources:
            issues.append(QualityIssue.INSUFFICIENT_SOURCES)

        # Calculate confidence score
        confidence_score = self._calculate_confidence(
            token_count=token_count,
            has_citations=has_citations,
            source_count=source_count,
            issues=issues,
        )

        # Determine if response is sufficient
        is_sufficient = len(issues) == 0 and token_count >= self.min_tokens

        return ResponseQuality(
            is_sufficient=is_sufficient,
            token_count=token_count,
            has_citations=has_citations,
            confidence_score=confidence_score,
            issues=issues,
            source_count=source_count,
        )

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count from text.

        Uses rough estimation: ~4 characters per token.
        This matches OpenAI's tiktoken approximation for English text.

        Args:
            text: Input text

        Returns:
            Estimated token count
        """
        if not text:
            return 0

        # Rough estimation: 1 token ≈ 4 characters
        return len(text) // 4

    def _has_citations(self, text: str) -> bool:
        """Check if text contains citation markers.

        Args:
            text: Input text

        Returns:
            True if citations found
        """
        for pattern in self.CITATION_PATTERNS:
            if re.search(pattern, text):
                return True
        return False

    def _is_generic_error(self, text: str) -> bool:
        """Check if text is a generic error message.

        Args:
            text: Input text

        Returns:
            True if generic error detected
        """
        text_lower = text.lower()

        for pattern in self.GENERIC_ERROR_PATTERNS:
            if re.search(pattern, text_lower):
                return True

        return False

    def _calculate_confidence(
        self, token_count: int, has_citations: bool, source_count: int, issues: list[QualityIssue]
    ) -> float:
        """Calculate overall confidence score.

        Args:
            token_count: Estimated tokens
            has_citations: Whether citations present
            source_count: Number of sources
            issues: Detected quality issues

        Returns:
            Confidence score 0.0-1.0
        """
        # Start with base confidence
        confidence = 0.5

        # Token count contribution (up to +0.3)
        if token_count >= self.min_tokens * 2:
            confidence += 0.3
        elif token_count >= self.min_tokens:
            confidence += 0.15

        # Citation contribution (+0.2)
        if has_citations:
            confidence += 0.2

        # Source count contribution (up to +0.2)
        if source_count >= self.min_sources * 2:
            confidence += 0.2
        elif source_count >= self.min_sources:
            confidence += 0.1

        # Penalty for each issue (-0.2 per issue)
        confidence -= len(issues) * 0.2

        # Clamp to [0.0, 1.0]
        return max(0.0, min(1.0, confidence))
