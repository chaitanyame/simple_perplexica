"""Quick test for Perplexity search endpoint."""

import asyncio
import httpx


async def test_perplexity_endpoint():
    """Test the /v1/search/perplexity endpoint."""
    
    print("🧪 Testing Perplexity Search Endpoint")
    print("=" * 60)
    
    # Test query
    query = "What is Pydantic AI and how does it work?"
    
    print(f"\n📝 Query: {query}")
    print(f"🎯 Endpoint: http://localhost:8001/api/v1/search/perplexity")
    
    payload = {
        "query": query,
        "mode": "balanced",
        "model": "sonar",  # Use Perplexity's model
        "timeout": 60,
    }
    
    print(f"\n📤 Sending request...")
    
    try:
        async with httpx.AsyncClient(timeout=70.0) as client:
            response = await client.post(
                "http://localhost:8001/api/v1/search/perplexity",
                json=payload,
            )
            
            print(f"\n✅ Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                
                print(f"\n🔍 Results:")
                print(f"  Session ID: {data.get('session_id')}")
                print(f"  Model: {data.get('model_used')}")
                print(f"  Mode: {data.get('mode')}")
                print(f"  Execution Time: {data.get('execution_time', 0):.2f}s")
                print(f"  Total Sources: {data.get('total_sources', 0)}")
                
                print(f"\n📝 Answer (first 300 chars):")
                answer = data.get('answer', '')
                print(f"  {answer[:300]}...")
                
                print(f"\n📚 Citations:")
                for source in data.get('sources', [])[:5]:
                    print(f"  • {source.get('title')}: {source.get('url')}")
                
                print(f"\n✅ Perplexity endpoint working correctly!")
                
            else:
                print(f"\n❌ Error: {response.text}")
                
    except httpx.ConnectError:
        print(f"\n❌ Connection Error: Make sure the API is running at localhost:8001")
        print("   Run: docker compose up research-api")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_perplexity_endpoint())
