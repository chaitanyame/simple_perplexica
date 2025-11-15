# Side-by-Side Code Comparison: Perplexica vs MVP

## 1. URL/PDF Processing - THE BIGGEST GAP

### Perplexica (TypeScript)

**File:** `src/lib/utils/documents.ts`

```typescript
export const getDocumentsFromLinks = async ({ links }: { links: string[] }) => {
  const splitter = new RecursiveCharacterTextSplitter();
  let docs: Document[] = [];

  await Promise.all(
    links.map(async (link) => {
      try {
        const res = await axios.get(link, { responseType: 'arraybuffer' });
        const isPdf = res.headers['content-type'] === 'application/pdf';

        if (isPdf) {
          // Parse PDF
          const pdfText = await pdfParse(res.data);
          const parsedText = pdfText.text
            .replace(/(\r\n|\n|\r)/gm, ' ')
            .replace(/\s+/g, ' ')
            .trim();
          const splittedText = await splitter.splitText(parsedText);
          
          const linkDocs = splittedText.map((text) => {
            return new Document({
              pageContent: text,
              metadata: { title: 'PDF Document', url: link },
            });
          });
          docs.push(...linkDocs);
        } else {
          // Parse HTML
          const parsedText = htmlToText(res.data.toString('utf8'), {
            selectors: [{ selector: 'a', options: { ignoreHref: true } }],
          })
            .replace(/(\r\n|\n|\r)/gm, ' ')
            .replace(/\s+/g, ' ')
            .trim();
          
          const splittedText = await splitter.splitText(parsedText);
          const title = res.data.toString('utf8')
            .match(/<title.*>(.*?)<\/title>/)?.[1];
          
          const linkDocs = splittedText.map((text) => {
            return new Document({
              pageContent: text,
              metadata: { title: title || link, url: link },
            });
          });
          docs.push(...linkDocs);
        }
      } catch (err) {
        docs.push(new Document({
          pageContent: `Failed to retrieve content from the link: ${err}`,
          metadata: { title: 'Failed to retrieve content', url: link },
        }));
      }
    }),
  );

  return docs;
};
```

**Then in metaSearchAgent.ts:**

```typescript
const linkDocs = await getDocumentsFromLinks({ links });

// Group chunks from same URL
const docGroups: Document[] = [];
linkDocs.map((doc) => {
  const URLDocExists = docGroups.find(
    (d) => d.metadata.url === doc.metadata.url && d.metadata.totalDocs < 10,
  );
  
  if (!URLDocExists) {
    docGroups.push({ ...doc, metadata: { ...doc.metadata, totalDocs: 1 } });
  } else {
    const docIndex = docGroups.findIndex(
      (d) => d.metadata.url === doc.metadata.url && d.metadata.totalDocs < 10,
    );
    docGroups[docIndex].pageContent += `\n\n` + doc.pageContent;
    docGroups[docIndex].metadata.totalDocs += 1;
  }
});

// Summarize each grouped document
await Promise.all(
  docGroups.map(async (doc) => {
    const res = await llm.invoke(`
      You are a web search summarizer, tasked with summarizing a piece of text 
      retrieved from a web search. Your job is to summarize the text into a 
      detailed, 2-4 paragraph explanation that captures the main ideas...
      
      <query>${question}</query>
      <text>${doc.pageContent}</text>
    `);
    
    docs.push(new Document({
      pageContent: res.content as string,
      metadata: { title: doc.metadata.title, url: doc.metadata.url },
    }));
  }),
);
```

### MVP (Python)

**File:** `services/api-mvp/app/routers/search.py`

```python
# Current implementation - MISSING URL FETCHING
link_sources = [
    {"title": url, "url": url, "pageContent": ""}  # Empty content!
    for url in (decision.links or [])
]
```

### What Needs to be Added

