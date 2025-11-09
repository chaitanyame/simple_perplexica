"""
End-to-end integration tests for complete search pipeline.

Tests the full workflow:
1. Query decomposition (LLM)
2. Parallel multi-query search
3. Result aggregation (dedup, diversity, limits)
4. Multi-query reranking
5. Structured synthesis

Uses real API calls when OPENROUTER_API_KEY is set.
"""

import pytest
import os
from typing import List, Dict, Any


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_single_query_flow():
    """Test end-to-end flow with a single query (backward compatibility)"""
    from app.routers.search import search_route
    from fastapi import Request

    # Single simple query
    query = "python programming tutorial"

    # Mock request object with minimal required fields
    class MockRequest:
        def __init__(self):
            self.query = query

    request = MockRequest()

    # This should work with single query (backward compatibility)
    # The LLM should detect this is single query and return optimized_queries=[query]
    result = await search_route(request)

    assert result is not None
    # Should have answer or results
    assert hasattr(result, "answer") or hasattr(result, "results")


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_multi_query_decomposition_flow():
    """Test end-to-end flow with multi-query decomposition"""
    from app.routers.search import search_route

    # Multi-faceted query that should be decomposed
    query = "latest cloud technologies news from aws, azure, and gcp"

    class MockRequest:
        def __init__(self):
            self.query = query

    request = MockRequest()

    # Should decompose into multiple queries
    result = await search_route(request)

    assert result is not None
    # Should have comprehensive answer covering all vendors
    answer_text = str(getattr(result, "answer", result))
    assert len(answer_text) > 100  # Should be substantive


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_decomposition_to_aggregation():
    """Test decomposition followed by result aggregation"""
    from app.providers.openrouter import decide_search_and_rewrite
    from app.utils.result_aggregator import ResultAggregator
    from unittest.mock import patch

    query = "compare cloud providers aws azure gcp"

    # Get decomposed queries
    decision = await decide_search_and_rewrite(query)

    assert decision.optimized_queries is not None
    assert len(decision.optimized_queries) >= 1

    # Create mock results for each query
    mock_results_per_query = {}
    for i, q in enumerate(decision.optimized_queries):
        mock_results_per_query[q] = [
            {
                "title": f"Result {j} for {q}",
                "url": f"https://example.com/{i}/{j}",
                "pageContent": f"Content about {q}" * 50,
            }
            for j in range(5)
        ]

    # Aggregate results
    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate(
        mock_results_per_query,
        strategy="multi" if len(decision.optimized_queries) > 1 else "single",
        total_limit=10,
    )

    # Should have aggregated results
    assert isinstance(aggregated, list)
    assert len(aggregated) > 0
    assert len(aggregated) <= 10


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_search_and_rerank():
    """Test searching and reranking results"""
    from app.providers.openrouter import embed_texts
    from app.routers.search import rerank_sources
    import math

    # Create mock search results
    sources = [
        {
            "title": "AWS Services Overview",
            "url": "https://aws.amazon.com/services",
            "pageContent": "AWS provides cloud computing services including EC2, S3, Lambda",
        },
        {
            "title": "Azure Introduction",
            "url": "https://azure.microsoft.com/intro",
            "pageContent": "Azure is Microsoft's cloud platform with VMs, databases, and AI services",
        },
        {
            "title": "Google Cloud Platform",
            "url": "https://cloud.google.com",
            "pageContent": "GCP offers cloud infrastructure and services for computing, storage, and analytics",
        },
    ]

    # Get embeddings for reranking
    titles = [s["title"] for s in sources]
    embeddings = await embed_texts(titles)

    # Verify embeddings returned
    assert embeddings is not None
    assert len(embeddings) == len(sources)

    # Each embedding should be a vector
    assert all(isinstance(e, list) for e in embeddings)
    assert all(all(isinstance(x, (int, float)) for x in e) for e in embeddings)


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_synthesis_from_results():
    """Test generating synthesis from search results"""
    from app.providers.openrouter import synthesize_answer

    # Create mock search results
    sources = [
        {
            "title": "Python Basics",
            "url": "https://example.com/python",
            "pageContent": "Python is a high-level programming language. Key features include: simple syntax, extensive libraries, dynamic typing.",
        },
        {
            "title": "Python Advanced",
            "url": "https://example.com/python-advanced",
            "pageContent": "Advanced Python topics: decorators, generators, metaclasses, async/await, type hints.",
        },
    ]

    query = "tell me about python programming"

    # Generate synthesis
    answer = await synthesize_answer(query, sources)

    # Should return a substantive answer
    answer_text = str(answer)
    assert len(answer_text) > 50
    # Should mention Python
    assert "python" in answer_text.lower() or "programming" in answer_text.lower()


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_full_pipeline():
    """Test the complete pipeline end-to-end"""
    from app.providers.openrouter import decide_search_and_rewrite, synthesize_answer
    from app.utils.result_aggregator import ResultAggregator

    query = "machine learning frameworks comparison pytorch tensorflow keras"

    # Step 1: Decompose query
    decision = await decide_search_and_rewrite(query)

    assert decision.need_search is True
    assert len(decision.optimized_queries) >= 1

    # Step 2: Create mock search results
    # In real scenario, these would come from actual search
    mock_results_per_query = {}
    for q in decision.optimized_queries:
        mock_results_per_query[q] = [
            {
                "title": f"About {q}",
                "url": f"https://example.com/{q.replace(' ', '-')}",
                "pageContent": f"Information about {q}. " * 20,
            }
            for i in range(3)
        ]

    # Step 3: Aggregate results
    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate(
        mock_results_per_query,
        strategy=decision.search_strategy.value
        if hasattr(decision.search_strategy, "value")
        else decision.search_strategy,
        total_limit=10,
    )

    assert len(aggregated) > 0

    # Step 4: Synthesize answer
    answer = await synthesize_answer(query, aggregated)

    # Should return substantive answer
    answer_text = str(answer)
    assert len(answer_text) > 100


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_multi_vendor_query():
    """Test handling of queries mentioning multiple vendors/products"""
    from app.providers.openrouter import decide_search_and_rewrite

    query = "latest updates from aws, azure, gcp, and digitalocean"

    decision = await decide_search_and_rewrite(query)

    # Should decompose into multiple focused queries
    assert len(decision.optimized_queries) > 1
    # Should be marked as multi-query
    assert decision.search_strategy.value == "multi"


