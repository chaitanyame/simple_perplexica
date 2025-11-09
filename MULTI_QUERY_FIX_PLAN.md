# Multi-Query Search Implementation Plan

## Problem Summary

The **Pipeline Demo** shows expected behavior with balanced multi-query results (AWS, Azure, GCP), but the actual **Search Service** only returns AWS results. This is because the search endpoint only executes the first optimized query and ignores the rest.

---

## Root Cause Analysis

### The Issue

**File:** `services/searchsvc/app/routers/search.py`
**Lines:** 238-239

```python
# For now, use first query for backward compatibility; multi-query support comes later
effective_query = (decision.optimized_queries[0] if decision.optimized_queries else req.query) if decision.need_search else None
sources = []
fetched = await get_sources(effective_query, req.focusMode)
```

### What's Happening

```
User Query: "latest cloud technologies news from aws, azure, and gcp"
    ↓
[Query Decomposition - WORKING ✅]
    ↓
Decomposed Queries:
  1. AWS cloud latest news and updates        ← USED
  2. Azure cloud latest news and updates      ← IGNORED
  3. Google Cloud Platform latest news        ← IGNORED
    ↓
[Search Execution - BROKEN ❌]
Only uses optimized_queries[0]
    ↓
Result: AWS-only articles (~10 AWS, 0 Azure, 0 GCP)
```

### Why It Happens

The comment explicitly states: "For now, use first query for backward compatibility; multi-query support comes later"

This was intentional as a placeholder, but now needs to be implemented for proper multi-query functionality.

---

## Solution Overview

Implement **parallel multi-query search** with result aggregation:

```
User Query: "aws, azure, gcp news"
    ↓
[Decomposition - Already Working]
    ↓
Decomposed Queries:
  1. AWS cloud latest news        ← Execute in parallel
  2. Azure cloud latest news      ← Execute in parallel
  3. GCP cloud latest news        ← Execute in parallel
    ↓
[Parallel Search - NEW]
  Query 1 → 5-10 AWS results
  Query 2 → 5-10 Azure results
  Query 3 → 5-10 GCP results
    ↓
[Result Aggregation - NEW]
  Deduplicate URLs
  Apply diversity filter (max 3 per domain)
  Sort by quality
  Limit to ~10 final results
    ↓
Final Result: Balanced (3-4 AWS, 3-4 Azure, 3-4 GCP)
```

---

## Implementation Steps

### Step 1: Update search.py - Implement Multi-Query Search

**File:** `services/searchsvc/app/routers/search.py`

**Current Code (lines 237-264):**
```python
# Force search for all queries: prefer first optimized query if provided
# For now, use first query for backward compatibility; multi-query support comes later
effective_query = (decision.optimized_queries[0] if decision.optimized_queries else req.query) if decision.need_search else None
sources = []

# ... link processing code ...

fetched = await get_sources(effective_query, req.focusMode)
sources = link_sources + (fetched or [])
```

**Replace With:**
```python
sources = []

# Process user-provided or LLM-suggested links by fetching actual content
link_sources = []
if decision.links:
    try:
        link_docs = await fetch_and_process_urls(decision.links)
        link_sources = [
            {
                "title": doc.get("title", ""),
                "url": doc.get("url", ""),
                "pageContent": doc.get("pageContent", ""),
            }
            for doc in link_docs
        ]
    except Exception as e:
        link_sources = [
            {"title": url, "url": url, "pageContent": f"Failed to fetch: {str(e)}"}
            for url in decision.links
        ]

# Multi-query search implementation
if decision.need_search:
    search_strategy = getattr(decision, 'search_strategy', 'single')

    if search_strategy == "multi" and len(decision.optimized_queries) > 1:
        # MULTI-QUERY: Execute all queries in parallel and aggregate
        all_results = []

        logger.info(
            "Multi-query search initiated",
            extra={
                "query_count": len(decision.optimized_queries),
                "queries": decision.optimized_queries,
            },
        )

        # Execute each query and collect results
        for idx, query in enumerate(decision.optimized_queries, 1):
            try:
                query_results = await get_sources(query, req.focusMode)

                # Tag results with source query for tracking
                for result in (query_results or []):
                    result['_source_query'] = query
                    result['_query_index'] = idx

                all_results.extend(query_results or [])

                logger.info(
                    f"Query {idx} search completed",
                    extra={
                        "query": query,
                        "result_count": len(query_results or []),
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Query {idx} failed",
                    extra={"query": query, "error": str(e)},
                )

        # AGGREGATION: Process multi-query results
        fetched = _aggregate_multi_query_results(all_results)

        logger.info(
            "Multi-query aggregation completed",
            extra={
                "raw_count": len(all_results),
                "final_count": len(fetched),
            },
        )
    else:
        # SINGLE-QUERY: Use existing behavior
        effective_query = (
            decision.optimized_queries[0]
            if decision.optimized_queries
            else req.query
        )

        logger.info(
            "Single-query search",
            extra={"query": effective_query},
        )

        fetched = await get_sources(effective_query, req.focusMode)
else:
    fetched = []

sources = link_sources + (fetched or [])
```

### Step 2: Add Result Aggregation Function

**Add to search.py (before the search endpoint function):**

