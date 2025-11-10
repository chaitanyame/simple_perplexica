# Phase 2 Week 4: Agent System - Planning Document

**Status**: ✅ Planning Complete - Ready for Implementation  
**Date**: 2025-01-XX  
**Focus**: SearchAgent and ResearchAgent with Pydantic AI  

---

## 📋 Executive Summary

Phase 2 introduces an **intelligent agent system** using **Pydantic AI** to coordinate complex search and research workflows. The agents will leverage Phase 1's foundation (LLM client, document processing, embeddings, vector store) to provide sophisticated query understanding and multi-step research capabilities.

### Key Deliverables
- **SearchAgent**: Query decomposition, search coordination, result ranking
- **ResearchAgent**: Multi-step research planning, iterative refinement, citation management
- **Target**: 150-160 tests (add ~20-25 agent tests), maintain 85%+ coverage
- **Quality**: TDD workflow (RED → GREEN → REFACTOR), mypy --strict, ruff clean

---

## 🎯 Week 4 Goals

### 1. SearchAgent Implementation
**Purpose**: Intelligent search coordination and query understanding

**Core Capabilities**:
- **Query Decomposition**: Break complex queries into focused sub-queries
- **Search Coordination**: Orchestrate parallel searches across multiple sources (SearxNG, SerperDev)
- **Result Ranking**: Intelligent relevance scoring and deduplication
- **Source Filtering**: Quality assessment and filtering

**Success Metrics**:
- 10-12 comprehensive tests covering all capabilities
- 90%+ code coverage for SearchAgent module
- Sub-200ms average query decomposition time
- Accurate multi-source result merging

### 2. ResearchAgent Implementation
**Purpose**: Multi-step research planning and execution

**Core Capabilities**:
- **Research Planning**: Generate step-by-step research plans
- **Iterative Refinement**: Adapt plan based on intermediate findings
- **Citation Management**: Track and organize source citations
- **Multi-Agent Coordination**: Delegate to SearchAgent for data gathering

**Success Metrics**:
- 10-12 comprehensive tests covering workflow scenarios
- 90%+ code coverage for ResearchAgent module
- Successful multi-step research execution
- Proper citation tracking and deduplication

---

## 🏗️ Pydantic AI Architecture

### Overview
Pydantic AI provides a **FastAPI-like** developer experience for building AI agents with:
- Type-safe dependency injection
- Structured output validation
- Built-in tool calling
- OpenRouter LLM integration via `openai` client
- Langfuse tracing support

### Core Concepts

#### 1. Agent Definition
```python
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel

class SearchOutput(BaseModel):
    """Type-safe structured output"""
    answer: str
    sources: list[dict[str, Any]]
    confidence: float

agent = Agent[SearchDeps, SearchOutput](
    'openai:gpt-4',  # Model via OpenRouter
    deps_type=SearchDeps,
    output_type=SearchOutput,
    instructions='You are a search coordinator...'
)
```

#### 2. Dependency Injection
```python
from dataclasses import dataclass

@dataclass
class SearchDeps:
    """Type-safe dependencies"""
    llm_client: OpenRouterClient
    db: AsyncSession
    tracer: LangfuseTracer
```

#### 3. Tool Registration
```python
@agent.tool
async def search_web(ctx: RunContext[SearchDeps], query: str) -> list[dict]:
    """Search external sources"""
    # Access dependencies via ctx.deps
    results = await ctx.deps.llm_client.search(query)
    return results
```

#### 4. Structured Output Modes

**NativeOutput (Recommended)**:
- Uses model's native structured output capabilities
- Faster and more reliable than ToolOutput
- Best for OpenAI models via OpenRouter

```python
from pydantic_ai import Agent, NativeOutput

agent = Agent(
    'openai:gpt-4',
    output_type=NativeOutput(SearchOutput)
)
```

**ToolOutput (Alternative)**:
- Instructs model to call internal tool for structured data
- Use if NativeOutput not supported by model

```python
from pydantic_ai import ToolOutput

agent = Agent(
    'openai:gpt-4',
    output_type=ToolOutput(SearchOutput)
)
```

#### 5. Agent Execution
```python
# Synchronous (for testing)
result = agent.run_sync('What is AI?', deps=deps)
print(result.output)  # Type: SearchOutput
print(result.usage())  # Token usage

# Asynchronous (production)
result = await agent.run('What is AI?', deps=deps)

# Streaming
async with agent.run_stream('What is AI?', deps=deps) as result:
    async for text in result.stream_text():
        print(text)
```

---

## 🔧 SearchAgent Design

### Architecture

