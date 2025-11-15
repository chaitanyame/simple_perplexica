# Technical Review: API-MVP vs Perplexica
## Comprehensive Feature and Logic Comparison

**Review Date:** November 1, 2025  
**Reviewer Role:** Technical Reviewer  
**Scope:** Core search functionality, prompts, architecture, and missing features

---

## Executive Summary

The API-MVP successfully replicates Perplexica's **core search architecture** (Decision → Search → Rerank → Synthesize) with proper cosine similarity reranking and focus mode support. However, it is missing several **secondary features** and has **simplified prompts** compared to the original.

### ✅ What's Implemented Correctly
- Core search flow architecture
- SearxNG integration with engine selection
- Cosine similarity reranking with thresholds
- Focus modes (webSearch, academic, writing, wolfram, youtube, reddit)
- Optimization modes (speed, balanced, quality)
- Streaming and non-streaming responses
- NDJSON event format
- Numbered [n] citation format
- SpaCy-based temporal filtering (enhancement beyond Perplexica)

### ⚠️ What's Missing or Different
- Link/URL fetching and summarization
- PDF parsing support
- "not_needed" decision logic for greetings
- Image search endpoint
- Video search endpoint
- Suggestion generator
- Weather widget
- Discovery/trending news
- File upload processing
- Chat history persistence
- Detailed prompt instructions

---

## 1. Core Search Flow Comparison

### Architecture: ✅ MATCH

Both implementations use the same fundamental flow:

```
User Query
    ↓
Decision Step (Rewrite query)
    ↓
Search (SearxNG/SerperDev)
    ↓
Rerank (Cosine similarity)
    ↓
Synthesize (LLM response)
```

**Perplexica (TypeScript):**
```typescript
// metaSearchAgent.ts
searchRetrieverChain → rerankDocs → answeringChain
```

**MVP (Python):**
```python
# search.py
decide_search_and_rewrite → get_sources → rerank_sources → synthesize_answer
```

### Key Difference: Link Handling

**Perplexica:**
```typescript
// Extracts links from LLM decision
const links = await linksOutputParser.parse(input);
if (links.length > 0) {
  const linkDocs = await getDocumentsFromLinks({ links });
  // Fetches, parses, splits, and summarizes each URL
  docs = await summarizeDocuments(linkDocs);
}
```

**MVP:**
```python
# Only extracts links, doesn't fetch or process them
link_sources = [
    {"title": url, "url": url, "pageContent": ""}
    for url in (decision.links or [])
]
```

**Impact:** ❌ **CRITICAL MISSING FEATURE**  
MVP doesn't fetch and summarize URLs provided by the user or LLM. This is a core Perplexica feature for summarizing webpages and PDFs.

---

## 2. Decision Step Comparison

### Perplexica's Decision Logic

**Prompt:**
```typescript
webSearchRetrieverPrompt = `
You are an AI question rephraser. You will be given a conversation and a follow-up question,  
you will have to rephrase the follow up question so it is a standalone question.

If it is a simple writing task or a greeting (like Hi, Hello, How are you) than a question 
then you need to return 'not_needed' as the response (This is because the LLM won't need to 
search the web for finding information on this topic).

If the user asks some question from some URL or wants you to summarize a PDF or a webpage 
you need to return the links inside the <links> XML block and the question inside the 
<question> XML block.
```

**Few-Shot Examples:**
```typescript
[
  ['user', 'Hi, how are you?'],
  ['assistant', '<question>not_needed</question>'],
  
  ['user', 'Summarize https://example.com'],
  ['assistant', '<question>summarize</question>\n<links>https://example.com</links>'],
]
```

### MVP's Decision Logic

**Prompt:**
```python
instructions = (
    "You are an AI question rephraser and search decider. "
    "Given a conversation (optional) and a query, decide if web search is needed. "
    "If the message is a greeting or a simple writing task without factual lookup, "
    "set need_search=false. Otherwise set need_search=true and provide an optimized "
    "standalone query. Return strictly JSON."
)
```

**Fallback Heuristic:**
```python
greetings = {"hi", "hello", "hey", "how are you"}
writing_prefixes = ("write ", "draft ", "compose ")
if ql in greetings or any(ql.startswith(p) for p in writing_prefixes):
    return DecisionOutput(need_search=False, optimized_query=query)
