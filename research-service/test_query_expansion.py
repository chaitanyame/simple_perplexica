import requests
import json

# Test query expansion with ambiguous term
response = requests.post(
    "http://localhost:8001/api/v1/search",
    json={"query": "Is AI dangerous?", "mode": "speed"}
)

print("Testing Query Expansion Feature")
print("=" * 80)

if response.status_code == 200:
    data = response.json()
    print(f"\n‚úÖ Query: 'Is AI dangerous?'")
    print(f"Session ID: {data['session_id']}")
    print(f"\nAnswer length: {len(data['answer'])} chars")
    print(f"Sources: {len(data['sources'])}")
    
    # Check for diversity in domains
    domains = [s['url'].split('/')[2] for s in data['sources']]
    unique_domains = len(set(domains))
    print(f"Unique domains: {unique_domains}/{len(domains)} ({100*unique_domains/len(domains):.1f}%)")
    
    # Sample answer
    print(f"\nAnswer preview:")
    print(data['answer'][:300] + "...")
    
    print("\nÌ≥ä Query Expansion Impact:")
    print("  - Expected: Multiple sub-queries with term variations")
    print("  - Expected: 'AI', 'artificial intelligence', 'machine learning' variations")
    print("  - Expected: 20-30% broader source coverage")
    
else:
    print(f"‚ùå Error: {response.status_code}")
    print(response.text)
