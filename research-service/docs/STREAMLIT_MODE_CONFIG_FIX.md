# Streamlit Mode Configuration Fix

**Date**: 2025-01-11  
**Issue**: Streamlit UI sliders didn't honor selected mode configuration  
**Status**: ✅ Fixed

---

## Problem

When using Streamlit UI, the "Advanced Parameters" sliders showed **hardcoded defaults** (20 sources, 60s) regardless of the selected search mode:

- **SPEED** mode displays "5 sources | 15 seconds" but sliders showed 20, 60
- **BALANCED** mode displays "10 sources | 45 seconds" but sliders showed 20, 60  
- **DEEP** mode displays "20 sources | 60 seconds" (matched sliders) ✓

This created confusion: users saw "10 sources | 45 seconds" but the slider said "20" and "60".

**The backend was working correctly** (it used mode defaults when no override was provided), but the UI was confusing.

---

## Root Cause

In `streamlit_ui.py`:

```python
# BEFORE - Hardcoded slider defaults
max_sources = st.slider("Max Sources (override)", 5, 50, 20, ...)  # Always 20
timeout = st.slider("Timeout (s, override)", 10, 300, 60, ...)     # Always 60

# Hardcoded comparison
if max_sources != 20:  # Compared to hardcoded value
    payload["max_sources"] = max_sources
if timeout != 60:      # Compared to hardcoded value
    payload["timeout"] = timeout
```

---

## Solution

### 1. Dynamic Slider Defaults

Updated sliders to use **mode-specific defaults**:

```python
# Mode-specific defaults (from src/core/search_modes.py)
mode_defaults = {
    "speed": {"max_sources": 5, "timeout": 15},
    "balanced": {"max_sources": 10, "timeout": 45},
    "deep": {"max_sources": 20, "timeout": 60},
}
default_sources = mode_defaults[selected_mode]["max_sources"]
default_timeout = mode_defaults[selected_mode]["timeout"]

# Dynamic slider defaults
max_sources = st.slider(
    "Max Sources (override)", 
    5, 50, default_sources,  # Now uses 5/10/20 based on mode
    help=f"Leave at {default_sources} to use {selected_mode.upper()} mode default"
)
timeout = st.slider(
    "Timeout (s, override)", 
    10, 300, default_timeout,  # Now uses 15/45/60 based on mode
    help=f"Leave at {default_timeout}s to use {selected_mode.upper()} mode default"
)
```

### 2. Dynamic Override Detection

Updated payload logic to compare against **mode defaults**:

```python
# AFTER - Dynamic comparison
mode_defaults = {
    "speed": {"max_sources": 5, "timeout": 15},
    "balanced": {"max_sources": 10, "timeout": 45},
    "deep": {"max_sources": 20, "timeout": 60},
}
default_sources = mode_defaults[mode]["max_sources"]
default_timeout = mode_defaults[mode]["timeout"]

# Only send overrides if user changed from mode default
if max_sources != default_sources:
    payload["max_sources"] = max_sources
if timeout != default_timeout:
    payload["timeout"] = timeout
```

---

## Behavior

### Before Fix

| Mode | Display | Slider Default | API Receives | Actual Behavior |
|------|---------|---------------|--------------|-----------------|
| SPEED | 5 sources, 15s | 20, 60 | Mode config (5, 15) | ✅ Correct but confusing |
| BALANCED | 10 sources, 45s | 20, 60 | Mode config (10, 45) | ✅ Correct but confusing |
| DEEP | 20 sources, 60s | 20, 60 | Mode config (20, 60) | ✅ Correct |

### After Fix

| Mode | Display | Slider Default | API Receives | User Experience |
|------|---------|---------------|--------------|-----------------|
| SPEED | 5 sources, 15s | 5, 15 | Mode config (5, 15) | ✅ Clear & consistent |
| BALANCED | 10 sources, 45s | 10, 45 | Mode config (10, 45) | ✅ Clear & consistent |
| DEEP | 20 sources, 60s | 20, 60 | Mode config (20, 60) | ✅ Clear & consistent |