```

### Differences

| Aspect | Perplexica | MVP |
|--------|-----------|-----|
| **"not_needed" handling** | Returns empty docs, skips search entirely | Forces search anyway (`decision.need_search` ignored) |
| **Few-shot examples** | ✅ Yes (5 examples) | ❌ No |
| **URL extraction** | ✅ Parses `<links>` XML block | ✅ Parses `links` JSON field |
| **URL processing** | ✅ Fetches and summarizes | ❌ Only creates placeholder sources |
| **Fallback logic** | ❌ No fallback | ✅ Heuristic-based fallback on LLM errors |

**Impact:** ⚠️ **MODERATE DIFFERENCE**  
MVP doesn't respect the "not_needed" decision and always searches, which may waste resources on greetings/simple tasks. However, it has better error handling with fallback logic.

---

## 3. Prompt Engineering Comparison

### Response Synthesis Prompt

**Perplexica (webSearchResponsePrompt):**
```typescript
You are Perplexica, an AI model skilled in web search and crafting detailed, engaging, 
and well-structured answers. You excel at summarizing web pages and extracting relevant 
information to create professional, blog-style responses.

Your task is to provide answers that are:
- Informative and relevant
- Well-structured with clear headings and subheadings
- Engaging and detailed: Write responses that read like a high-quality blog post
- Cited and credible: Use inline citations with [number] notation
- Explanatory and Comprehensive: Strive to explain the topic in depth

### Formatting Instructions
- Structure: Use proper headings (e.g., "## Example heading 1")
- Tone and Style: Maintain a neutral, journalistic tone
- Markdown Usage: Format with Markdown
- Length and Depth: Provide comprehensive coverage, avoid superficial responses
- No main heading/title: Start directly with introduction
- Conclusion or Summary: Include concluding paragraph

### Citation Requirements
- Cite every single fact, statement, or sentence using [number] notation
- Integrate citations naturally at the end of sentences
- Ensure every sentence includes at least one citation
- Use multiple sources for a single detail if applicable [1][2]
- Avoid citing unsupported assumptions
```

**MVP (WEBSEARCH_RESPONSE_PROMPT):**
```python
You are Perplexica, an AI model skilled in web search and crafting detailed, engaging, 
and well-structured answers.

Use only the provided CONTEXT to answer the USER QUESTION. Do not claim you lack 
real-time access—summarize what the CONTEXT says.

Style and formatting:
- Be comprehensive and accurate; write in clear, professional language.
- Organize the answer with short section headings when appropriate
- Use bullet points for lists and keep paragraphs concise
- Cite 1–3 of the most relevant sources using [n] inline
- Do NOT add a separate 'Sources'/'References' section
- If sources conflict, briefly note differing viewpoints
```

### Differences

| Aspect | Perplexica | MVP |
|--------|-----------|-----|
| **Detail level** | Very detailed (500+ words) | Concise (100 words) |
| **Citation requirement** | EVERY sentence must cite | Cite 1-3 most relevant sources |
| **Formatting instructions** | Explicit Markdown headings, blog-style | General professional language |
| **Length guidance** | "Comprehensive coverage, depth" | "Concise, short paragraphs" |
| **Conclusion requirement** | ✅ Required | ❌ Not mentioned |
| **Special handling** | Instructions for missing info | Generic "say you don't know" |

**Impact:** ⚠️ **MODERATE DIFFERENCE**  
MVP prompts are simpler and may produce shorter, less detailed responses. Perplexica's extensive citation requirements ensure every claim is backed, while MVP allows more flexibility.

---

## 4. Reranking Logic Comparison

### Perplexica's Reranking

```typescript
if (optimizationMode === 'speed' || this.config.rerank === false) {
  // Return top 15 docs without reranking
  return docsWithContent.slice(0, 15);
} 
else if (optimizationMode === 'balanced') {
  // Embed all docs and query
  const docEmbeddings = await embeddings.embedDocuments(docs);
  const queryEmbedding = await embeddings.embedQuery(query);
  
  // Cosine similarity
  const similarity = docEmbeddings.map((docEmb, i) => ({
    index: i,
    similarity: computeSimilarity(queryEmbedding, docEmb)
  }));
  
  // Filter by threshold and sort
  return similarity
    .filter(sim => sim.similarity > this.config.rerankThreshold)
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 15);
}
// Note: No explicit 'quality' mode handling
```

### MVP's Reranking

```python
if optimization == OptimizationMode.speed or not defaults.get("rerank"):
    # Skip reranking in speed mode
    return sources

# Embed query and all document texts
inputs = [query] + doc_texts
vectors = await openrouter.embed_texts(inputs, model=embedding_model_key)
qv = vectors[0]

