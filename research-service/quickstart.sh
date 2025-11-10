#!/bin/bash
# Quick start script for research-service Docker deployment

set -e

echo "🚀 Research Service - Docker Quick Start"
echo "========================================"

# Check if Docker is running
echo ""
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop."
    exit 1
fi
echo "✓ Docker is running"

# Check if .env exists
if [ ! -f .env ]; then
    echo ""
    echo "⚠️  .env file not found. Creating from example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "✓ Created .env file"
        echo ""
        echo "⚠️  IMPORTANT: Edit .env and add your API keys:"
        echo "  - OPENROUTER_API_KEY"
        echo "  - LANGFUSE_PUBLIC_KEY"
        echo "  - LANGFUSE_SECRET_KEY"
        echo ""
        read -p "Press Enter after editing .env file..."
    else
        echo "❌ .env.example not found. Please create .env manually."
        exit 1
    fi
fi

# Build and start services
echo ""
echo "� Building Docker images..."
docker-compose build

echo ""
echo "🚀 Starting all services..."
docker-compose up -d

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check service health
echo ""
echo "� Service Status:"
docker-compose ps

echo ""
echo "✅ Services are running!"
echo ""
echo "📚 Access Points:"
echo "  🌐 API Server:    http://localhost:8001"
echo "  📖 API Docs:      http://localhost:8001/api/docs"
echo "  🎨 Streamlit UI:  http://localhost:8501"
echo "  💚 Health Check:  http://localhost:8001/api/v1/health"
echo ""
echo "📋 Useful Commands:"
echo "  docker-compose logs -f              # View logs"
echo "  docker-compose logs -f research-api # API logs only"
echo "  docker-compose restart              # Restart services"
echo "  docker-compose down                 # Stop services"
echo "  docker-compose down -v              # Stop & remove data"
echo ""

# Test API
echo "🧪 Testing API..."
sleep 3
if curl -s http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo "✅ API is responding!"
    echo ""
    echo "🎉 Setup complete! Open http://localhost:8501 in your browser"
else
    echo "⚠️  API not ready yet. Check logs: docker-compose logs research-api"
fi
