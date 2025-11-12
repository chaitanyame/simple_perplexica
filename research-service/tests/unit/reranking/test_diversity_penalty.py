"""Tests for diversity penalty in semantic reranking.

Tests that reranker promotes diversity to avoid redundant results.

TDD Phase: RED - Tests should fail initially.
"""

from __future__ import annotations

import pytest

from src.services.embedding.semantic_reranker import SemanticReranker, RerankingConfig


class TestDiversityPenalty:
    """Test diversity penalty functionality."""

    @pytest.mark.asyncio
    async def test_penalize_duplicate_content(self, embedding_service):
        """Test that duplicate content receives diversity penalty.
        
        Given: Multiple documents with similar content
        When: Reranking with diversity enabled
        Then: Similar documents should score lower than diverse ones
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(diversity_penalty=0.3),
        )
        
        query = "What is machine learning?"
        
        # First 2 docs are nearly identical
        documents = [
            "Machine learning is a subset of AI that trains models on data.",
            "Machine learning is a branch of AI that trains models using data.",  # Near duplicate
            "Python is a popular programming language for web development.",  # Different topic
            "Machine learning enables computers to learn from experience.",  # Related but different
        ]
        
        results = await reranker.rerank_with_diversity(
            query=query,
            documents=documents,
        )
        
        # Extract scores
        scores = {idx: score for idx, score in results}
        
        # Document 1 (near-duplicate of 0) should be penalized
        assert scores[1] < scores[0], "Near-duplicate should score lower"
        
        # Diverse document (2) might score lower in relevance but should be preserved
        # Document 3 (related but different) should maintain good score
        assert scores[3] > scores[1], "Diverse related content should score higher than duplicate"

    @pytest.mark.asyncio
    async def test_diversity_threshold_control(self, embedding_service):
        """Test that diversity threshold controls penalty strength.
        
        Given: Similar documents
        When: Reranking with different diversity thresholds
        Then: Higher threshold = more aggressive deduplication
        """
        query = "Python programming"
        documents = [
            "Python is a high-level programming language.",
            "Python is a popular high-level language.",  # Similar
            "Java is an object-oriented language.",  # Different
        ]
        
        # Low penalty
        reranker_low = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                diversity_penalty=0.1,
                diversity_threshold=0.85,
            ),
        )
        
        results_low = await reranker_low.rerank_with_diversity(query, documents)
        scores_low = {idx: score for idx, score in results_low}
        
        # High penalty
        reranker_high = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                diversity_penalty=0.5,
                diversity_threshold=0.85,
            ),
        )
        
        results_high = await reranker_high.rerank_with_diversity(query, documents)
        scores_high = {idx: score for idx, score in results_high}
        
        # With high penalty, duplicate should be more heavily penalized
        penalty_low = scores_low[0] - scores_low[1]
        penalty_high = scores_high[0] - scores_high[1]
        
        assert penalty_high > penalty_low, "Higher diversity penalty should create larger score gap"

    @pytest.mark.asyncio
    async def test_no_penalty_for_diverse_content(self, embedding_service):
        """Test that truly diverse content is not penalized.
        
        Given: Documents covering different aspects of a topic
        When: Reranking with diversity enabled
        Then: All documents should maintain their base relevance scores
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(diversity_penalty=0.3),
        )
        
        query = "web development"
        documents = [
            "HTML is the markup language for web pages.",
            "CSS provides styling for web applications.",
            "JavaScript adds interactivity to websites.",
            "React is a frontend framework for building UIs.",
        ]
        
        # Get base scores without diversity penalty
        base_results = await embedding_service.rerank(query, documents)
        base_scores = {idx: score for idx, score in base_results}
        
        # Get scores with diversity penalty
        results = await reranker.rerank_with_diversity(query, documents)
        div_scores = {idx: score for idx, score in results}
        
        # All documents are diverse (similarity < threshold), so scores should be unchanged
        # Check that each document's score is within 1% of its base score
        for idx in base_scores.keys():
            score_ratio = div_scores[idx] / base_scores[idx] if base_scores[idx] > 0 else 1.0
            assert score_ratio > 0.99, f"Document {idx} was penalized despite being diverse (ratio: {score_ratio:.4f})"

    @pytest.mark.asyncio
    async def test_mmr_algorithm_implementation(self, embedding_service):
        """Test Maximal Marginal Relevance (MMR) algorithm.
        
        Given: Set of documents
        When: Applying MMR for diversity
        Then: Selected documents should balance relevance and diversity
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(
                diversity_penalty=0.5,  # Equal weight for diversity
                use_mmr=True,
            ),
        )
        
        query = "artificial intelligence applications"
        documents = [
            "AI is used in healthcare for disease diagnosis.",
            "Artificial intelligence helps doctors diagnose diseases.",  # Duplicate
            "AI powers recommendation systems in e-commerce.",
            "Machine learning enables fraud detection in banking.",
            "AI assists with autonomous vehicle navigation.",
        ]
        
        results = await reranker.rerank_with_mmr(query, documents, top_k=3)
        
        # Should select 3 diverse documents
        assert len(results) == 3
        
        selected_indices = [idx for idx, _ in results]
        
        # Documents 0 and 1 are duplicates, should not both be selected
        assert not (0 in selected_indices and 1 in selected_indices), (
            "MMR should not select near-duplicate documents"
        )

    @pytest.mark.asyncio
    async def test_diversity_preserves_top_result(self, embedding_service):
        """Test that diversity doesn't harm the most relevant result.
        
        Given: Documents with clear relevance ranking
        When: Applying diversity penalty
        Then: Top result should always be preserved
        """
        reranker = SemanticReranker(
            embedding_service=embedding_service,
            config=RerankingConfig(diversity_penalty=0.5),
        )
        
        query = "FastAPI framework"
        documents = [
            "FastAPI is a modern web framework for building APIs with Python.",  # Most relevant
            "FastAPI provides automatic API documentation and validation.",  # Also relevant
            "Django is a full-stack Python web framework.",  # Different framework
        ]
        
        results = await reranker.rerank_with_diversity(query, documents)
        
        # Top result should still be document 0 (most relevant)
        top_doc_idx = results[0][0]
        assert top_doc_idx == 0, "Most relevant document should remain on top"
