# Research Service API - Testing Guide

This guide provides comprehensive testing procedures for the Research Service API.

---

## Table of Contents

1. [Pre-requisites](#pre-requisites)
2. [Health Check](#health-check)
3. [Search Endpoint Tests](#search-endpoint-tests)
4. [Research Endpoint Tests](#research-endpoint-tests)
5. [Document Endpoints Tests](#document-endpoints-tests)
6. [Session Endpoints Tests](#session-endpoints-tests)
7. [Error Handling Tests](#error-handling-tests)
8. [Performance Tests](#performance-tests)
9. [Integration Tests](#integration-tests)

---

## Pre-requisites

### Services Running

```bash
# Check services
docker-compose ps

# Expected output:
# research_postgres  PostgreSQL for document storage
# research_redis     Redis for caching
# research_api       FastAPI server (port 8001)
```

### Tools Required

- `curl` or Postman for API testing
- `jq` for JSON parsing (optional)
- `docker` for service management

### Base URL

```
http://localhost:8001/api
```

---

## Health Check

### Test 1.1: Basic Health Check

**Endpoint:** `GET /v1/health`

**Request:**

```bash
curl http://localhost:8001/api/v1/health
```

**Expected Response:** `200 OK`

```json
{
  "status": "healthy",
  "service": "research-service",
  "version": "0.1.0",
  "environment": "development"
}
```

**Validation:**

```bash
curl -s http://localhost:8001/api/v1/health | jq '.status == "healthy"'
# Output: true
```

---

## Search Endpoint Tests

### Test 2.1: Speed Mode Search

**Endpoint:** `POST /v1/search`

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Python programming?",
    "mode": "speed",
    "timeout": 30
  }'
```

**Expected Response:**

```json
{
  "session_id": "...",
  "query": "What is Python programming?",
  "answer": "...",
  "sources": [
    {
      "title": "...",
      "url": "...",
      "relevance": 0.95,
      "final_score": 0.94
    }
  ],
  "mode": "speed",
  "execution_time": 15.23,
  "confidence": 0.90
}
```

**Validations:**

- ✓ Status code: 200
- ✓ Has `session_id` (UUID)
- ✓ Has non-empty `answer`
- ✓ Has at least 1 source
- ✓ `execution_time` < 30 seconds
- ✓ `confidence` > 0.5

**Test Command:**

```bash
curl -s -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Python?", "mode": "speed"}' | jq '
    {
      has_session_id: (.session_id != null),
      has_answer: (.answer | length > 0),
      has_sources: (.sources | length > 0),
      execution_time: .execution_time,
      confidence: .confidence
    }
  '
```

---

### Test 2.2: Balanced Mode Search

**Endpoint:** `POST /v1/search`

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do machine learning algorithms work?",
    "mode": "balanced",
    "max_sources": 15,
    "timeout": 90
  }'
```

**Validations:**

- ✓ Status code: 200
- ✓ Sources > speed mode (should be ~10)
- ✓ `execution_time` < 90 seconds
- ✓ `confidence` > 0.7

---

### Test 2.3: Deep Mode Search

**Endpoint:** `POST /v1/search`

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest advancements in quantum computing?",
    "mode": "deep",
    "timeout": 120
  }'
```

**Validations:**

- ✓ Status code: 200
- ✓ Has 15+ sources
- ✓ `execution_time` < 120 seconds
- ✓ Rich answer with multiple perspectives

---

### Test 2.4: Custom LLM Model

**Endpoint:** `POST /v1/search`

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is artificial intelligence?",
    "mode": "balanced",
    "model": "anthropic/claude-3.5-sonnet"
  }'
```

**Validations:**

- ✓ Status code: 200
- ✓ `model_used` matches requested model
- ✓ Response quality appropriate for model

---

### Test 2.5: Invalid Query (Validation Error)

**Endpoint:** `POST /v1/search`

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "   "}'
```

**Expected Response:** `400 Bad Request`

```json
{
  "error": "invalid_request",
  "message": "Query cannot be empty or whitespace-only",
  "details": [
    {
      "field": "query",
      "message": "Query cannot be empty or whitespace-only",
      "type": "validation_error"
    }
  ]
}
```

**Validations:**

- ✓ Status code: 400
- ✓ Has `error` field
- ✓ Has `details` array

---

### Test 2.6: Timeout Handling

**Endpoint:** `POST /v1/search`

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Very complex question requiring extensive research",
    "timeout": 5
  }'
```

**Expected Behavior:**

- Search should timeout after 5 seconds
- Return error or partial results

---

## Research Endpoint Tests

### Test 3.1: Basic Research

**Endpoint:** `POST /v1/research`

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are AI agents and how do they work?",
    "mode": "balanced",
    "max_iterations": 3
  }'
```

**Expected Response:**

```json
{
  "session_id": "...",
  "query": "What are AI agents and how do they work?",
  "plan": {
    "steps": [
      {
        "step_number": 1,
        "description": "...",
        "search_query": "..."
      }
    ],
    "complexity": "moderate"
  },
  "findings": "...",
  "citations": [
    {
      "source_id": "1",
      "title": "...",
      "url": "...",
      "relevance": 0.95
    }
  ],
  "confidence": 0.85,
  "execution_time": 145.67
}
```

**Validations:**

- ✓ Status code: 200
- ✓ Has comprehensive `plan`
- ✓ Has `findings` (>100 characters)
- ✓ Has multiple `citations`
- ✓ `confidence` score present
- ✓ Proper trace URL

---

### Test 3.2: Research with Custom Iterations

**Endpoint:** `POST /v1/research`

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Latest AI advancements in 2024",
    "max_iterations": 5,
    "timeout": 300
  }'
```

**Validations:**

- ✓ Research completes successfully
- ✓ Multiple iterations executed
- ✓ Plan has multiple steps

---

## Document Endpoints Tests

### Test 4.1: Upload Document

**Endpoint:** `POST /documents/upload`

**Create test file:**

```bash
cat > /tmp/test_doc.txt << 'EOF'
This is a test document for the Research Service API.

Key Information:
- The API supports multiple endpoints
- Document upload requires multipart/form-data
- Collections organize documents by topic
- RAG enables Q&A over uploaded documents

Features:
1. Fast upload processing
2. Automatic chunking and embedding
3. Vector-based similarity search
EOF
```

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/documents/upload \
  -F "file=@/tmp/test_doc.txt" \
  -F "collection=test_docs"
```

**Expected Response:** `201 Created`

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "test_doc.txt",
  "source_type": "text",
  "collection": "test_docs",
  "chunks_created": 2,
  "embedding_dimension": 384,
  "status": "success",
  "message": "Successfully uploaded and processed 2 chunks"
}
```

**Validations:**

- ✓ Status code: 201
- ✓ `document_id` is UUID
- ✓ `chunks_created` > 0
- ✓ `status` is "success"

**Save for later tests:**

```bash
DOCUMENT_ID="550e8400-e29b-41d4-a716-446655440000"
COLLECTION="test_docs"
```

---

### Test 4.2: Query Documents

**Endpoint:** `POST /documents/query`

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/documents/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the key features?",
    "collection": "test_docs",
    "top_k": 5
  }'
```

**Expected Response:**

```json
{
  "query": "What are the key features?",
  "answer": "Based on the documents, the key features include...",
  "sources": [
    {
      "content": "...",
      "similarity": 0.85,
      "metadata": {
        "chunk_id": 0,
        "filename": "test_doc.txt"
      }
    }
  ],
  "total_chunks_found": 2,
  "chunks_used": 1,
  "execution_time": 4.23
}
```

**Validations:**

- ✓ Status code: 200
- ✓ Has non-empty `answer`
- ✓ `sources` is non-empty
- ✓ `chunks_used` <= `total_chunks_found`
- ✓ `execution_time` < 15 seconds

---

### Test 4.3: List Documents

**Endpoint:** `GET /documents`

**Request:**

```bash
curl "http://localhost:8001/api/v1/documents?collection=test_docs&limit=10"
```

**Expected Response:**

```json
{
  "documents": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "test_doc.txt",
      "collection": "test_docs",
      "chunks_count": 2,
      "created_at": "2025-11-13T23:29:08.854550",
      "access_count": 1
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 10
}
```

**Validations:**

- ✓ Status code: 200
- ✓ Returns list of documents
- ✓ Pagination works (`skip`, `limit`)

---

### Test 4.4: Delete Document

**Endpoint:** `DELETE /documents/{document_id}`

**Request:**

```bash
curl -X DELETE \
  "http://localhost:8001/api/v1/documents/550e8400-e29b-41d4-a716-446655440000"
```

**Expected Response:** `200 OK`

```json
{
  "document_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "deleted",
  "message": "Document and associated chunks deleted successfully"
}
```

**Validations:**

- ✓ Status code: 200
- ✓ Document is actually deleted (verify with GET)

---

## Session Endpoints Tests

### Test 5.1: Retrieve Session

**Endpoint:** `GET /v1/sessions/{session_id}`

**From previous search, use the `session_id` returned:**

```bash
curl http://localhost:8001/api/v1/sessions/550e8400-e29b-41d4-a716-446655440000
```

**Expected Response:**

```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "query": "What is Python?",
  "mode": "search",
  "result": {
    "session_id": "...",
    "query": "...",
    "answer": "...",
    "sources": [...]
  },
  "created_at": "2025-11-13T23:35:12.123456Z",
  "completed_at": "2025-11-13T23:35:25.234567Z"
}
```

**Validations:**

- ✓ Status code: 200
- ✓ Has complete session information
- ✓ `result` contains full response

---

## Error Handling Tests

### Test 6.1: Missing Required Field

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Expected Response:** `422 Unprocessable Entity`

---

### Test 6.2: Invalid Data Type

**Request:**

```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Python?",
    "max_sources": "not_a_number"
  }'
```

**Expected Response:** `422 Unprocessable Entity`

---

### Test 6.3: Not Found Error

**Request:**

```bash
curl http://localhost:8001/api/v1/sessions/invalid-uuid
```

**Expected Response:** `404 Not Found`

---

### Test 6.4: Rate Limit

**Send requests rapidly (>10 in 60 seconds):**

```bash
for i in {1..15}; do
  curl -X POST http://localhost:8001/api/v1/search \
    -H "Content-Type: application/json" \
    -d '{"query": "test"}' &
  sleep 0.1
done
```

**Expected Response:** `429 Too Many Requests`

```json
{
  "error": "rate_limit_exceeded",
  "message": "Too many requests"
}
```

---

## Performance Tests

### Test 7.1: Search Speed Benchmark

**Measure response time for each mode:**

```bash
# Speed mode
time curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AI?", "mode": "speed"}' > /dev/null

# Balanced mode
time curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AI?", "mode": "balanced"}' > /dev/null

# Deep mode
time curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is AI?", "mode": "deep"}' > /dev/null
```

**Expected Times:**

- Speed: < 30s
- Balanced: 30-90s
- Deep: 60-120s

---

### Test 7.2: Concurrent Requests

**Test handling of concurrent requests:**

```bash
# Send 5 concurrent requests
for i in {1..5}; do
  curl -X POST http://localhost:8001/api/v1/search \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"Test query $i\"}" &
done
wait

# All should complete successfully
```

---

## Integration Tests

### Test 8.1: Full Workflow

**Complete end-to-end workflow:**

```bash
#!/bin/bash

# 1. Health check
echo "1. Health check..."
curl -s http://localhost:8001/api/v1/health | jq '.status'

# 2. Search
echo "2. Searching..."
SEARCH_RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is API?", "mode": "speed"}')
SESSION_ID=$(echo $SEARCH_RESPONSE | jq -r '.session_id')
echo "Session: $SESSION_ID"

# 3. Get session
echo "3. Retrieving session..."
curl -s http://localhost:8001/api/v1/sessions/$SESSION_ID | jq '.query'

# 4. Upload document
echo "4. Uploading document..."
UPLOAD_RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/documents/upload \
  -F "file=@/tmp/test_doc.txt" \
  -F "collection=integration_test")
DOC_ID=$(echo $UPLOAD_RESPONSE | jq -r '.document_id')
echo "Document: $DOC_ID"

# 5. Query document
echo "5. Querying document..."
curl -s -X POST http://localhost:8001/api/v1/documents/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this?", "collection": "integration_test"}' | jq '.answer'

# 6. List documents
echo "6. Listing documents..."
curl -s "http://localhost:8001/api/v1/documents?collection=integration_test" | jq '.total'

# 7. Cleanup
echo "7. Deleting document..."
curl -s -X DELETE "http://localhost:8001/api/v1/documents/$DOC_ID" | jq '.status'

echo "All tests passed!"
```

---

### Test 8.2: Langfuse Integration

**Verify tracing is working:**

```bash
# Search response should have trace_url
RESPONSE=$(curl -s -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}')

TRACE_URL=$(echo $RESPONSE | jq -r '.trace_url')

if [ ! -z "$TRACE_URL" ] && [ "$TRACE_URL" != "null" ]; then
  echo "✓ Tracing enabled: $TRACE_URL"
else
  echo "✗ Tracing disabled"
fi
```

---

## Automated Testing Script

**Complete test script:**

```bash
#!/bin/bash

set -e

BASE_URL="http://localhost:8001/api"
FAILED=0

echo "=== Research Service API Test Suite ==="
echo "Base URL: $BASE_URL"
echo ""

# Helper function
test_endpoint() {
  local name=$1
  local method=$2
  local endpoint=$3
  local data=$4

  echo -n "Testing $name... "

  if [ -z "$data" ]; then
    curl -s -X $method "$BASE_URL$endpoint" > /dev/null && echo "✓" || { echo "✗"; ((FAILED++)); }
  else
    curl -s -X $method "$BASE_URL$endpoint" \
      -H "Content-Type: application/json" \
      -d "$data" > /dev/null && echo "✓" || { echo "✗"; ((FAILED++)); }
  fi
}

# Run tests
test_endpoint "Health Check" "GET" "/v1/health" ""
test_endpoint "Speed Search" "POST" "/v1/search" '{"query":"test","mode":"speed"}'
test_endpoint "Balanced Search" "POST" "/v1/search" '{"query":"test","mode":"balanced"}'

echo ""
echo "Test Results: $((3 - FAILED))/3 passed"
[ $FAILED -eq 0 ] && echo "All tests passed!" || echo "Some tests failed!"

exit $FAILED
```

---

## Docker Health Check

**Verify all services are healthy:**

```bash
docker-compose ps

# All services should show "Up" status
# postgres: healthy
# redis: healthy
# research-api: running
```

---

## Monitoring & Logging

**Check API logs:**

```bash
# View recent logs
docker-compose logs research-api | tail -20

# Follow logs
docker-compose logs -f research-api

# Filter by level
docker-compose logs research-api | grep ERROR
docker-compose logs research-api | grep WARNING
```

---

## Success Criteria

All tests pass if:

- ✓ Health check returns 200
- ✓ All endpoints respond with correct status codes
- ✓ Response formats match specifications
- ✓ Validation errors are handled properly
- ✓ Trace URLs are present in responses
- ✓ Performance meets expected benchmarks
- ✓ Concurrent requests handled correctly
- ✓ Error messages are clear and helpful