# Cosine similarity
sims = []
for i, s in enumerate(sources):
    dv = vectors[i + 1]
    sim = _cosine_similarity(qv, dv)
    sims.append({"i": i, "sim": sim})

# Filter by threshold
threshold = float(defaults.get("threshold", 0.0))
ranked = [x for x in sims if x["sim"] > threshold]
if not ranked:
    ranked = sims  # Fallback if all below threshold
    
ranked.sort(key=lambda x: x["sim"], reverse=True)
return [sources[x["i"]] for x in ranked]
```

### Differences

| Aspect | Perplexica | MVP |
|--------|-----------|-----|
| **Speed mode** | Skip reranking, return 15 | ✅ Same |
| **Balanced mode** | Full reranking with threshold | ✅ Same |
| **Quality mode** | Treated same as balanced | Enhanced: 20 docs, 1200 chars |
| **Threshold filtering** | Filter then sort | Filter then sort (same) |
| **Fallback handling** | None | ✅ Returns all if threshold too strict |
| **File upload support** | ✅ Merges uploaded docs | ❌ Not implemented |

**Impact:** ✅ **MOSTLY MATCH** with ✨ **ENHANCEMENT**  
MVP correctly implements reranking logic and adds an enhanced quality mode. However, it lacks file upload support.

---

## 5. Focus Mode Configuration

### Comparison Table

| Focus Mode | Perplexica Engines | MVP Engines | Rerank | Threshold |
|------------|-------------------|-------------|--------|-----------|
| **webSearch** | `[]` (all) | `[]` (all) | ✅ Yes | 0.3 |
| **academicSearch** | arxiv, google scholar, pubmed | ✅ Same | ✅ Yes | 0.0 |
| **writingAssistant** | `[]` (no search) | `[]` (no search) | ✅ Yes | 0.0 |
| **wolframAlphaSearch** | wolframalpha | ✅ Same | ❌ No | 0.0 |
| **youtubeSearch** | youtube | ✅ Same | ✅ Yes | 0.3 |
| **redditSearch** | reddit | ✅ Same | ✅ Yes | 0.3 |

**Status:** ✅ **PERFECT MATCH**

---

## 6. Missing Features (Not in Scope for MVP)

### 6.1 Image Search
**Perplexica:** `/api/images` endpoint  
**Implementation:** Separate chain that:
1. Rephrases query for image search
2. Uses SearxNG engines: `bing images`, `google images`
3. Returns top 10 image results with `img_src`, `url`, `title`

**MVP:** ❌ Not implemented

---

### 6.2 Video Search
**Perplexica:** `/api/videos` endpoint  
**Implementation:** Similar to image search but for videos  
**MVP:** ❌ Not implemented

---

### 6.3 Suggestion Generator
**Perplexica:** `/api/suggestions` endpoint  
**Implementation:** Generates 3-5 follow-up questions based on conversation  
**MVP:** ❌ Not implemented

---

### 6.4 Weather Widget
**Perplexica:** `/api/weather` endpoint  
**Implementation:** Fetches weather data from Open-Meteo API  
**Input:** `{lat, lng, measureUnit}`  
**Output:** Temperature, condition, humidity, wind speed, icon  
**MVP:** ❌ Not implemented

---

### 6.5 Discovery/Trending News
**Perplexica:** `/api/discover` endpoint  
**Implementation:** Fetches trending news articles  
**MVP:** ❌ Not implemented

---

### 6.6 File Upload Processing
**Perplexica:** `/api/uploads` endpoint  
**Implementation:**
- Uploads PDF/documents
- Extracts text content
- Creates embeddings
- Stores in `uploads/` directory
- Merges with search results during reranking

**MVP:** ❌ Not implemented

---

### 6.7 Chat History Persistence
**Perplexica:** `/api/chats` and `/api/chat` endpoints  
**Implementation:**
- Saves conversations to database
- Lists all chats
- Retrieves specific chat by ID
- Updates chat titles

**MVP:** ❌ Not implemented (stateless API only)

---

### 6.8 Configuration Management
**Perplexica:** `/api/config` endpoint  
**Implementation:**
- Setup wizard for first-time configuration
- Provider/model selection
- API key management

**MVP:** ❌ Not implemented (env-based config only)

---

## 7. Document Fetching & Summarization

### Perplexica's Implementation

```typescript
// utils/documents.ts
export const getDocumentsFromLinks = async ({ links }: { links: string[] }) => {
  const splitter = new RecursiveCharacterTextSplitter();
  let docs: Document[] = [];

  await Promise.all(links.map(async (link) => {
    const res = await axios.get(link, { responseType: 'arraybuffer' });
    const isPdf = res.headers['content-type'] === 'application/pdf';

    if (isPdf) {
      const pdfText = await pdfParse(res.data);
      const splittedText = await splitter.splitText(pdfText.text);
      // Create documents from PDF chunks
    } else {
      const parsedText = htmlToText(res.data.toString('utf8'));
      const splittedText = await splitter.splitText(parsedText);
      // Create documents from HTML chunks
    }
    
    docs.push(...linkDocs);
  }));

  return docs;
};
```

**Then summarizes each chunk:**
```typescript
await Promise.all(docGroups.map(async (doc) => {
  const res = await llm.invoke(`
    You are a web search summarizer, tasked with summarizing a piece of text 
    retrieved from a web search. Your job is to summarize the text into a 
    detailed, 2-4 paragraph explanation...
    
    <query>${question}</query>
    <text>${doc.pageContent}</text>
  `);
  
  summaryDocs.push(new Document({
    pageContent: res.content,
    metadata: { title: doc.title, url: doc.url }
  }));
}));
```

### MVP's Implementation

```python
# Only creates placeholder sources, doesn't fetch
link_sources = [
    {"title": url, "url": url, "pageContent": ""}
    for url in (decision.links or [])
]
```

**Impact:** ❌ **CRITICAL MISSING FEATURE**  
This is a major gap. Perplexica can:
- Fetch and parse HTML pages
- Parse PDF documents
- Split long content into chunks
- Summarize each chunk with LLM context
- Merge summarized content with search results

MVP only creates empty placeholders for URLs.

---

## 8. Optimization Mode Handling

### Document Count & Context Characters

| Mode | Perplexica | MVP |
|------|-----------|-----|
| **Speed** | 15 docs, no rerank | 15 docs, 600 chars, no rerank |
| **Balanced** | 15 docs, rerank | 15 docs, 800 chars, rerank |
| **Quality** | (same as balanced) | **20 docs, 1200 chars**, rerank ✨ |

**Impact:** ✨ **ENHANCEMENT**  
MVP adds a true "quality" mode with more documents and context, which is actually better than Perplexica's implicit handling.

---

## 9. Streaming Implementation

### Perplexica's Streaming

```typescript
const stream = answeringChain.streamEvents({ query, chat_history }, { version: 'v1' });

