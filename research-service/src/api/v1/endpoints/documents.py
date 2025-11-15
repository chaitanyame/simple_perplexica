"""Document management endpoints.

Provides API routes for:
- Document upload (PDF, Word, Excel)
- Document query (RAG-based Q&A)
- Document listing
- Document deletion
"""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.database.session import get_db
from src.services.document import (
    DocumentService,
    DocumentServiceError,
)
from src.services.document.dockling_processor import DocklingProcessor
from src.services.embedding.embedding_service import EmbeddingService
from src.services.llm.langfuse_tracer import LangfuseTracer
from src.services.llm.openrouter_client import OpenRouterClient
from ..schemas import (
    DocumentDeleteResponse,
    DocumentListResponse,
    DocumentQueryRequest,
    DocumentQueryResponse,
    DocumentUploadResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentService:
    """Get DocumentService instance with dependencies.

    Args:
        db: Database session

    Returns:
        Configured DocumentService
    """
    embedding_service = EmbeddingService()
    document_processor = DocklingProcessor()

    return DocumentService(
        db=db,
        embedding_service=embedding_service,
        document_processor=document_processor,
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: Annotated[UploadFile, File(description="Document file (PDF, Word, Excel, or text)")],
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    collection: Annotated[str, Form(description="Collection name for organization")] = "default",
) -> DocumentUploadResponse:
    """Upload and process a document.

    **Workflow:**
    1. Validate file type and size
    2. Extract text using Dockling
    3. Chunk text into segments
    4. Generate embeddings
    5. Store in vector database

    **Supported Formats:**
    - PDF (application/pdf)
    - Word (application/vnd.openxmlformats-officedocument.wordprocessingml.document)
    - Excel (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
    - Text (text/plain)

    **Limits:**
    - Max file size: 50MB
    - Chunk size: 1000 characters
    - Chunk overlap: 200 characters

    Args:
        file: Uploaded document file
        collection: Collection name (default: "default")
        document_service: Document service dependency

    Returns:
        DocumentUploadResponse with document_id, chunks_created, embedding_dimension

    Raises:
        HTTPException 400: Invalid file type or size
        HTTPException 500: Processing error
    """
    logger.info(
        f"📄 Uploading document: {file.filename} (type={file.content_type}, collection={collection})"
    )

    try:
        # Validate filename
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Filename is required",
            )

        # Upload and process
        result = await document_service.upload_document(
            file=file.file,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            collection=collection,
        )

        logger.info(f"✅ Document uploaded: {result.document_id} ({result.chunks_created} chunks)")

        return DocumentUploadResponse(
            document_id=result.document_id,
            filename=result.filename,
            source_type=result.source_type,
            collection=result.collection,
            chunks_created=result.chunks_created,
            embedding_dimension=384,  # all-MiniLM-L6-v2 dimension
            status=result.status,
            message=result.message,
        )

    except DocumentServiceError as e:
        logger.error(f"Document upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during upload: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Upload failed: {str(e)}",
        ) from e