```
SearchAgent
├── Query Decomposition Tool
│   ├── Complex query analysis
│   ├── Sub-query generation
│   └── Intent classification
├── Search Coordination Tool
│   ├── Parallel search execution
│   ├── Source prioritization
│   └── Timeout management
├── Result Ranking Tool
│   ├── Relevance scoring
│   ├── Source quality assessment
│   └── Deduplication
└── Output Validation
    ├── Source count validation
    ├── Relevance threshold check
    └── Citation formatting
```

### Pydantic Models

```python
# src/agents/search_agent.py

from pydantic import BaseModel, Field

class SubQuery(BaseModel):
    """Decomposed sub-query"""
    query: str = Field(..., min_length=1, max_length=200)
    intent: str = Field(..., description="factual|opinion|definition")
    priority: int = Field(ge=1, le=5)

class SearchSource(BaseModel):
    """Search result source"""
    title: str
    url: str
    snippet: str
    relevance: float = Field(ge=0.0, le=1.0)
    source_type: str  # web|academic|news

class SearchOutput(BaseModel):
    """Final search output"""
    sub_queries: list[SubQuery]
    sources: list[SearchSource]
    execution_time: float
    confidence: float = Field(ge=0.0, le=1.0)
```

### Dependencies

```python
@dataclass
class SearchAgentDeps:
    """SearchAgent dependencies"""
    llm_client: OpenRouterClient
    tracer: LangfuseTracer
    db: AsyncSession
    searxng_client: httpx.AsyncClient
    serperdev_api_key: str
    max_sources: int = 20
    timeout: float = 60.0
```

### Tools

#### 1. Query Decomposition
```python
@search_agent.tool
async def decompose_query(
    ctx: RunContext[SearchAgentDeps],
    complex_query: str
) -> list[SubQuery]:
    """
    Break complex query into focused sub-queries.
    
    Args:
        ctx: Agent context with dependencies
        complex_query: User's complex question
        
    Returns:
        List of sub-queries with intent and priority
    """
    # LLM call via ctx.deps.llm_client
    # Return structured SubQuery list
    pass
```

#### 2. Search Coordination
```python
@search_agent.tool
async def coordinate_search(
    ctx: RunContext[SearchAgentDeps],
    sub_queries: list[SubQuery]
) -> list[SearchSource]:
    """
    Execute parallel searches across multiple sources.
    
    Args:
        ctx: Agent context with dependencies
        sub_queries: Decomposed queries to search
        
    Returns:
        Combined and deduplicated search results
    """
    # Parallel execution with asyncio.gather
    # Call SearxNG and SerperDev
    # Deduplicate by URL
    pass
```

#### 3. Result Ranking
```python
@search_agent.tool
async def rank_results(
    ctx: RunContext[SearchAgentDeps],
    sources: list[SearchSource],
    original_query: str
) -> list[SearchSource]:
    """
    Rank and filter results by relevance.
    
    Args:
        ctx: Agent context
        sources: Raw search results
        original_query: User's original question
        
    Returns:
        Top-ranked sources (up to max_sources)
    """
    # Embedding-based relevance scoring
    # Quality filtering
    # Return top-k results
    pass
```

### Output Validation

```python
@search_agent.output_validator
async def validate_search_output(
    ctx: RunContext[SearchAgentDeps],
    output: SearchOutput
) -> SearchOutput:
    """
    Validate search output meets quality criteria.
    
    Raises:
        ModelRetry: If output doesn't meet criteria
    """
    if len(output.sources) < 5:
        raise ModelRetry('Need at least 5 sources')
    
    if output.confidence < 0.5:
        raise ModelRetry('Confidence too low, refine search')
    
    return output
```

---

## 🔧 ResearchAgent Design

### Architecture

```
ResearchAgent
├── Research Planning Tool
│   ├── Multi-step plan generation
│   ├── Dependency analysis
│   └── Time estimation
├── Search Delegation Tool (calls SearchAgent)
│   ├── Query formulation
│   ├── Result collection
│   └── Citation extraction
├── Synthesis Tool
│   ├── Cross-source analysis
│   ├── Contradiction detection
│   └── Gap identification
└── Citation Management
    ├── Source tracking
    ├── Deduplication
    └── Formatting
```

### Pydantic Models

```python
# src/agents/research_agent.py

class ResearchStep(BaseModel):
    """Single research step"""
    step_number: int = Field(ge=1)
    description: str
    search_query: str
    expected_outcome: str
    depends_on: list[int] = Field(default_factory=list)

class ResearchPlan(BaseModel):
    """Multi-step research plan"""
    original_query: str
    steps: list[ResearchStep]
    estimated_time: float
    complexity: str = Field(pattern=r'^(simple|medium|complex)$')

class Citation(BaseModel):
    """Research citation"""
    source_id: str
    title: str
    url: str
    excerpt: str
    relevance: float

class ResearchOutput(BaseModel):
    """Final research output"""
    plan: ResearchPlan
    findings: str = Field(..., min_length=100)
    citations: list[Citation]
    confidence: float = Field(ge=0.0, le=1.0)
    execution_steps: int
```

