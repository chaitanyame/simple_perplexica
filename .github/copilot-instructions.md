# GitHub Copilot Instructions - Research Service Development Standards

**Last Updated**: 2025-11-09

## 🎯 CRITICAL: Test-Driven Development (TDD) - MANDATORY

### ⚠️ BEFORE WRITING ANY CODE, READ THIS:

**TDD Workflow (RED-GREEN-REFACTOR):**
1. ✅ **RED**: Write failing test first
2. ✅ **GREEN**: Write minimal code to pass test
3. ✅ **REFACTOR**: Improve code while keeping tests green

**Enforcement Rules:**
- ❌ **NEVER** write implementation code before tests
- ❌ **NEVER** commit untested code
- ✅ **ALWAYS** write tests for new features first
- ✅ **ALWAYS** ensure tests fail before implementation
- ✅ **ALWAYS** run full test suite before committing

**Test Coverage Requirements:**
- Minimum: **80%** overall coverage
- Critical paths: **100%** coverage
- Edge cases: **Mandatory** testing
- Error handling: **Mandatory** testing

---

## 🏗️ Active Technologies

### Research Service (research-service/)
- **Backend**: FastAPI 0.115.5 + Python 3.11
- **Database**: PostgreSQL 16 + pgvector 0.3.6
- **Cache**: Redis 7 (redis-py 5.2.0)
- **AI Framework**: Pydantic AI 0.0.14
- **LLM**: OpenRouter (Claude 3.5, DeepSeek) via openai 1.55.3
- **Monitoring**: Langfuse 2.56.0
- **Document Processing**: Dockling 2.14.0
- **Web Crawling**: Crawl4AI 0.4.249
- **Embeddings**: Sentence-Transformers 3.3.1 (384D)
- **Testing**: pytest 8.3.4, pytest-asyncio 0.24.0
- **Linting**: Ruff 0.8.1, mypy 1.13.0

### Existing Services (services/)
- **Search Service**: Python 3.11 + FastAPI
- **SearxNG Integration**: HTTP client
- **SerperDev Integration**: HTTP client

---

## 📁 Project Structure

```
research-service/
├── src/                          # ✅ Implementation AFTER tests
│   ├── api/v1/endpoints/         # FastAPI routes
│   ├── agents/                   # Pydantic AI agents
│   ├── core/                     # Config, pipelines
│   ├── database/                 # Models, repositories
│   ├── services/                 # External integrations
│   ├── rag/                      # Vector store, retrieval
│   └── utils/                    # Utilities
├── tests/                        # ✅ Write FIRST
│   ├── unit/                     # Fast, isolated tests
│   ├── integration/              # DB, external services
│   └── e2e/                      # Full pipeline tests
├── docs/                         # Documentation
├── alembic/                      # Database migrations
└── streamlit_app.py             # Testing UI

services/
├── searchsvc/                    # Existing search service
└── researchsvc/                  # Legacy (being replaced)
```

---

## 🐍 Python Code Standards

### Type Hints (MANDATORY)

```python
# ✅ GOOD
def process_query(
    query: str,
    max_sources: int = 20,
    timeout: float = 60.0
) -> dict[str, Any]:
    """Process query with type-safe parameters."""
    pass

# ❌ BAD - No type hints
def process_query(query, max_sources=20):
    pass
```

### Docstrings (MANDATORY)

```python
# ✅ GOOD
def embed_text(text: str) -> list[float]:
    """Generate embedding vector for text.
    
    Args:
        text: Input text to embed (1-10000 chars)
        
    Returns:
        384-dimensional embedding vector
        
    Raises:
        ValueError: If text is empty or too long
        EmbeddingError: If model fails
        
    Example:
        >>> embed_text("hello world")
        [0.1, 0.2, ..., 0.9]
    """
    pass

# ❌ BAD - No docstring
def embed_text(text):
    pass
```

### Imports Organization

