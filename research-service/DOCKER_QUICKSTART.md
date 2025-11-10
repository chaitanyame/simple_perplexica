# 🚀 Research Service - Quick Start with Docker

Complete research and search service with multi-agent AI, RAG, and vector search - **all in Docker containers**.

## 📋 Prerequisites

- **Docker Desktop** (Windows/Mac) or **Docker Engine + Docker Compose** (Linux)
- **API Keys** (get them before starting):
  - [OpenRouter API Key](https://openrouter.ai/keys) - For LLM access
  - [Langfuse Keys](https://cloud.langfuse.com) - For monitoring (optional but recommended)

## ⚡ Quick Start (3 Steps)

### 1️⃣ Clone & Configure

```bash
cd research-service

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use any text editor
```

**Required in `.env`:**
```bash
OPENROUTER_API_KEY=your_actual_key_here
LANGFUSE_PUBLIC_KEY=your_public_key_here
LANGFUSE_SECRET_KEY=your_secret_key_here
```

### 2️⃣ Start Everything

**Linux/Mac:**
```bash
./quickstart.sh
```

**Windows:**
```bash
quickstart.bat
```

Or manually:
```bash
docker-compose up -d
```

### 3️⃣ Access the Services

- **🎨 Streamlit UI**: http://localhost:8501 ← Start here!
- **📖 API Docs**: http://localhost:8001/api/docs
- **💚 Health Check**: http://localhost:8001/api/v1/health

## 🎯 What's Included

The Docker setup runs 4 containers:

| Service | Port | Description |
|---------|------|-------------|
| **research-api** | 8001 | FastAPI server with SearchAgent & ResearchAgent (external port to avoid conflicts) |
| **streamlit** | 8501 | Interactive web UI for testing |
| **postgres** | 5433 | PostgreSQL 16 + pgvector for RAG (external port to avoid conflicts) |
| **redis** | 6380 | Redis for caching (external port to avoid conflicts) |

**Note**: External ports (8001, 5433, 6380) are used to avoid conflicts with other services. Internal container communication still uses standard ports.

## 🔍 Using the Service

### Via Streamlit UI (Recommended)

1. Open http://localhost:8501
2. Choose mode: **Search** (fast) or **Research** (deep)
3. Enter your query
4. View results with citations and sources
5. Export as JSON

### Via API

**Search Endpoint:**
```bash
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is Pydantic AI?",
    "max_sources": 20,
    "timeout": 60
  }'
```

**Research Endpoint:**
```bash
curl -X POST http://localhost:8001/api/v1/research \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Explain AI agents and their applications",
    "max_iterations": 3,
    "timeout": 300
  }'
```

**Get Session:**
```bash
curl http://localhost:8001/api/v1/sessions/{session_id}
```

## 📊 Monitoring

- **View logs**: `docker-compose logs -f`
- **API logs only**: `docker-compose logs -f research-api`
- **Streamlit logs**: `docker-compose logs -f streamlit`
- **Langfuse traces**: Check your Langfuse dashboard

## 🛠️ Common Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Stop and remove all data (fresh start)
docker-compose down -v

# Rebuild after code changes
docker-compose up -d --build

# Run database migrations
docker-compose exec research-api alembic upgrade head

# Run tests
docker-compose exec research-api pytest tests/ -v
```

## 🔧 Configuration

All configuration is in `.env`:

```bash
# LLM Settings
LLM_MODEL=anthropic/claude-3.5-sonnet      # or deepseek/deepseek-chat
OPENROUTER_API_KEY=your_key

# Search Settings
SEARCH_MAX_SOURCES=20                       # Max sources to fetch
RESEARCH_MAX_ITERATIONS=3                   # Research depth
DEFAULT_TIMEOUT=60                          # Seconds

# Search Configuration (uses SerperDev by default)
SERPER_API_KEY=your_serper_key              # Primary search (required)
SEARXNG_BASE_URL=http://localhost:8080     # Fallback (optional)
```

## 🐛 Troubleshooting

### Services won't start

```bash
# Check Docker is running
docker info

# Check logs for errors
docker-compose logs

# Try fresh start
docker-compose down -v
docker-compose up -d --build
```

### API returns errors

```bash
# Check if .env has valid API keys
cat .env

# Check API health
curl http://localhost:8001/api/v1/health

# View API logs
docker-compose logs -f research-api
```

### Database connection errors

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Run migrations
docker-compose exec research-api alembic upgrade head

# Fresh database
docker-compose down -v
docker-compose up -d
```

### Port conflicts

If ports 8000, 8501, 5432, or 6379 are in use, edit `docker-compose.yml`:

```yaml
services:
  research-api:
    ports:
      - "8001:8000"  # Change left side only
```

## 📁 Project Structure

```
research-service/
├── docker-compose.yml          # Main Docker orchestration
├── Dockerfile                  # API server image
├── Dockerfile.streamlit        # Streamlit UI image
├── quickstart.sh/.bat          # Quick start scripts
├── .env.example                # Environment template
├── src/
│   ├── main.py                # FastAPI app entry
│   ├── agents/                # SearchAgent, ResearchAgent
│   ├── api/v1/endpoints/      # API routes
│   └── services/              # LLM, embedding, crawling
├── streamlit_ui.py            # Streamlit interface
└── tests/                     # Test suite
```

## 🎓 Next Steps

1. **Try Search Mode**: Fast web search with citations
2. **Try Research Mode**: Deep multi-step research
3. **Explore API Docs**: http://localhost:8000/api/docs
4. **Check Langfuse**: Monitor LLM calls and costs
5. **Run Tests**: `docker-compose exec research-api pytest`

## 📚 Documentation

- [Architecture Overview](docs/STREAMLIT_ARCHITECTURE.md)
- [Development Roadmap](ROADMAP.md)
- [Phase 2 Status](docs/PHASE2_WEEK5_STATUS.md)
- [API Specification](docs/API_SPECIFICATION.md)

## 🤝 Contributing

The service is fully functional and ready for testing. Known limitations:

- Some endpoint tests need refinement (core functionality works)
- E2E test suite not yet complete
- Production hardening pending (rate limiting, auth, etc.)

See [PHASE2_WEEK5_STATUS.md](docs/PHASE2_WEEK5_STATUS.md) for detailed status.

## 📝 License

See LICENSE file in root directory.

---

**🎉 You're all set!** Open http://localhost:8501 and start researching!
