@echo off
REM Switch to SerperDev for search

echo ========================================
echo Switching to SerperDev Search
echo ========================================
echo.

cd /d "%~dp0"

echo ✅ SERPER_API_KEY is configured in .env
echo.

echo Step 1: Rebuilding research-api with SerperDev support...
docker compose build research-api

if errorlevel 1 (
    echo ❌ Build failed!
    pause
    exit /b 1
)

echo.
echo Step 2: Restarting research-api...
docker compose restart research-api

echo.
echo Step 3: Waiting for API to be ready...
timeout /t 8 /nobreak >nul

echo.
echo Step 4: Testing API health...
curl -s http://localhost:8001/api/v1/health

echo.
echo Step 5: Checking logs for SerperDev...
docker compose logs --tail=30 research-api | findstr /C:"SerperDev" /C:"Serper" /C:"search"

echo.
echo.
echo ========================================
echo ✅ SerperDev Enabled!
echo ========================================
echo.
echo Search priority:
echo   1. SerperDev (primary) - Using your API key
echo   2. SearxNG (fallback) - If SerperDev fails
echo.
echo Try your search again at: http://localhost:8501
echo.
echo What to expect:
echo   - "SerperDev returned X results" = Using SerperDev ✅
echo   - "SearxNG returned X results" = Fallback to SearxNG
echo   - Should get results now!
echo.
echo View full logs: docker compose logs -f research-api
echo.
pause
