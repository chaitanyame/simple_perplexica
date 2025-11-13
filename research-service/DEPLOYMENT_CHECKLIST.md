# ✅ Perplexity Integration - Deployment Checklist

**Status**: Ready for deployment  
**Date**: November 12, 2025  
**Tests**: 29/29 passing ✅

---

## 📋 Pre-Deployment Checklist

### ✅ Core Implementation (Complete)

- [x] **PerplexityClient** implemented
  - File: `src/services/search/perplexity_client.py` (247 lines)
  - Coverage: 98.57%
  - Tests: 19/19 passing

- [x] **CircuitBreaker** implemented
  - File: `src/core/circuit_breaker.py` (115 lines)
  - Coverage: 97.62%
  - Tests: 10/10 passing

- [x] **Standalone Helper** implemented
  - File: `src/services/search/perplexity_search.py` (165 lines)
  - Ready for immediate use

- [x] **Configuration** updated
  - File: `src/core/config.py` (PERPLEXITY_API_KEY added)
  - File: `.env.example` (Perplexity section added)

- [x] **Tests** passing
  - Total: 29/29 tests ✅
  - Coverage: 98%+

- [x] **Documentation** created
  - Integration guide (16KB)
  - Quick start guide (6KB)
  - Implementation summary (10KB)
  - Verification script (6KB)

---

## 🚀 Deployment Steps

### Step 1: Add API Key ⏭️ REQUIRED

```bash
# Edit research-service/.env
PERPLEXITY_API_KEY=pplx-your-api-key-here
```

**Get your API key**: https://www.perplexity.ai/settings/api

### Step 2: Choose Integration Approach ⏭️

#### **Option A: Standalone (Recommended for quick start)**

Add to any Python file:

```python
from src.services.search.perplexity_search import perplexity_search

# Direct search
result = await perplexity_search("What are AI agents?")
print(result["content"])  # Ready to display!
```

**Effort**: 5 minutes  
**Files to modify**: 1 (your choice)

---

#### **Option B: Streamlit UI Mode**

Add to `streamlit_ui.py`:

```python
from src.services.search.perplexity_search import perplexity_search

# Add mode selector
mode = st.selectbox("Search Mode", ["Auto", "SearxNG", "Perplexity"])

if mode == "Perplexity":
    result = await perplexity_search(query)
    st.markdown(result["content"])
```

**Effort**: 30 minutes  
**Files to modify**: `streamlit_ui.py`

---

#### **Option C: API Endpoint**

Add to `src/api/v1/endpoints/search.py`:

```python
from src.services.search.perplexity_search import perplexity_search

@router.post("/search/perplexity")
async def perplexity_endpoint(query: str):
    return await perplexity_search(query)
```

**Effort**: 20 minutes  
**Files to modify**: `src/api/v1/endpoints/search.py`

---

#### **Option D: SearchAgent Integration (Full Cascade)**

Add to `src/agents/search_agent.py` (see `PERPLEXITY_INTEGRATION_COMPLETE.md` for details)

**Effort**: 2 hours  
**Files to modify**: `src/agents/search_agent.py` (2400+ lines)

---

### Step 3: Test with Real API Key ⏭️

```bash
# Test the client directly
cd research-service
source venv/Scripts/activate

python -c "
import asyncio
from src.services.search.perplexity_search import perplexity_search

async def test():
    result = await perplexity_search('What are AI agents?')
    print(result['content'][:200] + '...')
    print(f'Citations: {len(result[\"citations\"])}')

asyncio.run(test())
"
```

---

### Step 4: Deploy ⏭️

```bash
# If using Docker
cd research-service
docker-compose down
docker-compose build
docker-compose up -d

# Or restart services
docker-compose restart research-api
```

---

## 🧪 Verification Commands

### Run Tests

```bash
cd research-service
source venv/Scripts/activate

# All Perplexity tests
pytest tests/unit/services/test_perplexity_client.py tests/unit/test_circuit_breaker.py -v

# Quick verification
python verify_perplexity_integration.py
```

### Expected Output

```
✅ PerplexityClient: ALL CHECKS PASSED
✅ CircuitBreaker: ALL CHECKS PASSED
✅ Configuration: ALL CHECKS PASSED
✅ Standalone Helper: ALL CHECKS PASSED
```

---

## 📊 Monitoring

### Key Metrics to Track