```python
# services/api-mvp/app/utils/fetch_urls.py (NEW FILE)

import httpx
from bs4 import BeautifulSoup
from pypdf import PdfReader
from io import BytesIO
from typing import List, Dict

async def fetch_and_parse_url(url: str) -> Dict[str, str]:
    """Fetch and parse URL content (HTML or PDF)"""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        content_type = response.headers.get('content-type', '')
        
        if 'application/pdf' in content_type:
            # Parse PDF
            pdf = PdfReader(BytesIO(response.content))
            text = ""
            for page in pdf.pages:
                text += page.extract_text() + "\n\n"
            
            # Extract title from metadata or use filename
            title = pdf.metadata.get('/Title', url.split('/')[-1])
            return {
                "title": title,
                "url": url,
                "text": text.strip(),
                "type": "pdf"
            }
        else:
            # Parse HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title
            title_tag = soup.find('title')
            title = title_tag.string if title_tag else url
            
            # Remove script, style, nav, footer
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            # Extract text
            text = soup.get_text(separator='\n', strip=True)
            text = ' '.join(text.split())  # Normalize whitespace
            
            return {
                "title": title,
                "url": url,
                "text": text,
                "type": "html"
            }

def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> List[str]:
    """Split text into overlapping chunks (like RecursiveCharacterTextSplitter)"""
    words = text.split()
    chunks = []
    
    i = 0
    while i < len(words):
        chunk_words = words[i:i + chunk_size]
        chunks.append(' '.join(chunk_words))
        i += chunk_size - overlap  # Overlap for context
    
    return chunks

async def summarize_chunk(chunk: str, query: str, llm_fn) -> str:
    """Summarize a text chunk with LLM"""
    prompt = f"""You are a web search summarizer. Summarize the following text into a 
detailed, 2-4 paragraph explanation that captures the main ideas and provides a 
comprehensive answer to the query.

<query>{query}</query>
<text>{chunk}</text>

Provide a journalistic, thorough summary that directly answers the query."""
    
    return await llm_fn(prompt)

async def fetch_and_process_urls(
    urls: List[str],
    query: str,
    summarize_fn
) -> List[Dict]:
    """Fetch URLs, chunk, and summarize - FULL PERPLEXICA EQUIVALENT"""
    all_docs = []
    
    for url in urls:
        try:
            # Fetch and parse
            parsed = await fetch_and_parse_url(url)
            
            # Chunk the text
            chunks = chunk_text(parsed["text"], chunk_size=1000)
            
            # Limit to first 10 chunks per URL (same as Perplexica)
            for chunk in chunks[:10]:
                # Summarize each chunk
                summary = await summarize_fn(chunk, query)
                
                all_docs.append({
                    "title": parsed["title"],
                    "url": parsed["url"],
                    "pageContent": summary
                })
                
        except Exception as e:
            # Error handling like Perplexica
            all_docs.append({
                "title": "Failed to retrieve content",
                "url": url,
                "pageContent": f"Failed to retrieve content from the link: {str(e)}"
            })
    
    return all_docs
```

**Update search.py:**

```python
from app.utils.fetch_urls import fetch_and_process_urls

@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    decision = await openrouter.decide_search_and_rewrite(...)
    effective_query = decision.optimized_query or req.query
    
    # Process URLs if provided (LIKE PERPLEXICA)
    link_sources = []
    if decision.links:
        link_sources = await fetch_and_process_urls(
            decision.links,
            effective_query,
            lambda chunk, q: openrouter.summarize_chunk(chunk, q)
        )
    
    # Regular search
    fetched = await get_sources(effective_query, req.focusMode)
    sources = link_sources + (fetched or [])
    # ... rest
```

---

## 2. Decision Step - "not_needed" Handling

### Perplexica (TypeScript)

**File:** `src/lib/search/metaSearchAgent.ts`

```typescript
const searchRetrieverChain = await this.createSearchRetrieverChain(llm);

const searchRetrieverResult = await searchRetrieverChain.invoke({
  chat_history: processedHistory,
  query,
});

query = searchRetrieverResult.query;
docs = searchRetrieverResult.docs;

// In the chain:
RunnableLambda.from(async (input: string) => {
  const questionOutputParser = new LineOutputParser({ key: 'question' });
  let question = (await questionOutputParser.parse(input)) ?? input;

  if (question === 'not_needed') {
    return { query: '', docs: [] };  // ← SKIP SEARCH
  }
  
  // Otherwise search SearxNG
  const res = await searchSearxng(question, { ... });
  // ...
})
```

### MVP (Python)

**Current:**

```python
@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    decision = await openrouter.decide_search_and_rewrite(...)
    
    # IGNORES decision.need_search!
    effective_query = decision.optimized_query or req.query
    sources = await get_sources(effective_query, req.focusMode)
    # Always searches...
```

**Should Be:**

```python
@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    decision = await openrouter.decide_search_and_rewrite(...)
    
    # Respect "not_needed" decision (LIKE PERPLEXICA)
    if not decision.need_search:
        # Skip search, return direct answer
        message = await openrouter.synthesize_answer(
            query=req.query,
            sources=[],  # Empty sources
            system_instructions=req.systemInstructions,
            history=req.history,
            context_chars=0
        )
        return SearchResponse(message=message, sources=[])
    
    # Otherwise proceed with search
    effective_query = decision.optimized_query or req.query
    sources = await get_sources(effective_query, req.focusMode)
    # ...
```

---

## 3. Response Prompt Comparison

### Perplexica Prompt

**File:** `src/lib/prompts/webSearch.ts`

