"""Tests for recency boost in semantic reranking.

Tests temporal scoring to prioritize recent content.

TDD Phase: RED - Tests should fail initially.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from src.services.embedding.semantic_reranker import (
    DocumentWithMetadata,
    RecencyConfig,
    SemanticReranker,
    RerankingConfig,
)


class TestRecencyBoost:
    """Test recency boost functionality."""

    @pytest.mark.asyncio
    async def test_boost_recent_documents(self, embedding_service):
        """Test that recent documents receive score boost.
        
        Given: Documents with different publication dates
        When: Reranking with recency boost enabled
        Then: Recent documents should score higher than older ones
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                recency_config=RecencyConfig(
                    enabled=True,
                    weight=0.2,
                    half_life_days=180,  # 6 months
                )
            ),
        )
        
        query = "latest machine learning techniques"
        
        now = datetime.utcnow()
        documents = [
            DocumentWithMetadata(
                content="Neural networks are the foundation of deep learning.",
                published_at=now - timedelta(days=365),  # 1 year old
            ),
            DocumentWithMetadata(
                content="Transformer models revolutionized NLP in recent years.",
                published_at=now - timedelta(days=30),  # 1 month old
            ),
            DocumentWithMetadata(
                content="New attention mechanisms improve model efficiency.",
                published_at=now - timedelta(days=7),  # 1 week old
            ),
        ]
        
        results = await reranker.rerank_with_recency(query, documents)
        scores = {idx: score for idx, score in results}
        
        # More recent documents should score higher
        assert scores[2] > scores[1], "1-week-old doc should score higher than 1-month-old"
        assert scores[1] > scores[0], "1-month-old doc should score higher than 1-year-old"

    @pytest.mark.asyncio
    async def test_recency_weight_controls_boost(self, embedding_service):
        """Test that recency weight controls boost strength.
        
        Given: Same documents with different weights
        When: Comparing scores with low vs high recency weight
        Then: Higher weight = stronger boost for recent content
        """
        query = "Python programming"
        now = datetime.utcnow()
        
        documents = [
            DocumentWithMetadata(
                content="Python is a versatile programming language.",
                published_at=now - timedelta(days=730),  # 2 years old
            ),
            DocumentWithMetadata(
                content="Python 3.12 introduces new performance improvements.",
                published_at=now - timedelta(days=30),  # 1 month old
            ),
        ]
        
        # Low recency weight
        reranker_low = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                recency_config=RecencyConfig(
                    enabled=True,
                    weight=0.1,
                    half_life_days=365,
                )
            ),
        )
        
        results_low = await reranker_low.rerank_with_recency(query, documents)
        scores_low = {idx: score for idx, score in results_low}
        
        # High recency weight
        reranker_high = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                recency_config=RecencyConfig(
                    enabled=True,
                    weight=0.4,
                    half_life_days=365,
                )
            ),
        )
        
        results_high = await reranker_high.rerank_with_recency(query, documents)
        scores_high = {idx: score for idx, score in results_high}
        
        # Score gap between new and old should be larger with high weight
        gap_low = scores_low[1] - scores_low[0]
        gap_high = scores_high[1] - scores_high[0]
        
        assert gap_high > gap_low, "Higher recency weight should create larger score gap"

    @pytest.mark.asyncio
    async def test_half_life_decay_function(self, embedding_service):
        """Test that half-life decay follows exponential curve.
        
        Given: Documents at half-life intervals
        When: Calculating recency scores
        Then: Each half-life should reduce score by 50%
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                recency_config=RecencyConfig(
                    enabled=True,
                    weight=1.0,  # Pure recency for testing
                    half_life_days=180,
                )
            ),
        )
        
        query = "test query"
        now = datetime.utcnow()
        
        documents = [
            DocumentWithMetadata(
                content="Content A",
                published_at=now,  # Now
            ),
            DocumentWithMetadata(
                content="Content B",
                published_at=now - timedelta(days=180),  # 1 half-life
            ),
            DocumentWithMetadata(
                content="Content C",
                published_at=now - timedelta(days=360),  # 2 half-lives
            ),
        ]
        
        recency_scores = await reranker._calculate_recency_scores(documents)
        
        # Score at 1 half-life should be ~0.5 of current
        assert 0.45 <= recency_scores[1] / recency_scores[0] <= 0.55
        
        # Score at 2 half-lives should be ~0.25 of current
        assert 0.20 <= recency_scores[2] / recency_scores[0] <= 0.30

    @pytest.mark.asyncio
    async def test_missing_date_uses_default(self, embedding_service):
        """Test that documents without dates use default handling.
        
        Given: Documents with and without publication dates
        When: Reranking with recency
        Then: Missing dates should use configured default (e.g., assume old)
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                recency_config=RecencyConfig(
                    enabled=True,
                    weight=0.3,
                    default_age_days=730,  # Assume 2 years old if missing
                )
            ),
        )
        
        query = "technology trends"
        now = datetime.utcnow()
        
        documents = [
            DocumentWithMetadata(
                content="AI is transforming industries.",
                published_at=now - timedelta(days=30),  # Has date
            ),
            DocumentWithMetadata(
                content="Cloud computing enables scalability.",
                published_at=None,  # Missing date
            ),
        ]
        
        results = await reranker.rerank_with_recency(query, documents)
        scores = {idx: score for idx, score in results}
        
        # Document with recent date should score higher than one with missing date
        assert scores[0] > scores[1], "Recent doc should outscore doc with missing date"

    @pytest.mark.asyncio
    async def test_recency_disabled_uses_pure_relevance(self, embedding_service):
        """Test that disabling recency uses only relevance scores.
        
        Given: Documents with different dates
        When: Recency boost is disabled
        Then: Scores should be based purely on relevance
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                recency_config=RecencyConfig(enabled=False)
            ),
        )
        
        query = "Python programming"
        now = datetime.utcnow()
        
        documents = [
            DocumentWithMetadata(
                content="Python is great for data science and machine learning.",
                published_at=now - timedelta(days=365),
            ),
            DocumentWithMetadata(
                content="Java is used for enterprise applications.",
                published_at=now - timedelta(days=7),
            ),
        ]
        
        results = await reranker.rerank_with_recency(query, documents)
        scores = {idx: score for idx, score in results}
        
        # Even though doc 1 is newer, doc 0 is more relevant to Python query
        # With recency disabled, relevance should dominate
        assert scores[0] > scores[1], "Relevance should dominate when recency disabled"

    @pytest.mark.asyncio
    async def test_temporal_query_increases_recency_weight(self, embedding_service):
        """Test that temporal queries automatically increase recency weight.
        
        Given: Query with temporal keywords (latest, recent, new, current)
        When: Reranking with adaptive recency
        Then: Recency weight should be automatically boosted
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                recency_config=RecencyConfig(
                    enabled=True,
                    weight=0.2,  # Base weight
                    adaptive=True,  # Enable adaptive weighting
                )
            ),
        )
        
        temporal_query = "latest developments in quantum computing"
        now = datetime.utcnow()
        
        documents = [
            DocumentWithMetadata(
                content="Quantum computing basics and theory.",
                published_at=now - timedelta(days=1095),  # 3 years old
            ),
            DocumentWithMetadata(
                content="Recent advances in quantum error correction.",
                published_at=now - timedelta(days=30),
            ),
        ]
        
        results = await reranker.rerank_with_adaptive_recency(temporal_query, documents)
        scores = {idx: score for idx, score in results}
        
        # Recent document should significantly outscore old one for temporal query
        assert scores[1] > scores[0], "Recent doc should win for temporal query"
        
        # Score gap should be larger than with non-temporal query
        assert (scores[1] - scores[0]) > 0.2, "Temporal query should create large score gap"
