# ⚡ Quick Start Guide

**Get up and running in 5 minutes!**

---

## 🎯 Overview

You're about to start building the Research Service following **Test-Driven Development (TDD)**. Everything is ready except for your environment setup.

---

## ✅ What's Already Done

- ✅ Project structure complete (14 files created)
- ✅ Database models and migrations ready
- ✅ FastAPI application scaffold created
- ✅ Test infrastructure configured
- ✅ Dependencies updated to latest versions (2025)
- ✅ TDD standards and documentation complete
- ✅ Docker setup for PostgreSQL + Redis

---

## 🚀 Setup (5 Minutes)

### 1️⃣ Create Environment File (2 min)

```bash
cd research-service

# Copy example to .env
cp .env.example .env
```

**Edit `.env` and add your API keys:**

```bash
# Required keys (get from providers):
OPENROUTER_API_KEY=sk-or-v1-your-key-here         # https://openrouter.ai/keys
LANGFUSE_PUBLIC_KEY=pk-lf-your-key-here           # https://langfuse.com
LANGFUSE_SECRET_KEY=sk-lf-your-key-here           # https://langfuse.com

# Optional (can use dummy values for now):
SERPER_API_KEY=your-serper-key-here               # https://serper.dev (optional)
```

### 2️⃣ Install Dependencies (2 min)

```bash
# Install everything
pip install -r requirements.txt -r requirements-dev.txt

# Verify (should show all ✅)
python verify_dependencies.py
```

### 3️⃣ Start Databases (1 min)

```bash
# Start PostgreSQL and Redis in background
docker-compose up -d postgres redis

# Wait 10 seconds for startup, then check
docker-compose ps

# Both should show "healthy"
```

### 4️⃣ Create Database Tables (30 sec)

```bash
# Run migration
alembic upgrade head

# Verify tables created (should see 3 tables)
docker exec -it research_postgres psql -U research_user -d research_db -c "\dt"
```

---

## ✅ Verify Setup

```bash
# Test imports (should succeed)
python -c "from src.database.models import ResearchSession; print('✅ Models OK')"

# Run tests (should all pass)
pytest tests/unit/test_models.py -v

# Start API (optional)
docker-compose up research-api

# In another terminal, test health endpoint
curl http://localhost:8001/api/v1/health
# Should return: {"status":"healthy",...}
```

---

## 🎯 Start Development (Week 1, Task 1)

Now you're ready to start TDD! First task: **OpenRouter LLM Client**

### Step 1: Create Test File

```bash
# Create test file
mkdir -p tests/unit/services/llm
touch tests/unit/services/llm/__init__.py
touch tests/unit/services/llm/test_openrouter_client.py
```

### Step 2: Write Tests FIRST (RED)

Open `tests/unit/services/llm/test_openrouter_client.py` and write:

```python
"""Tests for OpenRouter client."""

import pytest
from unittest.mock import AsyncMock, Mock
import httpx

# These imports will fail initially - that's expected!
from src.services.llm.openrouter_client import OpenRouterClient


@pytest.mark.asyncio
async def test_openrouter_client_initialization():
    """Test that OpenRouter client initializes correctly."""
    client = OpenRouterClient(api_key="test-key")
    
    assert client.api_key == "test-key"
    assert client.base_url == "https://openrouter.ai/api/v1"


@pytest.mark.asyncio
async def test_chat_completion_success(httpx_mock):
    """Test successful chat completion."""
    # Arrange
    httpx_mock.add_response(
        method="POST",
        url="https://openrouter.ai/api/v1/chat/completions",
        json={
            "choices": [{"message": {"content": "Hello!"}}],
            "usage": {"total_tokens": 10}
        }
    )
    
    client = OpenRouterClient(api_key="test-key")
    
    # Act
    response = await client.chat(
        messages=[{"role": "user", "content": "Hi"}],
        model="anthropic/claude-3.5-sonnet"
    )
    
    # Assert
    assert response["choices"][0]["message"]["content"] == "Hello!"
    assert response["usage"]["total_tokens"] == 10


# Add more tests...
```

### Step 3: Run Tests (Should FAIL - RED)

```bash
pytest tests/unit/services/llm/test_openrouter_client.py -v

# Expected: ImportError (module doesn't exist yet)
```

### Step 4: Implement Client (GREEN)

Create `src/services/llm/openrouter_client.py`:

```python
"""OpenRouter LLM client."""

import httpx
from typing import Any


class OpenRouterClient:
    """Client for OpenRouter API."""
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        """Initialize OpenRouter client."""
        self.api_key = api_key
        self.base_url = base_url
    
    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str
    ) -> dict[str, Any]:
        """Send chat completion request."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"messages": messages, "model": model}
            )
            response.raise_for_status()
            return response.json()
```

### Step 5: Run Tests (Should PASS - GREEN)

```bash
pytest tests/unit/services/llm/test_openrouter_client.py -v

# Expected: All tests pass ✅
```

### Step 6: Refactor & Add More Tests

Continue the TDD cycle:
- Add tests for error handling
- Add tests for retries
- Add tests for streaming
- Refactor implementation
- Ensure 80%+ coverage

```bash
# Check coverage
pytest tests/unit/services/llm/ --cov=src/services/llm --cov-report=html
```

---

## 📚 Key Resources

- **TDD Workflow**: `.github/copilot-instructions.md`
- **Code Standards**: `docs/DEVELOPMENT_STANDARDS.md`
- **Full Checklist**: `PRE_DEVELOPMENT_CHECKLIST.md`
- **Status Summary**: `SETUP_STATUS.md`
- **Implementation Plan**: `ROADMAP.md`

---

## 🆘 Troubleshooting

### Can't import pydantic/fastapi/etc?
```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### Database connection error?
```bash
docker-compose up -d postgres redis
docker-compose ps  # Check they're healthy
```

### Tests fail with validation errors?
```bash
# Make sure .env file exists with required keys
cat .env  # Should show your API keys
```

### Import errors for src modules?
```bash
# Make sure you're in research-service directory
pwd  # Should end with /research-service

# Run from project root
python -c "from src.main import app"
```

---

## ✅ Success Criteria

You're ready to develop when:

- [ ] `.env` file exists with API keys
- [ ] All dependencies installed (verify_dependencies.py passes)
- [ ] PostgreSQL and Redis running and healthy
- [ ] Alembic migration completed (3 tables exist)
- [ ] Can import `from src.main import app`
- [ ] Existing tests pass (`pytest tests/unit/test_models.py`)

---

**🎉 You're all set! Start with the TDD example above and build the OpenRouter client! 🚀**

**Remember: RED → GREEN → REFACTOR. Always write tests first!**