```python
# ✅ GOOD - Organized: stdlib, third-party, local
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select

from ..core.config import settings
from .models import Document

# ❌ BAD - Unorganized
from .models import Document
import httpx
from typing import Any
```

---

## 🧪 Testing Standards (TDD WORKFLOW)

### Test File Structure

```
tests/
├── unit/
│   ├── test_config.py           # Tests src/core/config.py
│   ├── test_models.py           # Tests src/database/models.py
│   ├── agents/
│   │   └── test_search_agent.py # Tests src/agents/search_agent.py
│   └── services/
│       └── test_llm_client.py   # Tests src/services/llm/
├── integration/
│   ├── test_database.py         # Tests DB integration
│   └── test_rag_pipeline.py     # Tests RAG with real DB
└── e2e/
    ├── test_search_pipeline.py  # Full search flow
    └── test_research_pipeline.py # Full research flow
```

### Test Writing Pattern (AAA)

```python
# ✅ GOOD - AAA Pattern (Arrange, Act, Assert)
@pytest.mark.asyncio
async def test_search_agent_decomposes_query(mock_llm_client):
    """Test that SearchAgent decomposes complex query into sub-queries.
    
    Given: A SearchAgent with mocked LLM client
    When: Decomposing a complex query
    Then: Returns multiple focused sub-queries
    """
    # Arrange
    agent = SearchAgent(llm_client=mock_llm_client)
    query = "What are AI agents and how do they work?"
    mock_llm_client.chat.return_value = {
        "sub_queries": ["what are AI agents", "how do AI agents work"]
    }
    
    # Act
    result = await agent.decompose_query(query)
    
    # Assert
    assert len(result.sub_queries) == 2
    assert "AI agents" in result.sub_queries[0]
    assert mock_llm_client.chat.called_once()

# ❌ BAD - No structure
async def test_agent():
    agent = SearchAgent()
    result = agent.decompose("query")
    assert result
```

### Test Fixtures

```python
# ✅ GOOD - Reusable, async-aware
@pytest_asyncio.fixture
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide async database session for tests."""
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()  # Always rollback

@pytest.fixture
def mock_openrouter_client() -> MagicMock:
    """Provide mocked OpenRouter client."""
    client = MagicMock(spec=OpenRouterClient)
    client.chat.return_value = {"content": "mocked response"}
    return client
```

### Test Markers

```python
# Use markers to categorize
@pytest.mark.unit
@pytest.mark.fast
def test_config_loading():
    """Unit test for config loading."""
    pass

@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.requires_db
async def test_database_connection():
    """Integration test requiring real DB."""
    pass

@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.requires_api
async def test_full_search_pipeline():
    """End-to-end test with real APIs."""
    pass
```

---

## 🗄️ Database Standards

### SQLAlchemy Models

```python
# ✅ GOOD - Complete model with types
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

class ResearchSession(Base):
    """Research session with query and results."""
    
    __tablename__ = "research_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
    
    # Relationships
    documents: Mapped[list["SessionDocument"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )
```

### Repository Pattern

```python
# ✅ GOOD - Abstract interface + implementation
from abc import ABC, abstractmethod

class SessionRepository(ABC):
    """Abstract repository for session operations."""
    
    @abstractmethod
    async def create(self, session: ResearchSession) -> ResearchSession:
        pass
    
    @abstractmethod
    async def get_by_id(self, session_id: uuid.UUID) -> ResearchSession | None:
        pass

class SQLSessionRepository(SessionRepository):
    """SQLAlchemy implementation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create(self, session: ResearchSession) -> ResearchSession:
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session
```

---

## 🚀 FastAPI Standards

### Endpoint Structure

