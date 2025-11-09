# Streamlit Testing UI - Quick Reference

## 🎯 Purpose

Comprehensive testing and debugging interface for the research service with:
- **Test Automation**: Run pytest suites from UI
- **Interactive Testing**: Manual search/research with full control
- **Performance Monitoring**: Real-time metrics and cost tracking
- **Debugging Tools**: Langfuse integration for trace analysis

---

## 📋 6-Page Application Structure

### 1. **Home & System Status**
- Service health checks (API, PostgreSQL, Redis, Langfuse, OpenRouter)
- Quick stats (sessions today, avg times, success rate, total cost)
- Recent sessions table with Langfuse trace links

### 2. **Test Runner** 🧪
- **Select test suites**: Unit, Integration, E2E with checkboxes
- **Configure execution**: Verbosity, stop-on-fail, coverage
- **Real-time output**: Live pytest console output streaming
- **Results summary**: Pass/fail counts, coverage %, failed tests list

### 3. **Search Mode Tester** 🔍
- **Query input**: Text box + example queries
- **Parameter controls**: Max queries, max sources, timeout, models
- **Progress tracking**: Step-by-step with timing (8 steps)
- **Results display**: Answer, 20 sources with relevance, metrics, Langfuse link

### 4. **Research Mode Tester** 🔬
- **Research question**: Text box + example topics
- **Advanced params**: Iterations, sources, crawl depth, doc types
- **Multi-iteration progress**: Real-time tracking across 3 iterations
- **Comprehensive report**: Markdown report with 80 sources, section-by-section citations
- **Detailed metrics**: Execution breakdown, LLM usage, RAG stats, gap analysis

### 5. **Performance Dashboard** 📊
- **Overview stats**: 6 key metrics (queries, times, cost, success rate)
- **Charts**: Execution time, token usage, cost analysis
- **Model comparison**: Performance by LLM model
- **Session history**: Filterable table with export

### 6. **Configuration & Settings** ⚙️
- **API config**: URL, connection test, rate limits
- **Default parameters**: Search and research mode defaults
- **LLM model selection**: Primary and planning models

---

## 🔑 Key Features

### Test Automation
```
✅ Run individual test files or full suites
✅ Real-time console output streaming  
✅ Coverage reports with percentage
✅ Failed test highlighting
✅ Configurable verbosity and stopping behavior
```

### Interactive Testing
```
✅ Search: 3-4 sub-queries, 20 sources, <60s
✅ Research: 2-3 iterations, 80 sources, <5min
✅ Full parameter control (timeouts, limits, models)
✅ Real-time progress with step timing
✅ Step-by-step status indicators
```

### Results Visualization
```
✅ Formatted markdown answers
✅ Source citations with relevance scores
✅ Token usage and cost calculation
✅ Execution time breakdown by phase
✅ Direct Langfuse trace links
✅ Export to PDF/JSON/CSV
```

### Performance Monitoring
```
✅ Real-time metrics dashboard
✅ Time-series charts (execution, tokens, cost)
✅ Model performance comparison
✅ Success rate tracking
✅ Session history with filtering
```

---

## 🚀 Usage Workflows

### Workflow 1: Run Full Test Suite
1. Go to **Test Runner** page
2. Select "All Tests"
3. Enable coverage
4. Click "Run Selected Tests"
5. Watch real-time output
6. Review results summary

### Workflow 2: Test Search Query
1. Go to **Search Mode Tester** page
2. Enter query (or use example)
3. Adjust parameters (optional)
4. Click "Run Search"
5. Monitor progress (8 steps)
6. Review answer and sources
7. Click Langfuse link to debug

### Workflow 3: Deep Research
1. Go to **Research Mode Tester** page
2. Enter research question
3. Configure iterations (default: 3)
4. Set max sources (default: 80)
5. Click "Start Research"
6. Watch multi-iteration progress
7. Review comprehensive report
8. Export as PDF

### Workflow 4: Performance Analysis
1. Go to **Performance Dashboard**
2. Select time range (last 24h)
3. Review overview metrics
4. Analyze charts for trends
5. Compare model performance
6. Export session history as CSV

---

## 🎨 UI Components

### Progress Indicators
```python
✅ Completed step (with timing)
🔄 In-progress step (with spinner)
⏸️ Pending step
❌ Failed step (with error)
```

### Status Badges
```python
✅ Success (green)
⚠️ Warning (yellow)
❌ Failed (red)
⏭️ Skipped (gray)
🔄 Processing (blue)
```

