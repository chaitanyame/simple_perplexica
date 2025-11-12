"""Debug research endpoint step-by-step."""
import asyncio
import httpx


async def test_research():
    """Test research endpoint with detailed output."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        print("🔬 Testing research endpoint...")
        print("=" * 60)
        
        try:
            response = await client.post(
                "http://localhost:8001/api/v1/research",
                json={
                    "query": "What is machine learning?",
                    "max_iterations": 1,
                    "timeout": 90,
                    "mode": "balanced"
                }
            )
            
            print(f"Status: {response.status_code}")
            print(f"\nResponse:")
            print(response.text[:2000])  # First 2000 chars
            
        except Exception as e:
            print(f"❌ Exception: {type(e).__name__}: {e}")


if __name__ == "__main__":
    asyncio.run(test_research())
