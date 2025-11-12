"""Unit tests for hybrid retrieval (BM25 + Semantic).

Tests combining keyword search (BM25) with semantic search for better results.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_hybrid_search_combines_scores():
    """Test that hybrid search combines BM25 and semantic scores.
    
    Verifies that the hybrid search algorithm properly combines:
    - BM25 keyword relevance scores
    - Semantic similarity scores
    using the configured alpha weight.
    """
    # Mock sources with different score profiles
    sources = [
        {
            "title": "Python Programming",
            "bm25_score": 0.9,
            "semantic_score": 0.3,
        },
        {
            "title": "Python Tutorial",
            "bm25_score": 0.6,
            "semantic_score": 0.8,
        },
        {
            "title": "Learn Python",
            "bm25_score": 0.4,
            "semantic_score": 0.9,
        },
    ]
    
    # Simulate hybrid search with alpha=0.5 (equal weights)
    result = await hybrid_search("query", sources, alpha=0.5)
    
    # Verify hybrid score is computed correctly
    # hybrid_score = alpha * semantic + (1-alpha) * bm25
    # For first source: 0.5 * 0.3 + 0.5 * 0.9 = 0.6
    assert result[0]["hybrid_score"] > 0.5
    
    # Verify sources are reranked by hybrid score
    assert all(
        result[i]["hybrid_score"] >= result[i + 1]["hybrid_score"]
        for i in range(len(result) - 1)
    )


@pytest.mark.asyncio
async def test_hybrid_search_alpha_weights():
    """Test that alpha parameter controls semantic vs keyword weight."""
    sources = [
        {
            "title": "Test",
            "bm25_score": 1.0,
            "semantic_score": 0.0,
        },
    ]
    
    # Test with alpha=1.0 (100% semantic)
    result_semantic = await hybrid_search("query", sources, alpha=1.0)
    assert result_semantic[0]["hybrid_score"] == 0.0
    
    # Test with alpha=0.0 (100% keyword)
    result_keyword = await hybrid_search("query", sources, alpha=0.0)
    assert result_keyword[0]["hybrid_score"] == 1.0
    
    # Test with alpha=0.5 (balanced)
    result_balanced = await hybrid_search("query", sources, alpha=0.5)
    assert result_balanced[0]["hybrid_score"] == 0.5


@pytest.mark.asyncio
async def test_hybrid_search_empty_sources():
    """Test hybrid search with empty source list."""
    result = await hybrid_search("query", [], alpha=0.5)
    assert result == []


@pytest.mark.asyncio
async def test_hybrid_search_missing_scores():
    """Test hybrid search handles missing scores gracefully."""
    sources = [
        {
            "title": "No scores",
            # Missing bm25_score and semantic_score
        },
    ]
    
    result = await hybrid_search("query", sources, alpha=0.5)
    
    # Should default to 0.0 for missing scores
    assert result[0]["hybrid_score"] == 0.0


# Helper function to simulate hybrid search
async def hybrid_search(
    query: str,
    sources: list[dict],
    alpha: float = 0.5,
) -> list[dict]:
    """Combine BM25 and semantic scores for hybrid retrieval.
    
    Args:
        query: Search query
        sources: List of sources with bm25_score and semantic_score
        alpha: Weight for semantic score (0.0-1.0)
        
    Returns:
        Sources sorted by hybrid_score
        
    Formula:
        hybrid_score = alpha * semantic_score + (1-alpha) * bm25_score
    """
    for source in sources:
        bm25 = source.get("bm25_score", 0.0)
        semantic = source.get("semantic_score", 0.0)
        source["hybrid_score"] = alpha * semantic + (1 - alpha) * bm25
    
    # Sort by hybrid score descending
    return sorted(sources, key=lambda x: x["hybrid_score"], reverse=True)
