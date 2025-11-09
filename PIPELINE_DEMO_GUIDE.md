# Pipeline Demo Tab - Comprehensive Guide

## Overview

The **Pipeline Demo** tab in the Streamlit UI provides an interactive visualization of the complete search pipeline, showing how user queries are transformed into final answers with citations through 6 distinct processing stages.

## Access

In the Streamlit application, navigate to the **📊 Pipeline Demo** tab.

---

## Features

### 1. Example Selection

Two comprehensive examples demonstrate different pipeline scenarios:

#### Example 1: Multi-Query Decomposition
- **Input Query:** "latest cloud technologies news from aws, azure, and gcp"
- **Query Type:** Multi-faceted (3 separate vendors)
- **Pipeline Strategy:** Multi-query decomposition into 3 focused searches
- **Result Count:** 9 raw results → aggregated to ≤10 final results

#### Example 2: Single Query Search
- **Input Query:** "python programming tutorial for beginners"
- **Query Type:** Simple, single-focused topic
- **Pipeline Strategy:** Direct single query search (no decomposition)
- **Result Count:** 3-5 quality results from diverse sources

---

## Six-Stage Pipeline Visualization

### **Stage 1: Input Query**

**What it shows:** The exact user query entering the system

**Example for Multi-Query:**
```
latest cloud technologies news from aws, azure, and gcp
```

**Example for Single-Query:**
```
python programming tutorial for beginners
```

**Purpose:** Demonstrates the starting point before any processing

---

### **Stage 2: Query Decomposition**

**What it shows:** The LLM's analysis result for decomposition strategy

**Key Information:**
- `need_search` (bool): Whether web search is required
- `search_strategy` ("single" or "multi"): Type of search approach
- `optimized_queries` (List[str]): The final queries to execute

**Multi-Query Output Example:**
```
Need Search: True
Search Strategy: multi

Optimized Queries:
1. AWS cloud latest news and updates
2. Azure cloud latest news and updates
3. Google Cloud Platform latest news
```

**Single-Query Output Example:**
```
Need Search: True
Search Strategy: single

Optimized Queries:
1. Python programming tutorial for beginners
```

**How It Works:**
- LLM analyzes the original query for complexity
- Detects multi-faceted topics, multiple entities, complex requirements
- For simple queries → returns as-is (single strategy)
- For complex queries → decomposes into focused sub-queries (multi strategy)

---

### **Stage 3: Content Crawling Example**

**What it shows:** How URLs are fetched and converted to markdown for processing

**Input:**
```
URL: https://aws.amazon.com/blogs/aws/
```

**Output: Extracted Markdown Content**
```markdown
# AWS News and Announcements

## Latest Updates
- **New EC2 Instance Types**: Latest generation instances with better performance
- **AWS Lambda Improvements**: Enhanced cold start performance
- **RDS Auto Scaling**: Automatic scaling for databases

## Technical Details
AWS provides cloud computing services including compute, storage,
databases, networking, and more.
```

**Processing Method:**
- Uses **crawl4ai** for JavaScript-heavy pages (renders with browser)
- Falls back to **BeautifulSoup** for static HTML
- Converts HTML to clean, LLM-ready markdown
- Removes scripts, styles, and unnecessary HTML tags

---

### **Stage 4: Search Results**

**What it shows:** Raw search results from SearxNG/SerperDev for each optimized query

**Multi-Query Example Structure:**

