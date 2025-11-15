#!/bin/bash

# Test runner script with minimal environment configuration
export DATABASE_URL="postgresql+asyncpg://test:test@localhost:5432/test_db"
export REDIS_URL="redis://localhost:6379/0"
export OPENROUTER_API_KEY="test-key"
export LANGFUSE_PUBLIC_KEY="test"
export LANGFUSE_SECRET_KEY="test"
export LANGFUSE_BASE_URL="http://localhost"
export SEARXNG_BASE_URL="http://localhost:4000"
export SERPER_API_KEY="test"
export PERPLEXITY_API_KEY="test"
export PERPLEXITY_MODEL="test"
export LLM_MODEL="test"
export RESEARCH_LLM_MODEL="test"
export SYNTHESIS_LLM_MODEL="test"
export FALLBACK_LLM_MODEL="test"
export LOG_LEVEL="INFO"

# Run pytest with all test files
echo "Running all tests..."
./venv/Scripts/python.exe -m pytest tests/ -v --tb=short --maxfail=5 "$@"
