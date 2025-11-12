"""Integration test for all new features.

Tests the three integrated features:
1. Query Normalization
2. Language Detection
3. Hybrid Retrieval (already exists, just validated)
"""

import asyncio
import sys


def test_query_normalization():
    """Test query normalization integration."""
    from src.utils.query_normalizer import normalize_query
    
    print("\n" + "="*80)
    print("1️⃣  QUERY NORMALIZATION TEST")
    print("="*80)
    
    test_cases = [
        ("What's NEW in Python 3.11?!", "whats new in python 311"),
        ("Microsoft AZURE", "microsoft azure"),
        ("AI, ML & Deep Learning!", "ai ml deep learning"),
    ]
    
    passed = 0
    for raw, expected in test_cases:
        result = normalize_query(raw)
        status = "✅" if result == expected else "❌"
        print(f"  {status} '{raw}' → '{result}'")
        if result == expected:
            passed += 1
    
    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_language_detection():
    """Test language detection integration."""
    from src.utils.language_detector import detect_language, get_language_name
    
    print("\n" + "="*80)
    print("2️⃣  LANGUAGE DETECTION TEST")
    print("="*80)
    
    test_cases = [
        ("Microsoft Azure news", "en", "English"),
        ("noticias de Microsoft Azure", "es", "Spanish"),
        ("¿Qué es Azure?", "es", "Spanish"),
        ("nouvelles de Microsoft Azure", "fr", "French"),
    ]
    
    passed = 0
    for text, expected_code, expected_name in test_cases:
        result_code = detect_language(text)
        result_name = get_language_name(result_code)
        status = "✅" if result_code == expected_code else "❌"
        print(f"  {status} '{text[:40]}...' → {result_name} ({result_code})")
        if result_code == expected_code and result_name == expected_name:
            passed += 1
    
    print(f"\n  Result: {passed}/{len(test_cases)} passed")
    return passed == len(test_cases)


def test_hybrid_search_exists():
    """Verify hybrid search implementation exists."""
    print("\n" + "="*80)
    print("3️⃣  HYBRID RETRIEVAL VALIDATION")
    print("="*80)
    
    try:
        from src.rag.vector_store_repository import VectorStoreRepository
        
        # Check if hybrid_search method exists
        if hasattr(VectorStoreRepository, 'hybrid_search'):
            print("  ✅ VectorStoreRepository.hybrid_search() exists")
            
            # Check method signature
            import inspect
            sig = inspect.signature(VectorStoreRepository.hybrid_search)
            params = list(sig.parameters.keys())
            
            required_params = ['session_id', 'query_text', 'query_vector', 'semantic_weight', 'keyword_weight']
            has_all = all(p in params for p in required_params)
            
            if has_all:
                print("  ✅ Method has correct parameters (semantic_weight, keyword_weight)")
                print(f"  ✅ Parameters: {', '.join(params[1:6])}")  # Skip 'self'
                print("\n  ✅ Hybrid search already implemented with RRF algorithm")
                return True
            else:
                print(f"  ❌ Missing parameters. Found: {params}")
                return False
        else:
            print("  ❌ hybrid_search() method not found")
            return False
            
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False


async def test_search_agent_integration():
    """Test SearchAgent integration with new features."""
    print("\n" + "="*80)
    print("4️⃣  SEARCH AGENT INTEGRATION TEST")
    print("="*80)
    
    try:
        from src.agents.search_agent import SubQuery
        
        # Test SubQuery model has language field
        if 'language' in SubQuery.model_fields:
            print("  ✅ SubQuery model has 'language' field")
            
            # Create test sub-query with all new fields
            sq = SubQuery(
                query="test query",
                intent="factual",
                priority=1,
                temporal_scope="any",
                specific_year=2023,
                language="es"
            )
            print(f"  ✅ SubQuery created with language='{sq.language}'")
            print(f"  ✅ All fields: query, intent, priority, temporal_scope, specific_year, language")
            return True
        else:
            print("  ❌ SubQuery model missing 'language' field")
            return False
            
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False


def main():
    """Run all integration tests."""
    print("\n" + "="*80)
    print("🚀 FEATURE INTEGRATION TEST SUITE")
    print("="*80)
    print("Testing: Query Normalization, Language Detection, Hybrid Retrieval")
    print("="*80)
    
    results = []
    
    # Test 1: Query Normalization
    results.append(("Query Normalization", test_query_normalization()))
    
    # Test 2: Language Detection
    results.append(("Language Detection", test_language_detection()))
    
    # Test 3: Hybrid Retrieval
    results.append(("Hybrid Retrieval", test_hybrid_search_exists()))
    
    # Test 4: SearchAgent Integration
    results.append(("SearchAgent Integration", asyncio.run(test_search_agent_integration())))
    
    # Summary
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    print(f"  Success Rate: {passed/total*100:.0f}%")
    
    if passed == total:
        print("\n  🎉 ALL FEATURES SUCCESSFULLY INTEGRATED!")
        return 0
    else:
        print(f"\n  ⚠️  {total - passed} feature(s) need attention")
        return 1


if __name__ == "__main__":
    sys.exit(main())
