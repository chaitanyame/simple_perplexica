@echo off
REM Test runner for Windows
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

echo ========================================
echo Running Test Suite
echo ========================================
echo.

REM Run config tests first (fast)
echo [1/4] Running configuration validation tests...
venv\Scripts\python.exe -m pytest tests\unit\core\test_authority_config.py -v --tb=short --maxfail=3

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Config tests failed!
    exit /b %ERRORLEVEL%
)

echo.
echo [2/4] Running authority scorer unit tests...
venv\Scripts\python.exe -m pytest tests\unit\utils\test_authority_scorer.py -v --tb=short --maxfail=3

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Authority scorer tests failed!
    exit /b %ERRORLEVEL%
)

echo.
echo [3/4] Running authority integration tests...
venv\Scripts\python.exe -m pytest tests\integration\test_authority_scoring_integration.py -v --tb=short --maxfail=3

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Integration tests failed!
    exit /b %ERRORLEVEL%
)

echo.
echo [4/4] Running E2E tests...
venv\Scripts\python.exe -m pytest tests\e2e\test_search_with_authority.py -v --tb=short --maxfail=3

if %ERRORLEVEL% NEQ 0 (
    echo ERROR: E2E tests failed!
    exit /b %ERRORLEVEL%
)

echo.
echo ========================================
echo ALL TESTS PASSED!
echo ========================================

endlocal
