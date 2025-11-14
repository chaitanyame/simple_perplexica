#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test Query Expansion Feature."""

import requests
import time

print("Testing Query Expansion Feature")
print("=" * 80)

# Test 1: Ambiguous term
print("\nTest 1: Ambiguous query 'Python trends'")
print("Expected: Should expand to 'Python programming language trends'")

start = time.time()
response = requests.post(
    "http://localhost:8001/api/v1/search",
    json={"query": "Python trends", "mode": "speed"},
    timeout=120,
)
elapsed = time.time() - start

if response.status_code == 200:
    data = response.json()
    print(f"\nResponse received in {elapsed:.1f}s")
    print(f"Session ID: {data['session_id']}")
    print(f"Sources: {len(data['sources'])}")

    # Check diversity
    domains = [s["url"].split("/")[2] for s in data["sources"]]
    unique = len(set(domains))
    print(f"Domain diversity: {unique}/{len(domains)} ({100 * unique / len(domains):.1f}%)")

    # Show first 3 source titles
    print("\nFirst 3 source titles:")
    for i, source in enumerate(data["sources"][:3], 1):
        print(f"  {i}. {source['title'][:80]}")

    print("\nTo see query expansion in logs:")
    print("  docker logs research_api 2>&1 | grep -E 'EXPANSION|sub_queries' | tail -30")

else:
    print(f"\nError {response.status_code}")
    print(response.text[:500])
