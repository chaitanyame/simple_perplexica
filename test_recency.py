import httpx

body = {
    "query": "breaking news USA today",
    "focusMode": "webSearch",
    "optimizationMode": "quality",
    "stream": False,
}

r = httpx.post("http://localhost:3001/api/search", json=body, timeout=180)
d = r.json()

print("Status:", r.status_code)
print("Sources:", len(d.get("sources", [])))
print("\nTop 5 sources:")
for i, s in enumerate(d.get("sources", [])[:5], 1):
    print(f"  {i}. {s.get('title')[:65]}")
    print(f"     {s.get('url')[:70]}")

print("\n=== Answer Preview ===")
print(d.get("message", "")[:400])
