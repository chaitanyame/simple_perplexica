# Quick Reference: Missing Features & Recommendations

## Critical Gaps (Must Fix for Core Parity)

### 1. URL/PDF Fetching & Summarization ❌ HIGH PRIORITY

**What Perplexica Does:**
```typescript
// User asks: "Summarize https://example.com"
const links = ["https://example.com"];
const docs = await getDocumentsFromLinks({ links });
// Fetches URL, parses HTML/PDF, splits into chunks
// Then summarizes each chunk with LLM
```

**What MVP Does:**
```python
# Creates empty placeholder only
link_sources = [{"title": url, "url": url, "pageContent": ""}]
```

**Fix:** Implement `fetch_and_summarize_urls()` function
- Use `httpx` to fetch URLs
- Parse HTML with `beautifulsoup4`
- Parse PDFs with `pypdf` or `pdfplumber`
- Split text with chunking (500-1000 chars)
- Summarize each chunk with LLM

---

### 2. "not_needed" Decision Logic ❌ MEDIUM PRIORITY

**What Perplexica Does:**
```typescript
if (question === 'not_needed') {
  return { query: '', docs: [] };  // Skip search entirely
}
```

**What MVP Does:**
```python
# Always searches, ignores decision.need_search
effective_query = decision.optimized_query or req.query
sources = await get_sources(effective_query, req.focusMode)
```

**Fix:** Check decision before searching
```python
if not decision.need_search:
    # Return direct answer without search
    message = await openrouter.synthesize_answer(
        query=effective_query,
        sources=[],  # Empty sources
        system_instructions=req.systemInstructions,
        history=req.history,
    )
    return SearchResponse(message=message, sources=[])
```

---

### 3. Token-by-Token Streaming ⚠️ MEDIUM PRIORITY

**What Perplexica Does:**
```typescript
// Streams each token as it's generated
for await (const event of stream) {
  if (event.name === 'FinalResponseGenerator') {
    emitter.emit('data', { type: 'response', data: event.data.chunk });
  }
}
```

**What MVP Does:**
```python
# Generates full response then sends once
message = await openrouter.synthesize_answer(...)
yield json.dumps({"type": "response", "data": message}) + "\n"
```

**Fix:** Use OpenRouter streaming API
```python
async for chunk in openrouter.stream_answer(...):
    yield json.dumps({"type": "response", "data": chunk}) + "\n"
```

---

### 4. Enhanced Prompts ⚠️ LOW PRIORITY

**Current MVP Prompt:**
```python
"Cite 1–3 of the most relevant sources using [n] inline"
```

**Perplexica's Prompt:**
```typescript
"Cite every single fact, statement, or sentence using [number] notation.
Ensure every sentence includes at least one citation.
Write responses that read like a high-quality blog post with clear headings."
```

**Fix:** Replace with full Perplexica prompt from `src/lib/prompts/webSearch.ts`

---

## Feature Comparison Matrix

| Feature | Perplexica | MVP | Priority |
|---------|-----------|-----|----------|
| **Core search flow** | ✅ | ✅ | - |
| **SearxNG integration** | ✅ | ✅ | - |
| **Cosine reranking** | ✅ | ✅ | - |
| **Focus modes** | ✅ | ✅ | - |
| **URL fetching** | ✅ | ❌ | 🔴 HIGH |
| **PDF parsing** | ✅ | ❌ | 🔴 HIGH |
| **LLM summarization** | ✅ | ❌ | 🔴 HIGH |
| **"not_needed" logic** | ✅ | ❌ | 🟡 MEDIUM |
| **Token streaming** | ✅ | ❌ | 🟡 MEDIUM |
| **Detailed prompts** | ✅ | ⚠️ | 🟢 LOW |
| **Image search** | ✅ | ❌ | 🟢 LOW |
| **Video search** | ✅ | ❌ | 🟢 LOW |
| **Suggestions** | ✅ | ❌ | 🟢 LOW |
| **Weather widget** | ✅ | ❌ | 🟢 LOW |
| **File uploads** | ✅ | ❌ | 🟢 LOW |
| **Chat persistence** | ✅ | ❌ | 🟢 LOW |
| **SpaCy temporal** | ❌ | ✅ | ✨ Enhancement |
| **Quality mode (20 docs)** | ❌ | ✅ | ✨ Enhancement |

---

## Implementation Roadmap

### Sprint 1: Core Parity (Week 1-2)

**Goal:** Achieve 95% feature parity with Perplexica core search

1. **Implement URL/PDF fetching** (5 days)
   - [ ] Create `fetch_url()` function with httpx
   - [ ] Add HTML parsing with BeautifulSoup
   - [ ] Add PDF parsing with pypdf
   - [ ] Implement text chunking (RecursiveCharacterTextSplitter equivalent)
   - [ ] Add LLM summarization for chunks
   - [ ] Integrate with decision step's `links` output

2. **Add "not_needed" handling** (1 day)
   - [ ] Check `decision.need_search` before searching
   - [ ] Return direct answer for greetings/simple tasks

3. **Implement token streaming** (2 days)
   - [ ] Use OpenRouter's streaming endpoint
   - [ ] Yield chunks as they arrive
   - [ ] Update event_stream() to stream tokens

