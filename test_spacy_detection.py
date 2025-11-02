"""
Test SpaCy-based temporal intent detection locally
Run this AFTER rebuilding the container with SpaCy installed
"""

import sys
import os

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "services", "api-mvp"))

from app.search_clients.searxng import _detect_recency_need, _load_spacy_model


def test_spacy_installation():
    """Check if SpaCy model is installed"""
    print("Testing SpaCy installation...")
    nlp = _load_spacy_model()
    if nlp is None:
        print("❌ SpaCy model not found")
        print("Run: python -m spacy download en_core_web_sm")
        return False
    else:
        print(f"✅ SpaCy model loaded: {nlp.meta['lang']}_{nlp.meta['name']}")
        return True


def test_temporal_detection():
    """Test various queries to see NLP-based detection"""
    test_cases = [
        # Day-level
        ("breaking news today", "d"),
        ("latest AI developments", "d"),
        ("what happened yesterday", "d"),
        ("current events in politics", "d"),
        # Week-level
        ("news this week", "w"),
        ("recent tech updates", "w"),
        ("past week's events", "w"),
        # Month-level
        ("this month's stock market", "m"),
        ("last month's earnings", "m"),
        # No filter (historical)
        ("World War 2 history", None),
        ("how does photosynthesis work", None),
        ("best pizza recipe", None),
    ]

    print("\n" + "=" * 80)
    print("Testing NLP-based temporal detection")
    print("=" * 80)

    for query, expected in test_cases:
        result = _detect_recency_need(query)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{query}' → {result} (expected: {expected})")

        # Show SpaCy entity analysis for failed cases
        if result != expected:
            nlp = _load_spacy_model()
            if nlp:
                doc = nlp(query)
                print(f"   Entities: {[(ent.text, ent.label_) for ent in doc.ents]}")
                print(
                    f"   Tokens: {[(token.text, token.pos_, token.dep_) for token in doc]}"
                )


def test_entity_recognition():
    """Show how SpaCy recognizes temporal entities"""
    nlp = _load_spacy_model()
    if not nlp:
        return

    print("\n" + "=" * 80)
    print("SpaCy Entity Recognition Examples")
    print("=" * 80)

    examples = [
        "breaking news today in USA",
        "latest AI breakthroughs this week",
        "current events this month",
        "World War 2 started in 1939",
    ]

    for query in examples:
        doc = nlp(query)
        print(f"\nQuery: '{query}'")
        print(
            f"  DATE entities: {[ent.text for ent in doc.ents if ent.label_ == 'DATE']}"
        )
        print(
            f"  Temporal adjectives: {[token.text for token in doc if token.text.lower() in {'latest', 'breaking', 'recent', 'current'}]}"
        )
        print(f"  Detection result: {_detect_recency_need(query)}")


if __name__ == "__main__":
    if not test_spacy_installation():
        print("\n⚠️  Install SpaCy model first:")
        print("pip install spacy")
        print("python -m spacy download en_core_web_sm")
        sys.exit(1)

    test_temporal_detection()
    test_entity_recognition()

    print("\n" + "=" * 80)
    print("✅ All tests complete!")
    print("=" * 80)
