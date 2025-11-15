# Research Service Documentation

Complete documentation for the Research Service API and implementation.

---

## 📁 Folder Structure

```
docs/
├── INDEX.md                           # This file - documentation index
├── api/                               # API documentation
│   ├── README_API.md                  # API documentation overview
│   ├── API_SPECIFICATION.md           # Complete API reference
│   ├── API_QUICK_REFERENCE.md         # Quick lookup guide
│   ├── TESTING_GUIDE.md               # Testing procedures
│   └── openapi.yaml                   # OpenAPI 3.0 specification
├── PROCESS_FLOWS.md                   # Agent workflows and pipelines
├── STREAMLIT_APP_SPEC.md              # Streamlit UI specification
├── STREAMLIT_ARCHITECTURE.md          # UI architecture details
├── DEVELOPMENT_STANDARDS.md           # Coding standards and practices
├── COMPREHENSIVE_LOGGING.md           # Logging implementation guide
├── LIBRARY_VERSIONS.md                # Dependency versions
├── TEST_COVERAGE_SUMMARY.md           # Test coverage metrics
├── DIVERSITY_ENABLED_SUMMARY.md       # Diversity scoring feature
├── QUERY_EXPANSION_SUMMARY.md         # Query expansion implementation
├── TWO_PASS_SYNTHESIS_IMPLEMENTATION.md # Two-pass synthesis feature
├── TEST_EXECUTION_SUMMARY.md          # Test execution results
├── SEARCH_ACCURACY_ANALYSIS.md        # Search accuracy metrics
├── NO_API_CALLS_FIX.md                # API call prevention guide
└── CODEBASE_CLEANUP.md                # Project organization guide
```

---

## 🚀 API Documentation

Located in `docs/api/`

### Quick Start
1. **[README_API.md](api/README_API.md)** - Start here for overview and navigation
2. **[API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md)** - Common use cases and examples
3. **[API_SPECIFICATION.md](api/API_SPECIFICATION.md)** - Complete reference documentation

### Testing & Tools
- **[TESTING_GUIDE.md](api/TESTING_GUIDE.md)** - QA test procedures and examples
- **[openapi.yaml](api/openapi.yaml)** - Machine-readable OpenAPI spec

### Live Documentation
- **Swagger UI:** http://localhost:8001/api/docs
- **ReDoc:** http://localhost:8001/api/redoc
- **OpenAPI JSON:** http://localhost:8001/api/openapi.json

---

## 📋 Documentation Files

### API Documentation
| File | Purpose |
|------|---------|
| API_SPECIFICATION.md | Complete API reference with all endpoints, schemas, and examples |
| API_QUICK_REFERENCE.md | Quick lookup guide with common patterns and commands |
| TESTING_GUIDE.md | Test procedures with 20+ test cases and validation steps |
| README_API.md | Overview, navigation guide, and getting started steps |
| openapi.yaml | Machine-readable OpenAPI 3.0 specification |

### Architecture & Design
| File | Purpose |
|------|---------|
| PROCESS_FLOWS.md | Agent workflows, pipelines, and data flow diagrams |
| STREAMLIT_APP_SPEC.md | Streamlit UI components and specifications |
| STREAMLIT_ARCHITECTURE.md | UI architecture and component interaction |

### Development & Standards
| File | Purpose |
|------|---------|
| DEVELOPMENT_STANDARDS.md | Coding standards, TDD practices, and guidelines |
| COMPREHENSIVE_LOGGING.md | Logging implementation and best practices |
| LIBRARY_VERSIONS.md | Technology stack and dependency versions |

### Features & Implementation
| File | Purpose |
|------|---------|
| DIVERSITY_ENABLED_SUMMARY.md | Source diversity scoring feature documentation |
| QUERY_EXPANSION_SUMMARY.md | Query expansion implementation details |
| TWO_PASS_SYNTHESIS_IMPLEMENTATION.md | Two-pass synthesis with hallucination correction |

### Testing & Quality
| File | Purpose |
|------|---------|
| TEST_EXECUTION_SUMMARY.md | Test suite execution results and metrics |
| TEST_COVERAGE_SUMMARY.md | Code coverage analysis and reports |
| SEARCH_ACCURACY_ANALYSIS.md | Search accuracy benchmarks and analysis |

### Maintenance & Operations
| File | Purpose |
|------|---------|
| NO_API_CALLS_FIX.md | Guide to preventing unwanted API calls in tests |
| CODEBASE_CLEANUP.md | Project organization and cleanup documentation |

---

## 📖 How to Use

### For Different Audiences

**👨‍💻 Developers**
1. Read [README_API.md](api/README_API.md) for overview
2. Check [API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md) for examples
3. Reference [API_SPECIFICATION.md](api/API_SPECIFICATION.md) for details

**🧪 QA Engineers**
1. Follow [TESTING_GUIDE.md](api/TESTING_GUIDE.md)
2. Run test cases and validation checks
3. Verify performance benchmarks

**🔧 Integrators**
1. Import [openapi.yaml](api/openapi.yaml) into tools
2. Generate client libraries
3. Test with examples from QUICK_REFERENCE

**🏗️ Architects**
1. Review [API_SPECIFICATION.md](api/API_SPECIFICATION.md)
2. Check error handling and security
3. Plan deployment with configuration guide

---

## 🎯 Quick Navigation

### By Task

**Get a quick answer?**
→ Search mode - See API_QUICK_REFERENCE.md "Quick Answer" section

**Research a complex topic?**
→ Research mode - See API_QUICK_REFERENCE.md "Deep Research" section

