"""Document service for handling file uploads, extraction, and storage.

This module provides DocumentService for:
- File upload and validation
- Document extraction (PDF, Word, Excel) using Dockling
- Text chunking for optimal retrieval
- Embedding generation using Sentence-Transformers
- Vector storage in PostgreSQL + pgvector
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO

import structlog
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import RAGDocument, SessionDocument
from ..embedding.embedding_service import EmbeddingService
from .dockling_processor import DocklingProcessor

logger = structlog.get_logger(__name__)


class DocumentServiceError(Exception):
    """Exception raised for document service errors."""

    pass


@dataclass
class DocumentChunk:
    """Represents a chunk of document text.

    Attributes:
        content: Text content
        metadata: Chunk metadata (page, section, etc.)
    """

    content: str
    metadata: dict[str, Any]


@dataclass
class DocumentUploadResult:
    """Result of document upload operation.

    Attributes:
        document_id: UUID of stored document
        filename: Original filename
        source_type: Document type
        collection: Collection name
        chunks_created: Number of chunks
        status: Upload status
        message: Status message
    """

    document_id: uuid.UUID
    filename: str
    source_type: str
    collection: str
    chunks_created: int
    status: str
    message: str


class DocumentService:
    """Service for document upload, extraction, and storage.

    Handles the complete pipeline:
    1. File validation
    2. Text extraction (Dockling)
    3. Text chunking
    4. Embedding generation
    5. Vector storage

    Example:
        >>> service = DocumentService(
        ...     db=session,
        ...     embedding_service=embedding_svc,
        ...     document_processor=processor
        ... )
        >>> result = await service.upload_document(
        ...     file=uploaded_file,
        ...     filename="report.pdf",
        ...     collection="research"
        ... )
    """

    # Supported file types
    SUPPORTED_TYPES = {
        "application/pdf": "pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "word",
        "application/msword": "word",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "excel",
        "application/vnd.ms-excel": "excel",
        "text/plain": "text",
    }

    # Max file size: 50MB
    MAX_FILE_SIZE = 50 * 1024 * 1024

    # Chunking parameters
    CHUNK_SIZE = 1000  # characters per chunk
    CHUNK_OVERLAP = 200  # overlap between chunks

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService,
        document_processor: DocklingProcessor,
    ) -> None:
        """Initialize document service.

        Args:
            db: Database session
            embedding_service: Embedding generation service
            document_processor: Document extraction processor
        """
        self.db = db
        self.embedding_service = embedding_service
        self.document_processor = document_processor

    async def upload_document(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        collection: str = "default",
    ) -> DocumentUploadResult:
        """Upload and process a document.

        Args:
            file: File binary stream
            filename: Original filename
            content_type: MIME type
            collection: Collection name for organization

        Returns:
            DocumentUploadResult with upload details

        Raises:
            DocumentServiceError: If upload fails
        """
        logger.info(f"📄 Uploading document: {filename} (type={content_type}, collection={collection})")

        try:
            # Validate file type
            source_type = self._validate_file_type(content_type)

            # Read file content
            content = file.read()
            if len(content) > self.MAX_FILE_SIZE:
                raise DocumentServiceError(
                    f"File too large: {len(content)} bytes (max {self.MAX_FILE_SIZE})"
                )

            # Calculate content hash for deduplication
            content_hash = hashlib.sha256(content).hexdigest()

            # Check if document already exists
            existing_doc = await self._get_document_by_hash(content_hash)
            if existing_doc:
                logger.info(f"Document already exists: {existing_doc.id}")
                # Get chunk count
                chunks_count = await self._count_document_chunks(existing_doc.id)
                return DocumentUploadResult(
                    document_id=existing_doc.id,
                    filename=filename,
                    source_type=source_type,
                    collection=collection,
                    chunks_created=chunks_count,
                    status="success",
                    message=f"Document already exists (reusing existing ID: {existing_doc.id})",
                )

            # Extract text from document
            extracted_text = await self._extract_text(content, source_type, filename)

            # Chunk text
            chunks = self._chunk_text(extracted_text)
            logger.info(f"Created {len(chunks)} chunks from document")

            # Generate embeddings for all chunks
            chunk_embeddings = await self._generate_embeddings(chunks)

            # Store document and chunks
            document_id = await self._store_document(
                content_hash=content_hash,
                source_type=source_type,
                filename=filename,
                collection=collection,
                chunks=chunks,
                embeddings=chunk_embeddings,
            )

            logger.info(f"✅ Document uploaded successfully: {document_id}")
            return DocumentUploadResult(
                document_id=document_id,
                filename=filename,
                source_type=source_type,
                collection=collection,
                chunks_created=len(chunks),
                status="success",
                message=f"Successfully uploaded and processed {len(chunks)} chunks",
            )

        except DocumentServiceError:
            raise
        except Exception as e:
            logger.error(f"Document upload failed: {e}")
            raise DocumentServiceError(f"Upload failed: {str(e)}")

    async def query_documents(
        self,
        query: str,
        collection: str = "default",
        top_k: int = 10,
        similarity_threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Query documents for relevant chunks.

        Args:
            query: Search query
            collection: Collection to search
            top_k: Number of results
            similarity_threshold: Minimum similarity score

        Returns:
            List of relevant document chunks with metadata
        """
        logger.info(f"🔍 Querying documents: query='{query}', collection={collection}, top_k={top_k}")

        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.embed_text(query)

            # Search vector store
            stmt = (
                select(
                    RAGDocument.id,
                    RAGDocument.content,
                    RAGDocument.doc_metadata,
                    RAGDocument.source_type,
                    RAGDocument.source_url,
                    RAGDocument.created_at,
                    (1 - RAGDocument.embedding.cosine_distance(query_embedding)).label("similarity"),
                )
                .where(RAGDocument.doc_metadata["collection"].as_string() == collection)
                .order_by((1 - RAGDocument.embedding.cosine_distance(query_embedding)).desc())
                .limit(top_k * 2)  # Get more candidates for filtering
            )

            result = await self.db.execute(stmt)
            rows = result.all()

            # Filter by similarity threshold and limit
            chunks = []
            for row in rows:
                if row.similarity >= similarity_threshold:
                    chunks.append({
                        "document_id": str(row.id),
                        "content": row.content,
                        "metadata": row.doc_metadata or {},
                        "source_type": row.source_type,
                        "source_url": row.source_url,
                        "similarity": float(row.similarity),
                        "created_at": row.created_at.isoformat(),
                    })
                    if len(chunks) >= top_k:
                        break

            logger.info(f"Found {len(chunks)} relevant chunks (threshold={similarity_threshold})")
            return chunks

        except Exception as e:
            logger.error(f"Document query failed: {e}")
            raise DocumentServiceError(f"Query failed: {str(e)}")

    async def list_documents(
        self, collection: str | None = None
    ) -> list[dict[str, Any]]:
        """List all uploaded documents.

        Args:
            collection: Optional collection filter

        Returns:
            List of document metadata
        """
        try:
            # Query documents with chunk counts
            stmt = (
                select(
                    RAGDocument.id,
                    RAGDocument.doc_metadata,
                    RAGDocument.source_type,
                    RAGDocument.created_at,
                    RAGDocument.last_accessed,
                    RAGDocument.access_count,
                )
                .order_by(RAGDocument.created_at.desc())
            )

            if collection:
                stmt = stmt.where(RAGDocument.doc_metadata["collection"].as_string() == collection)

            result = await self.db.execute(stmt)
            rows = result.all()

            documents = []
            for row in rows:
                metadata = row.doc_metadata or {}
                documents.append({
                    "document_id": str(row.id),
                    "filename": metadata.get("filename", "unknown"),
                    "source_type": row.source_type,
                    "collection": metadata.get("collection", "default"),
                    "chunks_count": metadata.get("chunks_count", 1),
                    "created_at": row.created_at,
                    "last_accessed": row.last_accessed,
                    "access_count": row.access_count,
                })

            logger.info(f"Listed {len(documents)} documents")
            return documents

        except Exception as e:
            logger.error(f"List documents failed: {e}")
            raise DocumentServiceError(f"List failed: {str(e)}")

    async def delete_document(self, document_id: uuid.UUID) -> int:
        """Delete a document and all its chunks.

        Args:
            document_id: Document UUID to delete

        Returns:
            Number of chunks deleted

        Raises:
            DocumentServiceError: If deletion fails
        """
        try:
            # Count chunks before deletion
            count_stmt = select(func.count()).select_from(RAGDocument).where(
                RAGDocument.doc_metadata["parent_id"].as_string() == str(document_id)
            )
            count_result = await self.db.execute(count_stmt)
            chunks_count = count_result.scalar() or 0

            # Delete all chunks belonging to this document
            delete_stmt = delete(RAGDocument).where(
                RAGDocument.doc_metadata["parent_id"].as_string() == str(document_id)
            )
            await self.db.execute(delete_stmt)

            # Delete the parent document itself
            delete_parent = delete(RAGDocument).where(RAGDocument.id == document_id)
            await self.db.execute(delete_parent)

            await self.db.commit()

            logger.info(f"Deleted document {document_id} ({chunks_count} chunks)")
            return chunks_count + 1  # Include parent

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Document deletion failed: {e}")
            raise DocumentServiceError(f"Deletion failed: {str(e)}")

    def _validate_file_type(self, content_type: str) -> str:
        """Validate file type and return source type.

        Args:
            content_type: MIME type

        Returns:
            Source type (pdf/word/excel/text)

        Raises:
            DocumentServiceError: If type not supported
        """
        source_type = self.SUPPORTED_TYPES.get(content_type)
        if not source_type:
            raise DocumentServiceError(
                f"Unsupported file type: {content_type}. "
                f"Supported: {', '.join(self.SUPPORTED_TYPES.keys())}"
            )
        return source_type

    async def _extract_text(self, content: bytes, source_type: str, filename: str) -> str:
        """Extract text from document content.

        Args:
            content: File binary content
            source_type: Document type
            filename: Original filename

        Returns:
            Extracted text

        Raises:
            DocumentServiceError: If extraction fails
        """
        try:
            if source_type == "text":
                return content.decode("utf-8")

            # Use Dockling for PDF, Word, Excel
            extracted = await self.document_processor.extract_text(content, source_type)
            if not extracted or len(extracted.strip()) < 10:
                raise DocumentServiceError("Extracted text is empty or too short")

            return extracted

        except Exception as e:
            raise DocumentServiceError(f"Text extraction failed: {str(e)}")

    def _chunk_text(self, text: str) -> list[DocumentChunk]:
        """Split text into overlapping chunks.

        Args:
            text: Full document text

        Returns:
            List of document chunks
        """
        chunks = []
        start = 0
        chunk_id = 0

        while start < len(text):
            end = start + self.CHUNK_SIZE
            chunk_text = text[start:end]

            # Try to end on sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind(".")
                last_newline = chunk_text.rfind("\n")
                boundary = max(last_period, last_newline)
                if boundary > self.CHUNK_SIZE * 0.5:  # At least 50% of chunk
                    end = start + boundary + 1
                    chunk_text = text[start:end]

            chunks.append(
                DocumentChunk(
                    content=chunk_text.strip(),
                    metadata={"chunk_id": chunk_id, "start": start, "end": end},
                )
            )

            chunk_id += 1
            start = end - self.CHUNK_OVERLAP  # Overlap

        return chunks

    async def _generate_embeddings(self, chunks: list[DocumentChunk]) -> list[list[float]]:
        """Generate embeddings for document chunks.

        Args:
            chunks: List of document chunks

        Returns:
            List of embedding vectors
        """
        texts = [chunk.content for chunk in chunks]
        embeddings = await self.embedding_service.embed_batch(texts)
        return embeddings

    async def _store_document(
        self,
        content_hash: str,
        source_type: str,
        filename: str,
        collection: str,
        chunks: list[DocumentChunk],
        embeddings: list[list[float]],
    ) -> uuid.UUID:
        """Store document and all chunks in database.

        Args:
            content_hash: Content hash for deduplication
            source_type: Document type
            filename: Original filename
            collection: Collection name
            chunks: Document chunks
            embeddings: Chunk embeddings

        Returns:
            Document UUID
        """
        parent_id = uuid.uuid4()

        # Store each chunk as a separate RAGDocument
        for chunk, embedding in zip(chunks, embeddings):
            # Create unique hash for each chunk (stays within 64 char limit)
            chunk_hash = hashlib.sha256(
                f"{content_hash}_{chunk.metadata['chunk_id']}".encode()
            ).hexdigest()
            
            doc = RAGDocument(
                content=chunk.content,
                content_hash=chunk_hash,
                source_type=source_type,
                doc_metadata={
                    "parent_id": str(parent_id),
                    "filename": filename,
                    "collection": collection,
                    "chunk_id": chunk.metadata["chunk_id"],
                    "chunks_count": len(chunks),
                },
                embedding=embedding,
            )
            self.db.add(doc)

        await self.db.commit()
        return parent_id

    async def _get_document_by_hash(self, content_hash: str) -> RAGDocument | None:
        """Get document by content hash.

        Args:
            content_hash: Content hash

        Returns:
            Document if found, None otherwise
        """
        stmt = select(RAGDocument).where(RAGDocument.content_hash == content_hash).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _count_document_chunks(self, document_id: uuid.UUID) -> int:
        """Count chunks for a document.

        Args:
            document_id: Parent document ID

        Returns:
            Number of chunks
        """
        stmt = select(func.count()).select_from(RAGDocument).where(
            RAGDocument.doc_metadata["parent_id"].as_string() == str(document_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar() or 0
