# Library Version Updates - November 2025

This document tracks the latest stable versions of all dependencies used in the research service.

**Last Updated**: November 9, 2025

---

## 📦 Core Dependencies

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **FastAPI** | 0.109.0 | **0.115.5** | Major version bump with performance improvements |
| **Uvicorn** | 0.27.0 | **0.32.1** | HTTP server updates |
| **Pydantic** | 2.6.0 | **2.10.2** | Enhanced validation and performance |
| **Pydantic Settings** | 2.1.0 | **2.6.1** | Configuration management updates |
| **Pydantic AI** | 0.0.14 | **0.0.14** | Stable beta version |

---

## 🤖 AI & LLM

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **OpenAI** | 1.12.0 | **1.55.3** | Major updates for OpenRouter compatibility |
| **Langfuse** | 2.32.0 | **2.56.0** | Enhanced tracing and monitoring |
| **Sentence-Transformers** | 2.3.1 | **3.3.1** | Major version with better embeddings |

---

## 🗄️ Database

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **SQLAlchemy** | 2.0.27 | **2.0.36** | Bug fixes and performance |
| **AsyncPG** | 0.29.0 | **0.30.0** | PostgreSQL async driver |
| **Psycopg** | 3.1.18 | **3.2.3** | PostgreSQL driver updates |
| **pgvector** | 0.2.5 | **0.3.6** | Vector similarity search improvements |
| **Alembic** | 1.13.1 | **1.14.0** | Migration tool updates |

---

## 🕷️ Crawling & Document Processing

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **Crawl4AI** | 0.3.0 | **0.4.249** | Major updates for web scraping |
| **Dockling** | 0.2.0 | **2.14.0** | MAJOR version jump - PDF/Excel/Word extraction |
| **BeautifulSoup4** | 4.12.3 | **4.12.3** | Stable version (no update needed) |
| **Trafilatura** | 1.8.0 | **1.12.2** | Content extraction improvements |
| **Playwright** | 1.41.2 | **1.48.0** | Browser automation updates |

---

## 🌐 HTTP & Networking

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **HTTPX** | 0.26.0 | **0.28.0** | Async HTTP client updates |
| **Tenacity** | 8.2.3 | **9.0.0** | MAJOR version - retry logic improvements |

---

## 💾 Caching

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **Redis** | 5.0.1 | **5.2.0** | Performance improvements with hiredis |

---

## 🛠️ Utilities

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **python-dotenv** | 1.0.1 | **1.0.1** | Stable (no update) |
| **structlog** | 24.1.0 | **24.4.0** | Structured logging updates |
| **python-dateutil** | 2.8.2 | **2.9.0.post0** | Date utilities |
| **markdown** | 3.5.2 | **3.7** | Markdown processing |

---

## 🎨 Streamlit Testing UI

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **Streamlit** | 1.31.0 | **1.40.1** | Major UI framework updates |
| **Pandas** | 2.1.4 | **2.2.3** | Data manipulation |
| **NumPy** | 1.26.2 | **2.1.3** | MAJOR version with breaking changes |
| **Plotly** | 5.18.0 | **5.24.1** | Visualization library |
| **Matplotlib** | 3.8.2 | **3.9.2** | Plotting library |
| **ReportLab** | 4.0.7 | **4.2.5** | PDF generation |
| **WeasyPrint** | 60.1 | **62.3** | HTML to PDF conversion |

---

## 🧪 Testing & Development

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **pytest** | 7.4.4 | **8.3.4** | MAJOR version with new features |
| **pytest-asyncio** | 0.23.4 | **0.24.0** | Async testing support |
| **pytest-cov** | 4.1.0 | **6.0.0** | MAJOR version - coverage reporting |
| **pytest-mock** | 3.12.0 | **3.14.0** | Mocking utilities |
| **httpx-mock** | 0.8.0 | **0.8.2** | HTTP mocking |

---

## 🎯 Code Quality

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **Ruff** | 0.2.1 | **0.8.1** | Linter and formatter updates |
| **mypy** | 1.8.0 | **1.13.0** | Type checking improvements |
| **black** | 24.1.1 | **24.10.0** | Code formatter |

---

## 🔧 Type Stubs

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **types-redis** | 4.6.0.20240106 | **4.6.0.20241004** | Updated type hints |
| **types-python-dateutil** | 2.8.19.20240106 | **2.9.0.20241003** | Updated type hints |

---

## 🧰 Test Utilities

| Library | Previous | Current | Notes |
|---------|----------|---------|-------|
| **Faker** | 22.6.0 | **33.0.0** | MAJOR version - test data generation |
| **Freezegun** | 1.4.0 | **1.5.1** | Time mocking utilities |

---

## ⚠️ Breaking Changes to Watch

### NumPy 2.x
- **Impact**: Major API changes from 1.x to 2.x
- **Action**: Review NumPy usage in data processing code
- **Migration Guide**: https://numpy.org/devdocs/numpy_2_0_migration_guide.html

### pytest-cov 6.x
- **Impact**: Configuration changes and new reporting features
- **Action**: Review coverage configuration in `pyproject.toml`

### Tenacity 9.x
- **Impact**: API refinements and improved async support
- **Action**: Review retry decorators and async retry logic

### Dockling 2.x
- **Impact**: MAJOR version jump from 0.2.0 to 2.14.0
- **Action**: Review PDF/Excel/Word extraction code thoroughly
- **Note**: Likely significant API changes

### Sentence-Transformers 3.x
- **Impact**: Performance improvements and new models
- **Action**: Re-validate embedding dimensions (should still be 384D for MiniLM)

---

## 📝 Update Commands

```bash
# Update production dependencies
cd research-service
pip install -r requirements.txt --upgrade

# Update development dependencies
pip install -r requirements-dev.txt --upgrade

# Verify installations
pip list | grep -E "fastapi|pydantic|pytest|ruff"

# Run tests to ensure compatibility
pytest tests/ -v

# Check for outdated packages
pip list --outdated
```

---

## 🔄 Version Pinning Strategy

We use **exact version pinning** (`==`) for:
- ✅ **Stability**: Ensures consistent behavior across environments
- ✅ **Reproducibility**: Same versions in dev, test, and production
- ✅ **Security**: Explicit control over dependency updates

**Update Frequency**: Quarterly or when security patches are released

---

## 📅 Next Review Date

**March 2026** - Quarterly dependency review

---

## 🔗 Resources

- [FastAPI Changelog](https://github.com/tiangolo/fastapi/releases)
- [Pydantic Changelog](https://github.com/pydantic/pydantic/releases)
- [pytest Changelog](https://docs.pytest.org/en/stable/changelog.html)
- [Ruff Changelog](https://github.com/astral-sh/ruff/releases)
- [NumPy 2.0 Migration Guide](https://numpy.org/devdocs/numpy_2_0_migration_guide.html)

---

**Note**: Always test thoroughly after updating dependencies, especially for major version changes.