### Dependencies

```python
@dataclass
class ResearchAgentDeps:
    """ResearchAgent dependencies"""
    llm_client: OpenRouterClient
    tracer: LangfuseTracer
    db: AsyncSession
    search_agent: 'SearchAgent'  # Agent delegation
    vector_store: VectorStoreRepository
    max_iterations: int = 5
    timeout: float = 300.0
```

### Multi-Agent Coordination

```python
@research_agent.tool
async def gather_evidence(
    ctx: RunContext[ResearchAgentDeps],
    search_query: str
) -> list[SearchSource]:
    """
    Delegate to SearchAgent for evidence gathering.
    
    Args:
        ctx: Agent context
        search_query: Query for SearchAgent
        
    Returns:
        Search results from SearchAgent
    """
    # Delegate to SearchAgent
    result = await ctx.deps.search_agent.run(
        search_query,
        deps=SearchAgentDeps(...),  # Construct deps
        usage=ctx.usage  # Share usage tracking
    )
    
    return result.output.sources
```

---

## 🧪 Testing Strategy (TDD)

### Test Structure

```
tests/unit/agents/
├── __init__.py
├── test_search_agent.py        # 10-12 tests
└── test_research_agent.py      # 10-12 tests

tests/integration/agents/
├── __init__.py
├── test_search_pipeline.py     # 3-5 tests
└── test_research_pipeline.py   # 3-5 tests
```

### SearchAgent Test Plan

**tests/unit/agents/test_search_agent.py** (10-12 tests):

1. `test_search_agent_initialization` - Agent setup with dependencies
2. `test_decompose_simple_query` - Simple query → single sub-query
3. `test_decompose_complex_query` - Complex query → multiple sub-queries
4. `test_decompose_query_with_intent_classification` - Intent detection (factual/opinion/definition)
5. `test_coordinate_search_parallel_execution` - Multiple sources called in parallel
6. `test_coordinate_search_deduplication` - Duplicate URLs removed
7. `test_coordinate_search_timeout_handling` - Graceful timeout behavior
8. `test_rank_results_by_relevance` - Results sorted by relevance score
9. `test_rank_results_quality_filtering` - Low-quality sources filtered
10. `test_output_validation_min_sources` - Validates minimum source count
11. `test_output_validation_confidence_threshold` - Validates confidence level
12. `test_search_agent_full_workflow` - End-to-end search execution

**Test Pattern (AAA)**:
```python
# tests/unit/agents/test_search_agent.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from pydantic_ai.models.test import TestModel

from src.agents.search_agent import SearchAgent, SearchAgentDeps, SearchOutput

@pytest.mark.asyncio
async def test_decompose_complex_query():
    """Test that SearchAgent decomposes complex query into sub-queries.
    
    Given: A SearchAgent with mocked dependencies
    When: Decomposing a complex query
    Then: Returns multiple focused sub-queries with intent classification
    """
    # Arrange
    mock_llm = AsyncMock()
    mock_tracer = MagicMock()
    mock_db = AsyncMock()
    
    deps = SearchAgentDeps(
        llm_client=mock_llm,
        tracer=mock_tracer,
        db=mock_db,
        searxng_client=AsyncMock(),
        serperdev_api_key='test_key'
    )
    
    agent = SearchAgent(deps=deps)
    
    # Mock LLM response for decomposition
    mock_llm.chat.return_value = {
        'sub_queries': [
            {'query': 'what are AI agents', 'intent': 'definition', 'priority': 1},
            {'query': 'how do AI agents work', 'intent': 'factual', 'priority': 2}
        ]
    }
    
    # Act
    result = await agent.decompose_query('What are AI agents and how do they work?')
    
    # Assert
    assert len(result.sub_queries) == 2
    assert result.sub_queries[0].intent == 'definition'
    assert result.sub_queries[1].intent == 'factual'
    assert result.sub_queries[0].priority < result.sub_queries[1].priority
    mock_llm.chat.assert_called_once()
```

### ResearchAgent Test Plan

**tests/unit/agents/test_research_agent.py** (10-12 tests):

