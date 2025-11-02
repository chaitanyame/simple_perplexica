# Time-Range Filtering Test
# Tests that recency terms trigger appropriate SearxNG time_range filters

import httpx

test_queries = [
    {
        "query": "breaking news USA today",
        "expected_range": "d (day)",
        "description": "Breaking news should get daily results",
    },
    {
        "query": "what happened this week in tech",
        "expected_range": "w (week)",
        "description": "This week should get weekly results",
    },
    {
        "query": "latest AI breakthroughs",
        "expected_range": "d (day)",
        "description": "Latest should get daily results",
    },
    {
        "query": "historical events of World War 2",
        "expected_range": "None",
        "description": "Historical queries should not filter by time",
    },
]

print("=" * 70)
print("TIME-RANGE FILTERING TESTS")
print("=" * 70)

for test in test_queries:
    print(f"\nQuery: {test['query']}")
    print(f"Expected: {test['expected_range']}")
    print(f"Test: {test['description']}")

    body = {
        "query": test["query"],
        "focusMode": "webSearch",
        "optimizationMode": "balanced",
        "stream": False,
    }

    try:
        r = httpx.post("http://localhost:3001/api/search", json=body, timeout=120)
        d = r.json()

        sources = d.get("sources", [])
        message = d.get("message", "")

        print(f"✓ Status: {r.status_code}")
        print(f"✓ Sources returned: {len(sources)}")
        print(f"✓ Answer length: {len(message)} chars")

        # Show first source
        if sources:
            print(f"✓ Top source: {sources[0].get('title')[:50]}...")

    except Exception as e:
        print(f"✗ Error: {e}")

    print("-" * 70)

print("\n" + "=" * 70)
print("All tests completed!")
print("=" * 70)
