#!/bin/bash
# Quick connectivity test for research service dependencies

echo "🔍 Testing Research Service Dependencies..."
echo ""

echo "1. Testing SearxNG (port 8080)..."
if curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo "   ✅ SearxNG is accessible"
else
    echo "   ❌ SearxNG is NOT accessible"
    echo "   Fix: Make sure main docker-compose is running: docker-compose up -d searxng"
fi

echo ""
echo "2. Testing Research API (port 8001)..."
if curl -s http://localhost:8001/api/v1/health > /dev/null 2>&1; then
    echo "   ✅ Research API is accessible"
else
    echo "   ❌ Research API is NOT accessible"
    echo "   Fix: docker compose up -d research-api"
fi

echo ""
echo "3. Testing PostgreSQL (port 5433)..."
if nc -z localhost 5433 2>/dev/null || timeout 1 bash -c 'cat < /dev/null > /dev/tcp/localhost/5433' 2>/dev/null; then
    echo "   ✅ PostgreSQL is accessible"
else
    echo "   ❌ PostgreSQL is NOT accessible"
    echo "   Fix: docker compose up -d postgres"
fi

echo ""
echo "4. Testing Redis (port 6380)..."
if nc -z localhost 6380 2>/dev/null || timeout 1 bash -c 'cat < /dev/null > /dev/tcp/localhost/6380' 2>/dev/null; then
    echo "   ✅ Redis is accessible"
else
    echo "   ❌ Redis is NOT accessible"
    echo "   Fix: docker compose up -d redis"
fi

echo ""
echo "5. Checking environment variables..."
if [ -f .env ]; then
    echo "   ✅ .env file exists"
    if grep -q "OPENROUTER_API_KEY=sk-or-v1-" .env; then
        echo "   ✅ OPENROUTER_API_KEY is set"
    else
        echo "   ⚠️  OPENROUTER_API_KEY might not be valid"
    fi
    
    if grep -q "SERPER_API_KEY=" .env && ! grep -q "your-serper-key-here" .env; then
        echo "   ✅ SERPER_API_KEY is set"
    else
        echo "   ⚠️  SERPER_API_KEY might not be valid"
    fi
else
    echo "   ❌ .env file NOT found"
    echo "   Fix: cp .env.example .env and configure it"
fi

echo ""
echo "📋 Summary:"
echo "   If all checks pass, try your search again"
echo "   If SearxNG fails, check main app: cd .. && docker-compose ps"
echo "   If API fails, check logs: docker compose logs research-api"
