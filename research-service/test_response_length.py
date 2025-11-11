"""Test that LLM responses are now longer and more detailed.

This script tests the fix for short LLM-generated content.
"""

import httpx

API_BASE_URL = "http://localhost:8001/api/v1"

def test_response_length():
    """Test that responses are now longer and more detailed."""
    
    print("\n" + "="*70)
    print("🧪 TESTING LLM RESPONSE LENGTH FIX")
    print("="*70)
    
    test_cases = [
        {
            "mode": "balanced",
            "query": "Explain how AI agents work and their key components",
            "expected_min_words": 250,  # ~300-500 words requested
        },
        {
            "mode": "deep",
            "query": "Compare different AI agent frameworks and their architectures",
            "expected_min_words": 250,
        },
    ]
    
    results = []
    
    for idx, test in enumerate(test_cases, 1):
        print(f"\n{'─'*70}")
        print(f"Test {idx}/{len(test_cases)}: {test['mode'].upper()} Mode")
        print(f"Query: {test['query']}")
        print(f"{'─'*70}")
        
        try:
            response = httpx.post(
                f"{API_BASE_URL}/search",
                json={
                    "query": test['query'],
                    "mode": test['mode'],
                    "model": "anthropic/claude-3.5-sonnet",
                },
                timeout=90,
            )
            
            if response.status_code == 200:
                data = response.json()
                answer = data.get("answer", "")
                
                # Calculate metrics
                char_count = len(answer)
                word_count = len(answer.split())
                line_count = len(answer.split('\n'))
                
                print(f"\n📊 Response Metrics:")
                print(f"  - Characters: {char_count}")
                print(f"  - Words: {word_count}")
                print(f"  - Lines: {line_count}")
                print(f"  - Execution time: {data.get('execution_time', 0):.2f}s")
                print(f"  - Sources used: {len(data.get('sources', []))}")
                
                # Validation
                min_words = test['expected_min_words']
                
                if word_count >= min_words:
                    status = "✅ PASS"
                    print(f"\n{status} - Response is detailed ({word_count} >= {min_words} words)")
                else:
                    status = "❌ FAIL"
                    print(f"\n{status} - Response too short ({word_count} < {min_words} words)")
                
                # Show preview
                print(f"\n📝 Answer Preview (first 300 chars):")
                print(f"  {answer[:300]}...")
                
                results.append({
                    "mode": test['mode'],
                    "words": word_count,
                    "expected": min_words,
                    "passed": word_count >= min_words,
                })
            else:
                print(f"❌ Request failed: {response.status_code}")
                print(f"Error: {response.json()}")
                results.append({
                    "mode": test['mode'],
                    "words": 0,
                    "expected": min_words,
                    "passed": False,
                })
                
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")
            results.append({
                "mode": test['mode'],
                "words": 0,
                "expected": min_words,
                "passed": False,
            })
    
    # Summary
    print(f"\n{'='*70}")
    print("📊 SUMMARY")
    print(f"{'='*70}")
    
    for result in results:
        status = "✅" if result['passed'] else "❌"
        print(f"{status} {result['mode'].upper():10} - {result['words']} words (expected: >={result['expected']})")
    
    passed_count = sum(1 for r in results if r['passed'])
    total_count = len(results)
    
    print(f"\n{'='*70}")
    if passed_count == total_count:
        print(f"🎉 ALL TESTS PASSED ({passed_count}/{total_count})")
        print("✅ LLM responses are now longer and more detailed!")
    else:
        print(f"⚠️ SOME TESTS FAILED ({passed_count}/{total_count} passed)")
        print("Check the prompts and max_tokens settings")
    print(f"{'='*70}\n")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = test_response_length()
    exit(0 if success else 1)
