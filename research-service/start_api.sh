#!/bin/bash
# Startup script for Research Service API

echo "🚀 Starting Research Service API..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please copy .env.example to .env and configure your settings"
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate || source venv/Scripts/activate
else
    echo "❌ Error: venv not found. Please run: python -m venv venv"
    exit 1
fi

# Check if dependencies are installed
echo "✓ Checking dependencies..."
python -c "import fastapi, pydantic_ai" 2>/dev/null || {
    echo "❌ Dependencies not installed. Installing..."
    pip install -r requirements.txt
}

# Check database connection
echo "✓ Checking database connection..."
python -c "from src.core.config import settings; print(f'Database: {settings.DATABASE_URL}')"

# Start the API server
echo ""
echo "🌟 Starting FastAPI server on http://localhost:8000"
echo "📚 API Docs: http://localhost:8000/api/docs"
echo "🔍 Health Check: http://localhost:8000/api/v1/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""

uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
