# Research Service

Advanced search and research service with multi-agent architecture using Pydantic AI.

## Features

- **Fast Search Mode**: 30-60 second responses with multi-query decomposition
- **Deep Research Mode**: 2-5 minute comprehensive reports with iterative refinement
- **Pydantic AI Agents**: Structured agent framework for specialized tasks
- **RAG System**: PostgreSQL + pgvector for semantic memory
- **Document Extraction**: Dockling for PDF, Excel, Word
- **Web Crawling**: Crawl4AI for deep website data extraction
- **LLM Monitoring**: Langfuse integration for all agent runs

## Architecture

```
research-service/
├── src/                    # Source code
│   ├── api/               # FastAPI endpoints
│   ├── agents/            # Pydantic AI agents
│   ├── services/          # External service clients
│   ├── database/          # PostgreSQL + pgvector
│   ├── rag/              # RAG system
│   └── core/             # Pipeline orchestration
├── tests/                 # Test suite (TDD)
├── streamlit_app.py      # Testing UI
└── docker-compose.yml    # All services
```

## Technology Stack

- **Framework**: FastAPI, Python 3.11, Pydantic AI
- **LLM**: OpenRouter, Langfuse
- **Database**: PostgreSQL 16 + pgvector
- **Crawling**: Crawl4AI, Dockling
- **Search**: SearxNG, SerperDev (reused from main app)
- **Testing**: pytest, pytest-asyncio, Ruff, mypy

## Status

🚧 **Under Development** - Phase 1: Foundation (Weeks 1-3)

See [ROADMAP.md](ROADMAP.md) for detailed implementation plan.

## Existing Simple Perplexica

The original `simple_perplexica` codebase in `src/` and `services/` remains **completely untouched** and continues to work independently.
