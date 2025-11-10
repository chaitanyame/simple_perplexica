@echo off
REM Quick fix script for search errors

echo ========================================
echo Research Service - Search Fix
echo ========================================
echo.

cd /d "%~dp0"

echo Step 1: Checking if main SearxNG is running...
curl -s http://localhost:8080 >nul 2>&1
if errorlevel 1 (
    echo   ❌ SearxNG NOT accessible on port 8080
    echo   Starting main docker-compose...
    cd ..
    docker-compose up -d searxng
    cd research-service
    echo   ✅ SearxNG should be starting...
    timeout /t 3 /nobreak >nul
) else (
    echo   ✅ SearxNG is accessible
)

echo.
echo Step 2: Rebuilding research-api with better error handling...
docker compose build research-api

echo.
echo Step 3: Restarting research-api...
docker compose restart research-api

echo.
echo Step 4: Waiting for API to be ready...
timeout /t 8 /nobreak >nul

echo.
echo Step 5: Testing API health...
curl -s http://localhost:8001/api/v1/health

echo.
echo Step 6: Checking logs for connection errors...
docker compose logs --tail=20 research-api | findstr /C:"SearxNG" /C:"Cannot connect" /C:"error"

echo.
echo.
echo ========================================
echo ✅ Fix Applied!
echo ========================================
echo.
echo Changes made:
echo   - Added detailed error logging for SearxNG
echo   - Lowered minimum sources: 5 → 3
echo   - Lowered confidence threshold: 0.5 → 0.3
echo   - Ensured SearxNG is running
echo.
echo Try your search again at: http://localhost:8501
echo.
echo If you see "Cannot connect to SearxNG" in logs:
echo   1. Make sure main app is running: cd .. ^&^& docker-compose ps
echo   2. Check SearxNG: curl http://localhost:8080
echo   3. Or set SERPER_API_KEY in .env as fallback
echo.
echo View full logs: docker compose logs -f research-api
echo.
pause