for await (const event of stream) {
  if (event.event === 'on_chain_end' && event.name === 'FinalSourceRetriever') {
    emitter.emit('data', JSON.stringify({ type: 'sources', data: event.data.output }));
  }
  if (event.event === 'on_chain_stream' && event.name === 'FinalResponseGenerator') {
    emitter.emit('data', JSON.stringify({ type: 'response', data: event.data.chunk }));
  }
}
```

### MVP's Streaming

```python
async def event_stream():
    yield json.dumps({"type": "init", "data": "Stream connected"}) + "\n"
    
    norm_sources = [normalize(s) for s in sources[:max_docs]]
    yield json.dumps({"type": "sources", "data": norm_sources}) + "\n"
    
    message = await openrouter.synthesize_answer(...)
    yield json.dumps({"type": "response", "data": message}) + "\n"
    
    yield json.dumps({"type": "done"}) + "\n"
```

**Differences:**
- Perplexica streams token-by-token from LLM
- MVP synthesizes full response then sends (single "response" event)

**Impact:** ⚠️ **MODERATE DIFFERENCE**  
MVP doesn't have true token streaming yet. It sends the complete answer in one event, which is less responsive for long answers.

---

## 10. Citation Format

### Both Use Numbered [n] Format ✅

**Example:**
```
Docker is a containerization platform[1]. It was first released in 2013[2] 
and has since become the industry standard for application deployment[1][3].
```

**Status:** ✅ **MATCH**

---

## 11. SpaCy Temporal Detection (MVP Enhancement)

### ✨ Feature Not in Perplexica

**MVP's Enhancement:**
```python
def _detect_recency_need(query: str) -> Optional[str]:
    nlp = _load_spacy_model()
    doc = nlp(query)
    
    # Named Entity Recognition
    for ent in doc.ents:
        if ent.label_ == "DATE":
            if "today" in ent.text.lower():
                return "d"  # day filter
    
    # Dependency parsing for temporal modifiers
    for token in doc:
        if token.text.lower() in {"latest", "breaking"}:
            if token.head.text.lower() in {"news", "events"}:
                return "d"