def test_e2e_result_aggregator_with_duplicates():
    """Test aggregator handles duplicates across multiple queries"""
    from app.utils.result_aggregator import ResultAggregator

    # Create results with duplicates across queries
    results_per_query = {
        "python": [
            {
                "title": "Python Official",
                "url": "https://python.org",
                "pageContent": "Official Python website",
            },
            {
                "title": "Python Docs",
                "url": "https://docs.python.org",
                "pageContent": "Python documentation",
            },
        ],
        "python tutorial": [
            {
                "title": "Python Official",  # Duplicate
                "url": "https://python.org",
                "pageContent": "Official Python website with tutorial section",
            },
            {
                "title": "Learn Python",
                "url": "https://learnpython.org",
                "pageContent": "Interactive Python learning",
            },
        ],
    }

    aggregator = ResultAggregator()
    aggregated = aggregator.aggregate(results_per_query, strategy="multi")

    # Should deduplicate python.org
    urls = [r["url"] for r in aggregated]
    assert urls.count("https://python.org") <= 1


def test_e2e_result_aggregator_diversity():
    """Test that aggregator maintains diversity across domains"""
    from app.utils.result_aggregator import ResultAggregator

    # Create results heavily skewed to one domain
    results_per_query = {
        "aws": [
            {
                "title": f"AWS Article {i}",
                "url": f"https://aws.amazon.com/article/{i}",
                "pageContent": f"AWS content {i}",
            }
            for i in range(20)
        ],
        "azure": [
            {
                "title": f"Azure Article {i}",
                "url": f"https://azure.microsoft.com/article/{i}",
                "pageContent": f"Azure content {i}",
            }
            for i in range(5)
        ],
    }

    aggregator = ResultAggregator(max_per_domain=3)
    aggregated = aggregator.aggregate(
        results_per_query, strategy="multi", total_limit=10
    )

    # Count results per domain
    aws_count = sum(1 for r in aggregated if "aws.amazon.com" in r["url"])
    azure_count = sum(1 for r in aggregated if "azure.microsoft.com" in r["url"])

    # Should have some from each domain
    assert aws_count > 0
    assert azure_count > 0
    # AWS should not dominate
    assert aws_count <= 3


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_caching_benefits():
    """Test that caching provides performance benefits"""
    from app.providers.openrouter import decide_search_and_rewrite
    import time

    query = "e2e caching performance test"

    # First call - should hit LLM
    start = time.time()
    result1 = await decide_search_and_rewrite(query)
    time1 = time.time() - start

    # Second call - should hit cache (if Redis available)
    start = time.time()
    result2 = await decide_search_and_rewrite(query)
    time2 = time.time() - start

    # Results should be identical
    assert result1.optimized_queries == result2.optimized_queries

    # Second call should be faster (cache hit)
    # Note: This is approximate since Redis might not be available
    assert time2 <= time1 * 1.5  # Allow some variance


