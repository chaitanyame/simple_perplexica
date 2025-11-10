@echo off
REM Docker Compose Startup Script with Container Cleanup
REM This ensures old containers are removed before starting new ones

echo ========================================
echo Research Service - Docker Deployment
echo ========================================
echo.

cd /d "%~dp0"

echo Step 1: Cleaning up old containers...
docker compose down 2>nul
docker rm -f research_api research_streamlit research_postgres research_redis 2>nul

echo.
echo Step 2: Building and starting services...
docker compose up -d --build

if errorlevel 1 (
    echo.
    echo ❌ ERROR: Failed to start services!
    echo.
    echo Troubleshooting:
    echo 1. Check if ports are available:
    echo    - API: 8001
    echo    - UI: 8501
    echo    - PostgreSQL: 5433
    echo    - Redis: 6380
    echo.
    echo 2. Check Docker Desktop is running
    echo.
    echo 3. Try manual cleanup:
    echo    docker compose down -v
    echo    docker system prune -f
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo ✅ Services Started Successfully!
echo ========================================
echo.
echo 📚 Access Points:
echo   🎨 Streamlit UI:  http://localhost:8501
echo   🌐 API Server:    http://localhost:8001
echo   📖 API Docs:      http://localhost:8001/api/docs
echo   💚 Health Check:  http://localhost:8001/api/v1/health
echo.
echo 📋 Useful Commands:
echo   docker compose logs -f              # View logs
echo   docker compose logs -f research-api # API logs only
echo   docker compose ps                   # Check status
echo   docker compose down                 # Stop services
echo.

timeout /t 5 /nobreak >nul

echo 🧪 Testing API connectivity...
curl -s http://localhost:8001/api/v1/health >nul 2>&1
if errorlevel 1 (
    echo ⚠️  API not ready yet. Waiting for services to initialize...
    echo    Check logs with: docker compose logs -f research-api
) else (
    echo ✅ API is responding!
    echo.
    echo 🎉 Setup complete! Open http://localhost:8501 in your browser
)

echo.
pause
