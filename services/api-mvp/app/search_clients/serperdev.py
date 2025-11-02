import httpx
import os
from typing import List, Dict

SERPERDEV_API_KEY = os.getenv("SERPERDEV_API_KEY")
SERPERDEV_URL = os.getenv("SERPERDEV_URL", "https://google.serper.dev/search")


async def search(query: str) -> List[Dict]:
    if not SERPERDEV_API_KEY:
        raise RuntimeError("SERPERDEV_API_KEY not configured")
    headers = {"X-API-KEY": SERPERDEV_API_KEY, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.post(SERPERDEV_URL, json={"q": query}, headers=headers)
        r.raise_for_status()
        data = r.json()
        results = []
        for item in data.get("organic", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "pageContent": item.get("snippet", ""),
                }
            )
        return results
