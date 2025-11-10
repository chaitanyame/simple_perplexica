@echo off
REM Quick start script for Research Service (Windows)

echo.
echo 🚀 Research Service - Docker Quick Start
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop.
    exit /b 1
)
echo ✓ Docker is running

REM Check if .env exists
if not exist .env (
    echo.
    echo ⚠️  .env file not found. Creating from example...
    if exist .env.example (
        copy .env.example .env >nul
        echo ✓ Created .env file
        echo.
        echo ⚠️  IMPORTANT: Edit .env and add your API keys:
        echo   - OPENROUTER_API_KEY
        echo   - LANGFUSE_PUBLIC_KEY
        echo   - LANGFUSE_SECRET_KEY
        echo.
        pause
    ) else (
        echo ❌ .env.example not found. Please create .env manually.
        exit /b 1
    )
)

REM Build and start services
echo.
echo 🔨 Building Docker images...
docker-compose build

echo.
echo 🚀 Starting all services...
docker-compose up -d

echo.
echo ⏳ Waiting for services to be healthy...
timeout /t 10 /nobreak >nul

REM Check service health
echo.
echo 🔍 Service Status:
docker-compose ps

echo.
echo ✅ Services are running!
echo.
echo 📚 Access Points:
echo   🌐 API Server:    http://localhost:8001
echo   📖 API Docs:      http://localhost:8001/api/docs
echo   🎨 Streamlit UI:  http://localhost:8501
echo   💚 Health Check:  http://localhost:8001/api/v1/health
echo.
echo 📋 Useful Commands:
echo   docker-compose logs -f              # View logs
echo   docker-compose logs -f research-api # API logs only
echo   docker-compose restart              # Restart services
echo   docker-compose down                 # Stop services
echo   docker-compose down -v              # Stop ^& remove data
echo.
echo 🎉 Setup complete! Open http://localhost:8501 in your browser
echo.
pause