```
Query 1: AWS cloud latest news and updates
  ├─ Result 1
  │  ├─ Title: AWS announces new EC2 instances
  │  ├─ URL: https://aws.amazon.com/blogs/aws/ec2-new
  │  └─ Snippet: AWS has announced new EC2 instance types
  │             with 40% better performance...
  │
  ├─ Result 2
  │  ├─ Title: AWS Lambda Cold Start Reduction
  │  ├─ URL: https://aws.amazon.com/blogs/aws/lambda-cold-start
  │  └─ Snippet: The latest Lambda improvements reduce cold
  │             start latency by 50%...
  │
  └─ Result 3
     ├─ Title: RDS Multi-AZ Improvements
     ├─ URL: https://aws.amazon.com/blogs/aws/rds-improvements
     └─ Snippet: RDS now supports automatic failover with
                reduced recovery time...

Query 2: Azure cloud latest news and updates
  ├─ Result 1
  │  ├─ Title: Azure Compute Updates 2024
  │  ├─ URL: https://azure.microsoft.com/en-us/blog/compute-updates/
  │  └─ Snippet: Microsoft Azure introduces new compute options...
  │
  └─ Result 2
     ├─ Title: Azure SQL Database Enhancements
     ├─ URL: https://azure.microsoft.com/en-us/blog/sql-enhancements/
     └─ Snippet: Azure SQL now includes new performance optimization...

Query 3: Google Cloud Platform latest news
  ├─ Result 1
  │  ├─ Title: GCP Compute Engine Updates
  │  ├─ URL: https://cloud.google.com/blog/products/compute
  │  └─ Snippet: Google Cloud announces new machine types...
  │
  └─ Result 2
     ├─ Title: BigQuery Performance Improvements
     ├─ URL: https://cloud.google.com/blog/products/bigquery
     └─ Snippet: BigQuery now runs 3x faster with optimized...
```

**Key Points:**
- Each query executes independently in parallel
- SearxNG is primary (local self-hosted search)
- SerperDev is fallback (Google-like API)
- Results include title, URL, and content snippet

---

### **Stage 5: Result Aggregation**

**What it shows:** The step-by-step aggregation process that transforms raw results into final ranked list

**Aggregation Pipeline (6 Steps):**

| Step | Operation | Input | Output |
|------|-----------|-------|--------|
| 1 | Limit Per Query | Results per query (5-20) | Capped at 5/query |
| 2 | Flatten | Multiple lists (one per query) | Single list |
| 3 | Deduplicate | List with possible duplicates | Unique URLs only |
| 4 | Diversity Filter | Many results from same domain | Max 3 per domain |
| 5 | Sort by Quality | Unsorted results | Ranked by content length |
| 6 | Limit Total | ≤20 results | Final ≤10 results |

**Multi-Query Aggregation Example:**

```
Step 1: Limit per query → 5 results/query
  - Query 1: 20 results → 5 selected
  - Query 2: 20 results → 5 selected
  - Query 3: 20 results → 5 selected
  Total: 15 results

Step 2: Flatten → Single list of 15 results

Step 3: Deduplicate → Remove duplicate URLs
  - If same URL appears twice, keep version with longer content
  - Result: 15 → 14 unique URLs

Step 4: Diversity Filter → Max 3 per domain
  - AWS domain: keep best 3
  - Azure domain: keep best 2
  - GCP domain: keep best 2
  - Other domains: keep others
  - Result: 14 → 10 results

Step 5: Sort by Quality → Order by content length
  - Longer content = higher rank (quality proxy)

Step 6: Limit Total → Cap to 10 results
  - Result: Already 10, no change
  - Final: 10 results ready for synthesis
```

**Final Aggregated Results Display:**

```
Rank 1 (From AWS Query)
  Title: AWS announces new EC2 instances
  URL: https://aws.amazon.com/blogs/aws/ec2-new
  Content: AWS has announced new EC2 instance types with 40%...
  Source Query: AWS cloud latest news and updates

Rank 2 (From Azure Query)
  Title: Azure Compute Updates 2024
  URL: https://azure.microsoft.com/en-us/blog/compute-updates/
  Content: Microsoft Azure introduces new compute options...
  Source Query: Azure cloud latest news and updates

Rank 3 (From GCP Query)
  Title: GCP Compute Engine Updates
  URL: https://cloud.google.com/blog/products/compute
  Content: Google Cloud announces new machine types...
  Source Query: Google Cloud Platform latest news
```

---

### **Stage 6: Final Answer Synthesis**

**What it shows:** The LLM-generated answer with inline citations linking to sources

