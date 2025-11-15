# Utility Scripts

This directory contains utility scripts for development, testing, and maintenance.

## Scripts

### `fix_source_type.py`
Utility script to fix SearchSource instances by adding the required `source_type` field.

**Usage:**
```bash
python scripts/fix_source_type.py
```

**Purpose:**
- Adds `source_type="web"` to SearchSource instances missing this required field
- Used during test development to fix validation errors

### `quick_validator_test.py`
Quick validation test script for testing specific functionality.

**Usage:**
```bash
python scripts/quick_validator_test.py
```

**Purpose:**
- Quick smoke tests
- Development validation
- Not part of the main test suite

## Note

These scripts are for development use only and are not part of the production codebase or the main test suite.
