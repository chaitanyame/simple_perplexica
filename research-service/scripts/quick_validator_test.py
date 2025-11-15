"""Quick test of decomposition validator without pytest."""

import asyncio
from src.agents.decomposition_validator import DecompositionValidator
from src.agents.search_agent import SubQuery


async def test_validator():
    # Create validator
    validator = DecompositionValidator(
        coverage_threshold=0.7,
        redundancy_threshold=0.85,
        min_quality_score=0.6,
    )

    # Test good decomposition
    print("Testing GOOD decomposition...")
    original = "What are AI agents, how do they work, and what are their use cases?"
    good_subs = [
        SubQuery(query="what are AI agents", intent="definition", priority=1),
        SubQuery(query="how do AI agents work", intent="factual", priority=1),
        SubQuery(query="AI agent use cases", intent="factual", priority=1),
    ]

    score = await validator.evaluate_quality(original, good_subs)
    print("\nGood Decomposition Score:")
    print(f"  Coverage: {score.coverage_score:.2f}")
    print(f"  Redundancy: {score.redundancy_score:.2f}")
    print(f"  Overall: {score.overall_score:.2f}")
    print(f"  Passes: {score.passes_threshold}")
    print(f"  Issues: {score.issues}")

    # Test poor decomposition
    print("\n" + "=" * 60)
    print("Testing POOR decomposition...")
    poor_subs = [
        SubQuery(query="weather today", intent="factual", priority=1),
        SubQuery(query="stock market", intent="factual", priority=1),
    ]

    score2 = await validator.evaluate_quality(original, poor_subs)
    print("\nPoor Decomposition Score:")
    print(f"  Coverage: {score2.coverage_score:.2f}")
    print(f"  Redundancy: {score2.redundancy_score:.2f}")
    print(f"  Overall: {score2.overall_score:.2f}")
    print(f"  Passes: {score2.passes_threshold}")
    print(f"  Issues: {score2.issues}")

    print(
        "\n✅ Validator working correctly!"
        if not score2.passes_threshold
        else "\n❌ Should have failed"
    )


if __name__ == "__main__":
    asyncio.run(test_validator())
