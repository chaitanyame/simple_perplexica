# Research Service API - Quick Reference Guide

**Base URL:** `http://localhost:8001/api`

**API Docs:** `http://localhost:8001/api/docs` (Swagger UI)

---

## Common Use Cases

### 1. Quick Answer (30 seconds)

**Use Case:** Get a quick answer to a simple question.

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Python?",
    "mode": "speed",
    "timeout": 30
  }'
```

**Expected Response Time:** 10-30 seconds
**Sources Retrieved:** ~5
**Best For:** Simple factual questions

---

### 2. Balanced Research (60 seconds)

**Use Case:** Get a comprehensive answer with moderate research depth.

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do transformer models work?",
    "mode": "balanced"
  }'
```

**Expected Response Time:** 30-90 seconds
**Sources Retrieved:** ~10
**Best For:** General research, news articles

---

### 3. Deep Research (5 minutes)

**Use Case:** Comprehensive research with iterative refinement.

```bash
curl -X POST http://localhost:8001/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest advancements in AI?",
    "mode": "deep",
    "max_iterations": 5,
    "timeout": 300
  }'
```

**Expected Response Time:** 2-5 minutes
**Sources Retrieved:** ~20+ per iteration
**Best For:** Complex topics, comprehensive reports

---

### 4. Document Q&A

**Use Case:** Upload a document and ask questions about it.

```bash
# Upload
curl -X POST http://localhost:8001/api/v1/documents/upload \
  -F "file=@research_paper.pdf" \
  -F "collection=research"

# Query
curl -X POST http://localhost:8001/api/v1/documents/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings?",
    "collection": "research"
  }'
```

**Expected Response Time:** 5-15 seconds
**Best For:** Knowledge extraction from documents

---

## Endpoint Comparison

| Endpoint | Speed | Sources | Iterations | Use Case |
|----------|-------|---------|-----------|----------|
| `/v1/search` (speed) | 10-30s | 5 | 1 | Quick answers |
| `/v1/search` (balanced) | 30-90s | 10 | 1 | General research |
| `/v1/search` (deep) | 60-120s | 20 | 1 | Comprehensive search |
| `/v1/research` (speed) | 30-60s | 5 | 2 | Quick research |
| `/v1/research` (balanced) | 90-180s | 10 | 3-5 | Thorough research |
| `/v1/research` (deep) | 2-5m | 20 | 5 | Deep analysis |
| `/documents/query` | 5-15s | 10 | 0 | Document Q&A |

---

## Common Curl Commands

### Health Check
```bash
curl http://localhost:8001/api/v1/health
```

### Search with Custom Parameters
```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Pydantic?",
    "mode": "balanced",
    "max_sources": 15,
    "timeout": 60,
    "search_engine": "auto"
  }'
```

### Research with Custom LLM
```bash
curl -X POST http://localhost:8001/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are AI agents?",
    "model": "anthropic/claude-3.5-sonnet",
    "max_iterations": 5
  }'
```

### Upload Document with Collection
```bash
curl -X POST http://localhost:8001/api/v1/documents/upload \
  -F "file=@document.pdf" \
  -F "collection=my_papers"
```

### Query with Similarity Threshold
```bash
curl -X POST http://localhost:8001/api/v1/documents/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is the conclusion?",
    "collection": "my_papers",
    "top_k": 5,
    "similarity_threshold": 0.5
  }'
```

### List Documents
```bash
curl "http://localhost:8001/api/v1/documents?collection=my_papers&limit=10"
```

### Get Session Details
```bash
curl http://localhost:8001/api/v1/sessions/550e8400-e29b-41d4-a716-446655440000
```

---

## Python Client Examples

### Using Python Requests

```python
import requests
import json
import time

BASE_URL = "http://localhost:8001/api"

# Quick search
response = requests.post(
    f"{BASE_URL}/v1/search",
    json={
        "query": "What is machine learning?",
        "mode": "speed"
    }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Confidence: {result['confidence']}")
print(f"Time: {result['execution_time']}s")
print(f"Trace URL: {result['trace_url']}")
```

### Document Upload and Query

```python
import requests

BASE_URL = "http://localhost:8001/api"

# Upload
with open("paper.pdf", "rb") as f:
    response = requests.post(
        f"{BASE_URL}/v1/documents/upload",
        files={"file": f},
        data={"collection": "research"}
    )
    doc_id = response.json()["document_id"]
    print(f"Uploaded: {doc_id}")

# Query
response = requests.post(
    f"{BASE_URL}/v1/documents/query",
    json={
        "query": "What are the key findings?",
        "collection": "research"
    }
)

result = response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {len(result['sources'])}")
```

### Async Research with Polling

```python
import requests
import time

BASE_URL = "http://localhost:8001/api"

# Start research
response = requests.post(
    f"{BASE_URL}/v1/research",
    json={
        "query": "What are transformer models?",
        "max_iterations": 5
    }
)

session_id = response.json()["session_id"]
print(f"Started research: {session_id}")

# Poll for results
while True:
    response = requests.get(f"{BASE_URL}/v1/sessions/{session_id}")
    session = response.json()

    if session["completed_at"]:
        print("Research complete!")
        print(f"Findings: {session['result']['findings'][:200]}...")
        break

    print("Still researching...")
    time.sleep(10)
```

---

## Search Modes Explained

### Speed Mode
- **Purpose:** Quick answers for simple questions
- **Sources:** 5
- **Time:** 10-30 seconds
- **Example:** "Who won the 2024 World Cup?"

### Balanced Mode (Default)
- **Purpose:** Most common use case
- **Sources:** 10
- **Time:** 30-90 seconds
- **Example:** "How does machine learning work?"

