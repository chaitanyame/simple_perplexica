# Comprehensive Logging - Model Call Tracking

**Last Updated**: 2025-01-XX  
**Purpose**: Track all LLM calls, rate limits, errors, and phases for debugging

---

## 🎯 Overview

This document describes the comprehensive logging system implemented to track:
- ✅ **Model Usage**: Which model is called at which phase
- ⚠️ **Rate Limits**: When rate limiting occurs and which model
- ❌ **Errors**: API errors, timeouts, and fallback attempts
- 🔄 **Retries**: Retry attempts with exponential backoff
- 📊 **Token Usage**: Input/output token counts for each request

---

## 📝 Log Emoji Guide

| Emoji | Meaning | Location |
|-------|---------|----------|
| 🤖 | LLM request start (phase-specific) | search_agent.py |
| ✅ | Successful LLM response | openrouter_client.py |
| ⚠️ | Rate limit error | openrouter_client.py |
| ❌ | API error or failure | openrouter_client.py |
| 🔄 | Retry attempt or fallback switch | openrouter_client.py |
| ⏱️ | Timeout error | openrouter_client.py |
| 📤 | Request details (model, phase) | search_agent.py |
| 📥 | Response details | openrouter_client.py |
| 📊 | Token usage and metrics | openrouter_client.py |

---

## 🔍 Logging by Phase

### Phase 1: Query Decomposition

```
🤖 [PHASE: QUERY DECOMPOSITION] LLM CALL START
📤 Model: google/gemini-2.5-flash-lite
📤 Temperature: 0.3, Max Tokens: 500
🤖 LLM REQUEST START: model=google/gemini-2.5-flash-lite, temp=0.3, max_tokens=500, messages=X
✅ LLM RESPONSE SUCCESS: tokens_used=Y (input=A, output=B)
```

**Errors**:
```
⚠️ RATE LIMIT ERROR: model=google/gemini-2.5-flash-lite, attempt=1/10
🔄 RETRY: attempt 2/10, delay=2.0s, model=google/gemini-2.5-flash-lite
```

---

### Phase 2: Answer Generation

```
🤖 [PHASE: ANSWER GENERATION] LLM CALL START
📤 Model: google/gemini-2.5-flash-lite (final answer generation)
📤 Temperature: 0.7, Max Tokens: 2048
🤖 LLM REQUEST START: model=google/gemini-2.5-flash-lite, temp=0.7, max_tokens=2048, messages=X
✅ LLM RESPONSE SUCCESS: tokens_used=Y (input=A, output=B)
```

**Synthesis Model Switch** (if configured):
```
🔄 [PHASE: ANSWER GENERATION] Switching to synthesis model: google/gemini-2.5-flash-lite -> google/gemini-2.5-flash
```

**Errors**:
```
⏱️ TIMEOUT ERROR: model=google/gemini-2.5-flash-lite after 60.0s
🔄 RETRY: attempt 2/10, delay=4.0s, model=google/gemini-2.5-flash-lite
```

---

### Phase 3: Hallucination Regeneration

```
🤖 [PHASE: HALLUCINATION REGENERATION] LLM CALL START
📤 Model: google/gemini-2.5-flash-lite
📤 Regenerating due to 25.0% hallucinations
🤖 LLM REQUEST START: model=google/gemini-2.5-flash-lite, temp=0.3, max_tokens=2048, messages=X
✅ LLM RESPONSE SUCCESS: tokens_used=Y (input=A, output=B)
```

**Fallback After Rate Limits**:
```
⚠️ RATE LIMIT ERROR: model=google/gemini-2.5-flash-lite, attempt=2/10
🔄 FALLBACK: Switching model after rate limit: google/gemini-2.5-flash-lite -> google/gemini-2.5-flash
🤖 LLM REQUEST START: model=google/gemini-2.5-flash, temp=0.3, max_tokens=2048, messages=X
✅ LLM RESPONSE SUCCESS: tokens_used=Y (input=A, output=B)
```

---

## 🛠️ Implementation Details

### openrouter_client.py (Lines 72-360)

**Key Features**:
1. **Request Logging** (Line 143):
   - Model name, temperature, max_tokens, message count
   - Timestamp and request start marker

2. **Success Logging** (Lines 180-185):
   - Token usage breakdown (input/output)
   - Response received marker

3. **Rate Limit Handling** (Line 310):
   - Model causing rate limit
   - Attempt number (e.g., "1/10")
   - Retry delay

4. **Fallback Logic** (Lines 320-327):
   - Switches to fallback model after 2 rate limit attempts
   - Logs model switch: old_model -> new_model

5. **Error Logging**:
   - **Timeout** (Line 342): Model, timeout duration
   - **API Error** (Line 356): Model, HTTP status code, error message
   - **Fallback Failure** (Line 325): When fallback model also fails

---

### search_agent.py (Lines 462, 2380, 2529)

**Phase Tags**:
```python
# Query Decomposition
logger.info("🤖 [PHASE: QUERY DECOMPOSITION] LLM CALL START")

# Answer Generation
logger.info("🤖 [PHASE: ANSWER GENERATION] LLM CALL START")

# Hallucination Regeneration
logger.info("🤖 [PHASE: HALLUCINATION REGENERATION] LLM CALL START")
```