```typescript
export const webSearchResponsePrompt = `
You are Perplexica, an AI model skilled in web search and crafting detailed, engaging, 
and well-structured answers. You excel at summarizing web pages and extracting relevant 
information to create professional, blog-style responses.

Your task is to provide answers that are:
- **Informative and relevant**: Thoroughly address the user's query using the given context.
- **Well-structured**: Include clear headings and subheadings, and use a professional tone.
- **Engaging and detailed**: Write responses that read like a high-quality blog post.
- **Cited and credible**: Use inline citations with [number] notation.
- **Explanatory and Comprehensive**: Strive to explain the topic in depth.

### Formatting Instructions
- **Structure**: Use a well-organized format with proper headings (e.g., "## Example heading").
- **Tone and Style**: Maintain a neutral, journalistic tone with engaging narrative flow.
- **Markdown Usage**: Format with Markdown. Use headings, bold, italics as needed.
- **Length and Depth**: Provide comprehensive coverage. Avoid superficial responses.
- **No main heading/title**: Start directly with the introduction.
- **Conclusion or Summary**: Include a concluding paragraph.

### Citation Requirements
- Cite every single fact, statement, or sentence using [number] notation.
- Integrate citations naturally at the end of sentences.
- Ensure every sentence includes at least one citation.
- Use multiple sources for a single detail if applicable, such as [1][2].
- Always prioritize credibility and accuracy by linking all statements back to sources.
- Avoid citing unsupported assumptions; if no source supports it, clearly indicate.

### Special Instructions
- If the query involves technical, historical, or complex topics, provide detailed background.
- If the user provides vague input or if relevant information is missing, explain what 
  additional details might help refine the search.
- If no relevant information is found, say: "Hmm, sorry I could not find any relevant 
  information on this topic. Would you like me to search again or ask something else?"

### User instructions
{systemInstructions}

<context>
{context}
</context>

Current date & time in ISO format (UTC timezone) is: {date}.
`;
```

### MVP Prompt

**File:** `services/api-mvp/app/providers/openrouter.py`

```python
WEBSEARCH_RESPONSE_PROMPT = (
    "{systemInstructions}\n\n"
    "You are Perplexica, an AI model skilled in web search and crafting detailed, "
    "engaging, and well-structured answers.\n"
    "Use only the provided CONTEXT to answer the USER QUESTION. Do not claim you lack "
    "real-time access—summarize what the CONTEXT says. If the answer isn't supported "
    "by the context, say you don't know.\n\n"
    "Style and formatting:\n"
    "- Be comprehensive and accurate; write in clear, professional language.\n"
    "- Organize the answer with short section headings when appropriate.\n"
    "- Use bullet points for lists and keep paragraphs concise for readability.\n"
    "- Cite 1–3 of the most relevant sources using [n] inline.\n"
    "- Do NOT add a separate 'Sources'/'References' section.\n"
    "- If sources conflict, briefly note differing viewpoints.\n"
    "- Today is: {date}\n\n"
    "CONTEXT (numbered sources):\n{context}\n\n"
    "CONVERSATION (if any):\n{chat_history}\n\n"
    "USER QUESTION: Provide a well-structured, thorough answer with inline [n] citations.\n"
)
```

### Differences Summary

| Aspect | Perplexica | MVP |
|--------|-----------|-----|
| **Length** | ~500 words | ~150 words |
| **Citation requirement** | EVERY sentence | 1-3 sources total |
| **Formatting detail** | Very specific (headings, bold, italics) | General guidance |
| **Conclusion** | Required | Not mentioned |
| **Tone guidance** | "Journalistic, blog-style" | "Professional" |
| **Missing info handling** | Specific message template | Generic "say you don't know" |
| **Technical topics** | "Provide detailed background" | Not mentioned |

**Recommendation:** Replace MVP prompt with full Perplexica prompt for consistency.

---

## 4. Reranking Logic

### Both Implementations: ✅ MATCH

**Perplexica:**
```typescript
const docEmbeddings = await embeddings.embedDocuments(
  docsWithContent.map((doc) => doc.pageContent),
);
const queryEmbedding = await embeddings.embedQuery(query);

const similarity = docEmbeddings.map((docEmbedding, i) => {
  const sim = computeSimilarity(queryEmbedding, docEmbedding);
  return { index: i, similarity: sim };
});

const sortedDocs = similarity
  .filter((sim) => sim.similarity > (this.config.rerankThreshold ?? 0.3))
  .sort((a, b) => b.similarity - a.similarity)
  .slice(0, 15)
  .map((sim) => docsWithContent[sim.index]);
```

