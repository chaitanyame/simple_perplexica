# Migration Guide: Legacy Services to Research Service

**Date:** November 15, 2025  
**Branch:** feature/research-service-standalone

---

## Overview

The legacy services in `services/` directory have been removed and replaced with the mature `research-service/` implementation. This guide helps you migrate from the old endpoints to the new architecture.

---

## What Changed

### Removed Services

1. **services/searchsvc/** - Legacy web search API
   - Port: 3000/3001
   - Status: **REMOVED**
   - Replacement: `research-service/` search endpoints

2. **services/researchsvc/** - Legacy CrewAI research service
   - Port: 3002
   - Status: **REMOVED**
   - Replacement: `research-service/` research endpoints

3. **services/searchsvc/tools/** - Legacy Streamlit UI
   - Port: 8501
   - Status: **REMOVED**
   - Replacement: `research-service/streamlit_ui.py`

### Kept Services

1. **searxng** - Search engine (shared)
   - Port: 8080
   - Status: **ACTIVE** - Used by research-service

2. **redis** - Cache layer (shared)
   - Port: 6379
   - Status: **ACTIVE** - Used by research-service

---

## Port Migration

| Old Endpoint | New Endpoint | Service |
|--------------|--------------|---------|
| `http://localhost:3000` | `http://localhost:8001` | Search API |
| `http://localhost:3001` | `http://localhost:8001` | Search API (internal) |
| `http://localhost:3002` | `http://localhost:8001/api/v1/research` | Research API |
| `http://localhost:8501` | `http://localhost:8501` | Streamlit UI (research-service) |

---

## API Endpoint Migration

### Search Endpoints

**Old (services/searchsvc/):**
```bash
POST http://localhost:3000/api/search
```

**New (research-service/):**
```bash
POST http://localhost:8001/api/v1/search
```

### Research Endpoints

**Old (services/researchsvc/):**
```bash
POST http://localhost:3002/api/generate
```

**New (research-service/):**
```bash
POST http://localhost:8001/api/v1/research
```

---

## Docker Compose Migration

### Old Setup (Root docker-compose.yaml)

```bash
# Start all services including legacy API
docker-compose up
```

Services included: api, researchsvc, ui, searxng, redis

### New Setup (Split Architecture)

**1. Start shared services (root):**
```bash
# Start SearxNG and Redis
docker-compose up -d
```

**2. Start research-service:**
```bash
# Start research API and UI
cd research-service
docker-compose up -d
```

---

## Environment Variables

No changes needed! The research-service uses the same environment variables:
- `OPENROUTER_API_KEY`
- `OPENROUTER_MODEL`
- `SEARXNG_URL`
- `SERPER_API_KEY`
- `REDIS_URL`

---

## Feature Comparison

| Feature | Legacy Services | Research Service |
|---------|----------------|------------------|
| **Framework** | FastAPI + CrewAI | FastAPI + Pydantic AI |
| **Search** | SearxNG + SerperDev | SearxNG + SerperDev + Perplexity |
| **Document Processing** | None | Dockling (PDF/Excel/Word) |
| **Web Crawling** | Basic BeautifulSoup | Crawl4AI (advanced) |
| **Vector Search** | None | pgvector + Sentence-Transformers |
| **Database** | None | PostgreSQL + pgvector |
| **Caching** | Redis | Redis (port 6380) |
| **Monitoring** | None | Langfuse |
| **Test Coverage** | ~60% | 85% (134 tests) |
| **Agents** | 2 basic agents | 4+ specialized agents |

---

## Quick Start (New Architecture)

1. **Start shared services:**
```bash
docker-compose up -d
```

2. **Start research-service:**
```bash
cd research-service
docker-compose up -d
```

3. **Access services:**
- API: http://localhost:8001
- API Docs: http://localhost:8001/docs
- Streamlit UI: http://localhost:8501
- SearxNG: http://localhost:8080
- Redis: localhost:6379

4. **Test the API:**
```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are AI agents?",
    "max_sources": 20
  }'
```

---

## Legacy Code Preservation

The legacy services are preserved in git branch:
```bash
git checkout archive/legacy-services-2025-11-15
```

You can browse the old code, but it is no longer actively maintained.

---

## Getting Help

- **Documentation**: `research-service/docs/`
- **Roadmap**: `research-service/ROADMAP.md`
- **Development Standards**: `.github/copilot-instructions.md`
- **Architecture**: `docs/architecture/`

---

## Why Migrate?

✅ **More Features**: RAG, document processing, advanced crawling  
✅ **Better Testing**: 85% coverage vs ~60%  
✅ **Modern Stack**: Pydantic AI > CrewAI  
✅ **Active Development**: Phase 2 Week 5 progress  
✅ **Production Ready**: Comprehensive docs, monitoring, error handling

---

**Questions?** Check `research-service/docs/INDEX.md` for comprehensive documentation.
