# Research Service

AI-powered content generation service using multi-agent CrewAI system with OpenRouter.

## Overview

The Research Service generates comprehensive, well-researched blog posts on any topic using a two-agent system:

1. **Senior Research Analyst** - Searches the web, analyzes information, and creates detailed research briefs
2. **Content Writer** - Transforms research into engaging, accessible blog posts

## Features

- 🔍 **Web Research**: Automated web search using SerperDev API
- 🤖 **Multi-Agent System**: Two specialized AI agents work collaboratively
- 📝 **Content Generation**: Produces markdown-formatted blog posts
- ✅ **Fact-Checked**: Cross-references sources and maintains accuracy
- 🔗 **Citations**: Includes all source citations and references
- 🎯 **OpenRouter Integration**: Uses any OpenRouter-compatible LLM

## API Endpoints

### Health Check
```bash
GET /
GET /health
```

### Generate Content
```bash
POST /api/generate
```

**Request Body:**
```json
{
  "topic": "AI trends in 2025",
  "temperature": 0.7
}
```

**Response:**
```json
{
  "topic": "AI trends in 2025",
  "content": "# AI Trends in 2025\n\n...",
  "raw_output": "...",
  "status": "success"
}
```

## Configuration

### Environment Variables

Create a `.env` file with:

```bash
# Required: OpenRouter API Key
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=deepseek/deepseek-chat-v3.1:free

# Required: SerperDev API Key (for web search)
SERPERDEV_API_KEY=your_key_here

# Optional: Server Configuration
HOST=0.0.0.0
PORT=3002
```

### Get API Keys

- **OpenRouter**: https://openrouter.ai/keys
- **SerperDev**: https://serper.dev/

## Running Locally

### Option 1: With Docker (Recommended)

```bash
# From project root
docker compose up researchsvc
```

Service will be available at: http://localhost:3002

### Option 2: Without Docker

```bash
cd services/researchsvc

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Run the service
python -m app.main
```

## Usage Examples

### Using cURL

```bash
curl -X POST http://localhost:3002/api/generate \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Latest developments in quantum computing",
    "temperature": 0.7
  }'
```

### Using Python

```python
import requests

response = requests.post(
    "http://localhost:3002/api/generate",
    json={
        "topic": "Impact of AI on healthcare",
        "temperature": 0.7
    }
)

result = response.json()
print(result["content"])
```

### Using PowerShell

```powershell
$body = @{
    topic = "Future of renewable energy"
    temperature = 0.7
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "http://localhost:3002/api/generate" `
    -ContentType "application/json" -Body $body
```

## Architecture

```
researchsvc/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── models.py            # Pydantic models
│   ├── crews/
│   │   ├── __init__.py
│   │   └── research_crew.py # CrewAI multi-agent logic
│   └── routers/
│       ├── __init__.py
│       └── generate.py      # API endpoints
├── Dockerfile
├── requirements.txt
└── .env.example
```

## How It Works

1. **Request Received**: Client sends a topic and optional temperature
2. **Crew Creation**: Two AI agents are instantiated with specific roles
3. **Research Phase**: 
   - Research Analyst searches the web using SerperDev
   - Analyzes and synthesizes information
   - Creates structured research brief with citations
4. **Writing Phase**:
   - Content Writer receives research brief
   - Transforms technical content into engaging blog post
   - Maintains accuracy and preserves citations
5. **Response**: Formatted markdown content returned to client

## Models

### Default Model

- **deepseek/deepseek-chat-v3.1:free** - Fast, capable, and free via OpenRouter

### Alternative Models

You can use any OpenRouter model:

```bash
# In .env file
OPENROUTER_MODEL=anthropic/claude-3.5-sonnet
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
OPENROUTER_MODEL=meta-llama/llama-3.3-70b-instruct
```

## Performance

- **Typical Response Time**: 30-60 seconds (depends on topic complexity)
- **Rate Limits**: Based on your OpenRouter and SerperDev quotas
- **Concurrent Requests**: Handled via FastAPI async/await

## Troubleshooting

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "API key not found"
Check your `.env` file has correct keys set.

### Slow responses
- Complex topics take longer to research
- Consider using faster OpenRouter models
- Check your internet connection

### SERPERDEV_API_KEY errors
SerperDev is required for web search. Get a free key at https://serper.dev/

## Development

### Adding Custom Agents

Edit `app/crews/research_crew.py` to add more agents or modify existing ones.

### Changing Research Behavior

Modify agent backstories, task descriptions, or add new tools in `research_crew.py`.

### Testing

```bash
# Health check
curl http://localhost:3002/health

# Quick test
curl -X POST http://localhost:3002/api/generate \
  -H "Content-Type: application/json" \
  -d '{"topic": "test topic"}'
```

## License

Part of simple_perplexica project.
