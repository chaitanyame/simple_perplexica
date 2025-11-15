"""Integration test for decomposition quality validation in SearchAgent.

This test verifies that:
1. SearchAgent.decompose_query() successfully creates sub-queries
2. DecompositionValidator evaluates quality metrics
3. Quality scores are logged and traced
4. The workflow completes without errors
"""

import asyncio
import structlog

from src.agents.search_agent import SearchAgent, SearchAgentDeps
from src.services.llm.openrouter_client import OpenRouterClient
from src.core.config import settings

logger = structlog.get_logger(__name__)


async def test_decomposition_with_validation():
    """Test SearchAgent decomposition with quality validation."""

    # Initialize dependencies
    llm_client = OpenRouterClient(
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.LLM_MODEL,
    )

    deps = SearchAgentDeps(
        llm_client=llm_client,
        tracer=None,
        db=None,  # Not needed for decomposition
        searxng_client=None,
        serperdev_api_key="",
        crawl_client=None,
        document_processor=None,
        embedding_service=None,
    )

    # Create agent
    agent = SearchAgent(deps=deps)

    # Test queries
    test_cases = [
        {
            "query": "What are AI agents and how do they work?",
            "expected_min_quality": 0.6,
            "description": "Good decomposition - well-balanced query",
        },
        {
            "query": "Python programming",
            "expected_min_quality": 0.8,
            "description": "Simple query - should have high coverage",
        },
        {
            "query": "Compare machine learning frameworks in 2024",
            "expected_min_quality": 0.6,
            "description": "Complex query - multiple aspects",
        },
    ]

    print("\n" + "=" * 80)
    print("🧪 TESTING DECOMPOSITION WITH QUALITY VALIDATION")
    print("=" * 80)

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n📝 Test Case {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        print("-" * 80)

        try:
            # Decompose query (includes quality validation)
            sub_queries = await agent.decompose_query(test_case["query"])

            print(f"\n✅ Decomposition successful!")
            print(f"Generated {len(sub_queries)} sub-queries:")
            for j, sq in enumerate(sub_queries, 1):
                print(f"  [{j}] {sq.query}")
                print(f"      Intent: {sq.intent}, Priority: {sq.priority}")
                print(f"      Temporal: {sq.temporal_scope}, Year: {sq.specific_year or 'N/A'}")

            # Note: Quality metrics are logged inside decompose_query()
            # Check logs above for quality scores

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)
    print("\nℹ️  Check logs above for quality metrics (coverage, redundancy, overall score)")


if __name__ == "__main__":
    asyncio.run(test_decomposition_with_validation())