@router.post("/query", response_model=DocumentQueryResponse)
async def query_documents(
    request: DocumentQueryRequest,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentQueryResponse:
    """Query uploaded documents for information.

    **Workflow:**
    1. Generate query embedding
    2. Search vector database for similar chunks
    3. Filter by collection and similarity threshold
    4. Generate answer using LLM with retrieved context
    5. Return answer with source citations

    **Parameters:**
    - `query`: Natural language question
    - `collection`: Collection to search (default: "default")
    - `top_k`: Number of chunks to retrieve (5-50, default: 10)
    - `similarity_threshold`: Minimum similarity (0.0-1.0, default: 0.3)

    Args:
        request: Query request with parameters
        document_service: Document service dependency
        db: Database session

    Returns:
        DocumentQueryResponse with answer, sources, execution_time

    Raises:
        HTTPException 404: No documents found in collection
        HTTPException 500: Query processing error
    """
    import time

    start_time = time.time()
    logger.info(
        f"🔍 Querying documents: query='{request.query}', "
        f"collection={request.collection}, top_k={request.top_k}"
    )

    try:
        # Retrieve relevant chunks
        chunks = await document_service.query_documents(
            query=request.query,
            collection=request.collection,
            top_k=request.top_k,
            similarity_threshold=request.similarity_threshold,
        )

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No relevant documents found in collection '{request.collection}'",
            )

        # Generate answer using LLM
        gen = await _generate_answer(
            query=request.query,
            chunks=chunks,
        )
        answer = str(gen.get("content", ""))
        trace_url = gen.get("trace_url")

        execution_time = time.time() - start_time
        logger.info(f"✅ Query completed in {execution_time:.2f}s with {len(chunks)} sources")

        return DocumentQueryResponse(
            query=request.query,
            answer=answer,
            sources=chunks,
            total_chunks_found=len(chunks),
            chunks_used=len(chunks),
            execution_time=execution_time,
            trace_url=trace_url,
        )

    except HTTPException:
        raise
    except DocumentServiceError as e:
        logger.error(f"Document query failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {str(e)}",
        ) from e


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    collection: str | None = None,
    document_service: Annotated[DocumentService, Depends(get_document_service)] = None,
) -> DocumentListResponse:
    """List all uploaded documents.

    **Filters:**
    - `collection`: Filter by collection name (optional)

    **Returns:**
    - Document metadata (filename, type, collection, chunk count)
    - Creation and access timestamps
    - Access count statistics

    Args:
        collection: Optional collection filter
        document_service: Document service dependency

    Returns:
        DocumentListResponse with list of documents and total count

    Raises:
        HTTPException 500: List operation error
    """
    logger.info(f"📋 Listing documents (collection={collection or 'all'})")

    try:
        documents = await document_service.list_documents(collection=collection)

        logger.info(f"Found {len(documents)} documents")

        return DocumentListResponse(
            documents=documents,
            total_count=len(documents),
            collection=collection,
        )

    except DocumentServiceError as e:
        logger.error(f"Document listing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during listing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Listing failed: {str(e)}",
        ) from e


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: uuid.UUID,
    document_service: Annotated[DocumentService, Depends(get_document_service)],
) -> DocumentDeleteResponse:
    """Delete a document and all its chunks.

    **Warning:** This operation is irreversible!

    Args:
        document_id: UUID of document to delete
        document_service: Document service dependency

    Returns:
        DocumentDeleteResponse with deletion confirmation

    Raises:
        HTTPException 404: Document not found
        HTTPException 500: Deletion error
    """
    logger.info(f"🗑️ Deleting document: {document_id}")

    try:
        chunks_deleted = await document_service.delete_document(document_id)

        logger.info(f"✅ Deleted document {document_id} ({chunks_deleted} chunks)")

        return DocumentDeleteResponse(
            document_id=document_id,
            status="success",
            message=f"Successfully deleted document and {chunks_deleted} chunks",
            chunks_deleted=chunks_deleted,
        )

    except DocumentServiceError as e:
        logger.error(f"Document deletion failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
    except Exception as e:
        logger.error(f"Unexpected error during deletion: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Deletion failed: {str(e)}",
        ) from e


async def _generate_answer(
    query: str,
    chunks: list[dict],
) -> dict[str, str | None]:
    """Generate answer using LLM with retrieved context.

    Args:
        query: User query
        chunks: Retrieved document chunks

    Returns:
        Generated answer
    """
    # Initialize Langfuse tracer
    tracer = LangfuseTracer(
        public_key=settings.LANGFUSE_PUBLIC_KEY,
        secret_key=settings.LANGFUSE_SECRET_KEY,
        host=settings.LANGFUSE_BASE_URL,
    )
    # Prepare context from chunks
    context_parts = []
    for idx, chunk in enumerate(chunks, 1):
        filename = chunk.get("metadata", {}).get("filename", "unknown")
        context_parts.append(f"[{idx}] From '{filename}':\n{chunk['content']}\n")

    context = "\n".join(context_parts)

    # Create prompt
    prompt = f"""Based on the following document excerpts, answer the user's question.

**Context:**
{context}

**Question:** {query}

**Instructions:**
- Provide a clear, comprehensive answer based on the context
- Cite sources using [1], [2], etc. references
- If information is insufficient, state what's missing
- Be precise and factual

**Answer:**"""

    # Generate answer with LLM - Use Gemini 2.0 Flash Lite (less rate limiting)
    llm_client = OpenRouterClient(
        api_key=settings.OPENROUTER_API_KEY,
        model="google/gemini-2.0-flash-lite-001",  # Lite version with good context window
        tracer=tracer,
    )

    with tracer.trace_context(
        name="documents_query",
        metadata={"chunks": len(chunks)},
    ) as trace:
        response = await llm_client.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temperature for factual answers
            max_tokens=1000,
        )

    # Flush traces to Langfuse before returning
    tracer.flush()

    return {
        "content": response.get("content", "Unable to generate answer"),
        "trace_url": tracer.get_trace_url(trace),
    }
