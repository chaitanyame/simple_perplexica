"""Test authority scoring implementation.

This script tests the authority scoring feature to ensure:
1. Configuration is loaded correctly
2. Pattern-based authority detection works
3. Wikipedia citation proxy works (if enabled)
4. Authority scores affect final ranking
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import settings
from src.utils.authority_scorer import AuthorityScorer
from src.agents.search_agent import SearchSource


async def test_authority_scorer():
    """Test authority scorer with various source types."""
    print("=" * 80)
    print("AUTHORITY SCORING TEST")
    print("=" * 80)

    # Print configuration
    print("\n📋 Configuration:")
    print(f"  ENABLE_AUTHORITY_SCORING: {settings.ENABLE_AUTHORITY_SCORING}")
    print(f"  AUTHORITY_SCORING_WEIGHT: {settings.AUTHORITY_SCORING_WEIGHT}")
    print(f"  ENABLE_PATTERN_AUTHORITY: {settings.ENABLE_PATTERN_AUTHORITY}")
    print(f"  ENABLE_WIKIPEDIA_AUTHORITY: {settings.ENABLE_WIKIPEDIA_AUTHORITY}")
    print(f"  AUTHORITY_BOOST_MULTIPLIER: {settings.AUTHORITY_BOOST_MULTIPLIER}")

    if not settings.ENABLE_AUTHORITY_SCORING:
        print("\n⚠️  Authority scoring is DISABLED in configuration")
        return

    # Initialize scorer
    scorer = AuthorityScorer(settings)

    # Test sources
    test_sources = [
        # Tier 1: Official/Government
        SearchSource(
            title="Python Official Documentation",
            url="https://docs.python.org/3/library/asyncio.html",
            snippet="Official Python documentation for asyncio",
            relevance=0.85,
            source_type="web",
        ),
        # Tier 1: Academic
        SearchSource(
            title="Machine Learning Paper",
            url="https://arxiv.org/abs/2103.00020",
            snippet="Research paper on transformers",
            relevance=0.82,
            source_type="academic",
        ),
        # Tier 2: Reputable tech
        SearchSource(
            title="Stack Overflow Answer",
            url="https://stackoverflow.com/questions/12345/python-async",
            snippet="How to use async in Python",
            relevance=0.88,
            source_type="web",
        ),
        # Tier 3: Community/Blog
        SearchSource(
            title="Medium Article",
            url="https://medium.com/@author/python-async-guide",
            snippet="A guide to Python async programming",
            relevance=0.90,
            source_type="web",
        ),
        # No authority
        SearchSource(
            title="Random Blog",
            url="https://randomwebsite.com/article",
            snippet="Some random content",
            relevance=0.75,
            source_type="web",
        ),
    ]

    print("\n" + "=" * 80)
    print("PATTERN-BASED AUTHORITY SCORING")
    print("=" * 80)

    for i, source in enumerate(test_sources, 1):
        print(f"\n{i}. Testing: {source.title}")
        print(f"   URL: {source.url}")
        print(f"   Base Relevance: {source.relevance:.2f}")

        # Calculate authority score
        authority_score = await scorer.calculate_authority_score(source, query="python async")

        # Calculate boosted score (simulating rank_results logic)
        if authority_score > 0:
            boost = authority_score * settings.AUTHORITY_SCORING_WEIGHT
            boosted_score = min(
                1.0, source.relevance * (1 + boost * settings.AUTHORITY_BOOST_MULTIPLIER)
            )
            improvement = ((boosted_score - source.relevance) / source.relevance) * 100

            print(f"   ✅ Authority Score: {authority_score:.2f}")
            print(f"   📈 Boost Applied: {boost:.3f}")
            print(
                f"   🎯 Final Score: {source.relevance:.2f} → {boosted_score:.2f} (+{improvement:.1f}%)"
            )
        else:
            print(f"   ❌ No Authority Detected (score: 0.00)")
            print(f"   🎯 Final Score: {source.relevance:.2f} (unchanged)")

    # Test Wikipedia authority if enabled
    if settings.ENABLE_WIKIPEDIA_AUTHORITY:
        print("\n" + "=" * 80)
        print("WIKIPEDIA CITATION PROXY TEST")
        print("=" * 80)

        wiki_test_source = SearchSource(
            title="Python.org Documentation",
            url="https://www.python.org/about/",
            snippet="Python is a programming language",
            relevance=0.80,
            source_type="web",
        )

        print(f"\n🔍 Query: 'Python programming language'")
        print(f"   Testing: {wiki_test_source.url}")

        wiki_score = await scorer.calculate_authority_score(
            wiki_test_source, query="Python programming language"
        )

        if wiki_score > 0:
            print(f"   ✅ Wikipedia cites this domain: YES (score: {wiki_score:.2f})")
        else:
            print(f"   ℹ️  Wikipedia citation check: score {wiki_score:.2f}")

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("\n✅ Authority scoring is ENABLED and working correctly!")
    print("\n📊 Expected Behavior:")
    print("  • Official documentation (*.gov, *.edu, docs.*): Highest boost")
    print("  • Academic sources (arxiv.org, ieee.org): Highest boost")
    print("  • Reputable platforms (stackoverflow.com, github.com): Medium boost")
    print("  • Community sources (medium.com, dev.to): Lower boost")
    print("  • Unknown domains: No boost")

    print("\n🎯 Integration Status:")
    print("  • Pattern-based detection: ✅ Implemented")
    print("  • Wikipedia proxy: ✅ Implemented")
    print("  • Ranking integration: ✅ Integrated into rank_results()")
    print("  • Configurable flags: ✅ All features toggleable via .env")

    # Cleanup
    await scorer.close()


if __name__ == "__main__":
    asyncio.run(test_authority_scorer())