```python
# ✅ GOOD - Complete validation
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator

router = APIRouter(prefix="/v1", tags=["search"])

class SearchRequest(BaseModel):
    """Search request with validation."""
    
    query: str = Field(..., min_length=1, max_length=1000)
    max_sources: int = Field(20, ge=5, le=50)
    timeout: int = Field(60, ge=10, le=300)
    
    @validator("query")
    def query_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v.strip()

class SearchResponse(BaseModel):
    """Search response model."""
    session_id: uuid.UUID
    answer: str
    sources: list[dict[str, Any]]
    execution_time: float

@router.post("/search", response_model=SearchResponse)
async def search(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
) -> SearchResponse:
    """Execute search query."""
    try:
        pipeline = SearchPipeline(db=db)
        result = await pipeline.execute(
            query=request.query,
            max_sources=request.max_sources
        )
        return SearchResponse(**result)
    except SearchError as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🎨 Streamlit Standards

### Component Structure

```python
# ✅ GOOD - Reusable component
def render_search_result(
    result: dict,
    on_export: Optional[Callable] = None
) -> None:
    """Render search result with sources.
    
    Args:
        result: Search result dictionary
        on_export: Optional export callback
    """
    st.markdown("### 📄 Answer")
    st.markdown(result["answer"])
    
    st.markdown("### 📚 Sources")
    for idx, source in enumerate(result["sources"], 1):
        with st.expander(f"[{idx}] {source['title']}"):
            st.markdown(f"**URL:** {source['url']}")
            st.metric("Relevance", f"{source['relevance']:.2f}")
    
    if on_export and st.button("📤 Export"):
        on_export(result)
```

---

## 🔍 Pre-Commit Checklist

Before any commit, verify:

### ✅ Tests (MANDATORY)
- [ ] Tests written BEFORE implementation (TDD)
- [ ] All tests pass: `pytest tests/ -v`
- [ ] Coverage ≥ 80%: `pytest --cov=src --cov-report=html`
- [ ] Tests follow AAA pattern
- [ ] Edge cases tested
- [ ] Error conditions tested

### ✅ Code Quality
- [ ] Type hints on all functions
- [ ] Docstrings on all public functions/classes
- [ ] No linting errors: `ruff check .`
- [ ] No type errors: `mypy src/`
- [ ] Imports organized
- [ ] No commented-out code
- [ ] No print statements (use logger)

### ✅ Architecture
- [ ] Repository pattern for data access
- [ ] Dependency injection for services
- [ ] Custom exceptions for domain errors
- [ ] Async/await used consistently
- [ ] No blocking operations in async

---

## 🚨 Anti-Patterns to Avoid

### ❌ God Classes
```python
# BAD - One class doing everything
class SearchService:
    def search(self): pass
    def crawl(self): pass
    def embed(self): pass
    # ... 50 methods

# GOOD - Single responsibility
class SearchService:
    def __init__(self, crawler: Crawler, embedder: Embedder):
        self.crawler = crawler
        self.embedder = embedder
```

### ❌ Magic Numbers
```python
# BAD
if len(sources) > 20:  # Why 20?

# GOOD
MAX_SOURCES_SEARCH_MODE = 20
if len(sources) > MAX_SOURCES_SEARCH_MODE:
```

---

## 📋 Commands Reference

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest --cov=src --cov-report=html tests/

# Run specific test file
pytest tests/unit/test_config.py -v

# Run marked tests
pytest -m "unit and fast" -v

# Linting
ruff check .
ruff check --fix .

# Type checking
mypy src/

# Format code
ruff format .

# Database migrations
alembic upgrade head
alembic revision --autogenerate -m "message"

# Start services
docker-compose up -d
docker-compose up research-api streamlit
```

---

## 📚 Documentation

- Process Flows: `docs/PROCESS_FLOWS.md`
- Streamlit Spec: `docs/STREAMLIT_APP_SPEC.md`
- Architecture: `docs/STREAMLIT_ARCHITECTURE.md`
- Progress: `docs/PHASE1_WEEK1_PROGRESS.md`
- Roadmap: `ROADMAP.md`

---

**REMEMBER: Tests First, Code Second. No Exceptions. 🧪**

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
