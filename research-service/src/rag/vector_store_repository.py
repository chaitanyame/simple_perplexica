"""Vector store repository using pgvector for similarity search.

This module provides vector storage and similarity search functionality
using PostgreSQL pgvector extension.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.models import DocumentEmbedding


class VectorStoreError(Exception):
    """Exception raised for vector store-related errors."""

    pass


@dataclass
class SearchResult:
    """Search result with similarity score."""

    id: uuid.UUID
    content: str
    embedding: list[float]
    metadata: dict[str, Any]
    similarity_score: float


class VectorStoreRepository:
    """Repository for vector storage and similarity search.

    Attributes:
        db: AsyncSession for database operations
        dimension: Vector dimensionality (384 for all-MiniLM-L6-v2)

    Example:
        >>> repo = VectorStoreRepository(db=session)
        >>> doc_id = await repo.store_vector(
        ...     session_id=uuid.uuid4(),
        ...     content="AI research paper",
        ...     embedding=[0.1, 0.2, ..., 0.9]
        ... )
    """

    def __init__(self, db: AsyncSession, dimension: int = 384) -> None:
        """Initialize vector store repository.

        Args:
            db: AsyncSession for database operations
            dimension: Vector dimensionality (default: 384)
        """
        self.db = db
        self.dimension = dimension

    async def store_vector(
        self,
        session_id: uuid.UUID,
        content: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None
    ) -> uuid.UUID:
        """Store a single vector in the database.

        Args:
            session_id: Research session UUID
            content: Text content associated with the vector
            embedding: Vector embedding (384-dimensional)
            metadata: Optional metadata dictionary

        Returns:
            UUID of the stored document

        Raises:
            VectorStoreError: If content is empty or embedding dimension is wrong
        """
        # Validate input
        if not content or not content.strip():
            raise VectorStoreError("Content cannot be empty")

        if len(embedding) != self.dimension:
            raise VectorStoreError(
                f"Embedding dimension must be {self.dimension}, got {len(embedding)}"
            )

        try:
            # Create document embedding
            doc_embedding = DocumentEmbedding(
                session_id=session_id,
                content=content.strip(),
                embedding=embedding,
                doc_metadata=metadata or {}
            )

            self.db.add(doc_embedding)
            await self.db.commit()
            await self.db.refresh(doc_embedding)

            return doc_embedding.id

        except Exception as e:
            await self.db.rollback()
            raise VectorStoreError(f"Failed to store vector: {e}") from e

    async def store_batch(
        self,
        session_id: uuid.UUID,
        documents: list[dict[str, Any]]
    ) -> list[uuid.UUID]:
        """Store multiple vectors in a batch.

        Args:
            session_id: Research session UUID
            documents: List of documents with 'content', 'embedding', and optional 'metadata'

        Returns:
            List of UUIDs for stored documents

        Raises:
            VectorStoreError: If documents list is empty or validation fails
        """
        if not documents:
            raise VectorStoreError("Documents list cannot be empty")

        try:
            doc_embeddings = []

            for doc in documents:
                # Validate each document
                content = doc.get("content", "")
                if not content or not content.strip():
                    raise VectorStoreError("All documents must have non-empty content")

                embedding = doc.get("embedding", [])
                if len(embedding) != self.dimension:
                    raise VectorStoreError(
                        f"All embeddings must have dimension {self.dimension}"
                    )

                doc_embedding = DocumentEmbedding(
                    session_id=session_id,
                    content=content.strip(),
                    embedding=embedding,
                    doc_metadata=doc.get("metadata", {})
                )
                doc_embeddings.append(doc_embedding)

            # Bulk insert
            self.db.add_all(doc_embeddings)
            await self.db.commit()

            # Refresh to get IDs
            for doc_embedding in doc_embeddings:
                await self.db.refresh(doc_embedding)

            return [doc_embedding.id for doc_embedding in doc_embeddings]

        except VectorStoreError:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            raise VectorStoreError(f"Failed to store batch: {e}") from e

    async def similarity_search(
        self,
        session_id: uuid.UUID,
        query_vector: list[float],
        top_k: int = 10,
        similarity_threshold: float | None = None
    ) -> list[SearchResult]:
        """Perform cosine similarity search.

        Args:
            session_id: Research session UUID to search within
            query_vector: Query embedding vector
            top_k: Number of top results to return
            similarity_threshold: Optional minimum similarity score (0-1)

        Returns:
            List of SearchResult objects ordered by similarity

        Raises:
            VectorStoreError: If query vector dimension is wrong
        """
        if len(query_vector) != self.dimension:
            raise VectorStoreError(
                f"Query vector dimension must be {self.dimension}, got {len(query_vector)}"
            )

        try:
            # Calculate cosine similarity (1 - cosine distance)
            # pgvector's cosine_distance returns 1 - cosine_similarity
            similarity = 1 - DocumentEmbedding.embedding.cosine_distance(query_vector)

            # Build query
            stmt = (
                select(
                    DocumentEmbedding.id,
                    DocumentEmbedding.content,
                    DocumentEmbedding.embedding,
                    DocumentEmbedding.doc_metadata,
                    similarity.label("similarity_score")
                )
                .where(DocumentEmbedding.session_id == session_id)
                .order_by(similarity.desc())
                .limit(top_k)
            )

            # Apply similarity threshold if provided
            if similarity_threshold is not None:
                stmt = stmt.where(similarity >= similarity_threshold)

            # Execute query
            result = await self.db.execute(stmt)
            rows = result.all()

            # Convert to SearchResult objects
            return [
                SearchResult(
                    id=row.id,
                    content=row.content,
                    embedding=row.embedding,
                    metadata=row.doc_metadata or {},
                    similarity_score=float(row.similarity_score)
                )
                for row in rows
            ]

        except VectorStoreError:
            raise
        except Exception as e:
            raise VectorStoreError(f"Failed to perform similarity search: {e}") from e

    async def delete_by_session(self, session_id: uuid.UUID) -> int:
        """Delete all vectors for a session.

        Args:
            session_id: Research session UUID

        Returns:
            Number of documents deleted
        """
        try:
            stmt = delete(DocumentEmbedding).where(
                DocumentEmbedding.session_id == session_id
            )

            result = await self.db.execute(stmt)
            await self.db.commit()

            return result.rowcount or 0

        except Exception as e:
            await self.db.rollback()
            raise VectorStoreError(f"Failed to delete vectors: {e}") from e

    async def delete_vector(self, vector_id: uuid.UUID) -> bool:
        """Delete a single vector by ID.

        Args:
            vector_id: Document embedding UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            stmt = delete(DocumentEmbedding).where(
                DocumentEmbedding.id == vector_id
            )

            result = await self.db.execute(stmt)
            await self.db.commit()

            return (result.rowcount or 0) > 0

        except Exception as e:
            await self.db.rollback()
            raise VectorStoreError(f"Failed to delete vector: {e}") from e

    async def get_vector(
        self, vector_id: uuid.UUID
    ) -> dict[str, Any] | None:
        """Retrieve a vector by its ID.

        Args:
            vector_id: Document embedding UUID

        Returns:
            Dictionary with vector data or None if not found
        """
        try:
            stmt = select(DocumentEmbedding).where(
                DocumentEmbedding.id == vector_id
            )

            result = await self.db.execute(stmt)
            doc = result.scalar_one_or_none()

            if doc is None:
                return None

            return {
                "id": doc.id,
                "session_id": doc.session_id,
                "content": doc.content,
                "embedding": doc.embedding,
                "metadata": doc.doc_metadata or {},
                "created_at": doc.created_at
            }

        except Exception as e:
            raise VectorStoreError(f"Failed to retrieve vector: {e}") from e

    async def count_by_session(self, session_id: uuid.UUID) -> int:
        """Count vectors for a session.

        Args:
            session_id: Research session UUID

        Returns:
            Number of vectors in the session
        """
        try:
            stmt = select(func.count()).select_from(DocumentEmbedding).where(
                DocumentEmbedding.session_id == session_id
            )

            result = await self.db.execute(stmt)
            count = result.scalar_one()

            return count

        except Exception as e:
            raise VectorStoreError(f"Failed to count vectors: {e}") from e