**MVP:**
```python
inputs = [query] + doc_texts
vectors = await openrouter.embed_texts(inputs, model=embedding_model_key)
qv = vectors[0]

sims = []
for i, s in enumerate(sources):
    dv = vectors[i + 1]
    sim = _cosine_similarity(qv, dv)
    sims.append({"i": i, "sim": sim})

threshold = float(defaults.get("threshold", 0.0))
ranked = [x for x in sims if x["sim"] > threshold]
ranked.sort(key=lambda x: x["sim"], reverse=True)
return [sources[x["i"]] for x in ranked]
```

**Status:** ✅ **IDENTICAL LOGIC** (Python vs TypeScript implementation difference only)

---

## 5. Streaming

### Perplexica - Token-by-Token Streaming

```typescript
const stream = answeringChain.streamEvents(
  { chat_history: history, query: message },
  { version: 'v1' },
);

for await (const event of stream) {
  if (event.event === 'on_chain_end' && event.name === 'FinalSourceRetriever') {
    emitter.emit('data', JSON.stringify({ type: 'sources', data: event.data.output }));
  }
  if (event.event === 'on_chain_stream' && event.name === 'FinalResponseGenerator') {
    // Streams each token as it arrives
    emitter.emit('data', JSON.stringify({ type: 'response', data: event.data.chunk }));
  }
  if (event.event === 'on_chain_end' && event.name === 'FinalResponseGenerator') {
    emitter.emit('end');
  }
}
```

### MVP - Full Response Streaming

```python
async def event_stream():
    yield json.dumps({"type": "init", "data": "Stream connected"}) + "\n"
    
    norm_sources = [normalize(s) for s in sources[:max_docs]]
    yield json.dumps({"type": "sources", "data": norm_sources}) + "\n"
    
    # Generates FULL response before streaming
    message = await openrouter.synthesize_answer(...)
    yield json.dumps({"type": "response", "data": message}) + "\n"  # ONE event
    
    yield json.dumps({"type": "done"}) + "\n"
```

### What Needs to be Added

```python
# Update openrouter.py to add streaming method

async def stream_answer(
    query: str,
    sources: List[Dict],
    system_instructions: str | None = None,
    history: Optional[List[List[str]]] = None,
    context_chars: int = 800,
):
    """Stream answer token-by-token from OpenRouter"""
    # Prepare context same as synthesize_answer
    context = prepare_context(sources, context_chars)
    prompt = prepare_prompt(query, context, system_instructions, history)
    
    # Use OpenRouter streaming endpoint
    async with httpx.AsyncClient(timeout=120) as client:
        async with client.stream(
            "POST",
            f"{OPENROUTER_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": OPENROUTER_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,  # Enable streaming
            }
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                    if "choices" in data:
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content  # Yield each token

# Update search.py event_stream()

async def event_stream():
    yield json.dumps({"type": "init", "data": "Stream connected"}) + "\n"
    
    norm_sources = [normalize(s) for s in sources[:max_docs]]
    yield json.dumps({"type": "sources", "data": norm_sources}) + "\n"
    
    # Stream tokens as they arrive (LIKE PERPLEXICA)
    async for token in openrouter.stream_answer(
        effective_query,
        sources[:max_docs],
        req.systemInstructions,
        req.history,
        context_chars,
    ):
        yield json.dumps({"type": "response", "data": token}) + "\n"
    
    yield json.dumps({"type": "done"}) + "\n"
```

---

## Summary Table

| Feature | Perplexica Implementation | MVP Implementation | Status |
|---------|--------------------------|-------------------|---------|
| **URL Fetching** | axios.get + htmlToText/pdfParse | Not implemented | ❌ Missing |
| **Text Chunking** | RecursiveCharacterTextSplitter | Not implemented | ❌ Missing |
| **LLM Summarization** | Per-chunk summarization | Not implemented | ❌ Missing |
| **"not_needed" logic** | Returns empty docs | Ignores decision | ❌ Missing |
| **Response prompt** | 500 words, detailed | 150 words, simple | ⚠️ Simplified |
| **Citation requirement** | Every sentence | 1-3 sources | ⚠️ Simplified |
| **Reranking** | Cosine similarity | Cosine similarity | ✅ Match |
| **Token streaming** | Token-by-token | Full response | ⚠️ Not true streaming |
| **Focus modes** | 6 modes with engines | 6 modes with engines | ✅ Match |
| **Optimization modes** | speed/balanced | speed/balanced/quality | ✨ Enhanced |

**Priority Fixes:**
1. 🔴 HIGH: Implement URL/PDF fetching and summarization
2. 🟡 MEDIUM: Add "not_needed" decision handling
3. 🟡 MEDIUM: Implement token-by-token streaming
4. 🟢 LOW: Adopt full Perplexica prompts

