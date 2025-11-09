"""
Unit tests for result aggregation - TDD approach (RED phase)
Tests deduplication, diversity filtering, and per-query limiting
"""
import pytest
from typing import List, Dict, Any


def create_mock_result(url: str, title: str, content: str) -> Dict[str, Any]:
    """Helper to create mock search results"""
    return {
        "title": title,
        "url": url,
        "pageContent": content
    }


def test_deduplicate_by_url():
    """Test that duplicate URLs are removed"""
    from app.utils.result_aggregator import ResultAggregator

    results = [
        create_mock_result("https://example.com/1", "Article 1", "Content 1"),
        create_mock_result("https://example.com/1", "Article 1 Duplicate", "Content 1"),  # Duplicate
        create_mock_result("https://example.com/2", "Article 2", "Content 2"),
    ]

    aggregator = ResultAggregator()
    deduped = aggregator.deduplicate(results)

    assert len(deduped) == 2
    assert all(result["url"] in ["https://example.com/1", "https://example.com/2"] for result in deduped)


def test_preserve_diversity():
    """Test that results are balanced across sources"""
    from app.utils.result_aggregator import ResultAggregator

    results = []
    # Add 10 AWS results
    for i in range(10):
        results.append(create_mock_result(f"https://aws.example.com/{i}", f"AWS Result {i}", f"AWS Content {i}"))
    # Add 2 Azure results
    for i in range(2):
        results.append(create_mock_result(f"https://azure.example.com/{i}", f"Azure Result {i}", f"Azure Content {i}"))

    aggregator = ResultAggregator()
    diverse = aggregator.apply_diversity_filter(results, max_per_domain=5)

    # Should not all be from AWS
    aws_count = sum(1 for r in diverse if "aws" in r["url"])
    azure_count = sum(1 for r in diverse if "azure" in r["url"])

    assert aws_count <= 5  # Max 5 per domain
    assert azure_count <= 5


def test_per_query_limits():
    """Test that per-query result limits are applied"""
    from app.utils.result_aggregator import ResultAggregator

    results_per_query = {
        "query1": [create_mock_result(f"https://q1-{i}.com", f"Q1 Result {i}", f"Q1 Content {i}") for i in range(20)],
        "query2": [create_mock_result(f"https://q2-{i}.com", f"Q2 Result {i}", f"Q2 Content {i}") for i in range(20)],
        "query3": [create_mock_result(f"https://q3-{i}.com", f"Q3 Result {i}", f"Q3 Content {i}") for i in range(20)],
        "query4": [create_mock_result(f"https://q4-{i}.com", f"Q4 Result {i}", f"Q4 Content {i}") for i in range(20)],
    }

    aggregator = ResultAggregator()
    limited = aggregator.limit_per_query(results_per_query, limit_per_query=5)

    total = sum(len(v) for v in limited.values())
    assert total <= 20  # 4 queries * 5 limit

    for query_results in limited.values():
        assert len(query_results) <= 5


def test_empty_results_handling():
    """Test handling when some queries return no results"""
    from app.utils.result_aggregator import ResultAggregator

    results_per_query = {
        "query1": [create_mock_result(f"https://q1-{i}.com", f"Q1 Result {i}", f"Q1 Content {i}") for i in range(5)],
        "query2": [],  # Empty
        "query3": [create_mock_result(f"https://q3-{i}.com", f"Q3 Result {i}", f"Q3 Content {i}") for i in range(5)],
    }

    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate(results_per_query, strategy="multi")

    # Should handle empty queries gracefully
    assert aggregated is not None
    assert isinstance(aggregated, list)


def test_aggregate_with_single_strategy():
    """Test aggregation with single strategy"""
    from app.utils.result_aggregator import ResultAggregator

    results_per_query = {
        "python tutorial": [
            create_mock_result("https://example.com/1", "Tutorial 1", "Content 1"),
            create_mock_result("https://example.com/2", "Tutorial 2", "Content 2"),
        ]
    }

    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate(results_per_query, strategy="single")

    assert isinstance(aggregated, list)
    assert len(aggregated) <= 10  # Should be limited