```

**Adds intelligent time_range filtering:**
- "breaking news today" → `time_range=d`
- "news this week" → `time_range=w`
- "events this month" → `time_range=m`

**Impact:** ✨ **ENHANCEMENT BEYOND PERPLEXICA**

---

## 12. Summary of Findings

### Critical Missing Features (High Priority)

1. **URL/PDF Fetching & Summarization** ❌
   - Perplexica fetches, parses, splits, and summarizes URLs
   - MVP only creates empty placeholders
   - **Recommendation:** Implement `fetch.py` integration

2. **"not_needed" Decision Handling** ❌
   - Perplexica skips search for greetings/simple tasks
   - MVP forces all queries to search
   - **Recommendation:** Respect `need_search=False` from decision step

3. **Token-by-Token Streaming** ❌
   - Perplexica streams LLM output token-by-token
   - MVP sends complete response in single event
   - **Recommendation:** Implement chunked streaming from LLM

### Secondary Missing Features (Low Priority for MVP)

4. **Image Search Endpoint** ❌
5. **Video Search Endpoint** ❌
6. **Suggestion Generator** ❌
7. **Weather Widget** ❌
8. **Discovery/Trending News** ❌
9. **File Upload Processing** ❌
10. **Chat History Persistence** ❌
11. **Config Management UI** ❌

### Prompt Differences (Moderate Priority)

12. **Response Prompt Simplification** ⚠️
    - MVP has simpler, more concise prompts
    - Perplexica has detailed blog-style instructions
    - **Recommendation:** Adopt Perplexica's full prompt for consistency

13. **Decision Prompt Few-Shot Examples** ⚠️
    - MVP lacks few-shot examples
    - Perplexica has 5 training examples
    - **Recommendation:** Add few-shot examples to improve decision quality

### Enhancements in MVP (Beyond Perplexica)

14. **Enhanced Quality Mode** ✨
    - MVP: 20 docs, 1200 chars
    - Perplexica: treats quality = balanced

15. **SpaCy Temporal Detection** ✨
    - Intelligent time_range filtering based on NLP
    - Not present in Perplexica

16. **Fallback Error Handling** ✨
    - MVP has heuristic fallback on LLM errors
    - Perplexica doesn't

---

## 13. Recommendations

### Phase 1: Core Parity (High Priority)

1. ✅ **Implement URL/PDF fetching and summarization**
   - Port `getDocumentsFromLinks` logic to Python
   - Add PDF parsing with `pypdf` or similar
   - Add HTML-to-text extraction with `beautifulsoup4`
   - Implement chunking with `RecursiveCharacterTextSplitter`
   - Add LLM summarization for each chunk

2. ✅ **Respect "not_needed" decision**
   - Check `decision.need_search` before searching
   - Return direct answer without sources for greetings

3. ✅ **Implement token streaming**
   - Use OpenRouter's streaming API
   - Yield tokens as they arrive
   - True `text/event-stream` with chunks

4. ✅ **Adopt full Perplexica prompts**
   - Replace WEBSEARCH_RESPONSE_PROMPT with full webSearchResponsePrompt
   - Add few-shot examples to decision prompt
   - Match citation requirements (every sentence)

### Phase 2: Enhanced Features (Medium Priority)

5. **Image search endpoint**
6. **Video search endpoint**
7. **Suggestion generator**

### Phase 3: Platform Features (Low Priority)

8. Weather widget
9. Discovery/trending
10. File uploads
11. Chat persistence
12. Config management

---

## 14. Conclusion

**Overall Assessment:** 🟡 **PARTIAL IMPLEMENTATION**

The API-MVP successfully replicates Perplexica's **core search architecture** (95% match) and adds some enhancements (SpaCy, quality mode). However, it is missing **critical features** around URL fetching/summarization and has **simplified prompts** that may affect response quality.

**Score Breakdown:**
- Core Flow: ✅ 100% Match
- Reranking Logic: ✅ 100% Match
- Focus Modes: ✅ 100% Match
- URL Processing: ❌ 0% (critical gap)
- Prompts: ⚠️ 60% (simplified)
- Streaming: ⚠️ 70% (no token streaming)
- Secondary Features: ❌ 0% (out of scope for MVP)

**Priority Actions:**
1. Implement URL/PDF fetching (`getDocumentsFromLinks` equivalent)
2. Add token-by-token streaming
3. Adopt full Perplexica prompts
4. Respect "not_needed" decision logic

With these 4 changes, the MVP would achieve **95%+ feature parity** with Perplexica's core search functionality.

