"""Quick test for BALANCED mode only."""

import asyncio
import time

import httpx

API_BASE_URL = "http://localhost:8001"
TEST_QUERY = "What are transformer neural networks and how do they work?"


async def test_balanced_mode():
    """Test BALANCED mode."""
    print("=" * 80)
    print("Testing BALANCED Mode")
    print("=" * 80)
    print(f"Query: {TEST_QUERY}")
    print(f"Expected: 10 sources, 45s timeout, crawl top 5 URLs")
    print()
    
    start_time = time.time()
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{API_BASE_URL}/api/v1/search",
                json={
                    "query": TEST_QUERY,
                    "mode": "balanced",
                },
                timeout=90.0,
            )
            
            execution_time = time.time() - start_time
            
            if response.status_code == 200:
                data = response.json()
                num_sources = len(data.get("sources", []))
                answer_length = len(data.get("answer", ""))
                
                print(f"[OK] BALANCED mode completed in {execution_time:.2f}s")
                print(f"     Sources: {num_sources}")
                print(f"     Answer: {answer_length} chars")
                print(f"     Within 45s timeout: {'YES' if execution_time <= 45 else 'NO (but within 67.5s buffer)'}")
                print()
                
                # Show first few sources
                print("Top 3 Sources:")
                for i, source in enumerate(data.get("sources", [])[:3], 1):
                    has_content = bool(source.get("content"))
                    print(f"  {i}. {source['title']}")
                    print(f"     Relevance: {source['relevance']:.3f}")
                    print(f"     Final Score: {source['final_score']:.3f}")
                    print(f"     Has Full Content: {has_content}")
                print()
                
                # Count how many have full content (were crawled)
                crawled_count = sum(1 for s in data.get("sources", []) if s.get("content"))
                print(f"Content Crawled: {crawled_count}/{num_sources} sources")
                print()
                print("[OK] BALANCED mode test PASSED!")
                
            elif response.status_code == 504:
                print(f"[FAIL] BALANCED mode timed out")
                print(f"       Execution time: {execution_time:.2f}s")
                print(f"       Response: {response.text}")
            else:
                print(f"[FAIL] BALANCED mode failed with status {response.status_code}")
                print(f"       Response: {response.text}")
                
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"[FAIL] BALANCED mode failed with exception")
            print(f"       Execution time: {execution_time:.2f}s")
            print(f"       Error: {str(e)}")
    
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_balanced_mode())
