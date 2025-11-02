# Simple Perplexica API Specification

## Base URL
```
http://localhost:3001
```

## Endpoints

### 1. Search (POST /api/search)

Performs web search with AI-powered answer synthesis and citation.

**Endpoint**: `POST /api/search`

**Content-Type**: `application/json`

#### Request Body

```json
{
  "query": "string (required)",
  "focusMode": "webSearch | academicSearch | writingAssistant | wolframAlphaSearch | youtubeSearch | redditSearch (required)",
  "optimizationMode": "speed | balanced | quality (default: balanced)",
  "chatModel": {
    "providerId": "string",
    "key": "string"
  },
  "embeddingModel": {
    "providerId": "string", 
    "key": "string"
  },
  "history": [
    ["user message", "assistant response"],
    ["user message", "assistant response"]
  ],
  "systemInstructions": "string (optional)",
  "stream": false
}
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `query` | string | ✅ Yes | - | The search query or question |
| `focusMode` | enum | ✅ Yes | - | Search focus mode (see Focus Modes) |
| `optimizationMode` | enum | No | `balanced` | Quality vs speed optimization |
| `chatModel` | object | No | Default model | LLM model to use for synthesis |
| `embeddingModel` | object | No | Default model | Embedding model for reranking |
| `history` | array | No | `[]` | Conversation history for context |
| `systemInstructions` | string | No | `null` | Custom instructions for the AI |
| `stream` | boolean | No | `false` | Enable NDJSON streaming response |

#### Focus Modes

- **`webSearch`**: General web search (default engines)
- **`academicSearch`**: Academic sources (arXiv, Google Scholar, PubMed)
- **`writingAssistant`**: No search, direct LLM response
- **`wolframAlphaSearch`**: WolframAlpha computational engine
- **`youtubeSearch`**: YouTube video search
- **`redditSearch`**: Reddit discussion search

#### Optimization Modes

- **`speed`**: Fast response, minimal reranking
  - Max docs: 15
  - Context chars: 600
  - Reranking: Disabled
  - URL enrichment: Disabled

- **`balanced`**: Balance of speed and quality (default)
  - Max docs: 15
  - Context chars: 800
  - Reranking: Enabled
  - URL enrichment: Disabled

- **`quality`**: Maximum quality, comprehensive analysis
  - Max docs: 20
  - Context chars: 1200
  - Reranking: Enabled
  - URL enrichment: Top 3 URLs fetched and chunked

#### Response (Non-Streaming)

```json
{
  "message": "string",
  "sources": [
    {
      "title": "string",
      "url": "string",
      "pageContent": "string"
    }
  ]
}
```

#### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `message` | string | AI-generated answer with inline [n] citations |
| `sources` | array | List of sources used (numbered 1-N) |
| `sources[].title` | string | Source title or URL with chunk info |
| `sources[].url` | string | Source URL |
| `sources[].pageContent` | string | Content snippet or full text (if enriched) |

#### Response (Streaming)

When `stream: true`, returns `text/event-stream` with NDJSON events:

```json
{"type": "init", "data": "Stream connected"}
{"type": "sources", "data": [...]}
{"type": "response", "data": "AI answer text"}
{"type": "done"}
```

#### Example Request (cURL)

```bash
curl -X POST http://localhost:3001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the main features of Python?",
    "focusMode": "webSearch",
    "optimizationMode": "quality"
  }'
```

#### Example Request (PowerShell)

```powershell
$body = @{
    query = "What are the main features of Python?"
    focusMode = "webSearch"
    optimizationMode = "quality"
    stream = $false
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:3001/api/search" `
    -Method POST `
    -Body $body `
    -ContentType "application/json"

Write-Host $response.message
```

#### Example Request (JavaScript/Fetch)

```javascript
const response = await fetch('http://localhost:3001/api/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    query: 'What are the main features of Python?',
    focusMode: 'webSearch',
    optimizationMode: 'quality',
    stream: false
  })
});

const data = await response.json();
console.log(data.message);
console.log('Sources:', data.sources.length);
```

#### Example Request (Python)

```python
import requests

response = requests.post('http://localhost:3001/api/search', json={
    'query': 'What are the main features of Python?',
    'focusMode': 'webSearch',
    'optimizationMode': 'quality',
    'stream': False
})