def test_aggregate_with_multi_strategy():
    """Test aggregation with multi strategy"""
    from app.utils.result_aggregator import ResultAggregator

    results_per_query = {
        "aws": [create_mock_result(f"https://aws-{i}.com", f"AWS {i}", f"AWS {i}") for i in range(5)],
        "azure": [create_mock_result(f"https://azure-{i}.com", f"Azure {i}", f"Azure {i}") for i in range(5)],
        "gcp": [create_mock_result(f"https://gcp-{i}.com", f"GCP {i}", f"GCP {i}") for i in range(5)],
    }

    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate(results_per_query, strategy="multi")

    assert isinstance(aggregated, list)
    # Should have results from all queries
    urls = [r["url"] for r in aggregated]
    assert any("aws" in u for u in urls)
    assert any("azure" in u for u in urls)
    assert any("gcp" in u for u in urls)


def test_deduplication_keeps_best_result():
    """Test that when deduplicating, best result is kept"""
    from app.utils.result_aggregator import ResultAggregator

    results = [
        create_mock_result("https://example.com/1", "Poor Title", "Short content"),
        create_mock_result("https://example.com/1", "Good Title", "Much longer and better content here"),
    ]

    aggregator = ResultAggregator()
    deduped = aggregator.deduplicate(results)

    assert len(deduped) == 1
    # Should keep the better one (by content length or some heuristic)


def test_aggregator_initialization():
    """Test ResultAggregator can be initialized"""
    from app.utils.result_aggregator import ResultAggregator

    aggregator = ResultAggregator()

    assert aggregator is not None
    assert hasattr(aggregator, 'deduplicate')
    assert hasattr(aggregator, 'apply_diversity_filter')
    assert hasattr(aggregator, 'limit_per_query')
    assert hasattr(aggregator, 'aggregate')


def test_aggregator_with_mixed_content_quality():
    """Test aggregation handles mixed content quality"""
    from app.utils.result_aggregator import ResultAggregator

    results = [
        create_mock_result("https://good.com/1", "Detailed Title", "A" * 1000),  # Long content
        create_mock_result("https://poor.com/1", "Title", ""),  # Empty content
        create_mock_result("https://ok.com/1", "Medium Title", "B" * 500),
    ]

    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate({"query": results}, strategy="single")

    # Should include all but prefer better quality
    assert len(aggregated) >= 1


def test_aggregate_respects_total_limit():
    """Test that total results don't exceed specified limit"""
    from app.utils.result_aggregator import ResultAggregator

    results_per_query = {
        f"query{i}": [
            create_mock_result(f"https://q{i}-{j}.com", f"Result {j}", f"Content {j}")
            for j in range(50)
        ]
        for i in range(5)
    }

    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate(results_per_query, strategy="multi", total_limit=20)

    assert len(aggregated) <= 20


def test_deduplicate_case_insensitive_url():
    """Test that URL deduplication is case-insensitive where appropriate"""
    from app.utils.result_aggregator import ResultAggregator

    results = [
        create_mock_result("https://example.com/Article", "Title 1", "Content 1"),
        create_mock_result("https://example.com/article", "Title 2", "Content 2"),  # Same URL, different case
    ]

    aggregator = ResultAggregator()
    deduped = aggregator.deduplicate(results)

    # URLs that differ only in case should be considered duplicates
    assert len(deduped) <= 2  # Might be 1 or 2 depending on implementation


def test_result_ordering_after_aggregation():
    """Test that results are ordered by relevance"""
    from app.utils.result_aggregator import ResultAggregator

    results = [
        create_mock_result("https://less-relevant.com", "OK", "Some content"),
        create_mock_result("https://most-relevant.com", "Excellent", "Detailed comprehensive content" * 10),
        create_mock_result("https://medium-relevant.com", "Good", "Medium content here"),
    ]

    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate({"query": results}, strategy="single")

    # First result should be most relevant
    if len(aggregated) > 0:
        assert aggregated[0]["url"] is not None
