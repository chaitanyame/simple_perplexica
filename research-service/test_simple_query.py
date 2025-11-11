"""Test simple query that should not decompose much."""
import asyncio
import httpx

API_URL = "http://localhost:8001/api/v1/search"

async def test_simple_query():
    """Test a simple, straightforward query."""
    query = "what is Python programming language"
    
    print(f"Testing search API: {API_URL}")
    print(f"Query: {query}")
    print("\nWaiting for response...")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                API_URL,
                json={"query": query}
            )
            
            print(f"\nStatus: {response.status_code}\n")
            
            if response.status_code == 200:
                data = response.json()
                
                # Show decomposition
                print("=" * 80)
                print("QUERY DECOMPOSITION")
                print("=" * 80)
                if "sub_queries" in data:
                    for i, sq in enumerate(data["sub_queries"], 1):
                        print(f"{i}. Query: {sq['query']}")
                        print(f"   Intent: {sq['intent']}, Priority: {sq['priority']}")
                
                # Show answer (first 500 chars)
                print("\n" + "=" * 80)
                print("AI-GENERATED ANSWER")
                print("=" * 80)
                answer = data.get("answer", "No answer generated")
                print(answer[:500] + "..." if len(answer) > 500 else answer)
                
                # Show sources count
                print("\n" + "=" * 80)
                print(f"SOURCES ({len(data.get('sources', []))} found)")
                print("=" * 80)
                for i, source in enumerate(data.get("sources", [])[:5], 1):
                    print(f"[{i}] {source['title']}")
                    print(f"    {source['url']}")
                
                # Show metadata
                print(f"\nExecution Time: {data.get('execution_time', 0):.2f}s")
                print(f"Confidence: {int(data.get('confidence', 0) * 100)}%")
                
            else:
                print(f"ERROR: {response.text}")
                
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(test_simple_query())
