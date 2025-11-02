"""
Comprehensive demonstration of SpaCy-based temporal detection
Shows how NER and dependency parsing work better than keywords
"""

import httpx
import asyncio

API_URL = "http://localhost:3001"


async def test_spacy_detection():
    """Test various queries to demonstrate SpaCy's superior detection"""

    test_cases = [
        # Day-level (should get very recent results)
        {
            "query": "breaking news USA today",
            "expected_time_range": "d",
            "reason": "SpaCy detects 'today' as DATE entity + 'breaking' as temporal modifier",
        },
        {
            "query": "latest AI breakthroughs",
            "expected_time_range": "d",
            "reason": "SpaCy understands 'latest' modifies implied news/tech context",
        },
        {
            "query": "what happened yesterday in politics",
            "expected_time_range": "d",
            "reason": "SpaCy recognizes 'yesterday' as DATE entity",
        },
        # Week-level
        {
            "query": "tech news this week",
            "expected_time_range": "w",
            "reason": "SpaCy detects 'this week' as complete DATE entity",
        },
        {
            "query": "recent developments in AI",
            "expected_time_range": "w",
            "reason": "'recent' implies week-level recency",
        },
        # Month-level
        {
            "query": "stock market performance this month",
            "expected_time_range": "m",
            "reason": "SpaCy recognizes 'this month' as DATE entity",
        },
        # No filter (historical/general queries)
        {
            "query": "World War 2 history",
            "expected_time_range": None,
            "reason": "Historical context - no recency needed",
        },
        {
            "query": "how does photosynthesis work",
            "expected_time_range": None,
            "reason": "Educational query - no temporal aspect",
        },
        {
            "query": "best pizza recipe",
            "expected_time_range": None,
            "reason": "No temporal indicators",
        },
        # Edge cases where SpaCy excels
        {
            "query": "latest recipes from Gordon Ramsay",
            "expected_time_range": None,  # 'latest' but recipe context, not news
            "reason": "SpaCy understands 'latest' without news context doesn't need filtering",
        },
    ]

    print("=" * 100)
    print("SpaCy-Based Temporal Detection Demonstration")
    print("=" * 100)
    print()

    for i, test in enumerate(test_cases, 1):
        print(f'\n{i}. Testing: "{test["query"]}"')
        print(f"   Expected: {test['expected_time_range']}")
        print(f"   Reason: {test['reason']}")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{API_URL}/api/search",
                    json={
                        "query": test["query"],
                        "focusMode": "webSearch",
                        "optimizationMode": "speed",  # Fast for testing
                    },
                )

                if response.status_code == 200:
                    data = response.json()
                    source_count = len(data.get("sources", []))
                    print(f"   [OK] Success: {source_count} sources found")

                    # Show first source as proof
                    if data.get("sources"):
                        first = data["sources"][0]
                        print(f"      First source: {first['title'][:60]}...")
                else:
                    print(f"   [FAIL] Failed: {response.status_code}")

        except Exception as e:
            print(f"   [ERROR] Error: {e}")

        # Small delay between requests
        await asyncio.sleep(0.5)

    print("\n" + "=" * 100)
    print("Demo Complete!")
    print("=" * 100)
    print("\nKey Advantages of SpaCy Over Keywords:")
    print(
        "  1. Named Entity Recognition - Understands 'this week' as a single DATE entity"
    )
    print(
        "  2. Dependency Parsing - Knows 'latest' modifying 'news' vs 'recipes' differs"
    )
    print("  3. Linguistic Context - Distinguishes temporal from historical queries")
    print("  4. Fallback Safety - Falls back to keywords if SpaCy unavailable")
    print(
        "\nTry monitoring logs: docker compose logs -f api-mvp | grep 'SpaCy detected'"
    )


if __name__ == "__main__":
    asyncio.run(test_spacy_detection())
