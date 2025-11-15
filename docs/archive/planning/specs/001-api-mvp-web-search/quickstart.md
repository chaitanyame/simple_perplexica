# Quickstart: API-only MVP Web Search

## Run (Docker)

```bash
# Build and run the MVP API service (example port 3001)
docker build -t api-mvp ./services/api-mvp
docker run -p 3001:3001 --env-file .env api-mvp
```

## Test

```bash
# List providers
curl http://localhost:3001/api/providers

# Search
curl -X POST http://localhost:3001/api/search \
  -H 'Content-Type: application/json' \
  -d '{
    "focusMode": "webSearch",
    "query": "Latest sports headlines",
    "optimizationMode": "balanced"
  }'
```

## Notes
- Requires environment variables for OpenRouter and SearxNG/SerperDev.
- MVP returns textual answers with citations; no image/video payloads.
