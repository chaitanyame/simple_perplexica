import asyncio
import re
from typing import Dict, List, Optional

import httpx


def _strip_html(html: str) -> str:
    # Remove script and style blocks
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    # Remove all tags
    text = re.sub(r"<[^>]+>", " ", html)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def _fetch_text(
    url: str, timeout_sec: float = 10.0, max_bytes: int = 300_000
) -> Optional[str]:
    if not url:
        return None
    try:
        async with httpx.AsyncClient(
            timeout=timeout_sec,
            follow_redirects=True,
            headers={
                "User-Agent": "simple-perplexica/0.1 (+https://github.com/chaitanyame/simple_perplexica)"
            },
        ) as client:
            r = await client.get(url)
            if r.status_code >= 400:
                return None
            ctype = r.headers.get("content-type", "").lower()
            if "text/html" not in ctype and "xml" not in ctype and "text/" not in ctype:
                return None
            content = r.text
            if len(content) > max_bytes:
                content = content[:max_bytes]
            return _strip_html(content)
    except Exception:
        return None


async def enrich_sources_with_content(
    sources: List[Dict], limit: int = 20, timeout_sec: float = 10.0
) -> List[Dict]:
    if not sources:
        return sources
    # Only fetch for the first N to bound latency
    targets = sources[: max(1, limit)]

    async def _enrich(s: Dict) -> Dict:
        # Skip if we already have decent content
        content = s.get("pageContent") or ""
        if len(content) >= 300:
            return s
        text = await _fetch_text(s.get("url", ""), timeout_sec=timeout_sec)
        if text:
            s = dict(s)
            s["pageContent"] = text
        return s

    enriched = await asyncio.gather(*[_enrich(s) for s in targets])
    # Merge back
    out = list(sources)
    out[: len(enriched)] = enriched
    return out
