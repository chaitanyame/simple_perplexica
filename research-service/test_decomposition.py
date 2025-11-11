"""Test query decomposition with a complex query."""

import asyncio
import httpx


async def test_complex_query():
    """Test with a complex query that should be decomposed."""
    url = "http://localhost:8001/api/v1/search"
    payload = {
        "query": "what is recent news of microsoft azure",
        "mode": "search",
        "max_sources": 10,
    }

    print(f"Testing search API: {url}")
    print(f"Query: {payload['query']}\n")
    print("Waiting for response (this includes LLM calls for decomposition and answer generation)...\n")

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload)
            print(f"✅ Status: {response.status_code}\n")
            
            if response.status_code == 200:
                data = response.json()
                
                # Display sub-queries
                print("=" * 80)
                print("QUERY DECOMPOSITION")
                print("=" * 80)
                for idx, sq in enumerate(data.get("sub_queries", []), 1):
                    print(f"{idx}. Query: {sq['query']}")
                    print(f"   Intent: {sq['intent']}, Priority: {sq['priority']}")
                print()
                
                # Display answer
                print("=" * 80)
                print("AI-GENERATED ANSWER")
                print("=" * 80)
                answer = data.get("answer", "No answer available")
                print(answer[:500] + "..." if len(answer) > 500 else answer)
                print()
                
                # Display sources
                print("=" * 80)
                print(f"SOURCES ({len(data.get('sources', []))} found)")
                print("=" * 80)
                for idx, source in enumerate(data.get("sources", [])[:5], 1):
                    print(f"[{idx}] {source['title']}")
                    print(f"    {source['url']}")
                print()
                
                # Display metadata
                print(f"Execution Time: {data.get('execution_time', 0):.2f}s")
                print(f"Confidence: {data.get('confidence', 0):.0%}")
            else:
                error_data = response.json()
                print(f"ERROR: {error_data.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"ERROR: {e}")


if __name__ == "__main__":
    asyncio.run(test_complex_query())
