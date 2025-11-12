"""Unit tests for query normalization.

Tests query preprocessing and normalization for search operations.
"""

import pytest


def normalize_query(query: str) -> str:
    """Normalize query for search operations.
    
    Args:
        query: Raw query string
        
    Returns:
        Normalized query (lowercase, no special chars except spaces)
        
    Example:
        >>> normalize_query("Microsoft AZURE")
        "microsoft azure"
        >>> normalize_query("what's new?!")
        "whats new"
    """
    import re
    
    # Convert to lowercase
    normalized = query.lower()
    
    # Remove special characters except spaces
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Remove extra whitespace
    normalized = ' '.join(normalized.split())
    
    return normalized


def test_normalize_query_lowercase():
    """Test that query is converted to lowercase."""
    assert normalize_query("Microsoft AZURE") == "microsoft azure"


def test_normalize_query_special_chars():
    """Test that special characters are removed."""
    assert normalize_query("what's new?!") == "whats new"


def test_normalize_query_multiple_spaces():
    """Test that multiple spaces are collapsed."""
    assert normalize_query("hello    world") == "hello world"


def test_normalize_query_punctuation():
    """Test that punctuation is removed."""
    assert normalize_query("AI, ML & Deep Learning!") == "ai ml deep learning"


def test_normalize_query_empty():
    """Test empty query handling."""
    assert normalize_query("") == ""


def test_normalize_query_only_special_chars():
    """Test query with only special characters."""
    assert normalize_query("!!!???") == ""


def test_normalize_query_unicode():
    """Test query with unicode characters."""
    assert normalize_query("Café résumé") == "café résumé"


def test_normalize_query_numbers():
    """Test that numbers are preserved."""
    assert normalize_query("Python 3.11") == "python 311"


def test_normalize_query_mixed():
    """Test complex mixed query."""
    assert normalize_query("What's NEW in Python 3.11?!") == "whats new in python 311"
