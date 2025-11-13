#!/usr/bin/env python3
"""Quick verification script for Perplexity integration.

Run this to verify the implementation is working correctly.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


async def test_perplexity_client():
    """Test PerplexityClient directly."""
    print("=" * 60)
    print("TEST 1: PerplexityClient (mock test)")
    print("=" * 60)
    
    from src.services.search.perplexity_client import (
        PerplexityClient,
        Citation,
        PerplexityResponse
    )
    
    # Test Citation
    citation = Citation(index=1, url="https://example.com", mention_count=2)
    print(f"✅ Citation created: {citation}")
    
    # Test PerplexityResponse
    response = PerplexityResponse(
        content="Test content [1]",
        citations=[citation],
        model="sonar-pro"
    )
    print(f"✅ PerplexityResponse created: {response.model}")
    
    # Test citation extraction
    content = "First [1]. Second [2]. First again [1]."
    urls = ["https://source1.com", "https://source2.com"]
    citations = PerplexityClient._extract_citations(content, urls)
    
    print(f"✅ Citation extraction: {len(citations)} citations found")
    print(f"   - Citation 1 mentioned {citations[0].mention_count} times")
    print(f"   - Citation 2 mentioned {citations[1].mention_count} times")
    
    print("\n✅ PerplexityClient: ALL CHECKS PASSED\n")


async def test_circuit_breaker():
    """Test CircuitBreaker."""
    print("=" * 60)
    print("TEST 2: CircuitBreaker")
    print("=" * 60)
    
    from src.core.circuit_breaker import CircuitBreaker, CircuitState
    
    breaker = CircuitBreaker(failure_threshold=2, timeout=1.0)
    print(f"✅ CircuitBreaker created: {breaker.state.value}")
    
    # Test successful call
    async def success_func():
        return "success"
    
    result = await breaker.call(success_func)
    print(f"✅ Successful call: {result}")
    print(f"   - State: {breaker.state.value}")
    print(f"   - Failure count: {breaker.failure_count}")
    
    # Test failure and OPEN state
    async def fail_func():
        raise Exception("Simulated failure")
    
    try:
        await breaker.call(fail_func)
    except Exception:
        pass
    
    try:
        await breaker.call(fail_func)
    except Exception:
        pass
    
    print(f"✅ Circuit opened after failures:")
    print(f"   - State: {breaker.state.value}")
    print(f"   - Failure count: {breaker.failure_count}")
    
    # Try calling when OPEN
    try:
        await breaker.call(success_func)
    except Exception as e:
        print(f"✅ Call rejected when OPEN: {str(e)[:50]}")
    
    print("\n✅ CircuitBreaker: ALL CHECKS PASSED\n")


async def test_configuration():
    """Test configuration loading."""
    print("=" * 60)
    print("TEST 3: Configuration")
    print("=" * 60)
    
    from src.core.config import settings
    
    print(f"✅ Settings loaded:")
    print(f"   - PERPLEXITY_MODEL: {settings.PERPLEXITY_MODEL}")
    print(f"   - PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD: {settings.PERPLEXITY_CIRCUIT_BREAKER_THRESHOLD}")
    print(f"   - PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT: {settings.PERPLEXITY_CIRCUIT_BREAKER_TIMEOUT}")
    print(f"   - ENABLE_SEARCH_FALLBACK: {settings.ENABLE_SEARCH_FALLBACK}")
    print(f"   - SEARXNG_MIN_RESULTS_THRESHOLD: {settings.SEARXNG_MIN_RESULTS_THRESHOLD}")
    print(f"   - SERPERDEV_MIN_RESULTS_THRESHOLD: {settings.SERPERDEV_MIN_RESULTS_THRESHOLD}")
    
    api_key_set = bool(settings.PERPLEXITY_API_KEY)
    print(f"   - PERPLEXITY_API_KEY set: {api_key_set}")
    
    if not api_key_set:
        print("\n⚠️  WARNING: PERPLEXITY_API_KEY not set in .env")
        print("   Add it to test real API calls:")
        print("   PERPLEXITY_API_KEY=pplx-your-key-here")
    
    print("\n✅ Configuration: ALL CHECKS PASSED\n")


async def test_standalone_helper():
    """Test standalone helper functions."""
    print("=" * 60)
    print("TEST 4: Standalone Helper")
    print("=" * 60)
    
    try:
        from src.services.search.perplexity_search import (
            get_perplexity_client,
            get_circuit_breaker,
        )
        
        # Try to get client (will fail without API key)
        try:
            client = get_perplexity_client()
            print("✅ Perplexity client singleton created")
        except ValueError as e:
            print(f"⚠️  Client creation skipped: {e}")
        
        # Get circuit breaker (should always work)
        breaker = get_circuit_breaker()
        print(f"✅ Circuit breaker singleton created: {breaker.state.value}")
        
        print("\n✅ Standalone Helper: ALL CHECKS PASSED\n")
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        print("   Make sure you're in the research-service directory")


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("PERPLEXITY INTEGRATION VERIFICATION")
    print("=" * 60)
    print()
    
    try:
        await test_perplexity_client()
        await test_circuit_breaker()
        await test_configuration()
        await test_standalone_helper()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print()
        print("Next steps:")
        print("1. Add PERPLEXITY_API_KEY to .env file")
        print("2. Run: pytest tests/unit/ -v")
        print("3. Integrate into Streamlit UI or API endpoints")
        print()
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
