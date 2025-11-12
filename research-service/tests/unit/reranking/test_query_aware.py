"""Tests for query-aware reranking adaptations.

Tests that reranker adapts scoring based on query characteristics.

TDD Phase: RED - Tests should fail initially.
"""

from __future__ import annotations

import pytest

from src.services.embedding.semantic_reranker import (
    QueryType,
    RecencyConfig,
    SemanticReranker,
    RerankingConfig,
)


class TestQueryAwareReranking:
    """Test query-aware reranking functionality."""

    @pytest.mark.asyncio
    async def test_detect_factual_query(self, embedding_service):
        """Test detection of factual queries (what, who, when, where).
        
        Given: Factual query
        When: Analyzing query type
        Then: Should be classified as QueryType.FACTUAL
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(),
        )
        
        factual_queries = [
            "What is machine learning?",
            "Who invented Python?",
            "When was React released?",
            "Where is TensorFlow developed?",
        ]
        
        for query in factual_queries:
            query_type = await reranker.detect_query_type(query)
            assert query_type == QueryType.FACTUAL, f"'{query}' should be factual"

    @pytest.mark.asyncio
    async def test_detect_comparative_query(self, embedding_service):
        """Test detection of comparative queries (vs, compare, difference).
        
        Given: Comparative query
        When: Analyzing query type
        Then: Should be classified as QueryType.COMPARATIVE
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(),
        )
        
        comparative_queries = [
            "React vs Vue performance comparison",
            "Difference between Python and JavaScript",
            "Compare TensorFlow and PyTorch",
            "SQL vs NoSQL databases",
        ]
        
        for query in comparative_queries:
            query_type = await reranker.detect_query_type(query)
            assert query_type == QueryType.COMPARATIVE, f"'{query}' should be comparative"

    @pytest.mark.asyncio
    async def test_detect_temporal_query(self, embedding_service):
        """Test detection of temporal queries (latest, recent, current, trend).
        
        Given: Temporal query
        When: Analyzing query type
        Then: Should be classified as QueryType.TEMPORAL
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(),
        )
        
        temporal_queries = [
            "Latest machine learning trends",
            "Recent developments in AI",
            "Current state of quantum computing",
            "New features in Python 3.12",
        ]
        
        for query in temporal_queries:
            query_type = await reranker.detect_query_type(query)
            assert query_type == QueryType.TEMPORAL, f"'{query}' should be temporal"

    @pytest.mark.asyncio
    async def test_detect_analytical_query(self, embedding_service):
        """Test detection of analytical queries (how, why, explain).
        
        Given: Analytical query
        When: Analyzing query type
        Then: Should be classified as QueryType.ANALYTICAL
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(),
        )
        
        analytical_queries = [
            "How does gradient descent work?",
            "Why is Python popular for ML?",
            "Explain neural network backpropagation",
            "How to optimize database queries?",
        ]
        
        for query in analytical_queries:
            query_type = await reranker.detect_query_type(query)
            assert query_type == QueryType.ANALYTICAL, f"'{query}' should be analytical"

    @pytest.mark.asyncio
    async def test_factual_queries_prefer_concise_answers(self, embedding_service):
        """Test that factual queries favor concise, direct answers.
        
        Given: Factual query with concise and verbose answers
        When: Reranking with query-aware adaptation
        Then: Concise answers should score higher
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(query_aware=True),
        )
        
        query = "What is FastAPI?"
        documents = [
            "FastAPI is a modern web framework for Python.",  # Concise
            "FastAPI is a modern, fast (high-performance), web framework for building APIs with Python 3.7+ based on standard Python type hints. It provides automatic interactive API documentation, validation, and serialization. The framework was created by Sebastián Ramírez and first released in December 2018...",  # Verbose
            "Python web frameworks include Django, Flask, and FastAPI.",  # Related but less direct
        ]
        
        results = await reranker.rerank_with_query_awareness(query, documents)
        scores = {idx: score for idx, score in results}
        
        # Concise, direct answer should rank first
        assert results[0][0] == 0, "Concise answer should rank first for factual query"

    @pytest.mark.asyncio
    async def test_comparative_queries_prefer_side_by_side(self, embedding_service):
        """Test that comparative queries favor documents comparing both subjects.
        
        Given: Comparative query
        When: Reranking documents
        Then: Documents discussing both subjects should score higher
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(query_aware=True),
        )
        
        query = "React vs Vue performance"
        documents = [
            "React uses virtual DOM for efficient updates.",  # Only React
            "Vue is known for its simplicity and reactivity system.",  # Only Vue
            "React and Vue both use virtual DOM, but React has larger ecosystem while Vue has simpler learning curve.",  # Compares both
            "Angular is another popular frontend framework.",  # Different subject
        ]
        
        results = await reranker.rerank_with_query_awareness(query, documents)
        
        # Document comparing both should rank first
        assert results[0][0] == 2, "Comparative doc should rank first for comparative query"

    @pytest.mark.asyncio
    async def test_temporal_queries_boost_recency_automatically(self, embedding_service):
        """Test that temporal queries automatically boost recency weight.
        
        Given: Temporal query
        When: Reranking with query awareness
        Then: Recency weight should be increased automatically
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                query_aware=True,
                recency_config=RecencyConfig(
                    enabled=True,
                    weight=0.2,  # Base weight
                    adaptive=True,
                ),
            ),
        )
        
        temporal_query = "latest AI breakthroughs"
        
        # Check that query is detected as temporal
        query_type = await reranker.detect_query_type(temporal_query)
        assert query_type == QueryType.TEMPORAL
        
        # Check that effective recency weight is boosted
        effective_weight = await reranker.get_effective_recency_weight(temporal_query)
        assert effective_weight > 0.2, "Recency weight should be boosted for temporal query"

    @pytest.mark.asyncio
    async def test_analytical_queries_prefer_depth(self, embedding_service):
        """Test that analytical queries prefer comprehensive explanations.
        
        Given: Analytical query (how, why)
        When: Reranking documents
        Then: Detailed explanations should score higher than brief mentions
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(query_aware=True),
        )
        
        query = "How does neural network backpropagation work?"
        documents = [
            "Backpropagation is a key algorithm in neural networks.",  # Brief mention
            "Backpropagation calculates gradients by applying chain rule. First, compute forward pass to get predictions. Then, compute loss and gradients backward through each layer, updating weights using gradient descent. This iterative process minimizes the loss function.",  # Detailed explanation
            "Neural networks use various training algorithms.",  # Generic
        ]
        
        results = await reranker.rerank_with_query_awareness(query, documents)
        
        # Detailed explanation should rank first
        assert results[0][0] == 1, "Detailed explanation should rank first for analytical query"

    @pytest.mark.asyncio
    async def test_query_type_affects_diversity_weight(self, embedding_service):
        """Test that query type influences diversity preferences.
        
        Given: Different query types
        When: Applying diversity scoring
        Then: Comparative/exploratory queries should have higher diversity weight
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                query_aware=True,
                diversity_penalty=0.2,  # Base diversity
            ),
        )
        
        # Factual query - should prefer focused results (lower diversity)
        factual_query = "What is Python?"
        diversity_factual = await reranker.get_effective_diversity_penalty(factual_query)
        
        # Comparative query - should prefer diverse perspectives (higher diversity)
        comparative_query = "Compare Python vs JavaScript"
        diversity_comparative = await reranker.get_effective_diversity_penalty(comparative_query)
        
        assert diversity_comparative > diversity_factual, (
            "Comparative queries should have higher diversity penalty"
        )

    @pytest.mark.asyncio
    async def test_disable_query_awareness(self, embedding_service):
        """Test that query awareness can be disabled.
        
        Given: Query-aware reranker with awareness disabled
        When: Reranking
        Then: Should produce same scores as base reranker (no adaptations)
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(query_aware=False),
        )
        
        query = "What is Python?"
        documents = ["Python is a programming language.", "JavaScript is a programming language.", "HTML is a markup language."]
        
        # Get base reranker scores
        base_results = await embedding_service.rerank(query, documents)
        base_scores = {idx: score for idx, score in base_results}
        
        # Get query-aware reranker scores (should be identical when disabled)
        aware_results = await reranker.rerank_with_query_awareness(query, documents)
        aware_scores = {idx: score for idx, score in aware_results}
        
        # Scores should be identical to base reranker (no adaptations applied)
        for idx in base_scores.keys():
            assert abs(base_scores[idx] - aware_scores[idx]) < 1e-6, f"Score for doc {idx} should match base reranker when awareness disabled"