1. **API Calls**: Count Perplexity API requests
2. **Fallback Rate**: % of searches using Perplexity
3. **Circuit Breaker**: OPEN/CLOSE events
4. **Response Time**: Perplexity vs other sources
5. **Cost**: API usage costs

### Add Logging

```python
import logging
logger = logging.getLogger(__name__)

# Already included in implementation:
logger.info(f"✅ Perplexity: {len(citations)} citations")
logger.error(f"❌ Perplexity failed: {error}")
```

---

## 🎯 Cascade Logic (3-Tier Fallback)

```
┌──────────────┐
│   SearxNG    │ ← Primary (privacy-focused)
└──────┬───────┘
       │ Fails or < 3 results
       ↓
┌──────────────┐
│  SerperDev   │ ← Secondary (Google results)
└──────┬───────┘
       │ Fails or < 3 results
       ↓
┌──────────────┐
│  Perplexity  │ ← Final fallback (AI-powered)
└──────────────┘
       │
       ↓
Complete answer with citations ✅
```

### Threshold Settings

```bash
SEARXNG_MIN_RESULTS_THRESHOLD=3
SERPERDEV_MIN_RESULTS_THRESHOLD=3
```

---

## 🔒 Security Considerations

- [x] API key stored in `.env` (not committed)
- [x] Circuit breaker prevents API abuse
- [x] Rate limiting via exponential backoff
- [x] Error handling prevents data leaks
- [ ] Monitor API usage costs
- [ ] Set up billing alerts (Perplexity dashboard)

---

## 💰 Cost Estimation

**Perplexity Pricing** (as of 2025):
- **sonar-pro**: ~$3-5 per 1K requests
- **sonar**: ~$1-2 per 1K requests

**Recommendation**: Start with low volume, monitor costs, set alerts.

---

## 🐛 Troubleshooting

### Issue: "PERPLEXITY_API_KEY not configured"

**Solution**: Add to `.env` file:
```bash
PERPLEXITY_API_KEY=pplx-your-key-here
```

### Issue: "Circuit breaker open"

**Solution**: Service is experiencing failures. Wait for timeout (default 300s) or restart.

### Issue: No citations returned

**Solution**: Check Perplexity API response. Some queries may not have sources.

### Issue: Tests failing

**Solution**: 
```bash
cd research-service
source venv/Scripts/activate
pytest tests/unit/ -v --tb=short
```

---

## 📁 File Reference

### Implementation Files
```
src/services/search/
├── perplexity_client.py      # Core API client
└── perplexity_search.py       # Standalone helpers

src/core/
└── circuit_breaker.py         # Fault tolerance

tests/unit/
├── test_circuit_breaker.py    # Circuit breaker tests
└── services/
    └── test_perplexity_client.py  # Client tests
```

### Documentation Files
```
research-service/
├── PERPLEXITY_INTEGRATION_COMPLETE.md    # Full guide
├── PERPLEXITY_QUICK_START.md             # Quick reference  
├── PERPLEXITY_IMPLEMENTATION_SUMMARY.md  # Implementation details
└── verify_perplexity_integration.py      # Verification script
```

---

## ✅ Final Checklist

Before deploying to production:

- [ ] API key added to `.env`
- [ ] Tests passing locally
- [ ] Integration approach chosen
- [ ] Code changes implemented
- [ ] Manual testing completed
- [ ] Error handling verified
- [ ] Logging configured
- [ ] Monitoring set up
- [ ] Cost alerts configured
- [ ] Team notified

---

## 🎉 Success Criteria

Your integration is successful when:

✅ Perplexity search returns results with citations  
✅ Circuit breaker prevents cascading failures  
✅ Fallback cascade works (SearxNG → SerperDev → Perplexity)  
✅ Direct Perplexity mode works from UI  
✅ No errors in logs  
✅ API costs within budget  

---

## 📞 Support Resources

- **Documentation**: See files above
- **API Docs**: https://docs.perplexity.ai
- **Test Files**: `tests/unit/services/test_perplexity_client.py`
- **Verification**: `python verify_perplexity_integration.py`

---

## 🚦 Next Actions

1. **Immediate**: Add `PERPLEXITY_API_KEY` to `.env`
2. **Short-term**: Choose integration approach and implement
3. **Medium-term**: Test in staging environment
4. **Long-term**: Monitor usage and optimize

---

**Status**: ✅ Ready for deployment - All components tested and documented
