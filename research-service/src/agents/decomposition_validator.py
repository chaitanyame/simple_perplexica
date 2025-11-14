"""Query decomposition quality validator.

Validates decomposition quality using:
- Coverage: Do sub-queries cover the original intent?
- Redundancy: Are there duplicate/overlapping sub-queries?
- Completeness: Are key aspects missing?

This validator enables measurement-driven improvement without LLM cost.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from ..services.embedding.embedding_service import EmbeddingService
    from .search_agent import SubQuery

logger = structlog.get_logger(__name__)


@dataclass
class DecompositionQualityScore:
    """Quality metrics for a query decomposition."""

    coverage_score: float  # 0-1: How well sub-queries cover original
    redundancy_score: float  # 0-1: Amount of duplication (lower is better)
    completeness: bool  # All key aspects covered?
    overall_score: float  # Weighted combination
    passes_threshold: bool  # Meets minimum quality?
    issues: list[str] = field(default_factory=list)  # Specific problems identified

    def to_dict(self) -> dict[str, float | bool | list[str]]:
        """Convert to dict for logging/monitoring."""
        return {
            "coverage_score": self.coverage_score,
            "redundancy_score": self.redundancy_score,
            "completeness": self.completeness,
            "overall_score": self.overall_score,
            "passes_threshold": self.passes_threshold,
            "issues": self.issues,
        }


class DecompositionValidator:
    """Validates query decomposition quality without additional LLM calls.

    Uses semantic similarity (embedding-based) to score decomposition quality.
    This provides fast, cost-free validation with retry capability.

    Args:
        coverage_threshold: Minimum coverage score (0-1)
        redundancy_threshold: Maximum acceptable redundancy (0-1)
        min_quality_score: Minimum overall quality to pass
        max_retries: Maximum retry attempts for poor decompositions
    """

    def __init__(
        self,
        coverage_threshold: float = 0.7,
        redundancy_threshold: float = 0.85,
        min_quality_score: float = 0.6,
        max_retries: int = 2,
    ) -> None:
        self.coverage_threshold = coverage_threshold
        self.redundancy_threshold = redundancy_threshold
        self.min_quality_score = min_quality_score
        self.max_retries = max_retries

        # Lazy-load embedding service to avoid circular imports
        self._embedder: EmbeddingService | None = None

    def _get_embedder(self) -> EmbeddingService:
        """Lazy-load embedding service."""
        if self._embedder is None:
            from ..services.embedding.embedding_service import EmbeddingService

            self._embedder = EmbeddingService()
        return self._embedder

    async def score_coverage(self, original_query: str, sub_queries: list[SubQuery]) -> float:
        """Score how well sub-queries cover the original query intent.

        Uses semantic similarity between:
        - Original query
        - Concatenated sub-queries

        Args:
            original_query: The original user query
            sub_queries: List of decomposed sub-queries

        Returns:
            Coverage score 0-1 (higher is better)
        """
        if not original_query.strip() or not sub_queries:
            return 0.0

        try:
            embedder = self._get_embedder()

            # Combine sub-queries into single text
            combined_subqueries = " ".join(sq.query for sq in sub_queries)

            # Compute semantic similarity
            original_embedding = await embedder.embed_text(original_query)
            combined_embedding = await embedder.embed_text(combined_subqueries)

            # Cosine similarity
            similarity = self._cosine_similarity(original_embedding, combined_embedding)

            return max(0.0, min(1.0, similarity))

        except Exception as e:
            logger.error("Coverage scoring failed", error=str(e))
            return 0.5  # Neutral score on error

    async def score_redundancy(self, sub_queries: list[SubQuery]) -> float:
        """Score redundancy/duplication in sub-queries.

        Computes pairwise similarity between all sub-queries.
        High average similarity indicates redundancy.

        Args:
            sub_queries: List of sub-queries to check

        Returns:
            Redundancy score 0-1 (lower is better, 0 = no redundancy)
        """
        if len(sub_queries) <= 1:
            return 0.0  # Can't have redundancy with 0-1 queries

        try:
            embedder = self._get_embedder()

            # Get embeddings for all sub-queries
            import asyncio

            embeddings = await asyncio.gather(
                *[embedder.embed_text(sq.query) for sq in sub_queries]
            )

            # Compute pairwise similarities
            similarities: list[float] = []
            for i in range(len(embeddings)):
                for j in range(i + 1, len(embeddings)):
                    sim = self._cosine_similarity(embeddings[i], embeddings[j])
                    similarities.append(sim)

            # Average similarity = redundancy score
            avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0

            return max(0.0, min(1.0, avg_similarity))

        except Exception as e:
            logger.error("Redundancy scoring failed", error=str(e))
            return 0.3  # Conservative estimate

    async def is_complete(self, original_query: str, sub_queries: list[SubQuery]) -> bool:
        """Check if decomposition covers all key aspects.

        Uses heuristics:
        - Multi-part queries (and/or) should have 2+ sub-queries
        - Coverage score should meet threshold
        - At least one sub-query per identified aspect

        Args:
            original_query: Original query
            sub_queries: Decomposed sub-queries

        Returns:
            True if decomposition appears complete
        """
        if not sub_queries:
            return False

        # Check multi-part query coverage
        query_lower = original_query.lower()
        has_and = " and " in query_lower
        has_or = " or " in query_lower
        has_comma = "," in query_lower

        if (has_and or has_or or has_comma) and len(sub_queries) < 2:
            return False

        # Check coverage threshold
        coverage = await self.score_coverage(original_query, sub_queries)
        return coverage >= self.coverage_threshold

    async def evaluate_quality(
        self, original_query: str, sub_queries: list[SubQuery]
    ) -> DecompositionQualityScore:
        """Evaluate overall decomposition quality.

        Combines coverage, redundancy, and completeness into overall score.

        Args:
            original_query: Original query
            sub_queries: Decomposed sub-queries

        Returns:
            DecompositionQualityScore with all metrics
        """
        issues: list[str] = []

        # Score individual metrics
        coverage = await self.score_coverage(original_query, sub_queries)
        redundancy = await self.score_redundancy(sub_queries)
        completeness = await self.is_complete(original_query, sub_queries)

        # Identify issues
        if coverage < self.coverage_threshold:
            issues.append(f"Low coverage: {coverage:.2f} < {self.coverage_threshold}")

        if redundancy > self.redundancy_threshold:
            issues.append(f"High redundancy: {redundancy:.2f} > {self.redundancy_threshold}")

        if not completeness:
            issues.append("Incomplete decomposition: missing key aspects")

        # Compute overall score
        # Weight: coverage 50%, (1-redundancy) 30%, completeness 20%
        overall = coverage * 0.5 + (1.0 - redundancy) * 0.3 + (1.0 if completeness else 0.0) * 0.2

        passes = overall >= self.min_quality_score

        return DecompositionQualityScore(
            coverage_score=coverage,
            redundancy_score=redundancy,
            completeness=completeness,
            overall_score=overall,
            passes_threshold=passes,
            issues=issues,
        )

    @staticmethod
    def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        import math

        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have same dimension")

        dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)


__all__ = ["DecompositionQualityScore", "DecompositionValidator"]