4. **Enhance prompts** (1 day)
   - [ ] Copy full webSearchResponsePrompt from Perplexica
   - [ ] Add few-shot examples to decision prompt
   - [ ] Update citation requirements

### Sprint 2: Secondary Features (Week 3-4)

**Goal:** Add image/video search and suggestions

5. **Image search endpoint** (2 days)
   - [ ] Create `/api/images` route
   - [ ] Implement image search chain
   - [ ] Use SearxNG bing/google images engines

6. **Video search endpoint** (2 days)
   - [ ] Create `/api/videos` route
   - [ ] Implement video search chain

7. **Suggestion generator** (2 days)
   - [ ] Create `/api/suggestions` route
   - [ ] Generate 3-5 follow-up questions

### Sprint 3: Platform Features (Week 5+)

**Goal:** Add persistence and widgets

8. Weather widget
9. Discovery/trending news
10. File upload processing
11. Chat history persistence
12. Config management

---

## Code Examples for Critical Fixes

### Fix 1: URL Fetching Implementation

```python
# services/api-mvp/app/utils/fetch_urls.py

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from typing import List, Dict

async def fetch_and_parse_url(url: str) -> str:
    """Fetch URL and extract text content"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        content_type = response.headers.get('content-type', '')
        
        if 'application/pdf' in content_type:
            # Parse PDF
            pdf = PdfReader(BytesIO(response.content))
            text = ""
            for page in pdf.pages:
                text += page.extract_text()
            return text.strip()
        else:
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            # Remove scripts, styles
            for tag in soup(['script', 'style', 'nav', 'footer']):
                tag.decompose()
            text = soup.get_text(separator='\n', strip=True)
            return text

def chunk_text(text: str, chunk_size: int = 800) -> List[str]:
    """Split text into chunks"""
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += len(word) + 1
        if current_length > chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = len(word)
        else:
            current_chunk.append(word)
    
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks

async def fetch_and_summarize_urls(
    urls: List[str],
    query: str,
    llm_summarize_fn
) -> List[Dict]:
    """Fetch URLs, parse, chunk, and summarize with LLM"""
    results = []
    
    for url in urls:
        try:
            text = await fetch_and_parse_url(url)
            chunks = chunk_text(text, chunk_size=800)
            
            # Summarize each chunk
            for chunk in chunks[:5]:  # Limit to 5 chunks per URL
                summary = await llm_summarize_fn(
                    f"Summarize this text in relation to: {query}\n\nText: {chunk}"
                )
                results.append({
                    "title": url,
                    "url": url,
                    "pageContent": summary
                })
        except Exception as e:
            # Add error placeholder
            results.append({
                "title": f"Failed to fetch: {url}",
                "url": url,
                "pageContent": f"Error: {str(e)}"
            })
    
    return results
```

### Fix 2: Update search.py to use URL fetching

```python
# In search.py

from app.utils.fetch_urls import fetch_and_summarize_urls

@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    decision = await openrouter.decide_search_and_rewrite(...)
    
    # Check if search is not needed
    if not decision.need_search:
        message = await openrouter.synthesize_answer(
            query=req.query,
            sources=[],
            system_instructions=req.systemInstructions,
            history=req.history,
        )
        return SearchResponse(message=message, sources=[])
    
    effective_query = decision.optimized_query or req.query
    
    # Fetch and summarize any provided URLs
    link_sources = []
    if decision.links:
        link_sources = await fetch_and_summarize_urls(
            decision.links,
            effective_query,
            lambda text: openrouter.summarize_text(text)  # Add this method
        )
    
    # Regular search
    fetched = await get_sources(effective_query, req.focusMode)
    sources = link_sources + (fetched or [])
    
    # ... rest of the code
```

---

## Testing Checklist

### Test URL Fetching
- [ ] Test with HTML page: `"Summarize https://example.com"`
- [ ] Test with PDF: `"What does this PDF say: https://example.com/doc.pdf"`
- [ ] Test with multiple URLs
- [ ] Test with invalid URL (error handling)

### Test "not_needed" Logic
- [ ] Greeting: `"Hi, how are you?"` → no search
- [ ] Simple task: `"Write a poem about cats"` → no search
- [ ] Factual query: `"What is Docker?"` → search

### Test Token Streaming
- [ ] Long response streams progressively
- [ ] Sources arrive before response
- [ ] "done" event fires at end

### Test Enhanced Prompts
- [ ] Citations on every sentence
- [ ] Blog-style formatting with headings
- [ ] Conclusion/summary paragraph included

---

## Dependencies to Add

```txt
# Add to requirements.txt
beautifulsoup4==4.12.3
pypdf==4.3.1
lxml==5.3.0  # For BeautifulSoup HTML parsing
```

---

## Summary

**Current Status:** 🟡 Core architecture matches, critical features missing

**After Phase 1 fixes:** 🟢 95%+ feature parity with Perplexica

**Key Actions:**
1. Implement URL/PDF fetching and summarization
2. Add "not_needed" decision handling
3. Implement token streaming
4. Adopt full Perplexica prompts

**Timeline:** 2-3 weeks for complete core parity
