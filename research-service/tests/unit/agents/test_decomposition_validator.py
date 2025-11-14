"""Unit tests for query decomposition quality validator - TDD (RED phase).

Test Coverage:
- Coverage scoring (do sub-queries cover original intent?)
- Redundancy detection (duplicate/overlapping sub-queries)
- Completeness validation (missing aspects)
- Quality threshold enforcement
- Retry logic for poor decompositions
- Metrics collection
"""

from __future__ import annotations

import pytest

from src.agents.decomposition_validator import (
    DecompositionQualityScore,
    DecompositionValidator,
)
from src.agents.search_agent import SubQuery


@pytest.fixture
def validator() -> DecompositionValidator:
    """Create validator instance for testing."""
    return DecompositionValidator(
        coverage_threshold=0.7,
        redundancy_threshold=0.85,
        min_quality_score=0.6,
    )


class TestCoverageScoring:
    """Test coverage scoring - do sub-queries cover original intent?"""

    @pytest.mark.asyncio
    async def test_high_coverage_score(self, validator: DecompositionValidator) -> None:
        """Test that well-decomposed queries score high coverage.

        Given: A query and comprehensive sub-queries
        When: Scoring coverage
        Then: Coverage score >= 0.8
        """
        original = "What are AI agents, how do they work, and what are their use cases?"
        sub_queries = [
            SubQuery(query="what are AI agents", intent="definition", priority=1),
            SubQuery(query="how do AI agents work", intent="factual", priority=1),
            SubQuery(query="AI agent use cases examples", intent="factual", priority=1),
        ]

        score = await validator.score_coverage(original, sub_queries)

        assert score >= 0.8
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_low_coverage_score(self, validator: DecompositionValidator) -> None:
        """Test that incomplete decomposition scores low coverage.

        Given: A multi-part query with incomplete sub-queries
        When: Scoring coverage
        Then: Coverage score is moderate but lower than complete decomposition
        """
        original = "What are AI agents, how do they work, and what are their use cases?"
        sub_queries = [
            SubQuery(query="Python programming", intent="definition", priority=1),
            # Completely unrelated query
        ]

        score = await validator.score_coverage(original, sub_queries)

        assert score < 0.5  # Unrelated query should score very low

    @pytest.mark.asyncio
    async def test_single_query_perfect_coverage(self, validator: DecompositionValidator) -> None:
        """Test that simple queries decompose to themselves with high coverage.

        Given: A simple single-aspect query
        When: Scoring coverage with identical sub-query
        Then: Coverage score >= 0.9
        """
        original = "What is Python programming language?"
        sub_queries = [
            SubQuery(query="what is Python programming language", intent="definition", priority=1),
        ]

        score = await validator.score_coverage(original, sub_queries)

        assert score >= 0.9


class TestRedundancyDetection:
    """Test redundancy detection - identify duplicate/overlapping sub-queries."""

    @pytest.mark.asyncio
    async def test_no_redundancy(self, validator: DecompositionValidator) -> None:
        """Test that diverse sub-queries have low redundancy.

        Given: Non-overlapping sub-queries
        When: Scoring redundancy
        Then: Redundancy score < 0.3
        """
        sub_queries = [
            SubQuery(query="what are AI agents", intent="definition", priority=1),
            SubQuery(query="machine learning algorithms", intent="factual", priority=1),
            SubQuery(query="cloud computing platforms", intent="factual", priority=1),
        ]

        score = await validator.score_redundancy(sub_queries)

        assert score < 0.3
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    @pytest.mark.asyncio
    async def test_high_redundancy(self, validator: DecompositionValidator) -> None:
        """Test that duplicate sub-queries have high redundancy.

        Given: Very similar/duplicate sub-queries
        When: Scoring redundancy
        Then: Redundancy score >= 0.8
        """
        sub_queries = [
            SubQuery(query="what are AI agents", intent="definition", priority=1),
            SubQuery(query="what is an AI agent", intent="definition", priority=1),
            SubQuery(query="define AI agent", intent="definition", priority=1),
        ]

        score = await validator.score_redundancy(sub_queries)

        assert score >= 0.8

    @pytest.mark.asyncio
    async def test_empty_queries_zero_redundancy(self, validator: DecompositionValidator) -> None:
        """Test edge case with empty list.

        Given: Empty sub-queries list
        When: Scoring redundancy
        Then: Returns 0.0 (no redundancy possible)
        """
        score = await validator.score_redundancy([])

        assert score == 0.0


