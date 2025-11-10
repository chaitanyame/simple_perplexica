"""Tests for pgvector-based vector store repository.

Following TDD approach:
1. RED: Write failing tests first
2. GREEN: Implement to pass tests
3. REFACTOR: Clean up code
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DocumentEmbedding, ResearchSession
from src.rag.vector_store_repository import (
    SearchResult,
    VectorStoreError,
    VectorStoreRepository,
)


@pytest_asyncio.fixture
async def create_research_session(async_session: AsyncSession) -> uuid.UUID:
    """Create a research session in the database for testing."""
    session = ResearchSession(query="Test query", mode="search", status="pending")
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)
    return session.id


class TestVectorStoreRepositoryInitialization:
    """Test vector store repository initialization."""

    def test_initialize_with_session(self, async_session: AsyncSession) -> None:
        """Test initialization with database session."""
        repo = VectorStoreRepository(db=async_session)

        assert repo.db == async_session
        assert repo.dimension == 384


class TestVectorStoreRepositoryStoreVector:
    """Test storing vectors in the database."""

    @pytest.mark.asyncio
    async def test_store_single_vector_success(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test successful storage of a single vector."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session
        content = "This is a test document about AI."
        embedding = np.random.randn(384).tolist()

        result = await repo.store_vector(
            session_id=session_id,
            content=content,
            embedding=embedding,
            metadata={"source": "test", "page": 1},
        )

        assert isinstance(result, uuid.UUID)
        assert result is not None

        # Verify stored in database
        stmt = select(DocumentEmbedding).where(DocumentEmbedding.id == result)
        stored = await async_session.scalar(stmt)

        assert stored is not None
        assert stored.session_id == session_id
        assert stored.content == content
        assert len(stored.embedding) == 384
        assert stored.doc_metadata == {"source": "test", "page": 1}

    @pytest.mark.asyncio
    async def test_store_vector_with_minimal_metadata(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test storing vector with minimal metadata."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session
        content = "Minimal test."
        embedding = np.random.randn(384).tolist()

        result = await repo.store_vector(
            session_id=session_id, content=content, embedding=embedding
        )

        assert isinstance(result, uuid.UUID)

    @pytest.mark.asyncio
    async def test_store_vector_empty_content(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test storing vector with empty content raises error."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session
        embedding = np.random.randn(384).tolist()

        with pytest.raises(VectorStoreError) as exc_info:
            await repo.store_vector(session_id=session_id, content="", embedding=embedding)

        assert "content" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_store_vector_wrong_dimension(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test storing vector with wrong dimension raises error."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session
        embedding = np.random.randn(256).tolist()  # Wrong dimension

        with pytest.raises(VectorStoreError) as exc_info:
            await repo.store_vector(
                session_id=session_id, content="Test content", embedding=embedding
            )

        assert "dimension" in str(exc_info.value).lower()


class TestVectorStoreRepositoryBatchStore:
    """Test batch vector storage."""

    @pytest.mark.asyncio
    async def test_store_batch_success(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test successful batch storage."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session

        documents = [
            {
                "content": "First document about AI",
                "embedding": np.random.randn(384).tolist(),
                "metadata": {"page": 1},
            },
            {
                "content": "Second document about ML",
                "embedding": np.random.randn(384).tolist(),
                "metadata": {"page": 2},
            },
            {
                "content": "Third document about data",
                "embedding": np.random.randn(384).tolist(),
                "metadata": {"page": 3},
            },
        ]

        result_ids = await repo.store_batch(session_id=session_id, documents=documents)

        assert len(result_ids) == 3
        assert all(isinstance(id, uuid.UUID) for id in result_ids)

        # Verify all stored
        stmt = select(DocumentEmbedding).where(DocumentEmbedding.session_id == session_id)
        result = await async_session.execute(stmt)
        stored = result.scalars().all()

        assert len(stored) == 3

    @pytest.mark.asyncio
    async def test_store_empty_batch(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test storing empty batch raises error."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session

        with pytest.raises(VectorStoreError) as exc_info:
            await repo.store_batch(session_id=session_id, documents=[])

        assert "empty" in str(exc_info.value).lower()


class TestVectorStoreRepositorySimilaritySearch:
    """Test similarity search functionality."""

    @pytest_asyncio.fixture
    async def setup_test_vectors(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> tuple[uuid.UUID, list[uuid.UUID]]:
        """Set up test vectors for similarity search."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session

        # Create known vectors
        base_vector = [1.0] * 384
        similar_vector = [0.99] * 384  # Very similar
        different_vector = [-1.0] * 384  # Very different

        documents = [
            {"content": "Base document", "embedding": base_vector, "metadata": {"type": "base"}},
            {
                "content": "Similar document",
                "embedding": similar_vector,
                "metadata": {"type": "similar"},
            },
            {
                "content": "Different document",
                "embedding": different_vector,
                "metadata": {"type": "different"},
            },
        ]

        doc_ids = await repo.store_batch(session_id=session_id, documents=documents)
        return session_id, doc_ids

    @pytest.mark.asyncio
    async def test_similarity_search_success(
        self, async_session: AsyncSession, setup_test_vectors: tuple[uuid.UUID, list[uuid.UUID]]
    ) -> None:
        """Test successful similarity search."""
        repo = VectorStoreRepository(db=async_session)
        session_id, _ = setup_test_vectors

        # Search with base vector
        query_vector = [1.0] * 384
        results = await repo.similarity_search(
            session_id=session_id, query_vector=query_vector, top_k=3
        )

        assert len(results) == 3
        assert all(isinstance(r, SearchResult) for r in results)

        # Results should be ordered by similarity (descending)
        assert results[0].similarity_score >= results[1].similarity_score
        assert results[1].similarity_score >= results[2].similarity_score

        # Most similar should be base or similar document
        assert "document" in results[0].content.lower()

        # Different document should have lowest similarity
        assert results[2].content == "Different document"

    @pytest.mark.asyncio
    async def test_similarity_search_with_limit(
        self, async_session: AsyncSession, setup_test_vectors: tuple[uuid.UUID, list[uuid.UUID]]
    ) -> None:
        """Test similarity search with top_k limit."""
        repo = VectorStoreRepository(db=async_session)
        session_id, _ = setup_test_vectors

        query_vector = [1.0] * 384
        results = await repo.similarity_search(
            session_id=session_id, query_vector=query_vector, top_k=2
        )

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_similarity_search_with_threshold(
        self, async_session: AsyncSession, setup_test_vectors: tuple[uuid.UUID, list[uuid.UUID]]
    ) -> None:
        """Test similarity search with similarity threshold."""
        repo = VectorStoreRepository(db=async_session)
        session_id, _ = setup_test_vectors

        query_vector = [1.0] * 384
        results = await repo.similarity_search(
            session_id=session_id,
            query_vector=query_vector,
            top_k=10,
            similarity_threshold=0.95,  # High threshold
        )

        # Only highly similar documents should be returned
        assert len(results) <= 3
        assert all(r.similarity_score >= 0.95 for r in results)

    @pytest.mark.asyncio
    async def test_similarity_search_empty_results(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test similarity search with no matching documents."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session  # Non-existent session

        query_vector = [1.0] * 384
        results = await repo.similarity_search(
            session_id=session_id, query_vector=query_vector, top_k=5
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_similarity_search_wrong_dimension(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test similarity search with wrong vector dimension."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session

        query_vector = [1.0] * 256  # Wrong dimension

        with pytest.raises(VectorStoreError) as exc_info:
            await repo.similarity_search(session_id=session_id, query_vector=query_vector, top_k=5)

        assert "dimension" in str(exc_info.value).lower()


class TestVectorStoreRepositoryDelete:
    """Test vector deletion."""

    @pytest.mark.asyncio
    async def test_delete_by_session_id(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test deleting all vectors for a session."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session

        # Store some vectors
        documents = [
            {
                "content": f"Document {i}",
                "embedding": np.random.randn(384).tolist(),
                "metadata": {"index": i},
            }
            for i in range(5)
        ]

        await repo.store_batch(session_id=session_id, documents=documents)

        # Delete all for session
        deleted_count = await repo.delete_by_session(session_id=session_id)

        assert deleted_count == 5

        # Verify deleted
        stmt = select(DocumentEmbedding).where(DocumentEmbedding.session_id == session_id)
        result = await async_session.execute(stmt)
        remaining = result.scalars().all()

        assert len(remaining) == 0

    @pytest.mark.asyncio
    async def test_delete_single_vector(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test deleting a single vector by ID."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session

        # Store a vector
        doc_id = await repo.store_vector(
            session_id=session_id, content="Test document", embedding=np.random.randn(384).tolist()
        )

        # Delete it
        success = await repo.delete_vector(vector_id=doc_id)

        assert success is True

        # Verify deleted
        stmt = select(DocumentEmbedding).where(DocumentEmbedding.id == doc_id)
        result = await async_session.scalar(stmt)

        assert result is None


class TestVectorStoreRepositoryRetrieve:
    """Test vector retrieval."""

    @pytest.mark.asyncio
    async def test_get_vector_by_id(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test retrieving a vector by its ID."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session
        content = "Test document"
        embedding = np.random.randn(384).tolist()
        metadata = {"key": "value"}

        # Store vector
        doc_id = await repo.store_vector(
            session_id=session_id, content=content, embedding=embedding, metadata=metadata
        )

        # Retrieve it
        result = await repo.get_vector(vector_id=doc_id)

        assert result is not None
        assert result["content"] == content
        assert len(result["embedding"]) == 384
        assert result["metadata"] == metadata

    @pytest.mark.asyncio
    async def test_get_nonexistent_vector(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test retrieving a nonexistent vector."""
        repo = VectorStoreRepository(db=async_session)
        fake_id = uuid.uuid4()

        result = await repo.get_vector(vector_id=fake_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_count_vectors_by_session(
        self, async_session: AsyncSession, create_research_session: uuid.UUID
    ) -> None:
        """Test counting vectors for a session."""
        repo = VectorStoreRepository(db=async_session)
        session_id = create_research_session

        # Store multiple vectors
        documents = [
            {"content": f"Doc {i}", "embedding": np.random.randn(384).tolist(), "metadata": {}}
            for i in range(7)
        ]

        await repo.store_batch(session_id=session_id, documents=documents)

        # Count them
        count = await repo.count_by_session(session_id=session_id)

        assert count == 7


class TestVectorStoreRepositorySearchResult:
    """Test SearchResult dataclass."""

    def test_search_result_creation(self) -> None:
        """Test creating SearchResult instance."""
        result = SearchResult(
            id=uuid.uuid4(),
            content="Test content",
            embedding=[1.0] * 384,
            metadata={"test": True},
            similarity_score=0.95,
        )

        assert result.similarity_score == 0.95
        assert result.content == "Test content"
        assert len(result.embedding) == 384

    def test_search_result_ordering(self) -> None:
        """Test SearchResult can be sorted by similarity."""
        results = [
            SearchResult(
                id=uuid.uuid4(),
                content=f"Doc {i}",
                embedding=[],
                metadata={},
                similarity_score=score,
            )
            for i, score in enumerate([0.7, 0.9, 0.8])
        ]

        sorted_results = sorted(results, key=lambda x: x.similarity_score, reverse=True)

        assert sorted_results[0].similarity_score == 0.9
        assert sorted_results[1].similarity_score == 0.8
        assert sorted_results[2].similarity_score == 0.7