1. `test_research_agent_initialization` - Agent setup with SearchAgent delegation
2. `test_generate_research_plan_simple_query` - Simple query → 1-2 steps
3. `test_generate_research_plan_complex_query` - Complex query → 3+ steps
4. `test_plan_step_dependencies` - Steps have correct dependency order
5. `test_gather_evidence_via_search_agent` - SearchAgent delegation works
6. `test_synthesize_findings_from_sources` - Cross-source synthesis
7. `test_citation_extraction_and_formatting` - Citations properly tracked
8. `test_citation_deduplication` - Duplicate sources removed
9. `test_iterative_refinement_workflow` - Plan adapts based on findings
10. `test_output_validation_min_citations` - Validates citation count
11. `test_output_validation_findings_length` - Validates findings quality
12. `test_research_agent_full_workflow` - End-to-end research execution

---

## 📦 Implementation Checklist

### RED Phase (Tests First) ✅
- [ ] Create `tests/unit/agents/__init__.py`
- [ ] Create `tests/unit/agents/test_search_agent.py` with 10-12 tests
- [ ] Create `tests/unit/agents/test_research_agent.py` with 10-12 tests
- [ ] Run tests → confirm all tests FAIL with `ModuleNotFoundError`
- [ ] Commit: `test(agents): add SearchAgent and ResearchAgent tests (RED phase)`

### GREEN Phase (Minimal Implementation) ✅
- [ ] Create `src/agents/__init__.py`
- [ ] Create `src/agents/search_agent.py` with SearchAgent implementation
- [ ] Create `src/agents/research_agent.py` with ResearchAgent implementation
- [ ] Run tests → confirm all tests PASS
- [ ] Coverage check → ensure 90%+ for agent modules
- [ ] Commit: `feat(agents): implement SearchAgent and ResearchAgent (GREEN phase)`

### REFACTOR Phase (Quality Pass) ✅
- [ ] Add comprehensive docstrings to all agents, tools, models
- [ ] Run `mypy --strict src/agents/` → fix all type errors
- [ ] Run `ruff check src/agents/` → fix all linting issues
- [ ] Run `ruff format src/agents/` → format code
- [ ] Performance optimization (if needed)
- [ ] Run full test suite → ensure 100% pass rate
- [ ] Commit: `refactor(agents): quality pass with mypy and docstrings (REFACTOR phase)`

### Integration Tests ✅
- [ ] Create `tests/integration/agents/__init__.py`
- [ ] Create `tests/integration/agents/test_search_pipeline.py` (3-5 tests)
- [ ] Create `tests/integration/agents/test_research_pipeline.py` (3-5 tests)
- [ ] Run integration tests with real DB and LLM (mocked external APIs)
- [ ] Commit: `test(agents): add integration tests for agent pipelines`

### Documentation ✅
- [ ] Create `docs/PHASE2_WEEK4_PROGRESS.md` with comprehensive report
- [ ] Update `ROADMAP.md` with Week 4 completion status
- [ ] Add agent examples to `docs/PROCESS_FLOWS.md`
- [ ] Commit: `docs(week4): complete Week 4 with Agent System`

---

## 🎯 Success Criteria

### Code Quality
- ✅ **TDD Compliance**: All tests written BEFORE implementation
- ✅ **Test Coverage**: 90%+ for `src/agents/` module
- ✅ **Type Safety**: `mypy --strict` passing
- ✅ **Linting**: `ruff check` passing
- ✅ **Docstrings**: All public APIs documented

### Functionality
- ✅ **SearchAgent**: Query decomposition, search coordination, result ranking working
- ✅ **ResearchAgent**: Multi-step planning, SearchAgent delegation, citation management working
- ✅ **Integration**: Agents work with Phase 1 foundation (LLM, DB, embeddings)

### Performance
- ✅ **SearchAgent**: Sub-200ms query decomposition
- ✅ **ResearchAgent**: Complete research in < 60 seconds (simple queries)
- ✅ **Token Efficiency**: Reasonable token usage per query

### Metrics
- ✅ **Total Tests**: 150-160 (adding ~20-25 agent tests)
- ✅ **Overall Coverage**: 85%+
- ✅ **Commits**: 3-4 well-structured commits (RED, GREEN, REFACTOR, integration)

---

## 🚀 Next Steps (Week 5)

After Week 4 completion, Week 5 will focus on:

1. **FastAPI Endpoints** (v1/search, v1/research)
2. **End-to-End Pipeline Integration**
3. **Streamlit UI Integration**
4. **Performance Optimization**
5. **Production-Ready Error Handling**

---

## 📚 References

- **Pydantic AI Docs**: https://ai.pydantic.dev/
- **Pydantic AI GitHub**: https://github.com/pydantic/pydantic-ai
- **OpenRouter Integration**: Via `openai` client with custom base URL
- **Langfuse Tracing**: Already implemented in Phase 1
- **TDD Best Practices**: `docs/DEVELOPMENT_STANDARDS.md`

---

**Status**: ✅ Ready for Implementation  
**Next**: Begin RED phase with `test_search_agent.py`
