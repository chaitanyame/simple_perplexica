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
    """Search via SerperDev with retry logic for transient failures."""
    if not SERPERDEV_API_KEY:
        logger.error("SerperDev API key not configured")
        raise RuntimeError("SERPERDEV_API_KEY not configured")

    headers = {"X-API-KEY": SERPERDEV_API_KEY, "Content-Type": "application/json"}

    try:
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
            logger.info(
                "SerperDev search completed",
                extra={"query": query, "result_count": len(results)},
            )
            return results
    except httpx.HTTPError as e:
        logger.error(
            "SerperDev HTTP error",
            extra={"query": query, "error": str(e), "url": SERPERDEV_URL},
            exc_info=True,
        )
        raise
    except Exception as e:
        logger.error(
            "SerperDev search failed",
            extra={"query": query, "error": str(e)},
            exc_info=True,
        )
        raise
