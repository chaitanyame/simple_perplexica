"""Test that LLM responses now include specific details from sources.

This tests the fix for generic responses that don't explain specific items.
"""

import httpx

API_BASE_URL = "http://localhost:8001/api/v1"

def test_specific_details():
    """Test that responses extract and explain specific details from sources."""
    
    print("\n" + "="*70)
    print("🧪 TESTING SPECIFIC DETAIL EXTRACTION")
    print("="*70)
    
    # Use the exact query from the screenshot
    query = "recent news about Microsoft Azure"
    mode = "deep"
    
    print(f"\nQuery: {query}")
    print(f"Mode: {mode.upper()}")
    print(f"\n{'─'*70}")
    print("Sending request...")
    
    try:
        response = httpx.post(
            f"{API_BASE_URL}/search",
            json={
                "query": query,
                "mode": mode,
                "model": "anthropic/claude-3.5-sonnet",
            },
            timeout=120,
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "")
            sources = data.get("sources", [])
            
            # Metrics
            char_count = len(answer)
            word_count = len(answer.split())
            citation_count = answer.count('[')
            
            print(f"\n📊 Response Metrics:")
            print(f"  - Characters: {char_count}")
            print(f"  - Words: {word_count}")
            print(f"  - Citations: {citation_count}")
            print(f"  - Sources: {len(sources)}")
            print(f"  - Execution time: {data.get('execution_time', 0):.2f}s")
            
            # Check for specific indicators of detail
            indicators = {
                "Has dates": any(x in answer.lower() for x in ['2025', 'november', 'january', 'february']),
                "Has specific names": any(x in answer for x in ['Microsoft', 'Azure', 'Ignite', 'Build']),
                "Has numbers": any(char.isdigit() for char in answer),
                "Has citations": citation_count >= 10,
                "Has structure": any(x in answer for x in ['1.', '2.', '3.', '•', '-']),
                "Long enough": word_count >= 300,
            }
            
            print(f"\n✅ Quality Indicators:")
            for indicator, present in indicators.items():
                status = "✅" if present else "❌"
                print(f"  {status} {indicator}")
            
            # Show the answer
            print(f"\n{'='*70}")
            print("📝 FULL ANSWER:")
            print(f"{'='*70}")
            print(answer)
            print(f"{'='*70}")
            
            # Validation
            passed = sum(indicators.values()) >= 5  # At least 5/6 indicators
            
            if passed:
                print(f"\n✅ PASS - Response includes specific details")
            else:
                print(f"\n❌ FAIL - Response is too generic")
                print(f"   Only {sum(indicators.values())}/6 quality indicators present")
            
            return passed
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Error: {response.json()}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_specific_details()
    exit(0 if success else 1)
