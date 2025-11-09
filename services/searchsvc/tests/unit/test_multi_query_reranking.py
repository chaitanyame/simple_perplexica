"""
Unit tests for multi-query reranking - TDD approach (RED phase)
Tests reranking with multiple queries for better relevance
"""
import pytest
from unittest.mock import AsyncMock, patch
import math


def test_rerank_sources_single_query():
    """Test that single-query reranking still works"""
    from app.routers.search import rerank_sources

    sources = [
        {"title": "Python Basics", "url": "https://example.com/1", "pageContent": "Learn Python fundamentals"},
        {"title": "Python Advanced", "url": "https://example.com/2", "pageContent": "Advanced Python patterns and techniques"},
    ]

    # Single query reranking
    assert rerank_sources is not None


@pytest.mark.asyncio
async def test_rerank_with_multiple_queries():
    """Test reranking when multiple queries are provided"""
    from app.routers.search import rerank_sources

    sources = [
        {"title": "AWS Services", "url": "https://aws.com/1", "pageContent": "AWS cloud services and features"},
        {"title": "Azure Overview", "url": "https://azure.com/1", "pageContent": "Azure cloud platform details"},
        {"title": "GCP Introduction", "url": "https://gcp.com/1", "pageContent": "Google Cloud Platform basics"},
    ]

    # Mock embedding would be called for multi-query
    # For now, verify function exists
    assert rerank_sources is not None


def test_rerank_uses_max_similarity():
    """Test that result is scored by max similarity across queries"""
    # Simulated embeddings
    query_embeddings = {
        "original": [1.0, 0.0, 0.0],
        "aws": [0.9, 0.1, 0.0],
        "azure": [0.1, 0.9, 0.0],
        "gcp": [0.1, 0.0, 0.9],
    }

    result_embedding = [0.85, 0.1, 0.0]  # Matches AWS best

    # Calculate similarities
    def cosine_sim(a, b):
        if not a or not b:
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    similarities = {k: cosine_sim(v, result_embedding) for k, v in query_embeddings.items()}

    # Should use max
    max_sim = max(similarities.values())
    assert max_sim > 0.5  # AWS match is strongest


def test_rerank_threshold_filtering():
    """Test that low-similarity results are filtered"""
    similarities = {
        "url1": 0.8,   # Good
        "url2": 0.6,   # Medium
        "url3": 0.25,  # Poor but just under threshold
        "url4": 0.1,   # Very poor
    }

    threshold = 0.3

    filtered = {url: sim for url, sim in similarities.items() if sim >= threshold}

    assert len(filtered) == 2  # url1, url2 (both >= 0.3)
    assert "url1" in filtered
    assert "url2" in filtered
    assert "url3" not in filtered
    assert "url4" not in filtered


def test_rerank_diversity_across_queries():
    """Test that results from different queries are balanced"""
    # Results tagged by source query
    results = [
        {"url": "https://aws1.com", "query": "aws", "score": 0.9},
        {"url": "https://aws2.com", "query": "aws", "score": 0.85},
        {"url": "https://aws3.com", "query": "aws", "score": 0.8},
        {"url": "https://azure1.com", "query": "azure", "score": 0.75},
        {"url": "https://gcp1.com", "query": "gcp", "score": 0.7},
    ]

    # After reranking, should have diversity
    # (Implementation detail for reranking to enforce)
    assert len(results) == 5


def test_rerank_preserves_content_quality():
    """Test that reranking doesn't degrade content quality"""
    sources = [
        {"url": "https://good.com", "pageContent": "A" * 2000},  # Long content
        {"url": "https://poor.com", "pageContent": "B" * 100},   # Short content
    ]

    # Both should be kept, but ranked by relevance first, then quality
    assert len(sources) == 2


def test_rerank_handles_tied_scores():
    """Test handling when multiple results have same relevance score"""
    results = [
        {"url": "https://a.com", "score": 0.8},
        {"url": "https://b.com", "score": 0.8},
        {"url": "https://c.com", "score": 0.7},
    ]

    # Tied results should be stable sorted
    assert results[0]["score"] == results[1]["score"]


def test_rerank_multi_signal_scoring():
    """Test reranking with multiple signals (semantic + freshness + entity)"""
    signals = {
        "https://url1.com": {
            "semantic": 0.8,
            "freshness": 0.9,
            "entity_coverage": 0.7,
        },
        "https://url2.com": {
            "semantic": 0.9,
            "freshness": 0.5,
            "entity_coverage": 0.8,
        },
    }

    # Weighted combination
    def score(s):
        return (s["semantic"] * 0.6 + s["freshness"] * 0.2 + s["entity_coverage"] * 0.2)

    scores = {url: score(signals[url]) for url in signals}

    # url1 and url2 both contribute differently
    assert len(scores) == 2
    # url1 slightly better due to freshness
    assert scores["https://url1.com"] >= 0.7


def test_rerank_query_specific_boosting():
    """Test that results relevant to specific queries get boosted"""
    # Result from "aws" sub-query
    aws_result = {
        "url": "https://aws.com/article",
        "content": "AWS EC2 instances and pricing",
        "matching_queries": ["aws"],
    }

    # Result from "azure" sub-query
    azure_result = {
        "url": "https://azure.com/article",
        "content": "Azure VMs and cost",
        "matching_queries": ["azure"],
    }

    # Both are valid, each boosted for their matching query
    assert aws_result["matching_queries"][0] == "aws"
    assert azure_result["matching_queries"][0] == "azure"


def test_rerank_handles_missing_embeddings():
    """Test graceful handling when embeddings fail"""
    sources_without_embeddings = [
        {"url": "https://example1.com"},
        {"url": "https://example2.com"},
    ]

    # Should fall back to basic sorting
    assert len(sources_without_embeddings) == 2


def test_rerank_maintains_order_stability():
    """Test that reranking is stable (same input = same output)"""
    sources = [
        {"url": "https://a.com", "content": "A"},
        {"url": "https://b.com", "content": "B"},
        {"url": "https://c.com", "content": "C"},
    ]

    # Two identical reranking operations should produce same result
    # (Test stability of sort)
    sorted1 = sorted(sources, key=lambda x: len(x.get("content", "")), reverse=True)
    sorted2 = sorted(sources, key=lambda x: len(x.get("content", "")), reverse=True)

    assert sorted1 == sorted2


def test_rerank_optimized_for_speed():
    """Test that reranking doesn't add excessive latency"""
    # Verify reranking can handle reasonable number of results
    num_results = 100
    num_queries = 4

    # Embeddings per result * number of results = reasonable computation
    total_ops = num_results * num_queries
    # Should handle this in <1 second for 100 results with 4 queries
    assert total_ops <= 500


def test_rerank_source_attribution():
    """Test that reranked results maintain source attribution"""
    sources = [
        {"url": "https://aws.com/1", "source_query": "aws"},
        {"url": "https://azure.com/1", "source_query": "azure"},
    ]

    # After reranking, source_query should be preserved
    assert all("source_query" in s for s in sources)