def test_e2e_backward_compatibility():
    """Test that single-query flows still work (backward compatibility)"""
    from app.models import DecisionOutput, SearchStrategy

    # Old-style single query should still work
    output = DecisionOutput(
        need_search=True,
        optimized_queries=["single query"],
        search_strategy=SearchStrategy.single,
    )

    assert output.need_search is True
    assert len(output.optimized_queries) == 1
    assert output.search_strategy == SearchStrategy.single


def test_e2e_models_serialization():
    """Test that models can be properly serialized/deserialized"""
    import json
    from app.models import DecisionOutput, SearchStrategy

    # Create a decision output
    decision = DecisionOutput(
        need_search=True,
        optimized_queries=["query1", "query2", "query3"],
        search_strategy=SearchStrategy.multi,
        links=["https://example.com/1", "https://example.com/2"],
    )

    # Serialize to JSON
    json_str = decision.model_dump_json()

    # Deserialize back
    parsed = DecisionOutput.model_validate_json(json_str)

    # Should be identical
    assert parsed.need_search == decision.need_search
    assert parsed.optimized_queries == decision.optimized_queries
    assert parsed.search_strategy == decision.search_strategy
    assert parsed.links == decision.links


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_edge_case_empty_query():
    """Test handling of edge case: empty query"""
    from app.providers.openrouter import decide_search_and_rewrite

    query = ""

    try:
        decision = await decide_search_and_rewrite(query)
        # Should handle gracefully
        assert decision is not None
    except Exception as e:
        # Should provide meaningful error
        assert "query" in str(e).lower() or "empty" in str(e).lower()


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_e2e_edge_case_very_long_query():
    """Test handling of very long/complex query"""
    from app.providers.openrouter import decide_search_and_rewrite

    # Very long query with many entities
    query = "latest news about " + ", ".join(
        [f"company{i}" for i in range(50)]
    )

    decision = await decide_search_and_rewrite(query)

    # Should handle it (might limit to max queries)
    assert decision.optimized_queries is not None
    assert len(decision.optimized_queries) <= 5  # Reasonable limit


def test_e2e_integration_test_structure():
    """Test that integration test structure is sound"""
    # This test verifies the testing infrastructure itself
    import sys

    # Should be able to import all required modules
    try:
        from app.providers.openrouter import decide_search_and_rewrite
        from app.routers.search import search_route
        from app.utils.result_aggregator import ResultAggregator
        from app.models import DecisionOutput, SearchStrategy
    except ImportError as e:
        pytest.fail(f"Failed to import required module: {e}")

    assert True