**Generated Answer Example:**

```
The major cloud providers have released significant updates in 2024:

AWS [1] announces new EC2 instance types with 40% better performance,
enhanced Lambda cold start performance, and RDS multi-AZ improvements
with reduced recovery times.

Azure [2] introduces new compute options including VM SKUs and enhanced
SQL database performance optimization features.

Google Cloud Platform [3] announces new machine types, pricing updates,
and BigQuery performance improvements running 3x faster with optimized
query execution.

All three providers continue to compete on performance, features, and pricing.
```

**Citation References:**

```
[1] AWS announces new EC2 instances
    URL: https://aws.amazon.com/blogs/aws/ec2-new

[2] Azure Compute Updates 2024
    URL: https://azure.microsoft.com/en-us/blog/compute-updates/

[3] GCP Compute Engine Updates
    URL: https://cloud.google.com/blog/products/compute
```

**How Synthesis Works:**
- Takes the top 10 aggregated results as context
- Original query and results fed to LLM
- LLM generates natural language answer
- Citations [1], [2], [3] inserted inline
- Citation numbers correspond to source list
- Users can click/verify sources

---

## Complete Data Flow Diagram

```
┌──────────────────────────────────────┐
│  User Input Query                    │
│  (Complex multi-faceted question)    │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ STAGE 1: Input Query Display         │
│ Shows raw user input                 │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ STAGE 2: Query Decomposition (LLM)   │
│ ├─ Analyze query complexity          │
│ ├─ Decide: single vs multi strategy  │
│ └─ Generate 1-5 focused queries      │
└──────────────┬───────────────────────┘
               │
        ┌──────┴──────┐
        │             │
    (single)      (multi: 3 queries)
        │             │
        └──────┬──────┘
               │
               ▼
┌──────────────────────────────────────┐
│ STAGE 3: Content Crawling (Example)  │
│ crawl4ai/BeautifulSoup → Markdown    │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ STAGE 4: Parallel Search              │
│ Each query → SearxNG/SerperDev        │
│ Results: [20, 20, 20] = 60 total      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ STAGE 5: Result Aggregation          │
│ 1. Limit per query (5 each = 15)    │
│ 2. Flatten to single list            │
│ 3. Deduplicate by URL                │
│ 4. Diversity filter (max 3/domain)   │
│ 5. Sort by quality                   │
│ 6. Limit total (10 results)          │
│ Output: [≤10 best results]           │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ STAGE 6: Answer Synthesis (LLM)      │
│ ├─ Generate markdown answer          │
│ ├─ Add [1][2][3] citations           │
│ ├─ Link to sources                   │
│ └─ Include chat history context      │
└──────────────┬───────────────────────┘
               │
               ▼
┌──────────────────────────────────────┐
│ Final: Answer with Citations         │
│ + Source References                  │
│ + Transparency for verification      │
└──────────────────────────────────────┘
```

---

## Key Concepts

### Query Decomposition Strategies

**Single Query Strategy:**
- Used for: Simple, focused questions
- Example: "What is Python?"
- Output: One optimized query
- Search: Direct search on SearxNG

**Multi-Query Strategy:**
- Used for: Complex, multi-faceted questions
- Example: "Compare AWS, Azure, and GCP"
- Output: 3 separate focused queries
- Search: Parallel execution of all queries
- Benefit: More balanced, comprehensive results

### Crawling Methods

**crawl4ai (Primary):**
- Uses headless browser (Playwright)
- Renders JavaScript
- Handles dynamic content
- Slower but more complete

**BeautifulSoup (Fallback):**
- Static HTML parsing
- No JavaScript execution
- Faster
- Used when crawl4ai times out

### Aggregation Intelligence

**Deduplication:**
- Same URL appearing in multiple queries kept only once
- Version with longer/better content selected

**Diversity Filter:**
- Prevents domain monopolization
- Max 3 results per domain (configurable)
- Example: max 3 from aws.amazon.com
- Ensures variety of perspectives

