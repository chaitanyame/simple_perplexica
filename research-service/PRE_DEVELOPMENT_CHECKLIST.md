# 🚀 Pre-Development Checklist

**Complete this checklist before starting TDD development.**

Last Updated: November 9, 2025

---

## ✅ Infrastructure Complete

The following are already set up and ready:

- [x] Database models (ResearchSession, RAGDocument, SessionDocument)
- [x] Database session management (session.py)
- [x] Configuration system (config.py)
- [x] Alembic migration (001_initial_schema.py)
- [x] Test infrastructure (conftest.py, test fixtures)
- [x] Docker setup (docker-compose.yml, Dockerfile)
- [x] All `__init__.py` files created
- [x] FastAPI application entry point (src/main.py)
- [x] Dependencies updated to latest stable versions
- [x] TDD standards documentation
- [x] GitHub Copilot instructions
- [x] Library version tracking

---

## 📋 Required Setup Steps

### 1. Environment Configuration ⚠️ CRITICAL

```bash
cd research-service

# Copy the example environment file
cp .env.example .env

# Edit .env and fill in required API keys:
# - OPENROUTER_API_KEY (get from https://openrouter.ai)
# - LANGFUSE_PUBLIC_KEY (get from https://langfuse.com)
# - LANGFUSE_SECRET_KEY (get from https://langfuse.com)
# - SERPER_API_KEY (optional, for SerperDev search)
```

**Required API Keys:**
- ✅ **OpenRouter** - For LLM access (Claude, DeepSeek, etc.)
- ✅ **Langfuse** - For LLM monitoring and tracing
- ⚠️ **SerperDev** - Optional (can use SearxNG only)

### 2. Install Dependencies ⚠️ CRITICAL

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies (testing, linting)
pip install -r requirements-dev.txt

# Verify installations
python verify_dependencies.py
```

**Expected output:**
```
✅ All dependencies are correctly installed!
💡 You can now proceed with development.
```

### 3. Start Database Services ⚠️ CRITICAL

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be healthy (10-15 seconds)
docker-compose ps

# Expected: Both services show "healthy" status
```

**Verify database connection:**
```bash
# Should connect successfully
docker exec -it research_postgres psql -U research_user -d research_db -c "SELECT version();"
```

### 4. Run Database Migrations ⚠️ CRITICAL

```bash
# Apply initial schema migration
alembic upgrade head

# Verify tables created
docker exec -it research_postgres psql -U research_user -d research_db -c "\dt"

# Expected tables:
# - research_sessions
# - rag_documents
# - session_documents
```

### 5. Verify Setup

```bash
# Check main application can import
python -c "from src.main import app; print('✅ Import successful')"

# Run existing model tests
pytest tests/unit/test_models.py -v

# Expected: All tests pass

# Check code quality
ruff check src/
mypy src/

# Expected: No errors
```

---

## 🎯 Optional But Recommended

### A. Start All Services (Full Stack)

```bash
# Start everything (PostgreSQL, Redis, API, Streamlit)
docker-compose up -d

# Check API health
curl http://localhost:8001/api/v1/health

# Expected:
# {"status":"healthy","service":"research-service","version":"0.1.0"}

# Access API docs
# Browser: http://localhost:8001/api/docs
```

### B. Configure IDE

**VS Code Settings:**
```json
{
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

### C. Test Database Connection from Python

```bash
# Create test script
cat > test_connection.py << 'EOF'
import asyncio
from src.database.session import AsyncSessionLocal
from src.database.models import Base

async def test():
    async with AsyncSessionLocal() as session:
        result = await session.execute("SELECT 1")
        print(f"✅ Database connection successful: {result.scalar()}")

asyncio.run(test())
EOF

# Run test
python test_connection.py

# Clean up
rm test_connection.py
```

---

## 🚨 Common Issues & Solutions

### Issue: Import errors for `pgvector`

**Error:**
```
ModuleNotFoundError: No module named 'pgvector'
```

**Solution:**
```bash
pip install pgvector==0.3.6
```

### Issue: Database connection refused

**Error:**
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# If not running, start it
docker-compose up -d postgres

# Check logs
docker-compose logs postgres
```

### Issue: Alembic migration fails

**Error:**
```
sqlalchemy.exc.ProgrammingError: relation already exists
```

**Solution:**
```bash
# Drop all tables and retry
docker exec -it research_postgres psql -U research_user -d research_db -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Run migration again
alembic upgrade head
```

### Issue: OpenRouter API key invalid

**Error:**
```
openai.AuthenticationError: Invalid API key
```

**Solution:**
1. Verify key in `.env` file
2. Get new key from https://openrouter.ai/keys
3. Ensure no extra spaces or quotes around the key
4. Format: `OPENROUTER_API_KEY=sk-or-v1-xxxxx`

---

## 📊 Verification Checklist

Before starting development, verify:

- [ ] `.env` file exists with all required API keys
- [ ] Dependencies installed (`verify_dependencies.py` passes)
- [ ] PostgreSQL running and accessible
- [ ] Redis running and accessible
- [ ] Alembic migration completed successfully
- [ ] Can import `from src.main import app`
- [ ] Existing tests pass (`pytest tests/unit/test_models.py`)
- [ ] No linting errors (`ruff check src/`)
- [ ] No type errors (`mypy src/`)
- [ ] Health endpoint returns 200 (if running API)

---

## 🎓 Next Steps: TDD Development

Once all checkboxes above are complete:

### Week 1 - LLM & Monitoring (TDD)

**Task 1: OpenRouter Client**
1. Write tests first: `tests/unit/services/llm/test_openrouter_client.py`
2. Implement: `src/services/llm/openrouter_client.py`
3. Ensure tests pass
4. Coverage ≥ 80%

**Task 2: Langfuse Integration**
1. Write tests first: `tests/unit/services/llm/test_langfuse_tracer.py`
2. Implement: `src/services/llm/langfuse_tracer.py`
3. Ensure tests pass
4. Coverage ≥ 80%

**Reference:**
- TDD workflow: `.github/copilot-instructions.md`
- Code standards: `docs/DEVELOPMENT_STANDARDS.md`
- Implementation plan: `ROADMAP.md`

---

## 💡 Quick Reference Commands

```bash
# Development workflow
cd research-service

# Run tests
pytest tests/ -v                    # All tests
pytest tests/unit/ -v               # Unit tests only
pytest tests/integration/ -v        # Integration tests only
pytest -m "unit and fast"           # Fast unit tests
pytest --cov=src --cov-report=html  # With coverage

# Code quality
ruff check .                        # Lint
ruff check --fix .                  # Auto-fix
ruff format .                       # Format
mypy src/                           # Type check

# Database
docker-compose up -d postgres redis # Start databases
alembic upgrade head                # Apply migrations
alembic revision --autogenerate -m "message"  # Create migration

# API
docker-compose up research-api      # Start API
curl http://localhost:8001/api/v1/health  # Health check

# Streamlit UI
docker-compose up streamlit         # Start testing UI
# Browser: http://localhost:8501
```

---

## 📚 Important Files

- **Configuration**: `src/core/config.py`
- **Models**: `src/database/models.py`
- **Main App**: `src/main.py`
- **TDD Standards**: `.github/copilot-instructions.md`
- **Development Guide**: `docs/DEVELOPMENT_STANDARDS.md`
- **Implementation Plan**: `ROADMAP.md`
- **Dependencies**: `requirements.txt`, `requirements-dev.txt`
- **Library Versions**: `docs/LIBRARY_VERSIONS.md`

---

**Ready to start? Run through the checklist above, then we begin TDD implementation! 🚀**
