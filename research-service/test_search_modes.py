"""Test script for search modes (SPEED/BALANCED/DEEP).

Tests the same query across all 3 modes to verify:
1. Different performance characteristics (execution time)
2. Different numbers of sources returned
3. Different behaviors (crawling, reranking, RAG)
4. Proper configuration application

Usage:
    python test_search_modes.py
"""

import asyncio
import time
from typing import Any

import httpx

# Test configuration
API_BASE_URL = "http://localhost:8001"
TEST_QUERY = "What are transformer neural networks and how do they work?"

# Expected behaviors by mode
EXPECTED_BEHAVIORS = {
    "speed": {
        "max_sources": 5,
        "timeout": 15,
        "enable_reranking": False,
        "enable_crawling": False,
        "description": "⚡ Fast results, snippets only",
    },
    "balanced": {
        "max_sources": 10,
        "timeout": 30,
        "enable_reranking": True,
        "enable_crawling": True,
        "description": "⚖️ Balanced quality & speed",
    },
    "deep": {
        "max_sources": 20,
        "timeout": 60,
        "enable_reranking": True,
        "enable_crawling": True,
        "description": "🔍 Deep research with full content",
    },
}


async def test_search_mode(
    client: httpx.AsyncClient,
    mode: str,
) -> dict[str, Any]:
    """Test a single search mode.
    
    Args:
        client: HTTP client
        mode: Mode to test (speed/balanced/deep)
        
    Returns:
        Test results dictionary
    """
    expected = EXPECTED_BEHAVIORS[mode]
    
    start_time = time.time()
    
    try:
        response = await client.post(
            f"{API_BASE_URL}/api/v1/search",
            json={
                "query": TEST_QUERY,
                "mode": mode,
            },
            timeout=90.0,  # Allow time for all modes
        )
        
        execution_time = time.time() - start_time
        
        if response.status_code != 200:
            return {
                "mode": mode,
                "success": False,
                "error": response.text,
                "execution_time": execution_time,
            }
        
        data = response.json()
        num_sources = len(data.get("sources", []))
        
        # Validate results
        validation = {
            "correct_source_count": num_sources <= expected["max_sources"],
            "has_answer": bool(data.get("answer")),
            "has_sources": num_sources > 0,
            "within_timeout": execution_time <= expected["timeout"] * 1.5,  # Allow 50% buffer
        }
        
        result = {
            "mode": mode,
            "success": True,
            "execution_time": execution_time,
            "num_sources": num_sources,
            "expected_max_sources": expected["max_sources"],
            "expected_timeout": expected["timeout"],
            "has_answer": validation["has_answer"],
            "answer_length": len(data.get("answer", "")),
            "validation": validation,
            "all_validations_passed": all(validation.values()),
        }
        
        return result
        
    except Exception as e:
        execution_time = time.time() - start_time
        return {
            "mode": mode,
            "success": False,
            "error": str(e),
            "execution_time": execution_time,
        }


async def main():
    """Run all mode tests."""
    print("=" * 80)
    print("Testing Search Modes: SPEED / BALANCED / DEEP")
    print("=" * 80)
    print(f"Query: {TEST_QUERY}")
    print(f"API: {API_BASE_URL}")
    print()
    
    async with httpx.AsyncClient() as client:
        # Test all modes
        results = {}
        for mode in ["speed", "balanced", "deep"]:
            print(f"\n{'─' * 80}")
            print(f"Testing {mode.upper()} mode...")
            print(f"{'─' * 80}")
            
            result = await test_search_mode(client, mode)
            results[mode] = result
            
            # Print summary
            if result["success"]:
                print(f"[OK] {mode.upper()} - Completed in {result['execution_time']:.2f}s")
                print(f"     Sources: {result['num_sources']} (max: {result['expected_max_sources']})")
                print(f"     Answer: {result['answer_length']} chars")
                print(f"     Expected timeout: {result['expected_timeout']}s")
                
                # Validation details
                if result["all_validations_passed"]:
                    print(f"     All validations passed")
                else:
                    print(f"     Some validations failed:")
                    for check, passed in result["validation"].items():
                        status = "[OK]" if passed else "[FAIL]"
                        print(f"      {status} {check}")
            else:
                print(f"[FAIL] {mode.upper()} - Failed")
                print(f"       Error: {result.get('error', 'Unknown error')}")
            
            print()
            
            # Wait between tests to avoid rate limiting
            if mode != "deep":
                print("Waiting 2s before next test...")
                await asyncio.sleep(2)
    
    # Print final summary
    print("\n" + "=" * 80)
    print("Final Summary")
    print("=" * 80)
    
    for mode, result in results.items():
        if result["success"]:
            status = "[OK]" if result["all_validations_passed"] else "[WARN]"
            print(f"{status} {mode.upper():8} | {result['execution_time']:6.2f}s | "
                  f"{result['num_sources']:2} sources | "
                  f"{result['answer_length']:4} chars")
        else:
            print(f"[FAIL] {mode.upper():8} | FAILED")
    
    print("=" * 80)
    
    # Calculate performance comparison
    if all(r["success"] for r in results.values()):
        speed_time = results["speed"]["execution_time"]
        balanced_time = results["balanced"]["execution_time"]
        deep_time = results["deep"]["execution_time"]
        
        print("\nPerformance Comparison:")
        print(f"   SPEED vs BALANCED: {balanced_time / speed_time:.1f}x slower")
        print(f"   SPEED vs DEEP:     {deep_time / speed_time:.1f}x slower")
        print(f"   BALANCED vs DEEP:  {deep_time / balanced_time:.1f}x slower")
        
        print("\nSource Count Comparison:")
        print(f"   SPEED:    {results['speed']['num_sources']} sources")
        print(f"   BALANCED: {results['balanced']['num_sources']} sources")
        print(f"   DEEP:     {results['deep']['num_sources']} sources")
    
    print("\n[OK] Mode testing complete!")


if __name__ == "__main__":
    asyncio.run(main())