**Quality Scoring:**
- Content length as proxy for quality
- Longer content = higher rank
- Ensures comprehensive information

**Per-Query Limiting:**
- Balanced coverage across queries
- Single query: all results used
- Multi-query: 5 results per query
- Prevents any single query dominating

---

## Real-World Examples

### Use Case 1: Technology Comparison
**User Query:** "What are the differences between React, Vue, and Angular?"

**Pipeline Execution:**
1. **Decomposition:** Detects 3 frameworks → creates 3 queries
2. **Search:** Parallel search for each framework
3. **Results:** 15 raw results (5 per framework)
4. **Aggregation:** Deduplicate + diversity → 10 final results
5. **Synthesis:** Balanced comparison with all 3 represented

### Use Case 2: Tutorial Search
**User Query:** "How to learn Python for data science?"

**Pipeline Execution:**
1. **Decomposition:** Single focused query (Python + data science)
2. **Search:** Direct search for tutorials
3. **Results:** 10-15 results from search
4. **Aggregation:** Filter to top 10 diverse sources
5. **Synthesis:** Curated list of best tutorials with recommendations

### Use Case 3: News Aggregation
**User Query:** "Latest AI developments and announcements"

**Pipeline Execution:**
1. **Decomposition:** Could split into "AI research" + "AI news" or remain single
2. **Search:** Recent articles and news items
3. **Results:** Latest publications from multiple sources
4. **Aggregation:** Newest items, diverse sources
5. **Synthesis:** Summary of recent AI developments

---

## Using the Pipeline Demo

### Step 1: Open Application
```bash
docker-compose up ui
# Or locally
streamlit run services/searchsvc/tools/streamlit_app.py
```

### Step 2: Navigate to Pipeline Demo
Click the **📊 Pipeline Demo** tab in the navigation

### Step 3: Select Example
Choose from dropdown:
- "Multi-Query: Cloud Providers"
- "Single Query: Python Tutorial"

### Step 4: Explore Each Stage
Click through the 6 tabs to understand:
- Original question (Stage 1)
- How query is decomposed (Stage 2)
- URL extraction and markdown conversion (Stage 3)
- Raw search results (Stage 4)
- Aggregation steps and process (Stage 5)
- Final answer with citations (Stage 6)

### Step 5: Understand Flow
Visual progression shows exactly how input transforms to output

---

## Customization

### Adding New Examples

Edit `get_pipeline_examples()` in `services/searchsvc/tools/streamlit_app.py`:

```python
"Custom Example Name": {
    "input_query": "your question here",
    "decomposition": {
        "need_search": True,
        "strategy": "single" or "multi",
        "optimized_queries": ["query1", "query2", ...]
    },
    "crawl_example": {
        "url": "https://example.com",
        "markdown_content": "# Markdown content here..."
    },
    "search_results": {
        "query1": [
            {
                "title": "Result Title",
                "url": "https://...",
                "pageContent": "Snippet text..."
            },
            ...
        ],
        ...
    },
    "aggregation": {
        "step1_limit_per_query": "description",
        "step2_flatten": "description",
        "step3_deduplicate": "description",
        "step4_diversity_filter": "description",
        "step5_sort": "description",
        "step6_limit_total": "description",
        "final_results": [
            {
                "rank": 1,
                "title": "Result Title",
                "url": "https://...",
                "pageContent": "Content...",
                "source": "query name"
            },
            ...
        ]
    },
    "synthesis": {
        "answer": "Generated answer with [1][2] citations...",
        "sources": [
            {
                "num": 1,
                "title": "Source Title",
                "url": "https://..."
            },
            ...
        ]
    }
}
```

---

## Benefits

- **Transparency:** See exactly how questions become answers
- **Educational:** Understand system architecture and algorithm flow
- **Debugging:** Identify where issues occur in pipeline
- **Documentation:** Visual reference for system behavior
- **Verification:** Check which sources contributed to answer
- **Optimization:** Understand aggregation and ranking logic
- **Testing:** Compare expected vs actual outputs

