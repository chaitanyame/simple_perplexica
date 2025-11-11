# Day 3: PostgreSQL Full-Text Search + Hybrid Retrieval

**Date**: November 10, 2025  
**Status**: ✅ 75% Complete (Database Setup + Repository Implementation Done)  
**Time**: ~2 hours

## 🎯 Objective

Implement hybrid search combining:
1. **Vector similarity** (semantic search via pgvector)
2. **Full-Text Search** (keyword matching via PostgreSQL FTS)
3. **Reciprocal Rank Fusion** (RRF) to merge results

---

## ✅ Completed Work

### 1. PostgreSQL Full-Text Search Setup

#### Database Changes
- ✅ Added `content_fts tsvector` column to `rag_documents` table
- ✅ Created GIN index: `idx_rag_documents_content_fts` for fast FTS queries
- ✅ Created trigger function: `rag_documents_content_fts_trigger()`
- ✅ Created auto-update trigger on INSERT/UPDATE of content
- ✅ Initialized `content_fts` for existing rows

#### SQL Commands Executed
```sql
-- Add tsvector column
ALTER TABLE rag_documents 
ADD COLUMN IF NOT EXISTS content_fts tsvector;

-- Create GIN index
CREATE INDEX IF NOT EXISTS idx_rag_documents_content_fts 
ON rag_documents 
USING GIN(content_fts);

-- Create trigger function
CREATE OR REPLACE FUNCTION rag_documents_content_fts_trigger()
RETURNS trigger AS $$
BEGIN
    NEW.content_fts := to_tsvector('english', COALESCE(NEW.content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger
CREATE TRIGGER tsvector_update_trigger
BEFORE INSERT OR UPDATE OF content
ON rag_documents
FOR EACH ROW
EXECUTE FUNCTION rag_documents_content_fts_trigger();

-- Initialize existing rows
UPDATE rag_documents
SET content_fts = to_tsvector('english', COALESCE(content, ''))
WHERE content_fts IS NULL;
```

### 2. Hybrid Search Implementation

#### VectorStoreRepository.hybrid_search()

**File**: `src/rag/vector_store_repository.py`

**Method Signature**:
```python
async def hybrid_search(
    self,
    session_id: uuid.UUID,
    query_text: str,
    query_vector: list[float],
    top_k: int = 10,
    semantic_weight: float = 0.6,
    keyword_weight: float = 0.4,
) -> list[SearchResult]:
```

**Key Features**:
1. **Reciprocal Rank Fusion (RRF)**:
   - Formula: `1 / (k + rank)` where k=60 (standard constant)
   - Combines rankings from vector + FTS searches
   - Weighted by `semantic_weight` and `keyword_weight`

2. **SQL Query Strategy**:
   ```sql
   WITH session_docs AS (
       -- Filter to documents in current session
       SELECT DISTINCT document_id
       FROM session_documents
       WHERE session_id = :session_id
   ),
   vector_results AS (
       -- Vector similarity search
       SELECT id, content, embedding, doc_metadata,
              (1 - (embedding <=> :query_vector::vector)) AS vector_score,
              ROW_NUMBER() OVER (ORDER BY embedding <=> :query_vector::vector) AS vector_rank
       FROM rag_documents r
       INNER JOIN session_docs sd ON r.id = sd.document_id
   ),
   fts_results AS (
       -- Full-text search
       SELECT id, content, embedding, doc_metadata,
              ts_rank(content_fts, to_tsquery('english', :fts_query)) AS fts_score,
              ROW_NUMBER() OVER (ORDER BY ts_rank(...) DESC) AS fts_rank
       FROM rag_documents r
       INNER JOIN session_docs sd ON r.id = sd.document_id
       WHERE content_fts @@ to_tsquery('english', :fts_query)
   ),
   combined AS (
       -- Merge with RRF scoring
       SELECT 
           COALESCE(v.id, f.id) AS id,
           (semantic_weight / (60 + vector_rank) + 
            keyword_weight / (60 + fts_rank)) AS rrf_score
       FROM vector_results v
       FULL OUTER JOIN fts_results f ON v.id = f.id
   )
   SELECT * FROM combined ORDER BY rrf_score DESC LIMIT :top_k
   ```

3. **Validation**:
   - Checks vector dimension (384)
   - Ensures weights sum to 1.0
   - Fallback to pure vector search if no text query

4. **Error Handling**:
   - Raises `VectorStoreError` for validation failures
   - Handles SQL exceptions gracefully

---

## 📊 Architecture Clarification

### Database Tables

**Existing Tables**:
1. `rag_documents` - Persistent document store
   - ✅ Has `embedding` column (384D pgvector)
   - ✅ Has `content_fts` column (tsvector) - **JUST ADDED**
   - Used for long-term storage

2. `session_documents` - Association table
   - Links sessions to documents
   - Stores relevance scores

3. `research_sessions` - Session tracking
   - Stores query, mode, status, results

**Not Yet Created**:
- `document_embeddings` - Defined in models but table doesn't exist in DB
- This was meant for session-specific temporary storage
- Current implementation uses `rag_documents` directly

### Vector Storage Strategy

**Current**: All embeddings in PostgreSQL with pgvector
- ✅ Single database (no separate vector store)
- ✅ ACID compliance for embeddings + metadata
- ✅ Can combine vector + FTS in single SQL query
- ✅ 384-dimensional vectors (Sentence-Transformers)

---

## 🔄 Remaining Work (Day 3)

### 1. Update SearchAgent to Use Hybrid Search ⏳ IN PROGRESS

**File**: `src/agents/search_agent.py`

