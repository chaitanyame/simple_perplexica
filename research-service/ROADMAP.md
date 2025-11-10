# Research Service - Multi-Phase Development Plan

## Overview

This service provides both **fast search** and **deep research** capabilities using Pydantic AI agents, RAG with pgvector, and advanced document processing.

---

## 🎯 Key Technologies

| Technology | Purpose |
|-----------|---------|
| **Pydantic AI** | AI agent framework |
| **Dockling** | PDF, Excel, Word extraction |
| **Crawl4AI** | Website data extraction |
| **PostgreSQL + pgvector** | Vector database for RAG |
| **Langfuse** | LLM monitoring & tracing |
| **OpenRouter** | Multi-model LLM gateway |

---

## 📅 Development Phases

### **Phase 1: Foundation (Weeks 1-3)**
- Project setup with TDD
- PostgreSQL + pgvector + Redis
- LLM client with Langfuse tracing
- Dockling & Crawl4AI integration
- **Exit Criteria**: All services running, 80% test coverage

### **Phase 2: Agent System (Weeks 4-6)**
- Pydantic AI agent framework
- Search Agent (web search)
- Browse Agent (Crawl4AI)
- Document Agent (Dockling)
- Synthesizer Agent (report generation)
- **Exit Criteria**: 4 agents operational with structured outputs

### **Phase 3: RAG System (Weeks 7-8)**
- Embedding service (Sentence-Transformers)
- Vector store operations (pgvector)
- Semantic search & retrieval
- Memory manager for research context
- **Exit Criteria**: Vector search recall@10 ≥ 0.85

### **Phase 4: Pipeline Implementation (Weeks 9-11)**
- Search Pipeline (fast mode, <60s)
- Research Pipeline (deep mode, <5min)
- Multi-stage orchestration
- Iterative refinement
- **Exit Criteria**: E2E tests pass, pipelines meet performance targets

### **Phase 5: API & Testing UI (Weeks 12-13)**
- FastAPI endpoints (`/search`, `/research`)
- Request/response validation
- Error handling & rate limiting
- Comprehensive Streamlit testing UI with:
  - **Test Case Management**: Run all pytest tests from UI
  - **Search Mode Tester**: Interactive query testing with parameter controls
  - **Research Mode Tester**: Deep research with iteration monitoring
  - **Parameter Configuration**: Adjustable timeouts, source limits, models
  - **Results Visualization**: Side-by-side comparison, source citations
  - **Performance Metrics**: Execution time, token usage, cost tracking
  - **Langfuse Integration**: Direct links to traces for debugging
- **Exit Criteria**: API documented, Streamlit app fully functional

### **Phase 6: Deployment (Weeks 14-15)**
- Docker multi-stage builds
- Production Docker Compose
- Performance benchmarks
- Documentation
- **Exit Criteria**: MVP ready for internal use

### **Phase 7: Post-MVP Enhancements (Future)**
- Async job queue
- Horizontal scaling
- Advanced RAG features
- Production hardening

---

## 🧪 Testing Strategy (TDD)

- **Unit tests**: ≥80% coverage, mocked external services
- **Integration tests**: Real PostgreSQL/Redis, mocked APIs
- **E2E tests**: Full system with real external APIs

```bash
# Run tests
pytest tests/unit/ -v --cov=src
pytest tests/integration/ -v
pytest tests/e2e/ -v --slow
```

---

## 📊 Success Metrics

### Performance
- Search mode: **<60s** (p95)
- Research mode: **<5min** (p95)
- API response: **<200ms** (p95, excluding pipeline)

### Quality
- Test coverage: **≥80%**
- Langfuse trace capture: **100%** of agent runs
- Vector recall@10: **≥0.85**

### Reliability
- API uptime: **≥99%**
- Error rate: **<1%**
- Retry success: **≥90%**

---

## 🚀 Current Status

### ✅ Phase 1 Week 1-3: Foundation - **COMPLETE**

**Week 1** (5 commits, 61 tests, 81.23% coverage):
- ✅ Project setup with pytest + pytest-asyncio
- ✅ PostgreSQL + Redis Docker Compose
- ✅ Database models and migrations (Alembic)
- ✅ OpenRouter LLM client with retry logic
- ✅ Langfuse tracing integration
- **Deliverables**: Core infrastructure, config management, LLM client

**Week 2** (3 commits, 95 tests, 85.69% coverage):
- ✅ Dockling document processor (PDF, Excel, Word)
- ✅ Crawl4AI web crawler integration
- ✅ Comprehensive chunk extraction and metadata
- **Deliverables**: Document processing pipeline, web crawling capability

**Week 3** (2 commits, 134 tests, 85.20% coverage):
- ✅ Embedding service (sentence-transformers, 384D vectors)
- ✅ Vector store repository (pgvector + cosine similarity)
- ✅ Integration tests for RAG pipeline
- **Deliverables**: Complete RAG foundation (embed → store → search)

**Phase 1 Summary**:
- **Total Commits**: 10
- **Total Tests**: 134 passing
- **Coverage**: 85.20% (exceeds 80% target)
- **Status**: 🎉 **COMPLETE** - Ready for Phase 2

### ✅ Phase 2 Week 4: Agent System - **COMPLETE**

**Week 4** (7 commits, 36 tests, SearchAgent 95.51%, ResearchAgent 93.10% coverage):
- ✅ Pydantic AI agent framework with dependency injection
- ✅ SearchAgent: Query decomposition, parallel search, deduplication
- ✅ ResearchAgent: Multi-step planning, evidence synthesis, validation
- ✅ 27 unit tests (TDD: RED → GREEN → REFACTOR)
- ✅ 9 integration tests (real DB, mocked APIs, multi-agent coordination)
- ✅ Code quality: mypy --strict ✅, ruff ✅
- **Deliverables**: Production-ready SearchAgent & ResearchAgent

**Phase 2 Week 4 Summary**:
- **Total Commits**: 7 (3 RED, 4 GREEN+REFACTOR)
- **Total Tests**: 36 (27 unit + 9 integration) - 100% passing
- **Coverage**: SearchAgent 95.51%, ResearchAgent 93.10%
- **Status**: 🎉 **COMPLETE** - Ready for Week 5 (API & UI)

### 🔄 Phase 2 Week 5: API & Testing UI - **UP NEXT**

**Week 5 Goals** (Est. 5-6 days):
1. **FastAPI Endpoints** (3-4 days)
   - `/v1/search` - SearchAgent integration
   - `/v1/research` - ResearchAgent integration
   - `/v1/sessions/{id}` - Session retrieval
   - Request/response validation with Pydantic
   - Error handling middleware
   - OpenAPI documentation

2. **Streamlit Testing UI** (2-3 days)
   - Search mode interface with parameter controls
   - Research mode interface with real-time progress
   - Session history viewer
   - Export functionality (JSON, Markdown)
   - Langfuse trace viewer integration

3. **E2E Tests** (1 day)
   - Full API workflow tests
   - Performance benchmarks
   - Integration validation

**Week 5 Exit Criteria**:
- 15+ E2E tests passing
- API response time <200ms (p95)
- Streamlit UI fully functional
- OpenAPI schema complete

---

## 🔄 Relationship with Existing Codebase

The existing `simple_perplexica` code in `src/` and `services/` is **completely untouched**:
- Original search endpoints continue to work
- No shared code or dependencies
- Research service runs independently on port 8001
- Can reuse existing SearxNG/SerperDev configuration

This is a **separate microservice** that complements the existing system.
