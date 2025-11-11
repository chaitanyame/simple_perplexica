# Streamlit UI Mode Selector - Quick Reference

## 🎨 UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  🔍 Research Service                                             │
│  Advanced Search & Research powered by Multi-Agent AI           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  SIDEBAR                      │  MAIN CONTENT                   │
│  ─────────                    │  ────────────                   │
│                               │                                  │
│  ⚙️ Settings                  │  🔎 Fast Search                 │
│  ○ Search  ● Research         │                                  │
│                               │  Enter your search query         │
│  Query Optimization           │  ┌─────────────────────────┐    │
│  ○ ⚡ SPEED                   │  │ What is Pydantic AI?    │    │
│  ● ⚖️ BALANCED  ← DEFAULT    │  └─────────────────────────┘    │
│  ○ 🔍 DEEP                    │                                  │
│                               │  [🔍 Search]  [🗑️ Clear]       │
│  ╔═══════════════════════╗   │                                  │
│  ║ 10 sources | 45 secs  ║   │  ─────────────────────────────  │
│  ║                       ║   │  📄 Answer                       │
│  ║ ✨ Selective crawling ║   │  ┌─────────────────────────┐    │
│  ║    (5 URLs),          ║   │  │ Pydantic AI is a Python │    │
│  ║    reranking enabled  ║   │  │ framework that enables  │    │
│  ║                       ║   │  │ production-ready...     │    │
│  ║ 💡 Best for:          ║   │  └─────────────────────────┘    │
│  ║    Default for most   ║   │                                  │
│  ║    queries            ║   │  ┌──────┬─────────┬────────┬───┐│
│  ╚═══════════════════════╝   │  │ 21.6s│  85%   │ 10 src │⚖️ ││
│                               │  │ Time │Confid. │Sources │Mode│
│  Advanced Parameters          │  └──────┴─────────┴────────┴───┘│
│  Max Sources: ─────○── 20    │                                  │
│  Timeout:     ─────○── 60    │  📚 Sources                      │
│                               │  [1] Pydantic AI Docs            │
│  Model:                       │  [2] GitHub - pydantic-ai        │
│  anthropic/claude-3.5-sonnet  │  ...                            │
│                               │                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🎯 Mode Selection Guide

### ⚡ SPEED Mode
```
┌─────────────────────────┐
│ 5 sources | 15 seconds  │
│                         │
│ ✨ Snippets only,       │
│    no crawling          │
│                         │
│ 💡 Best for:            │
│    Quick lookups        │
└─────────────────────────┘
```

**When to use**:
- Quick fact checks
- Simple definitions
- Time-sensitive queries
- Mobile/low-bandwidth

**What you get**:
- Fast response (10-15s)
- 5 top sources
- Snippets only (no full content)
- No reranking overhead

---

### ⚖️ BALANCED Mode (Default)
```
┌─────────────────────────┐
│ 10 sources | 45 seconds │
│                         │
│ ✨ Selective crawling   │
│    (5 URLs), reranking  │
│    enabled              │
│                         │
│ 💡 Best for:            │
│    Default for most     │
│    queries              │
└─────────────────────────┘
```

**When to use**:
- General queries
- Standard research
- Blog posts, articles
- Default choice

**What you get**:
- Moderate speed (20-25s)
- 10 diverse sources
- Top 5 URLs crawled for full content
- Semantic reranking for relevance
- RAG with historical context

---

### 🔍 DEEP Mode
```
┌─────────────────────────┐
│ 20 sources | 60 seconds │
│                         │
│ ✨ Full crawling,       │
│    reranking,           │
│    RAG with history     │
│                         │
│ 💡 Best for:            │
│    Comprehensive        │
│    research             │
└─────────────────────────┘
```

**When to use**:
- Academic research
- Technical deep dives
- Complex questions
- Report writing

**What you get**:
- Comprehensive results (30-40s)
- 20+ diverse sources
- All URLs crawled for full content
- Semantic reranking
- RAG with full historical context
- Hybrid search (vector + FTS)

---

## 🔄 Mode Comparison

