"""Quick test for query decomposition fix."""
import httpx
import asyncio

async def test_search():
    """Test search endpoint to verify query decomposition works."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            "http://localhost:8001/api/v1/search",
            json={
                "query": "what is pydantic ai",
                "mode": "balanced"
            }
        )
        
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success!")
            print(f"Answer length: {len(data.get('answer', ''))} chars")
            print(f"Sources: {len(data.get('sources', []))}")
            print(f"\nAnswer preview:")
            print(data.get('answer', '')[:500])
        else:
            print(f"❌ Error: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_search())