data = response.json()
print(data['message'])
print(f"Sources: {len(data['sources'])}")
```

#### Example Response

```json
{
  "message": "Python stands out as a highly versatile and widely adopted programming language [1][2]. Its design philosophy emphasizes readability and ease of use [2][13].\n\n## Simplicity and Readability\n\nA cornerstone of Python's appeal is its straightforward syntax, which closely resembles human language [2][13]...",
  "sources": [
    {
      "title": "16 Key Features of Python Programming Language",
      "url": "https://www.scientecheasy.com/2022/08/features-of-python.html/",
      "pageContent": "Python is a high-level, interpreted programming language..."
    },
    {
      "title": "https://pythongeeks.org/features-of-python/ (chunk 1/3)",
      "url": "https://pythongeeks.org/features-of-python/",
      "pageContent": "About Python™ | Python.org\nNotice:\nWhile JavaScript is not essential..."
    }
  ]
}
```

---

### 2. Get Providers (GET /api/providers)

Returns available LLM and embedding model providers.

**Endpoint**: `GET /api/providers`

#### Response

```json
{
  "providers": [
    {
      "id": "string",
      "name": "string",
      "chatModels": [
        {
          "name": "string",
          "key": "string"
        }
      ],
      "embeddingModels": [
        {
          "name": "string",
          "key": "string"
        }
      ]
    }
  ]
}
```

#### Example Request

```bash
curl http://localhost:3001/api/providers
```

#### Example Response

```json
{
  "providers": [
    {
      "id": "openrouter",
      "name": "OpenRouter",
      "chatModels": [
        {
          "name": "DeepSeek Chat v3.1",
          "key": "deepseek/deepseek-chat-v3.1:free"
        }
      ],
      "embeddingModels": [
        {
          "name": "OpenAI Text Embedding Small",
          "key": "text-embedding-3-small"
        }
      ]
    }
  ]
}
```

---

### 3. Health Check (GET /)

Simple health check endpoint.

**Endpoint**: `GET /`

#### Response

```json
{
  "status": "ok"
}
```

---

## Features

### URL/PDF Content Fetching (Quality Mode Only)

When `optimizationMode: "quality"` is used:
- Automatically fetches full content from top 3 search result URLs
- Parses HTML with BeautifulSoup (removes scripts, styles, navigation)
- Parses PDF with pypdf (extracts all pages)
- Chunks content (2000 chars per chunk, 200 char overlap)
- Replaces shallow snippets with rich content (10-15x more context)

**Example**: Instead of 150-char snippet, sources contain 2000+ char chunks:
```json
{
  "title": "https://example.com/article (chunk 1/3)",
  "url": "https://example.com/article",
  "pageContent": "Full article content with 2000+ characters..."
}
```

### Temporal Detection (SpaCy NLP)

Automatically detects recency requirements using SpaCy Named Entity Recognition:
- **Daily**: "today", "breaking news", "latest", "current" → `time_range=d`
- **Weekly**: "this week", "recent", "past week" → `time_range=w`
- **Monthly**: "this month", "past month" → `time_range=m`

Applied to SearxNG search for fresh results.

### Cosine Similarity Reranking

Sources are reranked by semantic relevance using:
- OpenRouter embeddings API
- Cosine similarity between query and source content
- Focus-mode-specific thresholds:
  - `webSearch`: 0.3
  - `academicSearch`: 0.0
  - `redditSearch`: 0.3
  - etc.

Disabled in `speed` mode for faster response.

### Citation System

All responses use inline [n] citations matching source index:
- Sources numbered 1-N in response
- Citations appear as `[1]`, `[2]`, `[1][2]` inline
- Every sentence typically has 1-3 citations
- 48-50 citations per comprehensive response

**Example**:
```
Python is a high-level language [1][2]. It emphasizes readability [3].
```

### Blog-Style Responses

Enhanced Perplexica-style prompts generate:
- **Structure**: Clear headings (##), sections, conclusion
- **Tone**: Professional, journalistic, engaging
- **Length**: 4900-5400 characters (comprehensive)
- **Citations**: Every sentence cited
- **Format**: Markdown with bold, italics, lists

---

## Error Handling

### Validation Errors (422)

```json
{
  "detail": [
    {
      "loc": ["body", "query"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

### Common Error Scenarios

- Missing required fields (`query`, `focusMode`)
- Invalid enum values for `focusMode` or `optimizationMode`
- Invalid `chatModel` or `embeddingModel` structure
- Malformed `history` array

---

## Environment Configuration

The API uses environment variables (configured in docker-compose.yaml):

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENROUTER_API_KEY` | - | OpenRouter API key (required) |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter endpoint |
| `OPENROUTER_MODEL` | `deepseek/deepseek-chat-v3.1:free` | Default LLM model |
| `OPENROUTER_EMBEDDING_MODEL` | `text-embedding-3-small` | Default embedding model |
| `LLM_STRUCTURED_OUTPUT` | `false` | Enable structured output validation |

---

## Rate Limits

Depends on OpenRouter API limits for your API key:
- Free tier: Variable rate limits
- Paid tier: Higher limits based on plan

---

## Best Practices

### For Quality Responses
```json
{
  "query": "Your detailed question here",
  "focusMode": "webSearch",
  "optimizationMode": "quality",
  "stream": false
}
```

### For Fast Responses
```json
{
  "query": "Your question",
  "focusMode": "webSearch", 
  "optimizationMode": "speed",
  "stream": false
}
```

### For Conversational Context
```json
{
  "query": "Follow-up question",
  "focusMode": "webSearch",
  "history": [
    ["What is Python?", "Python is a programming language..."],
    ["What are its features?", "Python has many features..."]
  ]
}
```

### For Academic Research
```json
{
  "query": "Latest research on quantum computing",
  "focusMode": "academicSearch",
  "optimizationMode": "quality"
}
```

---

## OpenAPI Specification

The full OpenAPI 3.1.0 specification is available at:
```
GET http://localhost:3001/openapi.json
```

Interactive Swagger UI documentation:
```
http://localhost:3001/docs
```

ReDoc documentation:
```
http://localhost:3001/redoc
```

---

## Version

**API Version**: 0.1.0

**Last Updated**: November 1, 2025

---

## Support

For issues or questions:
- Repository: https://github.com/chaitanyame/simple_perplexica
- Branch: `001-api-mvp-web-search`
