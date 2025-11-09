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

**Phase 1, Week 1**: Project scaffolding

**Next Steps**:
1. Set up pytest with TDD configuration
2. Create Docker Compose (PostgreSQL, Redis)
3. Install dependencies (Pydantic AI, Dockling, Crawl4AI)
4. Database models and migrations

---

## 🔄 Relationship with Existing Codebase

The existing `simple_perplexica` code in `src/` and `services/` is **completely untouched**:
- Original search endpoints continue to work
- No shared code or dependencies
- Research service runs independently on port 8001
- Can reuse existing SearxNG/SerperDev configuration

This is a **separate microservice** that complements the existing system.
