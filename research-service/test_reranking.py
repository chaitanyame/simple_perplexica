"""Test semantic reranking functionality.

This script tests the cross-encoder reranking implementation.
"""

import asyncio

from src.services.embedding.embedding_service import EmbeddingService


async def test_reranking():
    """Test semantic reranking with cross-encoder."""
    print("🔧 Initializing EmbeddingService with cross-encoder...")
    service = EmbeddingService(
        model_name="all-MiniLM-L6-v2",
        reranker_model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        device="cpu",
    )

    # Test query
    query = "What are AI agents and how do they work?"
    
    # Test documents with varying relevance
    documents = [
        "AI agents are autonomous software systems that can perceive their environment, make decisions, and take actions to achieve specific goals.",
        "Machine learning is a subset of artificial intelligence that enables systems to learn from data.",
        "The weather today is sunny with a high of 75 degrees.",
        "Autonomous agents use sensors and actuators to interact with their environment and achieve objectives through planning and reasoning.",
        "Python is a popular programming language for AI development.",
    ]

    print(f"\n📝 Query: {query}")
    print(f"📄 Testing with {len(documents)} documents")
    print("\nDocuments:")
    for i, doc in enumerate(documents, 1):
        print(f"  [{i}] {doc[:80]}...")

    print("\n🔍 Running semantic reranking...")
    results = await service.rerank(query=query, documents=documents)

    print("\n✅ Reranking Results (sorted by score):")
    for idx, score in results:
        print(f"  [{idx + 1}] Score: {score:.4f} - {documents[idx][:80]}...")

    print("\n✨ Expected behavior:")
    print("  - Documents 1 and 4 (about AI agents) should score highest")
    print("  - Document 3 (about weather) should score lowest")

    print("\n📊 Validation:")
    top_idx, top_score = results[0]
    bottom_idx, bottom_score = results[-1]
    
    assert top_idx in [0, 3], f"Expected top result to be doc 1 or 4, got doc {top_idx + 1}"
    assert bottom_idx == 2, f"Expected bottom result to be doc 3, got doc {bottom_idx + 1}"
    assert top_score > 0.5, f"Expected top score > 0.5, got {top_score}"
    assert bottom_score < 0.2, f"Expected bottom score < 0.2, got {bottom_score}"
    
    print("✅ All assertions passed!")


if __name__ == "__main__":
    asyncio.run(test_reranking())
