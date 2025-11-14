# Research Service API Specification

**Version:** 0.1.0
**Base URL:** `http://localhost:8001/api`
**Documentation:** `http://localhost:8001/api/docs` (Swagger UI)

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base Response Format](#base-response-format)
4. [Endpoints](#endpoints)
   - [Health & Status](#health--status)
   - [Search](#search)
   - [Research](#research)
   - [Documents](#documents)
   - [Sessions](#sessions)
5. [Data Models](#data-models)
6. [Error Handling](#error-handling)
7. [Examples](#examples)
8. [Rate Limiting](#rate-limiting)
9. [Observability](#observability)

---

## Overview

The Research Service API provides intelligent search, deep research, and document analysis capabilities with:

- **Multi-LLM Support**: Configurable LLM backends (DeepSeek R1, Claude, Gemini, etc.)
- **Langfuse Integration**: Full LLM observability and tracing
- **Search Modes**: Speed/Balanced/Deep modes for different use cases
- **Document Management**: Upload and query PDFs, Word docs, Excel sheets, and text files
- **Session Tracking**: Persistent session management for audit trails
- **Observability**: Built-in tracing, logging, and performance monitoring

---

## Authentication

Currently, the API is **open** with no authentication required. For production deployments, implement:

- API Key authentication
- JWT tokens
- OAuth 2.0

**CORS Policy:** All origins allowed (configure for production)

---

## Base Response Format

All responses follow a consistent structure:

```json
{
  "data": {
    "/* endpoint-specific fields */": "..."
  },
  "meta": {
    "timestamp": "2025-11-13T23:35:12.123456Z",
    "version": "0.1.0"
  }
}
```

---

## Endpoints

### Health & Status

#### GET /v1/health

Health check endpoint for monitoring service availability.

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "service": "research-service",
  "version": "0.1.0",
  "environment": "development"
}
```

**Use Cases:**
- Kubernetes liveness/readiness probes
- Load balancer health checks
- Monitoring dashboards

---

### Search

Fast, focused search with query decomposition and source synthesis.

#### POST /v1/search

Performs a quick search and generates an answer from top sources.

**Request:**

```json
{
  "query": "What is Pydantic AI?",
  "mode": "balanced",
  "max_sources": 20,
  "timeout": 60,
  "model": null,
  "search_engine": "auto",
  "prompt_strategy": "auto",
  "enable_diversity": false,
  "enable_recency": false,
  "enable_query_aware": false
}
```

**Request Fields:**

| Field | Type | Required | Default | Range | Description |
|-------|------|----------|---------|-------|-------------|
| `query` | string | ✓ | - | 1-1000 chars | Search query |
| `mode` | enum | ✗ | balanced | speed/balanced/deep | Search depth (affects sources & timeout) |
| `max_sources` | integer | ✗ | null | 5-50 | Override mode's default source count |
| `timeout` | integer | ✗ | null | 10-300 | Timeout in seconds |
| `model` | string | ✗ | null | - | LLM model (e.g., `anthropic/claude-3.5-sonnet`) |
| `search_engine` | enum | ✗ | auto | searxng/serperdev/perplexity/auto | Search backend |
| `prompt_strategy` | enum | ✗ | auto | static/dynamic/auto | System prompt approach |
| `enable_diversity` | boolean | ✗ | false | - | Reduce duplicate results |
| `enable_recency` | boolean | ✗ | false | - | Boost recent sources |
| `enable_query_aware` | boolean | ✗ | false | - | Query-aware scoring |

**Response:** `200 OK`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "What is Pydantic AI?",
  "answer": "Pydantic AI is a library for building AI-powered applications...",
  "sub_queries": [
    {
      "query": "Pydantic AI features",
      "intent": "factual",
      "priority": 1
    }
  ],
  "sources": [
    {
      "title": "Pydantic AI Documentation",
      "url": "https://ai.pydantic.dev",
      "snippet": "Pydantic AI is a library for building AI-powered applications...",
      "relevance": 0.95,
      "semantic_score": 0.92,
      "final_score": 0.94,
      "source_type": "web"
    }
  ],
  "mode": "balanced",
  "execution_time": 12.34,
  "confidence": 0.92,
  "model_used": "deepseek/deepseek-r1:free",
  "trace_url": "https://langfuse.com/trace/xyz123",
  "grounding_score": 0.88,
  "hallucination_count": 0,
  "created_at": "2025-11-13T23:35:12.123456Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | UUID | Unique session identifier |
| `query` | string | Original search query |
| `answer` | string | AI-generated answer based on sources |
| `sub_queries` | array | Decomposed search queries |
| `sources` | array | Retrieved sources with scores |
| `mode` | string | Search mode used (speed/balanced/deep) |
| `execution_time` | float | Total execution time in seconds |
| `confidence` | float | Result confidence (0-1) |
| `model_used` | string | LLM model name |
| `trace_url` | string | Langfuse trace URL (for observability) |
| `grounding_score` | float | Hallucination detection score (0-1) |
| `hallucination_count` | integer | Number of unsupported claims |
| `created_at` | datetime | Response timestamp |

**Error Responses:**

- `400 Bad Request`: Invalid query or parameters
- `408 Request Timeout`: Search exceeded timeout
- `503 Service Unavailable`: Search engines unreachable
- `500 Internal Server Error`: Unexpected error

**Search Modes:**

| Mode | Sources | Timeout | Use Case |
|------|---------|---------|----------|
| `speed` | 5 | 30s | Quick answers, simple queries |
| `balanced` | 10 | 60s | General-purpose searches (default) |
| `deep` | 20 | 120s | Comprehensive research, complex queries |

---

### Research

Deep, iterative research with planning and synthesis.

#### POST /v1/research

Performs comprehensive research with multiple iterations and source synthesis.

**Request:**

```json
{
  "query": "What are AI agents and how do they work?",
  "mode": "balanced",
  "max_iterations": 5,
  "timeout": 300,
  "model": null,
  "prompt_strategy": "auto"
}
```

**Request Fields:**

| Field | Type | Required | Default | Range | Description |
|-------|------|----------|---------|-------|-------------|
| `query` | string | ✓ | - | 1-1000 chars | Research question |
| `mode` | enum | ✗ | balanced | speed/balanced/deep | Search depth |
| `max_iterations` | integer | ✗ | 5 | 1-10 | Max research cycles |
| `timeout` | integer | ✗ | 300 | 60-600 | Timeout in seconds |
| `model` | string | ✗ | null | - | LLM model |
| `prompt_strategy` | enum | ✗ | auto | static/dynamic/auto | Prompt approach |

**Response:** `200 OK`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "What are AI agents and how do they work?",
  "plan": {
    "original_query": "What are AI agents and how do they work?",
    "steps": [
      {
        "step_number": 1,
        "description": "Define AI agents and core concepts",
        "search_query": "what are AI agents definition",
        "expected_outcome": "Definition and key characteristics",
        "depends_on": []
      },
      {
        "step_number": 2,
        "description": "Research agent architectures",
        "search_query": "AI agent architecture components",
        "expected_outcome": "Common agent architectures",
        "depends_on": [1]
      }
    ],
    "estimated_time": 180.5,
    "complexity": "moderate"
  },
  "findings": "AI agents are autonomous systems that perceive their environment and take actions...",
  "citations": [
    {
      "source_id": "1",
      "title": "AI Agents Explained",
      "url": "https://example.com/ai-agents",
      "excerpt": "AI agents are autonomous systems...",
      "relevance": 0.95
    }
  ],
  "confidence": 0.89,
  "execution_time": 145.67,
  "execution_steps": [
    {
      "step": 1,
      "status": "completed",
      "duration": 45.2,
      "sources_found": 12
    }
  ],
  "model_used": "deepseek/deepseek-r1:free",
  "trace_url": "https://langfuse.com/trace/xyz123",
  "created_at": "2025-11-13T23:35:12.123456Z"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | UUID | Unique session identifier |
| `query` | string | Original research question |
| `plan` | object | Execution plan with steps |
| `findings` | string | Synthesized research findings |
| `citations` | array | Source citations used in findings |
| `confidence` | float | Result confidence (0-1) |
| `execution_time` | float | Total execution time in seconds |
| `execution_steps` | array | Detailed execution log |
| `model_used` | string | LLM model name |
| `trace_url` | string | Langfuse trace URL |
| `created_at` | datetime | Response timestamp |

---

### Documents

Document upload and RAG-based querying.

#### POST /documents/upload

Upload and process documents (PDF, Word, Excel, Text).

**Request:**

- **Content-Type:** `multipart/form-data`
- **Fields:**
  - `file` (required): Document file
  - `collection` (optional, default: "default"): Collection name

**cURL Example:**

```bash
curl -X POST http://localhost:8001/api/v1/documents/upload \
  -F "file=@document.pdf" \
  -F "collection=my_research"
```

**Response:** `201 Created`

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "research_paper.pdf",
  "source_type": "pdf",
  "collection": "my_research",
  "chunks_created": 45,
  "embedding_dimension": 384,
  "status": "success",
  "message": "Successfully uploaded and processed 45 chunks"
}
```

**Supported Formats:**

| Format | MIME Type | Max Size | Details |
|--------|-----------|----------|---------|
| PDF | `application/pdf` | 50MB | Text extraction via Dockling |
| Word | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` | 50MB | `.docx` files |
| Excel | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | 50MB | `.xlsx` files |
| Text | `text/plain` | 50MB | Raw text files |

**Chunking Parameters:**

- **Chunk Size:** 1000 characters
- **Chunk Overlap:** 200 characters
- **Max Pages:** 100

---

#### POST /documents/query

Query uploaded documents with RAG (Retrieval-Augmented Generation).

**Request:**

```json
{
  "query": "What are the key findings?",
  "collection": "my_research",
  "top_k": 10,
  "similarity_threshold": 0.3,
  "model": null
}
```

**Request Fields:**

| Field | Type | Required | Default | Range | Description |
|-------|------|----------|---------|-------|-------------|
| `query` | string | ✓ | - | 1-1000 chars | Question about documents |
| `collection` | string | ✗ | default | 1-100 chars | Collection to search |
| `top_k` | integer | ✗ | 10 | 5-50 | Chunks to retrieve |
| `similarity_threshold` | float | ✗ | 0.3 | 0.0-1.0 | Minimum similarity score |
| `model` | string | ✗ | null | - | LLM model for answer generation |

**Response:** `200 OK`

```json
{
  "query": "What are the key findings?",
  "answer": "Based on the uploaded documents, the key findings include...",
  "sources": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "Research findings show that...",
      "metadata": {
        "chunk_id": 5,
        "filename": "research_paper.pdf",
        "collection": "my_research"
      },
      "source_type": "pdf",
      "similarity": 0.92,
      "created_at": "2025-11-13T23:29:08.854550"
    }
  ],
  "total_chunks_found": 12,
  "chunks_used": 3,
  "execution_time": 8.99,
  "trace_url": "https://langfuse.com/trace/xyz123"
}
```

**Response Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | Original query |
| `answer` | string | Generated answer from documents |
| `sources` | array | Retrieved document chunks |
| `total_chunks_found` | integer | Total chunks above threshold |
| `chunks_used` | integer | Chunks used for answer generation |
| `execution_time` | float | Query execution time in seconds |
| `trace_url` | string | Langfuse trace URL |

---

#### GET /documents

List uploaded documents.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `collection` | string | null | Filter by collection name |
| `skip` | integer | 0 | Pagination offset |
| `limit` | integer | 50 | Pagination limit (max 100) |

**Response:** `200 OK`

```json
{
  "documents": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "research_paper.pdf",
      "source_type": "pdf",
      "collection": "my_research",
      "chunks_count": 45,
      "created_at": "2025-11-13T23:29:08.854550",
      "last_accessed": "2025-11-13T23:35:12.123456",
      "access_count": 3
    }
  ],
  "total": 5,
  "skip": 0,
  "limit": 50
}
```

---

#### DELETE /documents/{document_id}

Delete an uploaded document.

**Response:** `200 OK`

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "deleted",
  "message": "Document and associated chunks deleted successfully"
}
```

---

### Sessions

Session management for tracking and auditing.

#### GET /v1/sessions/{session_id}

Retrieve a specific session and its result.

**Response:** `200 OK`

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "What is Pydantic AI?",
  "mode": "search",
  "result": {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "What is Pydantic AI?",
    "answer": "Pydantic AI is a library...",
    "sources": [...],
    "execution_time": 12.34,
    "confidence": 0.92
  },
  "created_at": "2025-11-13T23:35:12.123456Z",
  "completed_at": "2025-11-13T23:35:25.234567Z"
}
```

---

## Data Models

### SearchSourceResponse

Individual source in search results.

```json
{
  "title": "Source Title",
  "url": "https://example.com",
  "snippet": "Content excerpt from the source...",
  "relevance": 0.95,
  "semantic_score": 0.92,
  "final_score": 0.94,
  "source_type": "web"
}
```

### SubQueryResponse

Sub-query from query decomposition.

```json
{
  "query": "Pydantic AI features",
  "intent": "factual",
  "priority": 1
}
```

### CitationResponse

Citation in research findings.

```json
{
  "source_id": "1",
  "title": "AI Agents Explained",
  "url": "https://example.com/ai-agents",
  "excerpt": "AI agents are autonomous systems...",
  "relevance": 0.95
}
```

### ResearchStepResponse

Individual research step.

```json
{
  "step_number": 1,
  "description": "Define AI agents and core concepts",
  "search_query": "what are AI agents definition",
  "expected_outcome": "Definition and key characteristics",
  "depends_on": []
}
```

---

## Error Handling

All errors follow a consistent format:

```json
{
  "error": "invalid_request",
  "message": "Query cannot be empty or whitespace-only",
  "details": [
    {
      "field": "query",
      "message": "Query cannot be empty",
      "type": "validation_error"
    }
  ],
  "trace_id": "abc123xyz"
}
```

### Error Codes

| Code | Status | Description | Solution |
|------|--------|-------------|----------|
| `invalid_request` | 400 | Invalid request format or parameters | Check request format and required fields |
| `validation_error` | 400 | Request validation failed | See `details` field for specific issues |
| `document_not_found` | 404 | Document or collection not found | Verify document_id or collection name |
| `collection_not_found` | 404 | Collection doesn't exist | Create collection or check name |
| `search_timeout` | 408 | Search exceeded timeout | Increase timeout or simplify query |
| `search_unavailable` | 503 | Search engines unreachable | Retry later or check search configuration |
| `internal_error` | 500 | Unexpected server error | Contact support with trace_id |

---

## Examples

### Example 1: Quick Search

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are LLMs?",
    "mode": "speed",
    "timeout": 30
  }'
```

### Example 2: Deep Research

```bash
curl -X POST http://localhost:8001/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do transformer models work in machine learning?",
    "mode": "deep",
    "max_iterations": 5,
    "timeout": 300
  }'
```

### Example 3: Document Upload and Query

```bash
# Upload a document
curl -X POST http://localhost:8001/api/v1/documents/upload \
  -F "file=@research.pdf" \
  -F "collection=my_papers"

# Query the document
curl -X POST http://localhost:8001/api/v1/documents/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main conclusions?",
    "collection": "my_papers",
    "top_k": 10
  }'
```

### Example 4: Session Tracking

```bash
# Extract session_id from search response
SESSION_ID="550e8400-e29b-41d4-a716-446655440000"

# Retrieve session details
curl http://localhost:8001/api/v1/sessions/$SESSION_ID
```

---

## Rate Limiting

**Default Rate Limit:** 10 requests per minute (configurable via `API_RATE_LIMIT`)

**Response Headers:**

```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8
X-RateLimit-Reset: 1699900260
```

**When Rate Limited (429):**

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests. Try again in 30 seconds.",
  "retry_after": 30
}
```

---

## Observability

### Langfuse Integration

All requests are traced in Langfuse with:

- **Trace ID**: Unique identifier for entire request
- **Span Tracking**: LLM calls, searches, document processing
- **Token Usage**: Input/output token counts
- **Latency Metrics**: End-to-end and per-component timing
- **Error Tracking**: Exceptions and failures

**Accessing Traces:**

The `trace_url` field in responses links directly to Langfuse:

```json
{
  "trace_url": "https://langfuse.com/trace/xyz123?projectId=abc"
}
```

### Logging

Structured JSON logging with:

- Request ID for correlation
- Operation type (search, research, upload)
- Duration and token counts
- Errors and warnings

**Log Level Configuration:** `LOG_LEVEL` environment variable

```
INFO: Normal operation
DEBUG: Detailed tracing (Langfuse flushes, cache hits)
WARNING: Degraded modes, fallbacks
ERROR: Failures and exceptions
```

### Metrics

Key metrics to monitor:

- **Request latency** (p50, p95, p99)
- **Error rate** by endpoint
- **Token usage** by model
- **Search engine availability**
- **Database query times**
- **Cache hit rates**

---

## Configuration

Key environment variables:

```env
# LLM Configuration
RESEARCH_LLM_MODEL=deepseek/deepseek-r1:free
RESEARCH_LLM_TEMPERATURE=0.3
RESEARCH_LLM_MAX_TOKENS=8192
RESEARCH_LLM_TIMEOUT=180

# Langfuse
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Search
SEARXNG_BASE_URL=http://localhost:8080
SERPER_API_KEY=...
PERPLEXITY_API_KEY=...

# API
API_RATE_LIMIT=10/minute
LOG_LEVEL=INFO
```

---

## Support

- **API Documentation:** `http://localhost:8001/api/docs`
- **ReDoc:** `http://localhost:8001/api/redoc`
- **OpenAPI Schema:** `http://localhost:8001/api/openapi.json`
