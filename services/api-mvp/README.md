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

## Run with Docker Compose
See repo-level docker-compose.yaml. Ensure .env is populated (copy from .env.example).
