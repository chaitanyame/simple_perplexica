#!/usr/bin/env python3
"""
Test Two-Pass Synthesis with DeepSeek R1 Regeneration

This script tests the two-pass synthesis implementation by sending queries
that are likely to trigger hallucinations, forcing regeneration.
"""

import httpx
import time
import json
from datetime import datetime


# Test queries designed to trigger hallucinations
TEST_QUERIES = [
    {
        "name": "Future Events (High Hallucination Risk)",
        "query": "What are the major features announced at Microsoft Build 2026?",
        "expected": "Should detect hallucinations about future events and regenerate",
    },
    {
        "name": "Obscure Technical Details",
        "query": "What are the exact performance benchmarks of Python 3.13 beta 2?",
        "expected": "May hallucinate specific numbers, should regenerate if detected",
    },
    {
        "name": "Recent News (Control)",
        "query": "What are the latest developments in AI safety research?",
        "expected": "Should have good sources, likely no regeneration needed",
    },
]


def test_two_pass_synthesis():
    """Test the two-pass synthesis implementation."""
    print("=" * 80)
    print("TWO-PASS SYNTHESIS TEST")
    print("=" * 80)
    print(f"Testing at: {datetime.now().isoformat()}\n")

    api_url = "http://localhost:8000/api/v1/search"

    for i, test in enumerate(TEST_QUERIES, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {i}/{len(TEST_QUERIES)}: {test['name']}")
        print(f"{'=' * 80}")
        print(f"Query: {test['query']}")
        print(f"Expected: {test['expected']}\n")

        try:
            start_time = time.time()

            # Send request
            with httpx.Client(timeout=120.0) as client:
                response = client.post(
                    api_url, json={"query": test["query"], "mode": "search", "max_sources": 10}
                )

            elapsed = time.time() - start_time

            if response.status_code == 200:
                result = response.json()

                print(f"✅ SUCCESS (took {elapsed:.1f}s)")
                print(f"\n📊 METRICS:")
                print(f"   - Session ID: {result.get('session_id', 'N/A')}")
                print(f"   - Sources: {len(result.get('sources', []))}")
                print(f"   - Answer Length: {len(result.get('answer', ''))} chars")

                # Check for grounding metrics (if present)
                if "grounding_score" in result:
                    print(f"   - Grounding Score: {result['grounding_score']:.2f}/1.0")

                if "hallucination_count" in result:
                    print(f"   - Hallucination Count: {result['hallucination_count']}")

                # Display answer preview
                answer = result.get("answer", "")
                preview = answer[:300] + "..." if len(answer) > 300 else answer
                print(f"\n📝 ANSWER PREVIEW:")
                print(f"   {preview}")

                # Check logs for regeneration (would need docker logs)
                print(f"\n💡 TIP: Check docker logs for regeneration details:")
                print(f"   docker logs research_api | grep -A 5 'REGENERATION'")

            else:
                print(f"❌ FAILED: HTTP {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"❌ ERROR: {e}")

        # Pause between tests
        if i < len(TEST_QUERIES):
            print(f"\nWaiting 2s before next test...")
            time.sleep(2)

    print(f"\n{'=' * 80}")
    print("TEST COMPLETE")
    print(f"{'=' * 80}")
    print("\n📋 NEXT STEPS:")
    print("1. Review answers above for quality")
    print("2. Check docker logs: docker logs research_api | grep 'REGENERATION'")
    print("3. Look for '🔄 PASS 2: REGENERATING' in logs")
    print("4. Compare grounding scores before/after regeneration")
    print("\n📈 MONITORING:")
    print("- Track regeneration frequency over 7 days")
    print("- Measure average improvement in grounding scores")
    print("- Calculate cost savings (should be $0 with free models)")


if __name__ == "__main__":
    test_two_pass_synthesis()