**Model Selection Logging**:
```python
# Synthesis model switch (if configured)
if settings.SYNTHESIS_LLM_MODEL:
    logger.info(
        f"🔄 [PHASE: ANSWER GENERATION] Switching to synthesis model: "
        f"{original_model} -> {settings.SYNTHESIS_LLM_MODEL}"
    )
```

---

## 🔄 Retry Logic

### Exponential Backoff

```
Attempt 1: delay = 1s
Attempt 2: delay = 2s (2^1)
Attempt 3: delay = 4s (2^2)
Attempt 4: delay = 8s (2^3)
...
Attempt 10: delay = 300s (max cap)
```

### Fallback After Rate Limits

```
Rate Limit 1 → Retry with same model (2^1 = 2s delay)
Rate Limit 2 → Switch to fallback model (2^2 = 4s delay)
Rate Limit 3+ → Retry with fallback model
```

---

## 📊 Example Log Sequence (Rate Limit Scenario)

### Successful Request
```
🤖 [PHASE: QUERY DECOMPOSITION] LLM CALL START
📤 Model: google/gemini-2.5-flash-lite
📤 Temperature: 0.3, Max Tokens: 500
🤖 LLM REQUEST START: model=google/gemini-2.5-flash-lite, temp=0.3, max_tokens=500, messages=3
✅ LLM RESPONSE SUCCESS: tokens_used=150 (input=120, output=30)
```

### Rate Limit → Retry → Fallback
```
🤖 [PHASE: ANSWER GENERATION] LLM CALL START
📤 Model: google/gemini-2.5-flash-lite (final answer generation)
📤 Temperature: 0.7, Max Tokens: 2048
🤖 LLM REQUEST START: model=google/gemini-2.5-flash-lite, temp=0.7, max_tokens=2048, messages=5

⚠️ RATE LIMIT ERROR: model=google/gemini-2.5-flash-lite, attempt=1/10
🔄 RETRY: attempt 2/10, delay=2.0s, model=google/gemini-2.5-flash-lite
🤖 LLM REQUEST START: model=google/gemini-2.5-flash-lite, temp=0.7, max_tokens=2048, messages=5

⚠️ RATE LIMIT ERROR: model=google/gemini-2.5-flash-lite, attempt=2/10
🔄 FALLBACK: Switching model after rate limit: google/gemini-2.5-flash-lite -> google/gemini-2.5-flash
🔄 RETRY: attempt 3/10, delay=4.0s, model=google/gemini-2.5-flash
🤖 LLM REQUEST START: model=google/gemini-2.5-flash, temp=0.7, max_tokens=2048, messages=5

✅ LLM RESPONSE SUCCESS: tokens_used=800 (input=600, output=200)
```

---

## 🧪 Testing the Logging

### Test Command
```bash
# Run a search query to see all logs
curl -X POST http://localhost:8000/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "GitHub Universe 2024",
    "search_mode": "semantic",
    "max_sources": 10,
    "enable_hallucination_detection": true
  }'
```

### View Logs
```bash
# Follow container logs
docker-compose logs -f research-api

# Filter for specific log types
docker-compose logs research-api | grep "🤖"  # LLM requests
docker-compose logs research-api | grep "⚠️"  # Rate limits
docker-compose logs research-api | grep "❌"  # Errors
docker-compose logs research-api | grep "🔄"  # Retries/fallbacks
```

---

## 📋 Configuration

### Environment Variables

```bash
# Model Configuration
LLM_MODEL=google/gemini-2.5-flash-lite
RESEARCH_LLM_MODEL=google/gemini-2.5-flash-lite
FALLBACK_LLM_MODEL=google/gemini-2.5-flash
SYNTHESIS_LLM_MODEL=  # Optional: dedicated synthesis model

# Retry Configuration (defaults)
MAX_RETRIES=10
INITIAL_DELAY=1.0
MAX_DELAY=300.0
RATE_LIMIT_ATTEMPTS_BEFORE_FALLBACK=2
```

---

## 🔧 Troubleshooting

### No Logs Appearing
1. Check container is running: `docker-compose ps`
2. Verify log level: `LOG_LEVEL=INFO` in .env
3. Rebuild container: `docker-compose build research-api`
4. Restart container: `docker-compose restart research-api`

### Rate Limits Not Triggering Fallback
1. Check `FALLBACK_LLM_MODEL` is set in .env
2. Verify `RATE_LIMIT_ATTEMPTS_BEFORE_FALLBACK=2` (default)
3. Look for "🔄 FALLBACK: Switching model" in logs

### Missing Phase Tags
1. Ensure search_agent.py has been updated with PHASE tags
2. Check lines 462, 2380, 2529 in search_agent.py
3. Rebuild container after code changes

---

## 📚 Related Documentation

- **Process Flows**: `docs/PROCESS_FLOWS.md`
- **Development Standards**: `docs/DEVELOPMENT_STANDARDS.md`
- **Two-Pass Synthesis**: `docs/TWO_PASS_SYNTHESIS_IMPLEMENTATION.md`
- **Query Expansion**: `docs/QUERY_EXPANSION_SUMMARY.md`

---

**REMEMBER**: All logs use emojis for quick visual scanning. Look for 🤖, ⚠️, ❌, and 🔄 markers! 🎯
