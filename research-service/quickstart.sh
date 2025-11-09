#!/bin/bash
# Quick start script for research-service development

set -e

echo "🚀 Research Service - Quick Start"
echo "=================================="

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: Please run this script from the research-service directory"
    exit 1
fi

# Create virtual environment
echo ""
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "🔧 Activating virtual environment..."
if [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate  # Windows Git Bash
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate  # Linux/Mac
else
    echo "❌ Error: Could not find activation script"
    exit 1
fi

# Upgrade pip
echo "⬆️  Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo "📚 Installing dependencies..."
pip install -r requirements.txt -r requirements-dev.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
    echo "⚠️  Please update .env with your actual API keys!"
fi

# Start PostgreSQL and Redis
echo ""
echo "🐘 Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

# Wait for PostgreSQL to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
sleep 5

# Run migrations
echo "🗃️  Running database migrations..."
alembic upgrade head

# Run tests
echo ""
echo "🧪 Running tests..."
pytest tests/ -v

# Check code quality
echo ""
echo "🔍 Checking code quality..."
echo "  - Ruff linting..."
ruff check .

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Update .env with your API keys (OPENROUTER_API_KEY, LANGFUSE keys)"
echo "  2. Start development server: uvicorn src.api.main:app --reload --port 8001"
echo "  3. Run tests: pytest tests/"
echo "  4. Check coverage: pytest --cov=src --cov-report=html tests/"
echo ""
echo "📖 See GETTING_STARTED.md for detailed instructions"
