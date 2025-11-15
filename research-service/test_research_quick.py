#!/usr/bin/env python3
"""Quick test for research endpoint."""

import requests
import json
import sys


def test_research_endpoint():
    """Test the research API endpoint."""
    url = "http://localhost:8001/api/v1/research"

    payload = {"query": "What is Python?", "mode": "balanced", "max_iterations": 1, "timeout": 120}

    print("🧪 Testing research endpoint...")
    print(f"📤 Query: {payload['query']}")
    print(f"⚙️  Mode: {payload['mode']}")
    print()

    try:
        response = requests.post(url, json=payload, timeout=180)

        print(f"📊 Status Code: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS - Research query completed!")
            print()
            print(f"📝 Plan Steps: {len(data.get('plan', {}).get('steps', []))}")
            print(f"📚 Citations: {len(data.get('citations', []))}")
            print(f"⏱️  Execution Time: {data.get('execution_time', 0):.2f}s")
            print(f"🎯 Confidence: {data.get('confidence', 0):.2f}")
            print()
            print("📄 Findings Preview:")
            findings = data.get("findings", "")
            print(findings[:300] + "..." if len(findings) > 300 else findings)
            return True
        else:
            print(f"❌ FAILED - Status {response.status_code}")
            print("Error:", response.text[:500])
            return False

    except requests.exceptions.Timeout:
        print("⏰ TIMEOUT - Request took too long")
        return False
    except Exception as e:
        print(f"❌ ERROR - {type(e).__name__}: {str(e)}")
        return False


if __name__ == "__main__":
    success = test_research_endpoint()
    sys.exit(0 if success else 1)
