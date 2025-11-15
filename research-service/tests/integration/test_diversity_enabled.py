import requests
import json

# Test diversity enabled by default
response = requests.post(
    "http://localhost:8001/api/v1/search",
    json={"query": "Is AI dangerous?", "mode": "speed"}
)

data = response.json()
print("Session:", data["session_id"])
print("\nAnswer length:", len(data["answer"]), "chars")
print("\nSources:", len(data["sources"]))

domains = [s["url"].split("/")[2] for s in data["sources"]]
unique = len(set(domains))
total = len(domains)
diversity_pct = 100 * unique / total if total > 0 else 0

print(f"\nDiversity metrics:")
print(f"  Unique domains: {unique}/{total} ({diversity_pct:.1f}%)")
print(f"  Expected: >70% (target for diversity enabled)")

if diversity_pct >= 70:
    print(f"\n✅ PASS: Diversity {diversity_pct:.1f}% >= 70%")
else:
    print(f"\n⚠️  WARNING: Diversity {diversity_pct:.1f}% < 70%")

print("\nTop domains:")
for d in sorted(set(domains))[:10]:
    count = domains.count(d)
    print(f"  - {d} ({count}x)")
