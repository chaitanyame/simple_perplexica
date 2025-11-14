# Research Service API Documentation

Complete API specifications and guides for the Research Service.

---

## 📚 Documentation Files

### 1. **API_SPECIFICATION.md** (Main Reference)
Comprehensive API specification covering:
- All endpoints with detailed descriptions
- Request/response schemas
- Error handling and codes
- Rate limiting
- Observability and Langfuse integration
- Configuration options

**Use for:** Complete API reference, integration planning, detailed endpoint specifications

---

### 2. **API_QUICK_REFERENCE.md** (Quick Guide)
Quick reference guide with:
- Common use cases and curl commands
- Search mode explanations
- Python client examples
- Search engine comparison
- Performance tips
- Debugging assistance

**Use for:** Quick lookups, getting started, common patterns

---

### 3. **TESTING_GUIDE.md** (QA & Testing)
Comprehensive testing procedures including:
- Pre-requisites and setup
- Test cases for each endpoint
- Validation checklist
- Performance benchmarks
- Integration test workflows
- Automated testing scripts

**Use for:** QA testing, validating functionality, performance verification

---

### 4. **openapi.yaml** (Machine-Readable Spec)
OpenAPI 3.0 specification in YAML format:
- Full API schema
- Request/response models
- All endpoints with examples
- Error responses

**Use for:** OpenAPI tools, client library generation, API testing tools

---

## 🚀 Getting Started

### 1. Read First
Start with **API_QUICK_REFERENCE.md** for a quick overview:
```bash
less API_QUICK_REFERENCE.md
```

### 2. Access Interactive Docs
```
http://localhost:8001/api/docs        # Swagger UI
http://localhost:8001/api/redoc       # ReDoc
http://localhost:8001/api/openapi.json # Raw OpenAPI spec
```

### 3. Try Examples
Copy curl examples from **API_QUICK_REFERENCE.md**:
```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "What is Python?"}'
```

### 4. Run Tests
Use **TESTING_GUIDE.md** to verify functionality:
```bash
# Health check
curl http://localhost:8001/api/v1/health

# Quick search
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "mode": "speed"}'
```

---

## 📋 Endpoint Summary

| Endpoint | Method | Purpose | Time |
|----------|--------|---------|------|
| `/v1/health` | GET | Service health | <1s |
| `/v1/search` | POST | Fast search | 10-120s |
| `/v1/research` | POST | Deep research | 2-5m |
| `/documents/upload` | POST | Upload documents | 5-30s |
| `/documents/query` | POST | Query documents | 5-15s |
| `/documents` | GET | List documents | <1s |
| `/documents/{id}` | DELETE | Delete document | <1s |
| `/v1/sessions/{id}` | GET | Get session | <1s |

---

## 🔑 Key Features

### Search Modes
- **Speed** (10-30s): Quick answers, simple queries
- **Balanced** (30-90s): General research, default mode
- **Deep** (60-120s): Comprehensive analysis, complex topics

### Document Types
- PDF (via Dockling extraction)
- Word documents (.docx)
- Excel spreadsheets (.xlsx)
- Plain text files

### Search Engines
- **SearXNG**: Open-source, no API key
- **SerperDev**: Google Search API
- **Perplexity**: AI-powered search
- **Auto**: Automatic fallback chain

### LLM Support
- DeepSeek R1 (default, free)
- Claude 3.5 Sonnet
- Gemini 2.0 Flash
- Custom OpenRouter models

### Observability
- **Langfuse Integration**: Full trace URLs in responses
- **Structured Logging**: JSON logs with correlation IDs
- **Token Usage Tracking**: Monitor costs and performance
- **Error Tracking**: Debug with trace IDs

---

## 📊 Common Use Cases

### 1. Quick Answer (Speed Mode)
**Time:** 10-30 seconds
**Cost:** Minimal
```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Python?",
    "mode": "speed"
  }'
```

### 2. Research Report (Deep Research)
**Time:** 2-5 minutes
**Cost:** Moderate
```bash
curl -X POST http://localhost:8001/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the latest AI advancements?",
    "max_iterations": 5
  }'
```

### 3. Document Q&A
**Time:** 5-15 seconds
**Cost:** Low
```bash
# Upload
curl -X POST http://localhost:8001/api/v1/documents/upload \
  -F "file=@document.pdf"

# Query
curl -X POST http://localhost:8001/api/v1/documents/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main findings?",
    "collection": "default"
  }'
```

---

## ⚙️ Configuration

Key environment variables:

```env
# API
API_PORT=8001
API_RATE_LIMIT=10/minute

# LLM (primary)
RESEARCH_LLM_MODEL=deepseek/deepseek-r1:free
RESEARCH_LLM_TEMPERATURE=0.3
RESEARCH_LLM_TIMEOUT=180

# Langfuse (observability)
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com

# Search
SEARXNG_BASE_URL=http://searxng:8080
SERPER_API_KEY=...

# Logging
LOG_LEVEL=INFO
```