### Interactive Elements
```python
[Button]          # Primary action
[Dropdown ▼]      # Selection menu
[Show more ▼]     # Expandable section
[📄 Icon Button]  # Icon with action
```

---

## 📊 Metrics Tracked

### Execution Metrics
- Total execution time
- Time per pipeline step
- Iteration breakdown (research mode)
- Timeout occurrences

### LLM Metrics (via Langfuse)
- Total LLM calls
- Input/output tokens
- Cost per call and total
- Model distribution
- Average latency

### RAG Metrics
- Documents stored
- Embeddings generated
- Vector searches performed
- Average relevance score
- Deduplication rate

### Quality Metrics
- Success/failure rate
- Gap analysis results
- Claim verification stats
- Source diversity

---

## 🔗 Langfuse Integration

Every API call includes Langfuse trace links:

```
🔗 Langfuse Trace:
[View Full Trace] → Full trace tree
[View Analytics] → Aggregated analytics
```

Traces include:
- All LLM calls with prompts/responses
- Token counts and costs
- Latency measurements
- Model used
- Error details (if failed)

---

## 💾 Export Options

### Search Results
- **JSON**: Full structured data
- **Markdown**: Answer + sources
- **PDF**: Formatted report

### Research Reports
- **PDF**: Publication-ready report with citations
- **Markdown**: Plain text with references
- **JSON**: Structured data with metadata

### Dashboard Data
- **CSV**: Session history table
- **JSON**: Metrics time-series
- **Charts**: PNG/SVG exports

---

## ⚙️ Configuration

### Environment Variables
```bash
RESEARCH_API_URL=http://localhost:8001
STREAMLIT_SERVER_PORT=8501
LANGFUSE_PUBLIC_KEY=your_key
```

### Default Parameters (Editable in UI)
```python
# Search Mode
MAX_SUB_QUERIES = 4
MAX_SOURCES = 20
SEARCH_TIMEOUT = 60

# Research Mode
MAX_ITERATIONS = 3
MAX_SOURCES = 80
RESEARCH_TIMEOUT = 300
```

---

## 🐛 Debugging Features

### Test Failures
- Detailed error messages
- Failed test list with line numbers
- Link to test file

### API Errors
- HTTP status codes
- Error messages from API
- Stack traces (if available)
- Retry suggestions

### Langfuse Traces
- Direct link to failing LLM call
- Prompt inspection
- Response analysis
- Token usage details

---

## 📦 Docker Deployment

### Build
```bash
docker build -f Dockerfile.streamlit -t research-streamlit .
```

### Run Standalone
```bash
docker run -p 8501:8501 \
  -e RESEARCH_API_URL=http://localhost:8001 \
  research-streamlit
```

### Run with Docker Compose
```bash
docker-compose up streamlit
# Access at http://localhost:8501
```

---

## 🎯 Implementation Timeline

### Week 12: Core Features
- Day 1-2: Test runner + API client
- Day 3-4: Search/research testers
- Day 5: Results visualization

### Week 13: Polish & Testing
- Day 1-2: Performance dashboard
- Day 3: Configuration & settings
- Day 4-5: Testing, bug fixes, documentation

---

## ✅ Acceptance Criteria

- [ ] Test runner executes all pytest suites
- [ ] Search tester completes <60s with results
- [ ] Research tester completes <5min with 80 sources
- [ ] Real-time progress updates work correctly
- [ ] Langfuse links open valid traces
- [ ] Dashboard shows accurate metrics
- [ ] Export functions work for all formats
- [ ] No errors in console for normal operations
- [ ] Responsive design works on 1920x1080 and 1366x768

---

## 🔮 Future Enhancements

1. **A/B Testing**: Compare different models side-by-side
2. **Batch Testing**: Run multiple queries in sequence
3. **Regression Detection**: Alert on performance degradation
4. **Custom Test Cases**: Build and save test scenarios
5. **CI/CD Integration**: Trigger tests from GitHub Actions
6. **Session Replay**: Replay past sessions for debugging
7. **Multi-User**: Support multiple concurrent users
8. **Annotations**: Add notes to test results

---

## 📚 Related Documentation

- `PROCESS_FLOWS.md` - Search and research mode details
- `ROADMAP.md` - Full development plan
- `GETTING_STARTED.md` - Setup instructions
- API documentation at `/docs` (FastAPI)

---

**Status**: Specification Complete - Ready for Implementation (Week 12-13)
