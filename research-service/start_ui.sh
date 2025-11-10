#!/bin/bash
# Startup script for Streamlit UI

echo "🎨 Starting Streamlit UI..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Using defaults..."
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo "✓ Activating virtual environment..."
    source venv/bin/activate || source venv/Scripts/activate
else
    echo "❌ Error: venv not found. Please run: python -m venv venv"
    exit 1
fi

# Check if Streamlit is installed
echo "✓ Checking dependencies..."
python -c "import streamlit" 2>/dev/null || {
    echo "❌ Streamlit not installed. Installing..."
    pip install streamlit httpx
}

# Check if API is running
echo "✓ Checking API availability..."
curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1 || {
    echo "⚠️  Warning: API not responding at http://localhost:8000"
    echo "   Please start the API first: ./start_api.sh"
    echo ""
}

# Start Streamlit
echo ""
echo "🌟 Starting Streamlit UI on http://localhost:8501"
echo "📚 Make sure API is running on http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop"
echo ""

streamlit run streamlit_ui.py
