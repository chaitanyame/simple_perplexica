import asyncio
from app.search_clients import searxng


async def test():
    # Test with recency query
    results = await searxng.search("breaking news USA today", engines=[], language="en")
    print(f"Got {len(results)} results from SearxNG with time_range")
    print("\nFirst 3 results:")
    for i, r in enumerate(results[:3], 1):
        print(f"\n{i}. {r.get('title')[:70]}")
        print(f"   URL: {r.get('url')}")
        content = r.get("pageContent") or ""
        print(f"   Content ({len(content)} chars): {content[:150]}...")


asyncio.run(test())