**Upload and query documents?**
→ Document endpoints - See API_QUICK_REFERENCE.md "Document Q&A" section

**Integrate with your app?**
→ See API_SPECIFICATION.md for complete endpoint details

**Test the API?**
→ Follow TESTING_GUIDE.md with curl or Python examples

**Generate client code?**
→ Import openapi.yaml into OpenAPI tools

---

## 🔗 External Resources

### API Documentation Endpoints
- **Swagger UI** (Interactive): http://localhost:8001/api/docs
- **ReDoc** (Readable): http://localhost:8001/api/redoc
- **OpenAPI Schema** (JSON): http://localhost:8001/api/openapi.json

### Configuration
- `.env` - Environment variables
- `docker-compose.yml` - Container setup

---

## 📚 Document Descriptions

### API_SPECIFICATION.md
**Comprehensive API reference** covering:
- All 8 endpoints with full descriptions
- Request/response schemas with examples
- Error codes and solutions
- Rate limiting details
- Search modes and engines
- Langfuse observability integration
- Configuration reference
- Data model definitions

**Best for:** Complete reference, integration planning, detailed understanding

---

### API_QUICK_REFERENCE.md
**Quick lookup guide** with:
- Common use cases with time/cost estimates
- Endpoint comparison table
- Curl command examples
- Python client examples (sync & async)
- Search mode explanations
- Search engine comparison
- Error handling guide
- Performance tips and tricks

**Best for:** Quick answers, getting started, copying examples

---

### TESTING_GUIDE.md
**Comprehensive testing procedures** including:
- Test cases for each endpoint (20+)
- Validation checklists
- Performance benchmarks with expected times
- Integration test workflows
- Error handling test cases
- Concurrent request testing
- Automated testing scripts
- Success criteria

**Best for:** QA testing, validating functionality, performance verification

---

### README_API.md
**Navigation and overview guide** featuring:
- File index and descriptions
- Getting started in 4 steps
- Endpoint summary table
- Key features overview
- Configuration reference
- Development structure
- Troubleshooting guide
- Support resources

**Best for:** Navigation, quick overview, finding what you need

---

### openapi.yaml
**Machine-readable OpenAPI 3.0 specification** with:
- Full API schema definition
- All request/response models
- Complete endpoint definitions
- Error response schemas
- Parameter descriptions
- Example values
- Proper tag organization

**Best for:** Code generation, API testing tools, documentation generation

---

## ✅ Checklist for Getting Started

- [ ] Read [README_API.md](api/README_API.md) for overview
- [ ] Try examples from [API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md)
- [ ] Run health check: `curl http://localhost:8001/api/v1/health`
- [ ] Test search endpoint with example query
- [ ] Upload a test document
- [ ] Query the document with RAG
- [ ] Check Langfuse trace URLs in responses
- [ ] Review [TESTING_GUIDE.md](api/TESTING_GUIDE.md) for validation

---

## 🔍 Finding Information

### Search Mode Explained?
→ [API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md) → Search Modes section

### How to Upload Documents?
→ [API_SPECIFICATION.md](api/API_SPECIFICATION.md) → Documents section

### Getting Timeout Errors?
→ [API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md) → Troubleshooting section

### Want Python Examples?
→ [API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md) → Python Client Examples section

### Need to Test Everything?
→ [TESTING_GUIDE.md](api/TESTING_GUIDE.md) → Full test procedures

### Integrating with Tools?
→ Use [openapi.yaml](api/openapi.yaml) with OpenAPI generators

---

## 📊 Documentation Statistics

- **Total Pages:** ~75 pages of documentation
- **Endpoints:** 8 fully documented
- **Test Cases:** 20+ with validation steps
- **Code Examples:** 30+ (curl, Python, Bash)
- **Error Codes:** 10+ with solutions
- **Configuration Options:** 30+ environment variables

---

## 🔄 File Organization Rationale

**Why separate docs folder?**
- Keeps documentation organized and separate from code
- Easy to share with non-technical stakeholders
- Can be published separately (docs site, wiki, etc.)
- Version controlled independently if needed

**Structure:**
```
docs/
  ├── api/              # API documentation
  ├── ARCHITECTURE.md   # (future) System design
  ├── DEPLOYMENT.md     # (future) Deployment guide
  └── TROUBLESHOOTING.md # (future) Common issues
```

---

## 💡 Tips

1. **Bookmark [README_API.md](api/README_API.md)** - It's your navigation hub
2. **Keep [API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md) handy** - Copy/paste examples
3. **Use interactive docs** - http://localhost:8001/api/docs for live testing
4. **Check Langfuse traces** - Click trace URLs in responses for debugging
5. **Run tests first** - Verify everything works with [TESTING_GUIDE.md](api/TESTING_GUIDE.md)

---

## 🆘 Need Help?

| Question | Location |
|----------|----------|
| What's this API about? | [README_API.md](api/README_API.md) |
| How do I use it? | [API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md) |
| What's the exact format? | [API_SPECIFICATION.md](api/API_SPECIFICATION.md) |
| How do I test it? | [TESTING_GUIDE.md](api/TESTING_GUIDE.md) |
| I need code! | Interactive docs: http://localhost:8001/api/docs |
| Something's broken? | [API_QUICK_REFERENCE.md](api/API_QUICK_REFERENCE.md) → Troubleshooting |

---

## 📝 Last Updated

November 13, 2025

---

## Version

**API Version:** 0.1.0
**Documentation Version:** 1.0
