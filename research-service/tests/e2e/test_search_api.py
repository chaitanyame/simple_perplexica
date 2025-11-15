#!/usr/bin/env python3
"""Quick test script to see the actual error from the API."""

import httpx
import json

API_URL = "http://localhost:8001/api/v1/search"

payload = {"query": "what is pydantic ai", "max_sources": 20, "timeout": 60}

print("🔍 Testing Search API...")
print(f"URL: {API_URL}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\n" + "=" * 50 + "\n")

try:
    response = httpx.post(API_URL, json=payload, timeout=30)

    print(f"Status Code: {response.status_code}")
    print(f"\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")

    print(f"\nResponse Body:")
    try:
        json_response = response.json()
        print(json.dumps(json_response, indent=2))
    except:
        print(response.text)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback

    traceback.print_exc()