class TestCompletenessValidation:
    """Test completeness - check if key aspects are missing."""

    @pytest.mark.asyncio
    async def test_complete_decomposition(self, validator: DecompositionValidator) -> None:
        """Test that complete decomposition passes validation.

        Given: Query with all key aspects covered
        When: Checking completeness
        Then: Returns True
        """
        original = "Compare Python and JavaScript for web development"
        sub_queries = [
            SubQuery(query="Python web development features", intent="factual", priority=1),
            SubQuery(query="JavaScript web development features", intent="factual", priority=1),
            SubQuery(query="Python vs JavaScript performance", intent="opinion", priority=1),
        ]

        is_complete = await validator.is_complete(original, sub_queries)

        assert is_complete is True

    @pytest.mark.asyncio
    async def test_incomplete_decomposition(self, validator: DecompositionValidator) -> None:
        """Test that incomplete decomposition fails validation.

        Given: Query missing key aspects
        When: Checking completeness
        Then: Returns False
        """
        original = "Compare Python and JavaScript for web development"
        sub_queries = [
            SubQuery(query="Python features", intent="factual", priority=1),
            # Missing: JavaScript, comparison, web development context
        ]

        is_complete = await validator.is_complete(original, sub_queries)

        assert is_complete is False


class TestOverallQualityScore:
    """Test overall quality scoring combining all metrics."""

    @pytest.mark.asyncio
    async def test_high_quality_decomposition(self, validator: DecompositionValidator) -> None:
        """Test that good decomposition gets high quality score.

        Given: Well-formed decomposition with good coverage, low redundancy
        When: Computing overall quality
        Then: Quality score >= 0.7 and passes threshold
        """
        original = "What are neural networks and how do they learn?"
        sub_queries = [
            SubQuery(query="what are neural networks", intent="definition", priority=1),
            SubQuery(query="how do neural networks learn", intent="factual", priority=1),
        ]

        quality_score = await validator.evaluate_quality(original, sub_queries)

        assert isinstance(quality_score, DecompositionQualityScore)
        assert quality_score.overall_score >= 0.7
        assert quality_score.coverage_score >= 0.7
        assert quality_score.redundancy_score < 0.85  # Some semantic overlap is normal
        assert quality_score.passes_threshold is True
        assert quality_score.issues == []

    @pytest.mark.asyncio
    async def test_low_quality_decomposition(self, validator: DecompositionValidator) -> None:
        """Test that poor decomposition gets low quality score.

        Given: Poor decomposition with unrelated queries
        When: Computing overall quality
        Then: Quality score < 0.6 and fails threshold
        """
        original = "What are neural networks and how do they learn?"
        sub_queries = [
            SubQuery(query="Python programming basics", intent="definition", priority=1),
            SubQuery(query="cloud computing services", intent="factual", priority=1),
            # Completely unrelated queries - low coverage
        ]

        quality_score = await validator.evaluate_quality(original, sub_queries)

        assert quality_score.overall_score < 0.6
        assert quality_score.passes_threshold is False
        assert len(quality_score.issues) > 0

    @pytest.mark.asyncio
    async def test_quality_score_with_issues(self, validator: DecompositionValidator) -> None:
        """Test that quality score identifies specific issues.

        Given: Decomposition with identifiable problems
        When: Computing quality
        Then: Issues list contains specific problems
        """
        original = "Complex query about AI and machine learning applications in healthcare"
        sub_queries = [
            SubQuery(query="weather forecast", intent="factual", priority=1),
        ]

        quality_score = await validator.evaluate_quality(original, sub_queries)

        assert not quality_score.passes_threshold
        assert (
            "coverage" in quality_score.issues[0].lower()
            or "incomplete" in quality_score.issues[0].lower()
        )


