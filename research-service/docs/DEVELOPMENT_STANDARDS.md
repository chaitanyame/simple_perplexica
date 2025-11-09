# Development Standards & Best Practices - Complete Reference

This document serves as the definitive guide for all development work on the research service. **Read this before writing any code.**

---

## 🎯 Table of Contents

1. [Test-Driven Development (TDD)](#test-driven-development-tdd)
2. [Python Backend Standards](#python-backend-standards)
3. [Database Development](#database-development)
4. [API Development](#api-development)
5. [Frontend Development](#frontend-development)
6. [Testing Best Practices](#testing-best-practices)
7. [Code Review Guidelines](#code-review-guidelines)
8. [Performance Standards](#performance-standards)
9. [Security Standards](#security-standards)
10. [Documentation Standards](#documentation-standards)

---

## 🧪 Test-Driven Development (TDD)

### The TDD Cycle (RED-GREEN-REFACTOR)

**Step 1: RED - Write a Failing Test**
```python
# tests/unit/agents/test_search_agent.py

@pytest.mark.asyncio
async def test_decompose_query_returns_sub_queries():
    """Test that complex query is decomposed into sub-queries."""
    # This test will FAIL because SearchAgent.decompose_query doesn't exist yet
    agent = SearchAgent()
    result = await agent.decompose_query("What are AI agents?")
    
    assert isinstance(result.sub_queries, list)
    assert len(result.sub_queries) > 0
    assert all(isinstance(q, str) for q in result.sub_queries)
```

**Step 2: GREEN - Write Minimal Code to Pass**
```python
# src/agents/search_agent.py

class SearchAgent:
    """Agent for search operations."""
    
    async def decompose_query(self, query: str) -> DecompositionResult:
        """Decompose query into sub-queries."""
        # Minimal implementation to make test pass
        return DecompositionResult(sub_queries=[query])

# Test now PASSES
```

**Step 3: REFACTOR - Improve Code Quality**
```python
# src/agents/search_agent.py

class SearchAgent:
    """Agent for search operations using LLM."""
    
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
    
    async def decompose_query(self, query: str) -> DecompositionResult:
        """Decompose complex query into focused sub-queries.
        
        Args:
            query: Original user query
            
        Returns:
            DecompositionResult with sub-queries list
            
        Raises:
            QueryDecompositionError: If LLM fails
        """
        if not query.strip():
            raise ValueError("Query cannot be empty")
        
        try:
            response = await self.llm_client.chat(
                prompt=self._build_decomposition_prompt(query)
            )
            return self._parse_decomposition(response)
        except LLMError as e:
            raise QueryDecompositionError(f"Failed to decompose query: {e}")
    
    def _build_decomposition_prompt(self, query: str) -> str:
        """Build prompt for query decomposition."""
        return f"""Decompose this query into 2-4 focused sub-queries:
        
        Query: {query}
        
        Return JSON: {{"sub_queries": ["query1", "query2"]}}
        """
    
    def _parse_decomposition(self, response: dict) -> DecompositionResult:
        """Parse LLM response into DecompositionResult."""
        sub_queries = response.get("sub_queries", [])
        return DecompositionResult(sub_queries=sub_queries)

# Test still PASSES, code is better
```

### TDD Benefits

**1. Design Before Implementation**
- Writing tests first forces you to think about API design
- Clarifies requirements and edge cases
- Results in better interfaces

**2. Built-in Documentation**
- Tests serve as executable documentation
- Show how to use the code
- Demonstrate expected behavior

**3. Refactoring Safety**
- Change implementation with confidence
- Tests catch regressions immediately
- Encourages better design

**4. Higher Code Quality**
- Forces small, focused functions
- Encourages loose coupling
- Results in testable code

### TDD Anti-Patterns to Avoid

**❌ Writing Tests After Implementation**
```python
# BAD - Implementation first, tests later
def search(query):
    # 200 lines of code
    pass

# Now trying to test...
def test_search():
    # Hard to test! Too many dependencies, side effects
    pass
```

**❌ Testing Implementation Details**
```python
# BAD - Testing private methods
def test_internal_state():
    agent = SearchAgent()
    assert agent._internal_counter == 0  # Don't test private state!
```

**❌ Overly Specific Mocks**
```python
# BAD - Mocking too much
def test_search():
    mock.assert_called_with(
        query="exact query",
        param1=123,
        param2="exact value",
        # ... 20 more parameters
    )  # Brittle! Breaks on minor changes
```

**✅ GOOD - Test Behavior, Not Implementation**
```python
# GOOD - Test public interface and behavior
@pytest.mark.asyncio
async def test_search_returns_relevant_results():
    """Test that search returns results matching query intent."""
    agent = SearchAgent(llm_client=mock_llm)
    
    results = await agent.search("machine learning basics")
    
    assert len(results) > 0
    assert all("machine learning" in r.lower() or "ML" in r for r in results)
```

---

## 🐍 Python Backend Standards

### Code Organization Principles

**1. Single Responsibility Principle (SRP)**
```python
# ✅ GOOD - Each class has one responsibility
class QueryDecomposer:
    """Decomposes queries into sub-queries."""
    def decompose(self, query: str) -> list[str]:
        pass

class SourceFetcher:
    """Fetches content from URLs."""
    async def fetch(self, url: str) -> str:
        pass

class ResultSynthesizer:
    """Synthesizes final answer from sources."""
    def synthesize(self, sources: list[dict]) -> str:
        pass

# ❌ BAD - God class doing everything
class SearchService:
    def decompose_query(self): pass
    def fetch_sources(self): pass
    def synthesize_results(self): pass
    def save_to_database(self): pass
    def send_notifications(self): pass
    # ... 50 more methods
```

**2. Dependency Injection**
```python
# ✅ GOOD - Dependencies injected
class SearchPipeline:
    """Search pipeline with injected dependencies."""
    
    def __init__(
        self,
        decomposer: QueryDecomposer,
        fetcher: SourceFetcher,
        synthesizer: ResultSynthesizer,
        db: AsyncSession
    ):
        self.decomposer = decomposer
        self.fetcher = fetcher
        self.synthesizer = synthesizer
        self.db = db
    
    async def execute(self, query: str) -> SearchResult:
        """Execute search pipeline."""
        sub_queries = self.decomposer.decompose(query)
        sources = await self._fetch_sources(sub_queries)
        answer = self.synthesizer.synthesize(sources)
        await self._save_to_db(answer)
        return SearchResult(answer=answer, sources=sources)

# Easy to test with mocks!
def test_pipeline():
    mock_decomposer = Mock()
    mock_fetcher = AsyncMock()
    mock_synthesizer = Mock()
    mock_db = AsyncMock()
    
    pipeline = SearchPipeline(
        decomposer=mock_decomposer,
        fetcher=mock_fetcher,
        synthesizer=mock_synthesizer,
        db=mock_db
    )
    # Test with controlled mocks

# ❌ BAD - Hard-coded dependencies
class SearchPipeline:
    def __init__(self):
        self.decomposer = QueryDecomposer()  # Hard-coded!
        self.fetcher = SourceFetcher()       # Can't mock!
        self.db = create_db_connection()     # Global state!
    
    # Impossible to test in isolation
```

**3. Interface Segregation**
```python
# ✅ GOOD - Small, focused interfaces
from abc import ABC, abstractmethod

class LLMClient(ABC):
    """Interface for LLM operations."""
    
    @abstractmethod
    async def chat(self, prompt: str) -> dict:
        """Send chat request."""
        pass

class StreamingLLMClient(LLMClient):
    """LLM client with streaming support."""
    
    @abstractmethod
    async def stream(self, prompt: str) -> AsyncIterator[str]:
        """Stream chat response."""
        pass

# Clients can implement just what they need
class OpenRouterClient(StreamingLLMClient):
    async def chat(self, prompt: str) -> dict:
        # Implementation
        pass
    
    async def stream(self, prompt: str) -> AsyncIterator[str]:
        # Implementation
        pass

# ❌ BAD - Fat interface
class LLMClient(ABC):
    @abstractmethod
    def chat(self): pass
    @abstractmethod
    def stream(self): pass
    @abstractmethod
    def embed(self): pass
    @abstractmethod
    def fine_tune(self): pass
    @abstractmethod
    def analyze_sentiment(self): pass
    # ... 20 more methods
    
    # Force all implementations to implement everything!
```

### Error Handling Patterns

**Custom Exception Hierarchy**
```python
# ✅ GOOD - Domain-specific exceptions
class ResearchServiceError(Exception):
    """Base exception for research service."""
    pass

class PipelineError(ResearchServiceError):
    """Error in pipeline execution."""
    pass

class QueryDecompositionError(PipelineError):
    """Failed to decompose query."""
    pass

class SourceFetchError(PipelineError):
    """Failed to fetch source."""
    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"Failed to fetch {url}: {reason}")

class LLMError(ResearchServiceError):
    """LLM-related error."""
    pass

class RateLimitError(LLMError):
    """Rate limit exceeded."""
    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limited. Retry after {retry_after}s")

# Usage with specific handling
try:
    result = await pipeline.execute(query)
except QueryDecompositionError as e:
    logger.error("Failed to decompose query", exc_info=e)
    # Return helpful error to user
except SourceFetchError as e:
    logger.warning(f"Source fetch failed: {e.url}")
    # Continue with partial results
except RateLimitError as e:
    logger.info(f"Rate limited, retrying after {e.retry_after}s")
    await asyncio.sleep(e.retry_after)
    # Retry operation
```

**Graceful Degradation**
```python
# ✅ GOOD - Partial failures don't stop everything
async def fetch_all_sources(urls: list[str]) -> list[SourceResult]:
    """Fetch sources with graceful degradation."""
    results = []
    
    for url in urls:
        try:
            content = await fetch_url(url, timeout=10)
            results.append(SourceResult(
                url=url,
                content=content,
                status="success",
                error=None
            ))
        except httpx.TimeoutException:
            logger.warning(f"Timeout fetching {url}")
            results.append(SourceResult(
                url=url,
                content=None,
                status="timeout",
                error="Request timed out"
            ))
        except httpx.HTTPError as e:
            logger.error(f"HTTP error for {url}: {e}")
            results.append(SourceResult(
                url=url,
                content=None,
                status="error",
                error=str(e)
            ))
    
    # Log summary
    successful = sum(1 for r in results if r.status == "success")
    logger.info(f"Fetched {successful}/{len(urls)} sources successfully")
    
    return results

# ❌ BAD - All or nothing
async def fetch_all_sources(urls: list[str]) -> list[str]:
    # One failure = entire operation fails
    return [await fetch_url(url) for url in urls]
```

### Async/Await Best Practices

**Parallel Execution**
```python
# ✅ GOOD - Parallel execution for independent tasks
async def process_multiple_queries(queries: list[str]) -> list[Result]:
    """Process queries in parallel."""
    tasks = [process_single_query(q) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Handle exceptions
    processed = []
    for query, result in zip(queries, results):
        if isinstance(result, Exception):
            logger.error(f"Failed to process {query}: {result}")
            processed.append(None)
        else:
            processed.append(result)
    
    return processed

# ❌ BAD - Sequential execution (slow!)
async def process_multiple_queries(queries: list[str]) -> list[Result]:
    results = []
    for query in queries:
        result = await process_single_query(query)  # Wait for each!
        results.append(result)
    return results
```

**Avoid Blocking Operations**
```python
# ✅ GOOD - Use async libraries
async def fetch_url(url: str) -> str:
    """Fetch URL asynchronously."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text

# ❌ BAD - Blocking in async function
async def fetch_url(url: str) -> str:
    response = requests.get(url)  # BLOCKS the event loop!
    return response.text

# If you must use blocking code:
async def call_blocking_function():
    """Call blocking function without blocking event loop."""
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,  # Use default executor
        blocking_function,
        arg1, arg2
    )
    return result
```

---

## 🗄️ Database Development

### Migration Strategy

**Always Use Migrations**
```bash
# ✅ GOOD - Create migration for every schema change
alembic revision --autogenerate -m "Add user_id to research_sessions"

# Edit the generated migration file
# Test migration up and down
alembic upgrade head
alembic downgrade -1
alembic upgrade head

# Commit migration file to git
```

**Migration Best Practices**
```python
# ✅ GOOD - Complete migration with data preservation
def upgrade() -> None:
    """Add user_id column with proper constraints."""
    # 1. Add column as nullable first
    op.add_column(
        "research_sessions",
        sa.Column("user_id", sa.UUID(), nullable=True)
    )
    
    # 2. Populate existing rows
    op.execute("""
        UPDATE research_sessions
        SET user_id = (SELECT id FROM users LIMIT 1)
        WHERE user_id IS NULL
    """)
    
    # 3. Make non-nullable
    op.alter_column(
        "research_sessions",
        "user_id",
        nullable=False
    )
    
    # 4. Add foreign key
    op.create_foreign_key(
        "fk_research_sessions_user_id",
        "research_sessions", "users",
        ["user_id"], ["id"]
    )
    
    # 5. Add index
    op.create_index(
        "ix_research_sessions_user_id",
        "research_sessions",
        ["user_id"]
    )

def downgrade() -> None:
    """Remove user_id column."""
    op.drop_index("ix_research_sessions_user_id")
    op.drop_constraint("fk_research_sessions_user_id", "research_sessions")
    op.drop_column("research_sessions", "user_id")
```

### Query Optimization

**Use Proper Indexing**
```python
# ✅ GOOD - Indexed columns for frequent queries
class ResearchSession(Base):
    __tablename__ = "research_sessions"
    
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    mode: Mapped[str] = mapped_column(String(20), index=True)  # Frequent filter
    status: Mapped[str] = mapped_column(String(20), index=True)  # Frequent filter
    user_id: Mapped[uuid.UUID] = mapped_column(UUID, ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)  # Range queries
    
    # Composite index for common query pattern
    __table_args__ = (
        Index("ix_sessions_user_status", "user_id", "status"),
    )
```

**Avoid N+1 Queries**
```python
# ✅ GOOD - Use joinedload/selectinload
from sqlalchemy.orm import selectinload

async def get_sessions_with_documents(user_id: uuid.UUID) -> list[ResearchSession]:
    """Get sessions with documents in one query."""
    result = await db.execute(
        select(ResearchSession)
        .where(ResearchSession.user_id == user_id)
        .options(selectinload(ResearchSession.documents))  # Load related data
    )
    return result.scalars().all()

# ❌ BAD - N+1 queries
async def get_sessions_with_documents(user_id: uuid.UUID) -> list[ResearchSession]:
    result = await db.execute(
        select(ResearchSession)
        .where(ResearchSession.user_id == user_id)
    )
    sessions = result.scalars().all()
    
    # This triggers one query PER session! (N+1 problem)
    for session in sessions:
        docs = session.documents  # Lazy load - new query!
    
    return sessions
```

**Batch Operations**
```python
# ✅ GOOD - Bulk insert
async def store_documents(documents: list[RAGDocument]) -> None:
    """Store multiple documents efficiently."""
    db.add_all(documents)  # Single INSERT with multiple VALUES
    await db.commit()

# ❌ BAD - Individual inserts
async def store_documents(documents: list[RAGDocument]) -> None:
    for doc in documents:
        db.add(doc)
        await db.commit()  # Separate transaction per document!
```

---

## 🚀 API Development

### Request Validation

**Pydantic Models for Validation**
```python
# ✅ GOOD - Comprehensive validation
from pydantic import BaseModel, Field, validator, root_validator

class SearchRequest(BaseModel):
    """Search request with validation."""
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text"
    )
    max_sources: int = Field(
        20,
        ge=5,
        le=50,
        description="Maximum sources to retrieve"
    )
    timeout: int = Field(
        60,
        ge=10,
        le=300,
        description="Timeout in seconds"
    )
    mode: Literal["search", "research"] = Field(
        "search",
        description="Execution mode"
    )
    
    @validator("query")
    def query_not_whitespace(cls, v: str) -> str:
        """Validate query is not just whitespace."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace")
        return v.strip()
    
    @root_validator
    def validate_mode_timeout_combination(cls, values):
        """Validate timeout is appropriate for mode."""
        mode = values.get("mode")
        timeout = values.get("timeout")
        
        if mode == "search" and timeout > 120:
            raise ValueError("Search mode timeout should not exceed 120s")
        if mode == "research" and timeout < 60:
            raise ValueError("Research mode requires at least 60s timeout")
        
        return values
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What are the latest AI developments?",
                "max_sources": 20,
                "timeout": 60,
                "mode": "search"
            }
        }
```

### Response Models

```python
# ✅ GOOD - Typed response models
from pydantic import BaseModel
from typing import Literal

class SourceMetadata(BaseModel):
    """Source metadata."""
    url: str
    title: str
    relevance: float = Field(ge=0.0, le=1.0)
    type: Literal["web", "pdf", "excel", "word"]
    fetched_at: datetime

class SearchResponse(BaseModel):
    """Search response with typed fields."""
    session_id: uuid.UUID
    query: str
    answer: str
    sources: list[SourceMetadata]
    execution_time: float
    token_count: int
    cost: float
    langfuse_trace_id: str
    metadata: dict[str, Any]
    
    class Config:
        schema_extra = {
            "example": {
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "query": "What are AI agents?",
                "answer": "AI agents are...",
                "sources": [
                    {
                        "url": "https://example.com",
                        "title": "AI Agents Explained",
                        "relevance": 0.95,
                        "type": "web",
                        "fetched_at": "2025-11-09T10:00:00Z"
                    }
                ],
                "execution_time": 45.2,
                "token_count": 8450,
                "cost": 0.0423,
                "langfuse_trace_id": "trace_abc123",
                "metadata": {}
            }
        }
```

### Error Responses

```python
# ✅ GOOD - Structured error responses
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    error_type: str
    detail: Optional[str] = None
    trace_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

@app.exception_handler(SearchError)
async def search_error_handler(
    request: Request,
    exc: SearchError
) -> JSONResponse:
    """Handle search errors with detailed response."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=str(exc),
            error_type=exc.__class__.__name__,
            detail=exc.detail if hasattr(exc, "detail") else None,
            trace_id=request.state.trace_id if hasattr(request.state, "trace_id") else None
        ).dict()
    )
```

---

## 🎨 Frontend Development

### Streamlit Component Patterns

**Reusable Components**
```python
# ✅ GOOD - Modular, reusable components
from typing import Callable, Optional
import streamlit as st

def render_metric_card(
    title: str,
    value: str,
    delta: Optional[str] = None,
    delta_color: str = "normal"
) -> None:
    """Render metric card with consistent styling."""
    with st.container():
        st.markdown(f"### {title}")
        col1, col2 = st.columns([3, 1])
        with col1:
            st.metric(label="", value=value, delta=delta, delta_color=delta_color)

def render_source_list(
    sources: list[dict],
    on_click: Optional[Callable[[str], None]] = None
) -> None:
    """Render list of sources with actions."""
    for idx, source in enumerate(sources, 1):
        with st.expander(f"[{idx}] {source['title']}"):
            st.markdown(f"**URL:** {source['url']}")
            st.metric("Relevance", f"{source['relevance']:.2f}")
            
            if on_click and st.button(f"View Details {idx}", key=f"view_{idx}"):
                on_click(source['url'])

# Usage
render_metric_card("Total Queries", "247", delta="+12")
render_source_list(results["sources"], on_click=view_source_details)
```

**State Management**
```python
# ✅ GOOD - Centralized state management
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AppState:
    """Application state container."""
    
    api_client: Optional[APIClient] = None
    current_query: str = ""
    search_results: list[dict] = field(default_factory=list)
    research_results: list[dict] = field(default_factory=list)
    test_history: list[dict] = field(default_factory=list)
    settings: dict = field(default_factory=dict)
    
    def add_search_result(self, result: dict) -> None:
        """Add search result to history."""
        self.search_results.append(result)
        if len(self.search_results) > 100:
            self.search_results = self.search_results[-100:]

def get_app_state() -> AppState:
    """Get or initialize application state."""
    if "app_state" not in st.session_state:
        st.session_state.app_state = AppState()
    return st.session_state.app_state

# Usage
state = get_app_state()
state.current_query = user_input
state.add_search_result(result)
```

---

## 📊 Performance Standards

### Response Time Targets

| Operation | Target (p95) | Maximum |
|-----------|--------------|---------|
| Search Mode | <60s | 120s |
| Research Mode | <5min | 10min |
| API Health Check | <100ms | 500ms |
| Database Query | <100ms | 1s |
| Vector Search | <500ms | 2s |

### Optimization Techniques

**Caching**
```python
# ✅ GOOD - Cache expensive operations
from functools import lru_cache
import redis

# In-memory cache for pure functions
@lru_cache(maxsize=1000)
def parse_query(query: str) -> ParsedQuery:
    """Parse query with caching."""
    # Expensive parsing operation
    return parsed

# Redis cache for async operations
class CachedEmbeddingService:
    """Embedding service with Redis caching."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")
    
    async def embed(self, text: str) -> list[float]:
        """Generate embedding with caching."""
        cache_key = f"embed:{hash(text)}"
        
        # Check cache
        if cached := await self.redis.get(cache_key):
            return json.loads(cached)
        
        # Generate embedding
        embedding = self.embedder.encode(text).tolist()
        
        # Cache for 1 hour
        await self.redis.setex(cache_key, 3600, json.dumps(embedding))
        
        return embedding
```

**Batch Processing**
```python
# ✅ GOOD - Batch operations
async def process_urls_in_batches(
    urls: list[str],
    batch_size: int = 10
) -> list[dict]:
    """Process URLs in batches to avoid overwhelming servers."""
    results = []
    
    for i in range(0, len(urls), batch_size):
        batch = urls[i:i + batch_size]
        
        # Process batch in parallel
        batch_results = await asyncio.gather(
            *[fetch_url(url) for url in batch],
            return_exceptions=True
        )
        
        results.extend(batch_results)
        
        # Rate limiting between batches
        if i + batch_size < len(urls):
            await asyncio.sleep(1.0)
    
    return results
```

---

## 🔒 Security Standards

### Input Validation

```python
# ✅ GOOD - Validate and sanitize all inputs
from pydantic import validator
import bleach

class UserInput(BaseModel):
    """User input with sanitization."""
    
    query: str
    
    @validator("query")
    def sanitize_query(cls, v: str) -> str:
        """Remove potentially harmful content."""
        # Remove HTML/JavaScript
        cleaned = bleach.clean(v, strip=True)
        # Limit length
        if len(cleaned) > 1000:
            raise ValueError("Query too long")
        return cleaned
```

### API Security

```python
# ✅ GOOD - Rate limiting and authentication
from fastapi import Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
security = HTTPBearer()

@app.post("/v1/search")
@limiter.limit("10/minute")
async def search(
    request: SearchRequest,
    credentials: HTTPAuthorizationCredentials = Security(security)
) -> SearchResponse:
    """Search with rate limiting and auth."""
    # Verify token
    user = await verify_token(credentials.credentials)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    # Execute search
    result = await execute_search(request, user)
    return result
```

---

## 📝 Documentation Standards

### Code Documentation

```python
# ✅ GOOD - Complete docstrings
async def process_research_query(
    query: str,
    max_iterations: int = 3,
    max_sources: int = 80,
    user_id: uuid.UUID,
    db: AsyncSession
) -> ResearchResult:
    """Process research query with iterative refinement.
    
    This function executes a multi-stage research pipeline:
    1. Research planning and query decomposition
    2. Multi-angle search across sources
    3. Deep content extraction with Crawl4AI and Dockling
    4. RAG processing and storage
    5. Initial synthesis
    6. Gap analysis and targeted research
    7. Enhanced final synthesis
    
    Args:
        query: User's research question (1-1000 chars)
        max_iterations: Maximum refinement iterations (1-5)
        max_sources: Maximum sources to process (20-150)
        user_id: ID of requesting user
        db: Async database session
        
    Returns:
        ResearchResult containing:
            - Comprehensive report (Markdown)
            - List of sources with metadata
            - Execution metrics
            - Langfuse trace ID
            
    Raises:
        QueryDecompositionError: If query cannot be decomposed
        SourceFetchError: If source fetching fails critically
        SynthesisError: If final synthesis fails
        DatabaseError: If database operations fail
        
    Example:
        >>> async with AsyncSessionLocal() as db:
        ...     result = await process_research_query(
        ...         query="How does climate change affect oceans?",
        ...         max_iterations=3,
        ...         max_sources=80,
        ...         user_id=user.id,
        ...         db=db
        ...     )
        ...     print(result.report)
        
    Note:
        - This operation may take 3-5 minutes
        - All LLM calls are traced in Langfuse
        - Results are cached for 1 hour
        
    See Also:
        - process_search_query: For faster, simpler searches
        - ResearchPipeline: The underlying pipeline class
    """
    pass
```

---

**This is your development bible. Follow these standards for consistent, high-quality code. 📘**

**Remember: Tests First, Code Second, Quality Always. 🎯**