| Feature | ⚡ SPEED | ⚖️ BALANCED | 🔍 DEEP |
|---------|----------|-------------|---------|
| **Sources** | 5 | 10 | 20 |
| **Timeout** | 15s | 45s | 60s |
| **Avg Time** | 10-15s | 20-25s | 30-40s |
| **URL Crawling** | ❌ No | ✅ Top 5 | ✅ All |
| **Reranking** | ❌ No | ✅ Yes | ✅ Yes |
| **RAG Context** | ❌ No | ✅ Yes | ✅ Yes |
| **Hybrid Search** | ❌ No | ✅ Yes | ✅ Yes |
| **Quality** | Basic | Good | Best |
| **Cost** | Low | Medium | High |

---

## 📱 Usage Examples

### Example 1: Quick Fact Check (SPEED)
```
Query: "What is the capital of France?"
Mode: ⚡ SPEED
Time: 12s
Sources: 5
Answer: "Paris is the capital of France..."
```

### Example 2: Technical Concept (BALANCED)
```
Query: "Explain Pydantic AI agents"
Mode: ⚖️ BALANCED
Time: 23s
Sources: 10
Answer: "Pydantic AI is a Python framework that enables
         production-ready agent and model development..."
```

### Example 3: Comprehensive Research (DEEP)
```
Query: "Compare AI agent frameworks: LangChain, 
       AutoGPT, and Pydantic AI"
Mode: 🔍 DEEP
Time: 38s
Sources: 20
Answer: "Here's a comprehensive comparison of three major
         AI agent frameworks, based on architecture,
         features, and use cases..."
```

---

## ⚙️ Advanced Override

The "Advanced Parameters" section lets you **override mode defaults**:

```python
# Example: BALANCED mode with custom settings
mode = "balanced"           # 10 sources default
max_sources = 15           # Override to 15
timeout = 60               # Override to 60s

# API receives:
{
    "query": "...",
    "mode": "balanced",     # Config applied first
    "max_sources": 15,      # Then override
    "timeout": 60           # Then override
}
```

**When to override**:
- You know the query needs more sources
- You're willing to wait longer
- Testing different configurations

**Default behavior** (recommended):
- Leave sliders at default (20, 60)
- Mode settings will be used automatically
- Most users never need to override

---

## 🎬 Workflow

1. **Select Mode** → Choose ⚡/⚖️/🔍 based on urgency
2. **Read Info Box** → Confirm mode fits your needs
3. **Enter Query** → Type your question
4. **Click Search** → Submit and wait
5. **View Results** → Mode badge shows what was used
6. **Verify Performance** → Check time/sources match expectations

---

## 🐛 Troubleshooting

### Mode not showing in results?
- **Check**: API version (restart `research-api`)
- **Check**: Streamlit version (restart `streamlit`)
- **Verify**: Response includes `"mode"` field

### Wrong number of sources?
- **SPEED**: Always 5 sources
- **BALANCED**: Up to 10 sources (may be fewer)
- **DEEP**: Up to 20 sources (may be fewer)
- **Note**: Actual count depends on search results

### Timeout errors?
- **SPEED**: Should never timeout (15s buffer)
- **BALANCED**: Rare (45s buffer)
- **DEEP**: Possible if crawling is slow
- **Solution**: Network issues, try again

---

## 📊 Performance Tips

### For Speed
1. Use ⚡ SPEED mode
2. Simple, specific queries
3. Avoid complex comparisons

### For Quality
1. Use 🔍 DEEP mode
2. Detailed queries with context
3. Leverage RAG with follow-ups

### For Balance
1. Use ⚖️ BALANCED (default)
2. Works for 90% of queries
3. Good speed/quality tradeoff

---

## 🔗 Related

- **Full Implementation**: `STREAMLIT_MODE_SELECTOR.md`
- **Mode Configs**: `src/core/search_modes.py`
- **API Spec**: `src/api/v1/schemas.py`
- **Testing**: `test_ui_modes.py`

---

**TL;DR**: Choose ⚡ for speed, ⚖️ for most queries (default), 🔍 for deep research. Mode shown in results. Override settings only if needed.