```python
def _aggregate_multi_query_results(results: List[Dict]) -> List[Dict]:
    """
    Aggregate multi-query search results:
    1. Deduplicate by URL (keep best version)
    2. Apply diversity filter (max 3 per domain)
    3. Sort by content quality
    4. Limit to ~10 results
    """
    if not results:
        return []

    # Step 1: Deduplicate by URL
    url_to_best = {}
    for result in results:
        url = result.get("url", "")
        if not url:
            continue

        # Keep version with longer content (assumed higher quality)
        if url not in url_to_best:
            url_to_best[url] = result
        else:
            existing = url_to_best[url]
            existing_content_len = len(existing.get("pageContent", ""))
            new_content_len = len(result.get("pageContent", ""))

            if new_content_len > existing_content_len:
                url_to_best[url] = result

    deduplicated = list(url_to_best.values())

    logger.info(
        "Deduplication completed",
        extra={
            "original_count": len(results),
            "deduplicated_count": len(deduplicated),
        },
    )

    # Step 2: Diversity filter (max 3 per domain)
    from urllib.parse import urlparse

    domain_counts = {}
    filtered = []

    for result in deduplicated:
        url = result.get("url", "")
        try:
            domain = urlparse(url).netloc
        except:
            domain = "unknown"

        domain_count = domain_counts.get(domain, 0)

        if domain_count < 3:  # Max 3 results per domain
            filtered.append(result)
            domain_counts[domain] = domain_count + 1

    logger.info(
        "Diversity filter completed",
        extra={
            "input_count": len(deduplicated),
            "filtered_count": len(filtered),
            "unique_domains": len(domain_counts),
        },
    )

    # Step 3: Sort by content quality (length)
    filtered.sort(
        key=lambda x: len(x.get("pageContent", "")),
        reverse=True
    )

    # Step 4: Limit to ~10 results
    limited = filtered[:10]

    logger.info(
        "Final limiting completed",
        extra={"final_count": len(limited)},
    )

    return limited
```

### Step 3: Update Logging

Make sure decomposition strategy is logged so you can debug:

**In the search endpoint (lines 213-221), update to:**

```python
logger.debug(
    "Decision completed",
    extra={
        "need_search": decision.need_search,
        "search_strategy": getattr(decision, 'search_strategy', 'single'),  # ADD THIS
        "optimized_queries": decision.optimized_queries,
        "optimized_queries_count": len(decision.optimized_queries),  # ADD THIS
        "links_count": len(decision.links) if decision.links else 0,
    },
)
```

---

## Testing the Fix

### Test Query 1: Multi-Query (Should Return Balanced Results)

```
Query: "latest cloud technologies news from aws, azure, and gcp"

Expected Behavior:
- Decomposed into 3 queries ✅
- All 3 queries executed ✅
- Results show mix of AWS, Azure, GCP ✅
- ~10 final results with balanced distribution ✅

Example Results:
1. AWS announces new EC2 instances
2. Azure Compute Updates 2024
3. GCP Compute Engine Updates
4. AWS Lambda improvements
5. Azure SQL enhancements
... (balanced)
```

### Test Query 2: Single Query (Should Work As Before)

```
Query: "python programming tutorial for beginners"

Expected Behavior:
- Detected as single query ✅
- Single query executed ✅
- Results from diverse sources ✅
- ~5-10 quality results ✅
```

### Test Query 3: Simple Query (Should Work As Before)

```
Query: "what is python"

Expected Behavior:
- Simple query recognized ✅
- Single query executed ✅
- Results returned normally ✅
```

---

## Verification Checklist

After implementing the fix, verify:

- [ ] Query decomposition detects multi-query correctly
- [ ] All decomposed queries are logged (DEBUG logs)
- [ ] All queries are executed (check INFO logs)
- [ ] Results are aggregated properly
- [ ] Final results are balanced across queries
- [ ] Deduplication removes duplicate URLs
- [ ] Diversity filter applied (max 3 per domain)
- [ ] Final result count is ~10
- [ ] Single-query behavior unchanged
- [ ] Test passes with multi-query decomposition

---

## Debug Commands

### Check Logs

```bash
# View decomposition decision
grep "Decision completed" logs/api.log

# View multi-query execution
grep "Multi-query" logs/api.log

# View aggregation results
grep "Aggregation completed" logs/api.log

# View individual query execution
grep "Query.*search completed" logs/api.log
```

### Use Debug View Tab

In Streamlit UI:
1. Open **🐛 Debug View** tab
2. Shows expected vs actual behavior
3. Lists implementation checklist
4. Provides test query

---

## Expected Results After Fix

### Before Fix (Current) ❌
```
Query: "aws, azure, gcp news"
Results: AWS-only (~10 AWS, 0 Azure, 0 GCP)
Sources: Only AWS domains
```

### After Fix ✅
```
Query: "aws, azure, gcp news"
Results: Balanced (3-4 AWS, 3-4 Azure, 3-4 GCP)
Sources: Mix of aws.amazon.com, azure.microsoft.com, cloud.google.com
```

---

## Key Files to Modify

1. **services/searchsvc/app/routers/search.py**
   - Lines 237-264: Replace single-query logic with multi-query logic
   - Add `_aggregate_multi_query_results()` function
   - Update logging

---

## Summary

**Root Cause:** Search endpoint only uses first decomposed query (line 238-239)

**Solution:**
1. Detect multi-query strategy from decomposition
2. Execute all queries in parallel
3. Aggregate results (deduplicate, diversity filter, limit)
4. Return balanced results

**Impact:**
- Pipeline Demo behavior now matches actual search results
- Multi-query decomposition works end-to-end
- User gets balanced results across multiple topics

**Estimated Implementation Time:** 30-45 minutes

---

## Questions?

Refer to:
- **PIPELINE_DEMO_GUIDE.md** - Shows expected behavior
- **🐛 Debug View** tab - Visual comparison and checklist
- **Test query examples** above - For verification

Good luck with the implementation!
