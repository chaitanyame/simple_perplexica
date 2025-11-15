@echo off
REM Quick test runner - runs tests and saves output to file
setlocal

set DATABASE_URL=postgresql+asyncpg://test:test@localhost:5432/test
set REDIS_URL=redis://localhost:6379
set OPENROUTER_API_KEY=test
set LANGFUSE_PUBLIC_KEY=test
set LANGFUSE_SECRET_KEY=test
set LANGFUSE_BASE_URL=http://localhost
set SEARXNG_BASE_URL=http://localhost:4000
set SERPER_API_KEY=test
set PERPLEXITY_API_KEY=test
set PERPLEXITY_MODEL=test
set LLM_MODEL=test
set RESEARCH_LLM_MODEL=test
set SYNTHESIS_LLM_MODEL=test
set FALLBACK_LLM_MODEL=test
set LOG_LEVEL=INFO

echo Running All Tests - Output saved to test_results.txt
echo.

REM Run all new tests in one go and save to file
venv\Scripts\python.exe -m pytest tests/unit/core/test_authority_config.py tests/unit/utils/test_authority_scorer.py tests/integration/test_authority_scoring_integration.py tests/e2e/test_search_with_authority.py -v --tb=short --maxfail=10 > test_results.txt 2>&1

echo.
echo Tests completed! Check test_results.txt for details
echo.

REM Show summary
findstr /C:"passed" /C:"failed" /C:"error" /C:"PASSED" /C:"FAILED" /C:"ERROR" test_results.txt | findstr /V "INFO:"

endlocal
