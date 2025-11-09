# API-only MVP Web Search Service

This service exposes minimal endpoints for web search and provider discovery.

## Endpoints
- GET /api/providers — list providers and models
- POST /api/search — perform web search and return textual answer with citations

## Env Vars
- OPENROUTER_API_KEY — required
- OPENROUTER_MODEL — default deepseek/deepseek-chat-v3.1:free
- SEARXNG_URL — default http://searxng:8080
- SERPERDEV_API_KEY — used for fallback SerperDev

### Advanced SearxNG Retrieval Tuning
The following optional env vars refine retrieval breadth & freshness. All are optional; sensible fallbacks are applied if unset.

- SEARXNG_ENGINES — Comma-separated engine whitelist (e.g. `bing,google,duckduckgo`). If unset, SearxNG default selection is used.
- SEARXNG_CATEGORIES — Comma-separated categories (e.g. `general,science,news,IT`). Helps diversify verticals.
- SEARXNG_LANGUAGE — ISO language code (e.g. `en`). If unset, defaults to English.
- SEARXNG_TIME_RANGE — Default recency window (e.g. `day`, `week`, `month`). Overridden when temporal intent is detected in the query.
- SEARXNG_PAGES — Integer number of paginated result pages to fetch per sub-query (>=1). More pages increases coverage & latency. Typical: 2–3.
- SEARXNG_BACKFILL_ENABLED — `true` / `false` (default `true`). When true, performs targeted vendor site backfill (aws.amazon.com, azure.microsoft.com, cloud.google.com) if canonical domains are missing from initial pages.

Tuning guidance:
1. Start with `SEARXNG_PAGES=2` to expand coverage with modest latency impact.
2. Add `SEARXNG_CATEGORIES=general,IT,science,news` for broader topical diversity.
3. Use `SEARXNG_TIME_RANGE=week` for scheduled daily runs unless you require ultra-fresh (`day`).
4. Disable backfill (`SEARXNG_BACKFILL_ENABLED=false`) only if vendor domains appear redundantly or latency constraints tighten.
5. Whitelist engines sparingly; letting SearxNG choose often yields better heterogeneity.

Temporal intent detection (e.g. phrases like "latest", "recent", specific months/years) will automatically narrow time_range even if a broader default is set.

## Run with Docker Compose
See repo-level docker-compose.yaml. Ensure .env is populated (copy from .env.example).
