@echo off
REM SearxNG Connectivity Test and Fix Script

echo ========================================
echo SearxNG Connectivity Diagnostics
echo ========================================
echo.

echo Test 1: Check if SearxNG container is running...
docker ps --filter "name=searxng" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
if errorlevel 1 (
    echo   ❌ Could not check Docker containers
    goto :docker_error
)

echo.
echo Test 2: Test SearxNG HTTP response...
curl -s -o nul -w "HTTP Status: %%{http_code}" http://localhost:8080
echo.

echo.
echo Test 3: Check research-service containers...
cd research-service 2>nul || cd .
docker compose ps

echo.
echo Test 4: Check research-api logs for SearxNG errors...
echo Looking for connection errors in last 50 lines...
docker compose logs --tail=50 research-api | findstr /C:"SearxNG" /C:"Cannot connect" /C:"Connection" /C:"got 0"

echo.
echo.
echo ========================================
echo Recommended Actions
echo ========================================
echo.
echo If SearxNG is NOT running:
echo   cd simple_perplexica (root folder)
echo   docker-compose up -d searxng
echo.
echo If SearxNG IS running but not accessible:
echo   Option 1: Use SERPER API instead
echo     - Edit research-service/.env
echo     - Set SERPER_API_KEY=your_key
echo.
echo   Option 2: Connect to main Docker network
echo     - Uncomment network config in docker-compose.yml
echo.
echo If you see "Cannot connect to SearxNG":
echo   - Check: curl http://localhost:8080
echo   - Check: docker network ls
echo   - Restart: docker compose restart research-api
echo.
pause
