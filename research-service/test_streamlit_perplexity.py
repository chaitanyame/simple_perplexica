"""Quick test to verify Perplexity works from Streamlit UI's perspective."""

import asyncio
import httpx


async def test_streamlit_perplexity_request():
    """Test with the exact payload Streamlit sends."""
    
    print("🧪 Testing Perplexity via Streamlit Payload")
    print("=" * 60)
    
    # Exact payload that Streamlit sends
    payload = {
        "query": "What is Pydantic AI?",
        "mode": "balanced",
        "model": "anthropic/claude-3.5-sonnet",
        "search_engine": "perplexity",  # This was causing 422 before
    }
    
    print(f"\n📤 Request:")
    print(f"  Endpoint: http://localhost:8001/api/v1/search/perplexity")
    print(f"  Payload: {payload}")
    
    try:
        async with httpx.AsyncClient(timeout=70.0) as client:
            response = await client.post(
                "http://localhost:8001/api/v1/search/perplexity",
                json=payload,
            )
            
            print(f"\n✅ Status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"\n🎉 SUCCESS! Perplexity working via Streamlit!")
                print(f"  Session ID: {data['session_id']}")
                print(f"  Model: {data['model_used']}")
                print(f"  Answer Length: {len(data['answer'])} chars")
                print(f"  Sources: {len(data['sources'])}")
                print(f"  Execution Time: {data['execution_time']:.2f}s")
                
                print(f"\n📝 Answer Preview:")
                print(f"  {data['answer'][:200]}...")
                
            elif response.status_code == 422:
                print(f"\n❌ Validation Error (422):")
                print(f"  {response.text}")
                
            else:
                print(f"\n❌ Error {response.status_code}:")
                print(f"  {response.text}")
                
    except Exception as e:
        print(f"\n❌ Request Failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_streamlit_perplexity_request())