See `.env` file for complete options.

---

## 🛠️ Development

### Project Structure
```
research-service/
├── src/
│   ├── api/              # API endpoints
│   │   └── v1/endpoints/ # Route handlers
│   ├── agents/           # AI agents
│   ├── services/         # Business logic
│   │   └── llm/          # LLM integration (Langfuse)
│   └── database/         # Database models
├── tests/                # Test suites
├── API_SPECIFICATION.md  # Full API reference
├── API_QUICK_REFERENCE.md # Quick guide
├── TESTING_GUIDE.md      # Testing procedures
├── openapi.yaml          # OpenAPI spec
└── docker-compose.yml    # Container setup
```

### Running Tests
```bash
# Health check
curl http://localhost:8001/api/v1/health

# Run test suite
bash tests/run_tests.sh
```

### Viewing Logs
```bash
# Follow logs
docker-compose logs -f research-api

# Filter by level
docker-compose logs research-api | grep ERROR
```

### Langfuse Tracing
Every response includes trace URLs for debugging:
```bash
curl -s -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}' | jq '.trace_url'
```

Click the URL to view in Langfuse dashboard.

---

## 📈 Performance

### Expected Response Times
- Health Check: < 1s
- Speed Search: 10-30s
- Balanced Search: 30-90s
- Deep Search: 60-120s
- Document Query: 5-15s
- Research (Deep): 2-5 minutes

### Benchmarks
Run performance tests:
```bash
# See TESTING_GUIDE.md for detailed benchmarks
bash tests/performance_test.sh
```

---

## 🔒 Security

### Current State
- No authentication (configure for production)
- CORS enabled for all origins (restrict for production)
- Rate limiting: 10 req/min per IP

### Recommended for Production
- API key authentication
- JWT tokens
- OAuth 2.0 integration
- CORS restrictions
- HTTPS/TLS enforcement

---

## 🐛 Troubleshooting

### Common Issues

**Search timeout?**
- Increase timeout parameter: `"timeout": 120`
- Simplify query
- Use speed mode

**No documents found?**
- Check collection name matches
- Verify document was uploaded successfully
- Check similarity threshold (default 0.3)

**Langfuse traces missing?**
- Verify API keys in .env
- Check `trace_url` in response
- Confirm Langfuse project access

**Rate limit exceeded?**
- Wait 60 seconds and retry
- Check `X-RateLimit-Remaining` header
- Stagger requests if needed

### Debug Commands
```bash
# Check service health
docker-compose ps

# View logs
docker-compose logs research-api

# Check API response
curl -v http://localhost:8001/api/v1/health

# Validate request format
curl -s ... | jq '.'
```

---

## 📞 Support

### Documentation
- **Full Spec:** API_SPECIFICATION.md
- **Quick Guide:** API_QUICK_REFERENCE.md
- **Testing:** TESTING_GUIDE.md
- **OpenAPI:** openapi.yaml

### Interactive Docs
- **Swagger UI:** http://localhost:8001/api/docs
- **ReDoc:** http://localhost:8001/api/redoc
- **OpenAPI JSON:** http://localhost:8001/api/openapi.json

### Debugging
- Check Langfuse trace URLs in responses
- Review structured logs with `docker-compose logs`
- Use trace IDs from error responses

---

## 🚢 Deployment

### Local Development
```bash
docker-compose up -d
# API available at http://localhost:8001/api
```

### Production
1. Configure environment variables
2. Set up authentication
3. Enable HTTPS/TLS
4. Configure CORS restrictions
5. Set appropriate rate limits
6. Configure backup/disaster recovery
7. Set up monitoring and alerting

---

## 📝 API Evolution

### Versioning
- Current version: **0.1.0**
- All endpoints under `/api/v1/`
- Breaking changes will use new version paths (v2, v3, etc.)

### Future Improvements
- Batch endpoint for multiple queries
- Streaming responses for long-running operations
- GraphQL support
- WebSocket subscriptions for real-time updates

---

## 📄 License

Research Service API - Apache 2.0

---

## Summary

| Document | Purpose | Audience |
|----------|---------|----------|
| API_SPECIFICATION.md | Complete reference | Developers, architects |
| API_QUICK_REFERENCE.md | Quick lookups | Developers, integrators |
| TESTING_GUIDE.md | QA procedures | QA engineers, developers |
| openapi.yaml | Machine-readable spec | Tools, generators |
| README_API.md | Navigation guide | Everyone |

**Start with:** API_QUICK_REFERENCE.md
**Explore with:** http://localhost:8001/api/docs
**Reference:** API_SPECIFICATION.md
**Verify with:** TESTING_GUIDE.md
