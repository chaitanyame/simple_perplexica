"""Test SearXNG connectivity after network fix."""
import asyncio
import httpx


async def test_searxng():
    """Test search endpoint with SearXNG."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/v1/search",
                json={
                    "query": "What is Python?",
                    "mode": "balanced",
                    "max_sources": 10
                }
            )
            print(f"✅ Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Sources: {len(data.get('sources', []))}")
                print(f"✅ Answer length: {len(data.get('answer', ''))} chars")
                print(f"\n📝 First 200 chars of answer:")
                print(data.get('answer', '')[:200])
            else:
                print(f"❌ Error: {response.text}")
        except Exception as e:
            print(f"❌ Exception: {e}")


if __name__ == "__main__":
    asyncio.run(test_searxng())
