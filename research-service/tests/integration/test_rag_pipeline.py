"""Integration tests for RAG pipeline components.

Tests the integration between:
- Embedding Service (sentence-transformers)
- Vector Store Repository (pgvector)

Validates end-to-end text embedding and vector similarity search.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ResearchSession
from src.rag.vector_store_repository import VectorStoreError, VectorStoreRepository
from src.services.embedding.embedding_service import EmbeddingService


@pytest.fixture
async def research_session(async_session: AsyncSession) -> ResearchSession:
    """Create a research session for integration tests."""
    session = ResearchSession(query="Test integration query", mode="search", status="processing")
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)
    return session


@pytest.fixture
def embedder() -> EmbeddingService:
    """Provide embedding service."""
    return EmbeddingService()


@pytest.fixture
def vector_store(async_session: AsyncSession) -> VectorStoreRepository:
    """Provide vector store repository."""
    return VectorStoreRepository(db=async_session)


class TestEmbeddingVectorStoreIntegration:
    """Test integration between embedding service and vector store."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_embed_and_store_pipeline(
        self,
        embedder: EmbeddingService,
        vector_store: VectorStoreRepository,
        research_session: ResearchSession,
    ) -> None:
        """Test complete pipeline: text → embedding → storage → retrieval."""
        # Sample text chunks
        texts = [
            "Machine learning is a subset of artificial intelligence.",
            "Supervised learning uses labeled training data.",
            "Unsupervised learning finds patterns without labels.",
            "Deep learning uses neural networks with multiple layers.",
            "Natural language processing enables language understanding.",
        ]

        # Step 1: Generate embeddings
        embeddings = await embedder.embed_batch(texts)

        assert len(embeddings) == len(texts)
        assert all(len(emb) == 384 for emb in embeddings)

        # Step 2: Store in vector database
        documents = [
            {"content": text, "embedding": embedding, "metadata": {"index": idx, "topic": "ai"}}
            for idx, (text, embedding) in enumerate(zip(texts, embeddings))
        ]

        doc_ids = await vector_store.store_batch(
            session_id=research_session.id, documents=documents
        )

        assert len(doc_ids) == len(texts)
        assert all(isinstance(doc_id, uuid.UUID) for doc_id in doc_ids)

        # Step 3: Search with query
        query = "What is supervised learning?"
        query_embedding = await embedder.embed_text(query)

        results = await vector_store.similarity_search(
            session_id=research_session.id, query_vector=query_embedding, top_k=3, threshold=0.3
        )

        assert len(results) > 0
        assert results[0].similarity_score > 0.3

        # Verify results ordered by similarity
        for i in range(len(results) - 1):
            assert results[i].similarity_score >= results[i + 1].similarity_score

        # Verify semantic relevance
        top_content = results[0].content.lower()
        assert "supervised" in top_content or "learning" in top_content

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_semantic_similarity_search(
        self,
        embedder: EmbeddingService,
        vector_store: VectorStoreRepository,
        research_session: ResearchSession,
    ) -> None:
        """Test semantic similarity search across diverse topics."""
        # Store documents on different topics
        topics = {
            "programming": [
                "Python is a high-level programming language.",
                "JavaScript runs in web browsers for frontend development.",
            ],
            "machine_learning": [
                "Neural networks learn from training data.",
                "Support vector machines are supervised learning models.",
            ],
            "databases": [
                "PostgreSQL is a relational database system.",
                "Vector databases store high-dimensional embeddings.",
            ],
        }

        all_texts = []
        all_metadata = []
        for topic, texts in topics.items():
            for text in texts:
                all_texts.append(text)
                all_metadata.append({"topic": topic})

        # Generate embeddings and store
        embeddings = await embedder.embed_batch(all_texts)

        documents = [
            {"content": text, "embedding": emb, "metadata": meta}
            for text, emb, meta in zip(all_texts, embeddings, all_metadata)
        ]

        await vector_store.store_batch(session_id=research_session.id, documents=documents)

        # Test queries for each topic
        test_queries = {
            "programming": "web development languages",
            "machine_learning": "deep learning algorithms",
            "databases": "storing vector embeddings",
        }

        for expected_topic, query in test_queries.items():
            query_embedding = await embedder.embed_text(query)

            results = await vector_store.similarity_search(
                session_id=research_session.id, query_vector=query_embedding, top_k=2
            )

            assert len(results) > 0
            # Top result should be from expected topic
            top_result_meta = results[0].doc_metadata
            assert top_result_meta is not None
            assert top_result_meta.get("topic") == expected_topic

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_batch_operations_performance(
        self,
        embedder: EmbeddingService,
        vector_store: VectorStoreRepository,
        research_session: ResearchSession,
    ) -> None:
        """Test batch operations with larger dataset."""
        # Generate 20 sample texts
        texts = [
            f"This is sample document number {i} about artificial intelligence and machine learning."
            for i in range(20)
        ]

        # Batch embed
        embeddings = await embedder.embed_batch(texts)

        assert len(embeddings) == 20
        assert all(len(emb) == 384 for emb in embeddings)

        # Batch store
        documents = [
            {"content": text, "embedding": emb, "metadata": {"doc_num": i}}
            for i, (text, emb) in enumerate(zip(texts, embeddings))
        ]

        doc_ids = await vector_store.store_batch(
            session_id=research_session.id, documents=documents
        )

        assert len(doc_ids) == 20

        # Verify count
        count = await vector_store.count_by_session(research_session.id)
        assert count == 20

        # Search and verify
        query_embedding = await embedder.embed_text("artificial intelligence")
        results = await vector_store.similarity_search(
            session_id=research_session.id, query_vector=query_embedding, top_k=5
        )

        assert len(results) == 5

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_cleanup_integration(
        self,
        embedder: EmbeddingService,
        vector_store: VectorStoreRepository,
        research_session: ResearchSession,
    ) -> None:
        """Test complete lifecycle: store → retrieve → delete."""
        # Store documents
        texts = ["Document 1", "Document 2", "Document 3"]
        embeddings = await embedder.embed_batch(texts)

        documents = [
            {"content": text, "embedding": emb, "metadata": {}}
            for text, emb in zip(texts, embeddings)
        ]

        doc_ids = await vector_store.store_batch(
            session_id=research_session.id, documents=documents
        )

        # Verify stored
        initial_count = await vector_store.count_by_session(research_session.id)
        assert initial_count == 3

        # Retrieve one
        retrieved = await vector_store.get_vector(doc_ids[0])
        assert retrieved is not None
        assert retrieved.content == "Document 1"

        # Delete one
        deleted = await vector_store.delete_vector(doc_ids[0])
        assert deleted is True

        # Verify count
        count_after_delete = await vector_store.count_by_session(research_session.id)
        assert count_after_delete == 2

        # Delete all by session
        deleted_count = await vector_store.delete_by_session(research_session.id)
        assert deleted_count == 2

        # Verify empty
        final_count = await vector_store.count_by_session(research_session.id)
        assert final_count == 0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_error_handling_integration(
        self,
        embedder: EmbeddingService,
        vector_store: VectorStoreRepository,
        research_session: ResearchSession,
    ) -> None:
        """Test error handling across components."""
        # Test embedding errors
        with pytest.raises(ValueError):
            await embedder.embed_text("")

        with pytest.raises(ValueError):
            await embedder.embed_text("   ")

        # Test vector store errors
        valid_embedding = await embedder.embed_text("test")

        # Wrong dimension
        with pytest.raises(VectorStoreError):
            await vector_store.store_vector(
                session_id=research_session.id,
                content="test",
                embedding=[1.0] * 128,  # Wrong dimension
                metadata={},
            )

        # Empty content
        with pytest.raises(VectorStoreError):
            await vector_store.store_vector(
                session_id=research_session.id, content="", embedding=valid_embedding, metadata={}
            )

        # Empty batch
        with pytest.raises(VectorStoreError):
            await vector_store.store_batch(session_id=research_session.id, documents=[])