### Deep Mode
- **Purpose:** Comprehensive research, complex topics
- **Sources:** 20
- **Time:** 60-120 seconds
- **Example:** "What are the latest advancements in quantum computing?"

---

## Search Engines

### Auto (Recommended)
- Tries SearXNG first
- Falls back to SerperDev
- Finally tries Perplexity
- **Best for:** Reliability

### SearXNG
- Open-source metasearch engine
- No API key required
- **Best for:** Privacy, offline deployments

### SerperDev
- Google Search API
- Requires API key
- **Best for:** Accuracy, structured results

### Perplexity
- AI-powered search
- Provides citations
- **Best for:** AI-generated summaries

---

## Prompt Strategies

### Static
- Uses fixed, pre-defined prompts
- Consistent results
- Faster processing
- **Best for:** Production, reliability

### Dynamic
- Adapts prompts based on query
- Better for specific queries
- Slightly slower
- **Best for:** Research, exploration

### Auto (Default)
- Uses config setting (`ENABLE_DYNAMIC_PROMPTS`)
- Automatic selection
- **Best for:** General use

---

## Rate Limiting

**Default:** 10 requests/minute

Check headers:
```bash
curl -i http://localhost:8001/api/v1/health
```

Response headers:
```
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 9
X-RateLimit-Reset: 1699900260
```

**Too many requests? Response:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests",
  "retry_after": 30
}
```

---

## Error Handling

### Validation Error
```json
{
  "error": "invalid_request",
  "message": "Query cannot be empty",
  "details": [
    {
      "field": "query",
      "message": "Query cannot be empty or whitespace-only",
      "type": "validation_error"
    }
  ]
}
```

**Solution:** Check request format and required fields

### Timeout
```json
{
  "error": "search_timeout",
  "message": "Search exceeded 30 seconds"
}
```

**Solution:** Increase timeout or simplify query

### Not Found
```json
{
  "error": "not_found",
  "message": "Collection 'my_research' not found"
}
```

**Solution:** Verify collection name or upload documents first

### Internal Error
```json
{
  "error": "internal_error",
  "message": "Unexpected error",
  "trace_id": "abc123xyz"
}
```

**Solution:** Contact support with trace_id

---

## Response Examples

### Successful Search Response
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "What is Pydantic?",
  "answer": "Pydantic is a data validation library for Python...",
  "sub_queries": [
    {
      "query": "Pydantic Python library",
      "intent": "factual",
      "priority": 1
    }
  ],
  "sources": [
    {
      "title": "Pydantic Documentation",
      "url": "https://docs.pydantic.dev/",
      "snippet": "Pydantic is a data validation library...",
      "relevance": 0.98,
      "semantic_score": 0.95,
      "final_score": 0.97,
      "source_type": "web"
    }
  ],
  "mode": "balanced",
  "execution_time": 45.23,
  "confidence": 0.93,
  "model_used": "deepseek/deepseek-r1:free",
  "trace_url": "https://langfuse.com/trace/xyz123",
  "grounding_score": 0.91,
  "hallucination_count": 0,
  "created_at": "2025-11-13T23:35:12.123456Z"
}
```

### Document Query Response
```json
{
  "query": "What are the key findings?",
  "answer": "Based on the document, the key findings include...",
  "sources": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "The research shows that...",
      "metadata": {
        "chunk_id": 5,
        "filename": "research.pdf",
        "collection": "my_papers"
      },
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

---

## Observability & Debugging

### Using Trace URLs
Every response includes a `trace_url`:
```json
{
  "trace_url": "https://langfuse.com/trace/xyz123?projectId=abc"
}
```

Click to view in Langfuse:
- LLM calls and tokens
- Response time breakdown
- Errors and warnings
- Full request/response logs

### Checking Logs
```bash
# View recent logs
docker-compose logs research-api | tail -20

# Follow logs
docker-compose logs -f research-api

# Filter by trace
docker-compose logs research-api | grep "xyz123"
```

### Debugging Failed Requests
```bash
# Get trace_id from error response
# Use it to find logs:
docker-compose logs research-api | grep "abc123xyz"

# Check Langfuse dashboard
# Go to trace URL provided in response
```

---

## Performance Tips

### 1. Use Appropriate Mode
- Speed mode for simple queries (saves time and money)
- Balanced for general use
- Deep only when necessary

### 2. Set Realistic Timeouts
- Speed: 30s
- Balanced: 60s
- Deep: 120s

### 3. Use Custom Models Wisely
- Free models (DeepSeek, Gemini) good for cost
- Claude for quality
- Match model to query complexity

### 4. Optimize Document Queries
- Use `similarity_threshold` to filter noise
- Set `top_k` based on document size
- Choose relevant collection

### 5. Monitor Token Usage
- Check `trace_url` for token counts
- Longer queries = more tokens
- Use shorter, focused queries

---

## Support & Resources

| Resource | URL |
|----------|-----|
| Swagger UI | http://localhost:8001/api/docs |
| ReDoc | http://localhost:8001/api/redoc |
| OpenAPI Schema | http://localhost:8001/api/openapi.json |
| Full Specification | API_SPECIFICATION.md |
| OpenAPI YAML | openapi.yaml |

---

## Environment Configuration

Key environment variables:

```env
# Search Configuration
SEARCH_MAX_QUERIES=4
SEARCH_MAX_SOURCES=20

# Research Configuration
RESEARCH_MAX_ITERATIONS=3
RESEARCH_MAX_SOURCES=80

# Rate Limiting
API_RATE_LIMIT=10/minute

# Logging
LOG_LEVEL=INFO

# LLM Model
RESEARCH_LLM_MODEL=deepseek/deepseek-r1:free

# Langfuse
LANGFUSE_PUBLIC_KEY=...
LANGFUSE_SECRET_KEY=...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

See `.env` file for complete configuration options.
