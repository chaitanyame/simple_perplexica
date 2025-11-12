"""Unit tests for language detection.

Tests automatic detection of query language for multi-lingual support.
"""

import pytest


def detect_language(text: str) -> str:
    """Detect language of text query.
    
    Args:
        text: Input text to analyze
        
    Returns:
        ISO 639-1 language code (e.g., 'en', 'es', 'fr')
        
    Example:
        >>> detect_language("Microsoft Azure news")
        "en"
        >>> detect_language("noticias de Microsoft Azure")
        "es"
    """
    # Simple rule-based detection for common patterns
    # In production, use langdetect or lingua library
    
    text_lower = text.lower()
    words = text_lower.split()
    
    # Check for Spanish-specific characters first (most specific)
    spanish_chars = ["ñ", "¿", "¡", "á"]
    if any(char in text_lower for char in spanish_chars):
        return "es"
    
    # Check for accented characters
    french_chars = ["é", "è", "ê", "à", "ù", "ç"]
    german_chars = ["ä", "ö", "ü", "ß"]
    
    if any(char in text_lower for char in french_chars):
        if "qu" in text_lower or "est" in words or "que" in words:
            return "fr"
    
    if any(char in text_lower for char in german_chars):
        return "de"
    
    # Spanish indicators (check before French due to overlapping words)
    spanish_words = ["noticias", "qué", "cómo", "para", "es", "son", "últimas", "cuáles"]
    spanish_count = sum(1 for word in spanish_words if word in words)
    
    # French indicators
    french_words = ["nouvelles", "le", "les", "pour", "avec", "dans", "est", "que"]
    french_count = sum(1 for word in french_words if word in words)
    
    # German indicators
    german_words = ["der", "die", "das", "ist", "und", "für", "nachrichten"]
    german_count = sum(1 for word in german_words if word in words)
    
    # Return language with highest word count
    if spanish_count > 0 and spanish_count >= french_count:
        return "es"
    if french_count > 0:
        return "fr"
    if german_count > 0:
        return "de"
    
    # Default to English
    return "en"


def test_detect_english():
    """Test English language detection."""
    assert detect_language("Microsoft Azure news") == "en"


def test_detect_spanish():
    """Test Spanish language detection."""
    assert detect_language("noticias de Microsoft Azure") == "es"


def test_detect_french():
    """Test French language detection."""
    assert detect_language("nouvelles de Microsoft Azure") == "fr"


def test_detect_german():
    """Test German language detection."""
    assert detect_language("Microsoft Azure Nachrichten") == "de"


def test_detect_english_with_numbers():
    """Test English detection with numbers."""
    assert detect_language("Python 3.11 features") == "en"


def test_detect_spanish_with_accents():
    """Test Spanish detection with accented characters."""
    assert detect_language("¿Qué es Azure?") == "es"


def test_detect_french_with_accents():
    """Test French detection with accented characters."""
    assert detect_language("Qu'est-ce que Azure?") == "fr"


def test_detect_short_query():
    """Test language detection with short query."""
    assert detect_language("Azure") == "en"


def test_detect_empty_query():
    """Test language detection with empty query."""
    assert detect_language("") == "en"


def test_detect_mixed_language():
    """Test language detection with mixed languages (defaults to English)."""
    assert detect_language("Azure cloud computing") == "en"


def test_detect_spanish_long_text():
    """Test Spanish detection with longer text."""
    text = "¿Cuáles son las últimas noticias de Microsoft Azure para desarrolladores?"
    assert detect_language(text) == "es"


def test_detect_case_insensitive():
    """Test that detection is case-insensitive."""
    assert detect_language("NOTICIAS DE AZURE") == "es"
    assert detect_language("noticias de azure") == "es"
