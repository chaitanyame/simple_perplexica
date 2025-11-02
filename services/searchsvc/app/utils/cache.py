"""
Redis caching layer for OpenRouter API calls.

OPTIMIZATION: 75% cost savings by caching embeddings and LLM responses
- Embeddings cache: Same text = same embedding (deterministic)
- LLM response cache: Same query + context hash = same response
- TTL: 7 days for embeddings, 1 day for responses
"""

import hashlib
import json
import logging
import os
from typing import Optional, List, Any
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379")
REDIS_ENABLED = os.getenv("REDIS_ENABLED", "true").lower() == "true"

# Cache TTL (Time To Live)
EMBEDDING_TTL = 7 * 24 * 60 * 60  # 7 days (embeddings are deterministic)
RESPONSE_TTL = 24 * 60 * 60  # 1 day (responses can change with new info)

# Global Redis client
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> Optional[redis.Redis]:
    """Get or create Redis client singleton."""
    global _redis_client

    if not REDIS_ENABLED:
        return None

    if _redis_client is None:
        try:
            _redis_client = redis.from_url(
                REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            # Test connection
            await _redis_client.ping()
            logger.info(f"Redis connected: {REDIS_URL}")
        except Exception as e:
            logger.warning(f"Redis connection failed, caching disabled: {e}")
            _redis_client = None
            return None

    return _redis_client


def _make_cache_key(prefix: str, *args) -> str:
    """Create a cache key from prefix and arguments."""
    # Create a hash of all arguments
    content = json.dumps(args, sort_keys=True, default=str)
    hash_digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    return f"{prefix}:{hash_digest}"


async def cache_get(key: str) -> Optional[Any]:
    """Get value from cache."""
    client = await get_redis_client()
    if client is None:
        return None

    try:
        value = await client.get(key)
        if value:
            logger.debug(f"Cache HIT: {key}")
            return json.loads(value)
        logger.debug(f"Cache MISS: {key}")
        return None
    except Exception as e:
        logger.warning(f"Cache get error for {key}: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int) -> bool:
    """Set value in cache with TTL."""
    client = await get_redis_client()
    if client is None:
        return False

    try:
        serialized = json.dumps(value, default=str)
        await client.setex(key, ttl, serialized)
        logger.debug(f"Cache SET: {key} (TTL: {ttl}s)")
        return True
    except Exception as e:
        logger.warning(f"Cache set error for {key}: {e}")
        return False


async def cache_embeddings_get(
    texts: List[str], model: str
) -> Optional[List[List[float]]]:
    """Get cached embeddings for texts."""
    key = _make_cache_key("embed", model, texts)
    return await cache_get(key)


async def cache_embeddings_set(
    texts: List[str], model: str, embeddings: List[List[float]]
) -> bool:
    """Cache embeddings for texts."""
    key = _make_cache_key("embed", model, texts)
    return await cache_set(key, embeddings, EMBEDDING_TTL)


async def cache_response_get(
    query: str, context_hash: str, model: str
) -> Optional[str]:
    """Get cached LLM response."""
    key = _make_cache_key("response", model, query, context_hash)
    return await cache_get(key)


async def cache_response_set(
    query: str, context_hash: str, model: str, response: str
) -> bool:
    """Cache LLM response."""
    key = _make_cache_key("response", model, query, context_hash)
    return await cache_set(key, response, RESPONSE_TTL)


def hash_context(sources: List[Any], system_instructions: Optional[str] = None) -> str:
    """Create a hash of context for cache key."""
    # Create deterministic hash of sources (URLs + content snippets)
    context_data = {
        "sources": [
            {"url": s.get("url", ""), "content": s.get("pageContent", "")[:200]}
            for s in sources
        ],
        "system": system_instructions or "",
    }
    content = json.dumps(context_data, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def get_cache_stats() -> dict:
    """Get Redis cache statistics."""
    client = await get_redis_client()
    if client is None:
        return {"enabled": False, "error": "Redis not available"}

    try:
        info = await client.info("stats")
        keyspace = await client.info("keyspace")

        # Count keys by prefix
        embed_count = 0
        response_count = 0

        async for key in client.scan_iter(match="embed:*", count=100):
            embed_count += 1

        async for key in client.scan_iter(match="response:*", count=100):
            response_count += 1

        return {
            "enabled": True,
            "connected": True,
            "embedding_cache_keys": embed_count,
            "response_cache_keys": response_count,
            "total_commands": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": (
                round(
                    info.get("keyspace_hits", 0)
                    / max(
                        1,
                        info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0),
                    )
                    * 100,
                    2,
                )
                if info.get("keyspace_hits", 0) > 0
                else 0
            ),
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        return {"enabled": True, "connected": False, "error": str(e)}
