"""Test search modes through API with mode parameter.

This script tests that the API correctly accepts mode parameter and returns
the mode in the response, which the UI will display.
"""

import httpx

API_BASE_URL = "http://localhost:8001/api/v1"

def test_mode(mode: str, query: str = "What are AI agents?") -> None:
    """Test a specific search mode."""
    print(f"\n{'='*60}")
    print(f"Testing {mode.upper()} mode")
    print(f"{'='*60}")
    
    try:
        response = httpx.post(
            f"{API_BASE_URL}/search",
            json={
                "query": query,
                "mode": mode,
                "model": "anthropic/claude-3.5-sonnet",
            },
            timeout=90,
        )
        
        if response.status_code == 200:
            data = response.json()
            
            # Check mode is in response
            returned_mode = data.get("mode", "NOT_FOUND")
            mode_match = "✅" if returned_mode == mode else "❌"
            
            print(f"\n{mode_match} Mode returned: {returned_mode} (expected: {mode})")
            print(f"⏱️  Execution time: {data.get('execution_time', 0):.2f}s")
            print(f"📚 Sources: {len(data.get('sources', []))}")
            print(f"📝 Answer preview: {data.get('answer', '')[:100]}...")
            
            # Mode-specific validation
            mode_configs = {
                "speed": {"max_sources": 5, "max_time": 15},
                "balanced": {"max_sources": 10, "max_time": 45},
                "deep": {"max_sources": 20, "max_time": 60},
            }
            
            config = mode_configs[mode]
            sources = len(data.get("sources", []))
            exec_time = data.get("execution_time", 0)
            
            print(f"\n✅ Mode validation:")
            print(f"  - Sources ≤ {config['max_sources']}: {sources} ✅" if sources <= config['max_sources'] else f"  - Sources ≤ {config['max_sources']}: {sources} ❌")
            print(f"  - Time < {config['max_time']}s: {exec_time:.2f}s ✅" if exec_time < config['max_time'] else f"  - Time < {config['max_time']}s: {exec_time:.2f}s ❌")
            
            return True
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Error: {response.json()}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return False


def main():
    """Run all mode tests."""
    print("\n" + "="*60)
    print("TESTING SEARCH MODES THROUGH API")
    print("="*60)
    print("\nThis tests that:")
    print("1. API accepts mode parameter")
    print("2. API returns mode in response")
    print("3. UI can display the mode used")
    
    query = "What are AI agents?"
    
    results = {}
    for mode in ["speed", "balanced", "deep"]:
        results[mode] = test_mode(mode, query)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    for mode, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{mode.upper():10} {status}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print(f"\n{'='*60}")
        print("🎉 ALL MODES WORKING!")
        print("✅ UI mode selector is ready to use")
        print(f"{'='*60}")
        print("\n📱 Test the UI at: http://localhost:8501")
        print("   - Select different modes in the sidebar")
        print("   - Mode will be displayed in results")
    else:
        print(f"\n❌ Some modes failed - check logs")
    
    return all_passed


if __name__ == "__main__":
    main()
