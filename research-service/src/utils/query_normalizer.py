"""Query normalization utilities for search operations.

Provides functions to normalize and clean user queries before processing.
"""

from __future__ import annotations

import re


def normalize_query(query: str) -> str:
    """Normalize query for search operations.
    
    Performs the following normalizations:
    - Converts to lowercase
    - Removes special characters (except spaces)
    - Collapses multiple whitespaces
    - Preserves unicode characters (accents, etc.)
    
    Args:
        query: Raw query string from user
        
    Returns:
        Normalized query string
        
    Example:
        >>> normalize_query("What's NEW in Python 3.11?!")
        "whats new in python 311"
        >>> normalize_query("Microsoft AZURE")
        "microsoft azure"
    """
    if not query:
        return ""
    
    # Convert to lowercase
    normalized = query.lower()
    
    # Remove special characters except spaces
    # \w = word characters (letters, digits, underscore, unicode)
    # \s = whitespace
    normalized = re.sub(r'[^\w\s]', '', normalized)
    
    # Remove extra whitespace (multiple spaces, tabs, newlines)
    normalized = ' '.join(normalized.split())
    
    return normalized


def extract_keywords(query: str) -> list[str]:
    """Extract keywords from normalized query.
    
    Args:
        query: Normalized query string
        
    Returns:
        List of keywords (words longer than 2 characters)
        
    Example:
        >>> extract_keywords("what is python 3.11")
        ["what", "python", "311"]
    """
    normalized = normalize_query(query)
    keywords = [word for word in normalized.split() if len(word) > 2]
    return keywords
