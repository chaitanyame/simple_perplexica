"""Direct API test to see detailed search logs."""

import asyncio
import httpx


async def test_search():
    """Test search API with minimal query."""
    url = "http://localhost:8001/api/v1/search"
    payload = {
        "query": "Python programming",
        "mode": "search",
        "max_sources": 10,
    }

    print(f"🔍 Testing search API: {url}")
    print(f"📝 Query: {payload['query']}\n")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload)
            print(f"✅ Status: {response.status_code}\n")
            
            if response.status_code == 200:
                data = response.json()
                
                # Display answer prominently
                print("=" * 80)
                print("📄 AI-GENERATED ANSWER")
                print("=" * 80)
                print(data.get("answer", "No answer available"))
                print("=" * 80)
                
                # Display sources
                print(f"\n� SOURCES ({len(data.get('sources', []))} found):")
                for idx, source in enumerate(data.get("sources", []), 1):
                    print(f"  [{idx}] {source['title']}")
                    print(f"      {source['url']}")
                
                # Display metadata
                print(f"\n⏱️  Execution Time: {data.get('execution_time', 0):.2f}s")
                print(f"📊 Confidence: {data.get('confidence', 0):.0%}")
            else:
                print(f"�📦 Full Response:\n{response.json()}")
        except Exception as e:
            print(f"❌ Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_search())
