# Diagnostic Tools

This directory contains diagnostic and testing utilities for the Simple Perplexica project.

## Available Tools

### `test-searxng-connectivity.bat`
**Purpose:** Tests connectivity to SearxNG service from Windows command line.

**Usage:**
```batch
cd docs/tools
test-searxng-connectivity.bat
```

**Tests:**
- SearxNG endpoint availability
- Basic search functionality
- Response format validation

**Note:** SearxNG must be running (via `docker-compose up searxng`)

---

### `test_research_quick.py`
**Purpose:** Quick manual testing of research service endpoints without full pytest suite.

**Usage:**
```bash
cd docs/tools
python test_research_quick.py
```

**Tests:**
- Basic API endpoint connectivity
- Quick query processing
- Response structure validation

**Note:** Use for rapid debugging. For comprehensive testing, use:
```bash
cd research-service
pytest tests/ -v
```

---

## Related Tools

### In `research-service/`
- `test-connectivity.sh` - Comprehensive dependency checker (PostgreSQL, Redis, SearxNG, OpenRouter)
- `run_tests.bat` / `run_tests.sh` - Full test suite runners
- `run_all_tests.bat` - Windows comprehensive test runner

### In `services/searchsvc/tools/`
- Streamlit UI for search service testing

---

**Last Updated:** November 15, 2025