---

## Source of Truth

**All mode configurations come from**: `src/core/search_modes.py`

```python
SEARCH_MODE_CONFIGS: dict[SearchMode, SearchModeConfig] = {
    SearchMode.SPEED: SearchModeConfig(
        max_sources=5,
        timeout=15,
        enable_reranking=False,
        enable_crawling=False,
        ...
    ),
    SearchMode.BALANCED: SearchModeConfig(
        max_sources=10,
        timeout=45,
        enable_reranking=True,
        enable_crawling=True,
        ...
    ),
    SearchMode.DEEP: SearchModeConfig(
        max_sources=20,
        timeout=60,
        enable_reranking=True,
        enable_crawling=True,
        ...
    ),
}
```

**How API uses it** (`src/api/v1/endpoints/search.py`):

```python
# Get mode configuration
search_mode = get_mode_from_string(request.mode)
config = search_mode.config

# Use request parameters or mode defaults
max_sources = request.max_sources if request.max_sources is not None else config.max_sources
timeout = request.timeout if request.timeout is not None else config.timeout
```

---

## Testing

### Test File Updates

Updated `test_temporal_queries.py` to **display mode configuration**:

```python
# Added mode config reference
MODE_CONFIGS = {
    "speed": {"max_sources": 5, "timeout": 15},
    "balanced": {"max_sources": 10, "timeout": 45},
    "deep": {"max_sources": 20, "timeout": 60},
}

# Now displays in test output
print(f"Mode: {test['mode'].upper()}")
mode_config = MODE_CONFIGS[test['mode']]
print(f"Config: {mode_config['max_sources']} sources | {mode_config['timeout']} seconds")
```

**Test Output Before**:
```
Query: GitHub Universe 2023 announcements
Mode: DEEP
Expected: 2023
```

**Test Output After**:
```
Query: GitHub Universe 2023 announcements
Mode: DEEP
Config: 20 sources | 60 seconds  ← NEW
Expected: 2023
```

---

## Files Changed

1. **streamlit_ui.py** (Lines 74-99, 120-148)
   - Dynamic slider defaults based on selected mode
   - Dynamic override detection based on mode defaults
   - Updated help text to show mode-specific defaults

2. **test_temporal_queries.py** (Lines 1-18, 60-66)
   - Added MODE_CONFIGS reference dict
   - Added config display in test output

---

## Related Issues

- ✅ Fixes confusion where UI displayed "10 sources" but slider showed "20"
- ✅ Improves UX by syncing slider defaults with mode selection
- ✅ Makes test output more informative (shows actual config being tested)
- ✅ Maintains backward compatibility (API behavior unchanged)

---

## Testing Checklist

- [ ] Start Streamlit UI: `cd research-service && streamlit run streamlit_ui.py`
- [ ] Select **SPEED** mode → Verify sliders show 5, 15
- [ ] Select **BALANCED** mode → Verify sliders show 10, 45
- [ ] Select **DEEP** mode → Verify sliders show 20, 60
- [ ] Submit search without changing sliders → Verify API uses mode config
- [ ] Change slider values → Verify API receives overridden values
- [ ] Run `python test_temporal_queries.py` → Verify config displayed

---

## Next Steps

Consider centralizing mode configs to avoid duplication:

```python
# Option 1: Import from search_modes.py
from src.core.search_modes import SEARCH_MODE_CONFIGS

mode_defaults = {
    "speed": {
        "max_sources": SEARCH_MODE_CONFIGS[SearchMode.SPEED].max_sources,
        "timeout": SEARCH_MODE_CONFIGS[SearchMode.SPEED].timeout,
    },
    ...
}

# Option 2: Create shared config module
# src/core/mode_config.py with JSON/YAML config file
```

This would ensure **single source of truth** across codebase.