**Changes Needed**:
1. Import `hybrid_search()` from `VectorStoreRepository`
2. Update retrieval logic to:
   - Generate query embedding (already done)
   - Extract query text
   - Call `hybrid_search(session_id, query_text, query_vector)`
   - Use configurable weights (default: 0.6 semantic + 0.4 keyword)

3. Add configuration:
   ```python
   SEMANTIC_WEIGHT = 0.6  # Weight for vector similarity
   KEYWORD_WEIGHT = 0.4   # Weight for keyword matching
   ```

**Expected Impact**:
- Better results for exact keyword matches (technical terms, acronyms)
- Still leverages semantic understanding for related concepts
- RRF naturally handles documents matching both criteria

### 2. Test Hybrid Search 🔜 NOT STARTED

**Test Queries**:
1. **Keyword-heavy**: "transformer architecture", "BERT model", "GPT-3"
2. **Semantic-heavy**: "how do neural networks learn?", "explain backpropagation"
3. **Mixed**: "transformer attention mechanism", "LSTM vs GRU comparison"

**Comparison Metrics**:
- Vector-only vs Hybrid search results
- FTS ranking scores
- Combined RRF scores
- Relevance of top-k results

**Success Criteria**:
- Hybrid search finds exact keyword matches in top results
- Semantic understanding preserved for concept-based queries
- No significant performance degradation (<100ms latency increase)

---

## 📈 Performance Considerations

### FTS Index (GIN)

**Benefits**:
- Fast keyword lookups (~1-5ms for typical queries)
- Supports complex queries (AND, OR, phrase matching)
- Normalized/stemmed tokens (English dictionary)

**Trade-offs**:
- Index size: ~30% of content size
- Slight INSERT/UPDATE overhead (triggers update tsvector)

### Hybrid Search Query

**Expected Performance**:
- Vector search: ~10-50ms (with ivfflat index)
- FTS search: ~1-5ms (with GIN index)
- RRF merge: ~1ms (in-memory operation)
- **Total**: ~12-56ms (acceptable for search API)

**Optimization Opportunities**:
- Limit session_docs CTE to recent documents
- Add `access_count` boost to RRF score
- Cache frequent query embeddings

---

## 🧪 Testing

### Unit Tests Needed

```python
# tests/unit/test_vector_store_repository.py

async def test_hybrid_search_basic():
    """Test basic hybrid search functionality."""
    repo = VectorStoreRepository(db=session)
    results = await repo.hybrid_search(
        session_id=uuid.uuid4(),
        query_text="transformer architecture",
        query_vector=[...],  # 384D vector
        top_k=5
    )
    assert len(results) <= 5
    assert all(r.similarity_score > 0 for r in results)

async def test_hybrid_search_weights():
    """Test hybrid search with custom weights."""
    results = await repo.hybrid_search(
        session_id=session_id,
        query_text="BERT",
        query_vector=vector,
        semantic_weight=0.3,
        keyword_weight=0.7  # Favor keywords
    )
    # Should prioritize exact "BERT" matches

async def test_hybrid_search_fallback():
    """Test fallback to vector search when no text query."""
    results = await repo.hybrid_search(
        session_id=session_id,
        query_text="",  # Empty text
        query_vector=vector
    )
    # Should still return results via vector search
```

### Integration Tests Needed

```python
# tests/integration/test_hybrid_search_integration.py

async def test_search_agent_hybrid_retrieval():
    """Test SearchAgent using hybrid search."""
    agent = SearchAgent(...)
    result = await agent.search(query="transformer architecture")
    
    # Verify both semantic and keyword results
    assert "transformer" in result["answer"].lower()
    assert any("transformer" in s["content"].lower() for s in result["sources"])
```

---

## 🎯 Next Steps

1. **Immediate** (30 minutes):
   - Update `SearchAgent._retrieve_from_vector_store()` to use `hybrid_search()`
   - Add weight configuration
   - Test with sample query

2. **Testing** (30 minutes):
   - Run test queries comparing vector vs hybrid
   - Measure latency
   - Verify ranking quality

3. **Polish** (30 minutes):
   - Add logging for hybrid search scores
   - Document configuration options
   - Update API documentation

**Estimated Time to Complete Day 3**: 1.5 hours remaining

---

## 🔍 Key Insights

### Why Hybrid Search?

1. **Vector Search Strengths**:
   - Captures semantic meaning
   - Handles synonyms, paraphrasing
   - Works across languages (with multilingual models)

2. **FTS Strengths**:
   - Exact keyword matching
   - Fast for specific terms (acronyms, proper nouns)
   - Boolean operators (AND, OR, NOT)

3. **RRF Benefits**:
   - No need to normalize scores across different ranges
   - Rank-based fusion is more robust than score-based
   - Naturally handles missing results (rank = 1000)

### Architecture Decision: Why PostgreSQL for Everything?

✅ **Advantages**:
- **Single source of truth**: No sync issues between vector store and metadata
- **ACID transactions**: Embeddings + metadata updated atomically
- **SQL power**: Complex joins, aggregations on metadata
- **Hybrid queries**: Combine vector + FTS in one query
- **Operational simplicity**: One database to backup, monitor, scale

❌ **Trade-offs**:
- Not as fast as specialized vector DBs (Pinecone, Weaviate)
- Index tuning required for optimal performance
- Memory usage for large vector sets

**Verdict**: For research service with <1M documents, PostgreSQL + pgvector + FTS is the sweet spot for simplicity and power.

---

## 📚 References

- **PostgreSQL FTS**: https://www.postgresql.org/docs/current/textsearch.html
- **pgvector**: https://github.com/pgvector/pgvector
- **Reciprocal Rank Fusion**: https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf
- **Hybrid Search Patterns**: https://www.pinecone.io/learn/hybrid-search-intro/

---

**Status**: Ready to proceed with SearchAgent integration! 🚀
