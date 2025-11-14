"""Simple integration test for year-specific routing."""

import asyncio

from src.agents.search_agent import SearchAgent, SearchAgentDeps, SubQuery
from src.services.llm.openrouter_client import OpenRouterClient
from src.core.config import settings


async def test_year_routing():
    """Test year-specific query routing."""

    print("\n" + "=" * 80)
    print("🧪 TESTING YEAR-SPECIFIC QUERY ROUTING TO SERPERDEV")
    print("=" * 80)

    # Initialize dependencies
    llm_client = OpenRouterClient(
        api_key=settings.OPENROUTER_API_KEY,
        model=settings.LLM_MODEL,
    )

    deps = SearchAgentDeps(
        llm_client=llm_client,
        tracer=None,
        db=None,
        searxng_client=None,
        serperdev_api_key=settings.SERPER_API_KEY,  # Required for year-specific routing
        crawl_client=None,
        document_processor=None,
        embedding_service=None,
    )

    agent = SearchAgent(deps=deps)

    # Test cases
    test_cases = [
        {
            "query": "AI developments 2023",
            "year": 2023,
            "description": "Year-specific (2023) → Should route to SerperDev",
        },
        {
            "query": "Machine learning trends 2024",
            "year": 2024,
            "description": "Year-specific (2024) → Should route to SerperDev",
        },
        {
            "query": "Python programming",
            "year": None,
            "description": "No year → Should use SearxNG",
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n\n📝 Test Case {i}: {test_case['description']}")
        print(f"Query: '{test_case['query']}'")
        print(f"Year: {test_case['year']}")
        print("-" * 80)

        sub_query = SubQuery(
            query=test_case["query"],
            intent="factual",
            priority=1,
            temporal_scope="any",
            specific_year=test_case["year"],
            language="en",
        )

        try:
            results = await agent._search_source(sub_query)

            print(f"\n✅ Search successful!")
            print(f"Results: {len(results)}")
            if results:
                print(f"Top result: {results[0].title}")
                print(f"Relevance: {results[0].relevance}")
                if test_case["year"]:
                    if results[0].relevance == 0.85:
                        print("✅ Correct relevance (0.85) - SerperDev was used!")
                    else:
                        print(f"⚠️  Unexpected relevance - expected 0.85 for SerperDev")
            else:
                print("⚠️  No results returned")

        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 80)
    print("✅ ROUTING TESTS COMPLETED")
    print("=" * 80)
    print("\nℹ️  Check logs above for routing decisions:")
    print("   - Year-specific queries should show: '📅 Year-specific query detected'")
    print("   - Non-year queries should show: '🌐 SearxNG primary search'")


if __name__ == "__main__":
    asyncio.run(test_year_routing())