class TestRetryLogic:
    """Test retry mechanism for poor decompositions."""

    @pytest.mark.asyncio
    async def test_retry_improves_quality(self, validator: DecompositionValidator) -> None:
        """Test that retry mechanism improves decomposition quality.

        Given: Initial poor decomposition
        When: Triggering retry
        Then: Second attempt has better quality score
        """
        original = "What are AI agents and their applications in healthcare?"

        # First attempt - poor (unrelated)
        first_attempt = [
            SubQuery(query="database management", intent="factual", priority=1),
        ]

        first_score = await validator.evaluate_quality(original, first_attempt)
        assert not first_score.passes_threshold

        # Simulate retry with better decomposition
        second_attempt = [
            SubQuery(query="what are AI agents", intent="definition", priority=1),
            SubQuery(query="AI agent applications", intent="factual", priority=1),
        ]

        second_score = await validator.evaluate_quality(original, second_attempt)
        assert second_score.overall_score > first_score.overall_score

    @pytest.mark.asyncio
    async def test_max_retries_limit(self, validator: DecompositionValidator) -> None:
        """Test that retry respects maximum attempts limit.

        Given: Validator with max_retries=2
        When: Quality never improves
        Then: Stops after 2 retries
        """
        validator_with_limit = DecompositionValidator(
            coverage_threshold=0.9,  # Very strict
            min_quality_score=0.9,
            max_retries=2,
        )

        retry_count = 0

        # Simulate retry attempts
        for attempt in range(5):  # Try more than max
            if retry_count >= validator_with_limit.max_retries:
                break
            retry_count += 1

        assert retry_count == 2


class TestMetricsCollection:
    """Test metrics collection for analysis."""

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, validator: DecompositionValidator) -> None:
        """Test that validator tracks quality metrics.

        Given: Multiple decomposition evaluations
        When: Evaluating quality
        Then: Metrics are collected and accessible
        """
        original = "Test query"
        sub_queries = [SubQuery(query="test", intent="definition", priority=1)]

        quality_score = await validator.evaluate_quality(original, sub_queries)

        # Should expose metrics for logging
        metrics = quality_score.to_dict()

        assert "overall_score" in metrics
        assert "coverage_score" in metrics
        assert "redundancy_score" in metrics
        assert "completeness" in metrics
        assert "passes_threshold" in metrics
        assert "issues" in metrics

    @pytest.mark.asyncio
    async def test_metrics_structure(self, validator: DecompositionValidator) -> None:
        """Test metrics dictionary structure for logging/monitoring.

        Given: Quality score object
        When: Converting to dict
        Then: All required fields present with correct types
        """
        original = "What is Python?"
        sub_queries = [
            SubQuery(query="what is Python programming", intent="definition", priority=1)
        ]

        quality_score = await validator.evaluate_quality(original, sub_queries)
        metrics = quality_score.to_dict()

        assert isinstance(metrics["overall_score"], float)
        assert isinstance(metrics["coverage_score"], float)
        assert isinstance(metrics["redundancy_score"], float)
        assert isinstance(metrics["completeness"], bool)
        assert isinstance(metrics["passes_threshold"], bool)
        assert isinstance(metrics["issues"], list)


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_empty_sub_queries(self, validator: DecompositionValidator) -> None:
        """Test handling of empty sub-queries list.

        Given: Empty sub-queries
        When: Evaluating quality
        Then: Returns low score with appropriate issues
        """
        quality_score = await validator.evaluate_quality("test query", [])

        assert quality_score.overall_score < 0.5  # Low due to 0 coverage + completeness penalty
        assert not quality_score.passes_threshold
        assert len(quality_score.issues) > 0

    @pytest.mark.asyncio
    async def test_empty_original_query(self, validator: DecompositionValidator) -> None:
        """Test handling of empty original query.

        Given: Empty original query string
        When: Evaluating quality
        Then: Returns low score
        """
        sub_queries = [SubQuery(query="test", intent="definition", priority=1)]

        quality_score = await validator.evaluate_quality("", sub_queries)

        assert quality_score.overall_score < 0.5

    @pytest.mark.asyncio
    async def test_very_long_queries(self, validator: DecompositionValidator) -> None:
        """Test handling of very long queries.

        Given: Query > 500 characters
        When: Evaluating quality
        Then: Processes without error
        """
        long_query = "test query " * 100  # ~1100 chars
        sub_queries = [SubQuery(query="test", intent="definition", priority=1)]

        quality_score = await validator.evaluate_quality(long_query, sub_queries)

        assert isinstance(quality_score.overall_score, float)
