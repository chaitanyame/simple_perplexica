import requests
import time

print("í´„ Testing Query Expansion Feature")
print("=" * 80)

# Start request
print("\ní³¤ Sending query: 'Python trends'")
print("   (This is ambiguous - could be programming language or snake)")

start = time.time()
response = requests.post(
    "http://localhost:8001/api/v1/search",
    json={"query": "Python trends", "mode": "speed"},
    timeout=120
)
elapsed = time.time() - start

if response.status_code == 200:
    data = response.json()
    print(f"\nâœ… Response received in {elapsed:.1f}s")
    print(f"   Session ID: {data['session_id']}")
    print(f"   Sources: {len(data['sources'])}")
    
    # Check diversity
    domains = [s['url'].split('/')[2] for s in data['sources']]
    unique = len(set(domains))
    print(f"   Domain diversity: {unique}/{len(domains)} ({100*unique/len(domains):.1f}%)")
    
    print("\ní³‹ Check Docker logs for:")
    print(f"   docker logs research_api 2>&1 | grep -E 'EXPANSION|sub_queries' | tail -30")
    
else:
    print(f"\nâŒ Error {response.status_code}")
    print(response.text[:500])
