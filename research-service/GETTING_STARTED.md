# 🎉 Research Service - Project Initialized

## ✅ What's Been Created

A **completely separate** research service has been created in `research-service/` directory.

### **Your existing codebase is 100% untouched:**
- ✅ `src/` - Original Simple Perplexica code
- ✅ `services/` - SearchSVC and ResearchSVC
- ✅ All existing APIs continue to work
- ✅ No shared dependencies or conflicts

---

## 📁 New Structure Created

```
research-service/               # NEW - Completely separate
├── src/                       # Source code
│   ├── api/                  # FastAPI endpoints
│   ├── agents/               # Pydantic AI agents
│   ├── core/                 # Pipeline orchestration
│   ├── services/             # External integrations
│   ├── database/             # PostgreSQL + pgvector
│   ├── rag/                  # RAG system
│   └── utils/                # Utilities
├── tests/                     # Test suite (TDD)
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docker-compose.yml         # PostgreSQL + Redis + API
├── requirements.txt           # Dependencies
├── requirements-dev.txt       # Dev dependencies
├── pyproject.toml            # Ruff, mypy, pytest config
├── Dockerfile                # Production image
├── .env.example              # Configuration template
├── README.md                 # Service documentation
└── ROADMAP.md               # 15-week implementation plan
```

---

## 🎯 Key Technologies

| Technology | Purpose |
|-----------|---------|
| **Pydantic AI** | AI agent framework |
| **Dockling** | PDF, Excel, Word extraction |
| **Crawl4AI** | Website data extraction |
| **PostgreSQL + pgvector** | Vector database (RAG) |
| **Langfuse** | LLM monitoring & tracing |
| **OpenRouter** | Multi-model LLM gateway |
| **FastAPI** | Async API framework |
| **Streamlit** | Testing UI |

---

## 🚀 Next Steps (Phase 1, Week 1)

### 1. **Set up environment**
```bash
cd research-service

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. **Configure environment**
```bash
# Copy example config
cp .env.example .env

# Edit .env with your API keys:
# - OPENROUTER_API_KEY
# - LANGFUSE_PUBLIC_KEY & LANGFUSE_SECRET_KEY
# - SERPER_API_KEY (optional)
```

### 3. **Start infrastructure**
```bash
# Start PostgreSQL + Redis
docker-compose up -d postgres redis

# Wait for services to be healthy
docker-compose ps
```

### 4. **Run tests (TDD approach)**
```bash
# Run unit tests
pytest tests/unit/ -v

# Run with coverage
pytest tests/unit/ -v --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### 5. **Code quality checks**
```bash
# Linting
ruff check src/ tests/

# Type checking
mypy src/

# Format code
ruff format src/ tests/
```

---

## 📊 Development Phases

| Phase | Timeline | Focus |
|-------|----------|-------|
| **Phase 1** | Weeks 1-3 | Foundation (DB, LLM, Dockling, Crawl4AI) |
| **Phase 2** | Weeks 4-6 | Pydantic AI agents (4 agents) |
| **Phase 3** | Weeks 7-8 | RAG system (pgvector) |
| **Phase 4** | Weeks 9-11 | Pipelines (search & research) |
| **Phase 5** | Weeks 12-13 | API & Streamlit UI |
| **Phase 6** | Weeks 14-15 | Deployment & docs |

**Total: 15 weeks (3.5 months) to MVP**

---

## 🔧 Configuration Details

### **Ports**
- Research API: `8001` (different from main app)
- PostgreSQL: `5432`
- Redis: `6379`
- Streamlit: `8501`

### **Database**
- PostgreSQL 16 with pgvector extension
- Database: `research_db`
- User: `research_user`
- Password: Set in `.env`

### **Services**
- **OpenRouter**: Multi-model LLM gateway (Claude, DeepSeek, etc.)
- **Langfuse**: LLM call tracing and monitoring
- **SearxNG/SerperDev**: Can reuse from main app

---

## 📝 Important Notes

### **No Conflicts with Existing Code**
- Research service runs on **port 8001** (main app uses 8000)
- Separate database (`research_db` vs main app DB)
- No shared code or imports
- Can run both services simultaneously

### **TDD Approach**
- Write tests FIRST, then implementation
- Target: **≥80% test coverage**
- Pytest configured with async support
- Ruff for linting, mypy for type checking

### **Pydantic AI Agents**
- Not traditional multi-agent (no agent-to-agent communication)
- Specialized task executors orchestrated by pipelines
- Structured outputs using Pydantic models
- Integrated with Langfuse for tracing

---

## 📖 Documentation

- **README.md**: Service overview and quick start
- **ROADMAP.md**: Detailed 15-week implementation plan
- **.env.example**: All configuration options explained
- **pyproject.toml**: Tool configurations (Ruff, mypy, pytest)

---

## 🎯 Success Criteria

### **Performance**
- Search mode: < 60 seconds
- Research mode: < 5 minutes

### **Quality**
- Test coverage: ≥ 80%
- Langfuse: 100% of LLM calls traced
- Vector recall@10: ≥ 0.85

### **Reliability**
- API uptime: ≥ 99%
- Error rate: < 1%

---

## ✨ Ready to Start!

Your existing Simple Perplexica code is safely backed up and untouched. The new research service is completely independent and ready for development.

**Start with Phase 1, Week 1:**
1. Set up Python environment
2. Configure `.env` file
3. Start Docker services
4. Write first tests (TDD)
5. Begin implementation

Good luck! 🚀
