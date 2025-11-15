import httpx
import os
import logging
from typing import List, Dict
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

SERPERDEV_API_KEY = os.getenv("SERPER_API_KEY") or os.getenv("SERPERDEV_API_KEY")
SERPERDEV_URL = os.getenv("SERPERDEV_URL", "https://google.serper.dev/search")
logger = logging.getLogger(__name__)


def is_available() -> bool:
    """Check if SerperDev is properly configured."""
    return bool(SERPERDEV_API_KEY)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.HTTPError, httpx.TimeoutException)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
)
async def search(query: str) -> List[Dict]:
    """Search via SerperDev with retry logic for transient failures.

    Sends a JSON body aligned with Serper.dev requirements:
    {"q": str, "gl": str, "hl": str, "num": int}
    """
    if not SERPERDEV_API_KEY:
        logger.error("SerperDev API key not configured")
        raise RuntimeError("SERPERDEV_API_KEY not configured")

    q = (query or "").strip()
    if not q:
        logger.warning("Empty query passed to SerperDev; returning empty result set")
        return []

    headers = {"X-API-KEY": SERPERDEV_API_KEY, "Content-Type": "application/json"}

    # Conservative, widely accepted defaults
    payload = {"q": q, "gl": "us", "hl": "en", "num": 10}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(SERPERDEV_URL, json=payload, headers=headers)
            try:
                r.raise_for_status()
            except httpx.HTTPStatusError as _:
                # Log full response body for 4xx diagnostics
                body = None
                try:
                    body = r.json()
                except Exception:
                    body = r.text
                logger.error(
                    "SerperDev HTTP status error",
                    extra={
                        "status": r.status_code,
                        "body": body,
                        "url": SERPERDEV_URL,
                        "payload": payload,
                    },
                    exc_info=True,
                )
                raise
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
            logger.info(
                "SerperDev search completed",
                extra={"query": q, "result_count": len(results)},
            )
            return results
    except httpx.HTTPError as e:
        logger.error(
            "SerperDev HTTP error",
            extra={"query": q, "error": str(e), "url": SERPERDEV_URL},
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            "SerperDev search failed",
            extra={"query": q, "error": str(e)},
            exc_info=True,
        )
        raise
