"""Language detection utilities for multi-lingual support.

Detects the language of user queries to enable language-specific processing
and improve search relevance for non-English queries.
"""

from __future__ import annotations


def detect_language(text: str) -> str:
    """Detect language of text query.
    
    Supports: English (en), Spanish (es), French (fr), German (de)
    
    Detection strategy:
    1. Check for language-specific characters (highest priority)
    2. Count language-specific words
    3. Return language with highest confidence
    4. Default to English
    
    Args:
        text: Input text to analyze
        
    Returns:
        ISO 639-1 language code (e.g., 'en', 'es', 'fr', 'de')
        
    Example:
        >>> detect_language("Microsoft Azure news")
        "en"
        >>> detect_language("noticias de Microsoft Azure")
        "es"
        >>> detect_language("¿Qué es Azure?")
        "es"
    """
    if not text:
        return "en"
    
    text_lower = text.lower()
    words = text_lower.split()
    
    # Check for Spanish-specific characters first (most specific)
    spanish_chars = ["ñ", "¿", "¡", "á"]
    if any(char in text_lower for char in spanish_chars):
        return "es"
    
    # Check for French-specific characters
    french_chars = ["é", "è", "ê", "à", "ù", "ç"]
    if any(char in text_lower for char in french_chars):
        if "qu" in text_lower or "est" in words or "que" in words:
            return "fr"
    
    # Check for German-specific characters
    german_chars = ["ä", "ö", "ü", "ß"]
    if any(char in text_lower for char in german_chars):
        return "de"
    
    # Word-based detection with scoring
    spanish_words = ["noticias", "qué", "cómo", "para", "es", "son", "últimas", "cuáles"]
    spanish_count = sum(1 for word in spanish_words if word in words)
    
    french_words = ["nouvelles", "le", "les", "pour", "avec", "dans", "est", "que"]
    french_count = sum(1 for word in french_words if word in words)
    
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


def get_language_name(code: str) -> str:
    """Get full language name from ISO code.
    
    Args:
        code: ISO 639-1 language code
        
    Returns:
        Full language name
        
    Example:
        >>> get_language_name("es")
        "Spanish"
    """
    language_map = {
        "en": "English",
        "es": "Spanish",
        "fr": "French",
        "de": "German",
    }
    return language_map.get(code, "English")
