"""Tests for database models."""

import uuid
from datetime import datetime

import pytest
from sqlalchemy import select

from src.database.models import RAGDocument, ResearchSession, SessionDocument


@pytest.mark.asyncio
async def test_research_session_creation(async_session):
    """Test creating a research session."""
    session = ResearchSession(
        query="What is machine learning?",
        mode="search",
        status="pending",
    )

    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)

    assert session.id is not None
    assert isinstance(session.id, uuid.UUID)
    assert session.query == "What is machine learning?"
    assert session.mode == "search"
    assert session.status == "pending"
    assert session.result is None
    assert session.error_message is None
    assert session.execution_time_seconds is None
    assert isinstance(session.created_at, datetime)
    assert session.completed_at is None


@pytest.mark.asyncio
async def test_research_session_with_result(async_session):
    """Test research session with result data."""
    result_data = {
        "answer": "Machine learning is...",
        "sources": ["https://example.com"],
    }

    session = ResearchSession(
        query="What is ML?",
        mode="research",
        status="completed",
        result=result_data,
        execution_time_seconds=45.2,
        completed_at=datetime.utcnow(),
    )

    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)

    assert session.result == result_data
    assert session.execution_time_seconds == 45.2
    assert session.completed_at is not None


@pytest.mark.asyncio
async def test_rag_document_creation(async_session):
    """Test creating a RAG document."""
    import hashlib

    content = "This is test content for RAG retrieval."
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    embedding = [0.1] * 384  # 384-dimensional vector

    document = RAGDocument(
        content=content,
        content_hash=content_hash,
        source_url="https://example.com/article",
        source_type="web",
        metadata={"title": "Test Article", "author": "Test Author"},
        embedding=embedding,
        token_count=10,
    )

    async_session.add(document)
    await async_session.commit()
    await async_session.refresh(document)

    assert document.id is not None
    assert document.content == content
    assert document.content_hash == content_hash
    assert document.source_url == "https://example.com/article"
    assert document.source_type == "web"
    assert document.metadata["title"] == "Test Article"
    assert document.token_count == 10
    assert document.access_count == 0
    assert document.last_accessed is None


@pytest.mark.asyncio
async def test_unique_content_hash(async_session):
    """Test that content_hash is unique constraint."""
    import hashlib

    content = "Unique content test"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    embedding = [0.1] * 384

    # Create first document
    doc1 = RAGDocument(
        content=content,
        content_hash=content_hash,
        source_type="web",
        embedding=embedding,
    )
    async_session.add(doc1)
    await async_session.commit()

    # Try to create second document with same hash
    doc2 = RAGDocument(
        content=content,
        content_hash=content_hash,
        source_type="web",
        embedding=embedding,
    )
    async_session.add(doc2)

    with pytest.raises(Exception):  # IntegrityError
        await async_session.commit()


@pytest.mark.asyncio
async def test_session_document_association(async_session):
    """Test association between session and document."""
    import hashlib

    # Create session
    session = ResearchSession(
        query="Test query",
        mode="search",
        status="pending",
    )
    async_session.add(session)

    # Create document
    content = "Test document content"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    embedding = [0.1] * 384

    document = RAGDocument(
        content=content,
        content_hash=content_hash,
        source_type="web",
        embedding=embedding,
    )
    async_session.add(document)

    await async_session.commit()
    await async_session.refresh(session)
    await async_session.refresh(document)

    # Create association
    session_doc = SessionDocument(
        session_id=session.id,
        document_id=document.id,
        relevance_score=0.95,
        used_in_synthesis=True,
    )
    async_session.add(session_doc)
    await async_session.commit()
    await async_session.refresh(session_doc)

    assert session_doc.id is not None
    assert session_doc.session_id == session.id
    assert session_doc.document_id == document.id
    assert session_doc.relevance_score == 0.95
    assert session_doc.used_in_synthesis is True


@pytest.mark.asyncio
async def test_session_document_relationship(async_session):
    """Test relationship loading between session and documents."""
    import hashlib

    # Create session
    session = ResearchSession(
        query="Test query",
        mode="search",
        status="pending",
    )
    async_session.add(session)

    # Create documents
    documents = []
    for i in range(3):
        content = f"Document {i} content"
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        embedding = [0.1 * (i + 1)] * 384

        doc = RAGDocument(
            content=content,
            content_hash=content_hash,
            source_type="web",
            embedding=embedding,
        )
        async_session.add(doc)
        documents.append(doc)

    await async_session.commit()

    # Create associations
    for doc in documents:
        session_doc = SessionDocument(
            session_id=session.id,
            document_id=doc.id,
            relevance_score=0.8,
        )
        async_session.add(session_doc)

    await async_session.commit()

    # Query session with documents using selectinload for async
    from sqlalchemy.orm import selectinload

    result = await async_session.execute(
        select(ResearchSession)
        .options(selectinload(ResearchSession.documents))
        .where(ResearchSession.id == session.id)
    )
    loaded_session = result.scalar_one()

    # Access relationship (loaded eagerly with selectinload)
    assert len(loaded_session.documents) == 3


@pytest.mark.asyncio
async def test_cascade_delete(async_session):
    """Test cascade delete on session deletion."""
    import hashlib

    # Create session
    session = ResearchSession(
        query="Test query",
        mode="search",
        status="pending",
    )
    async_session.add(session)

    # Create document
    content = "Test document"
    content_hash = hashlib.sha256(content.encode()).hexdigest()
    embedding = [0.1] * 384

    document = RAGDocument(
        content=content,
        content_hash=content_hash,
        source_type="web",
        embedding=embedding,
    )
    async_session.add(document)

    await async_session.commit()

    # Create association
    session_doc = SessionDocument(
        session_id=session.id,
        document_id=document.id,
    )
    async_session.add(session_doc)
    await async_session.commit()

    # Delete session
    await async_session.delete(session)
    await async_session.commit()

    # Check that association was also deleted
    result = await async_session.execute(
        select(SessionDocument).where(SessionDocument.session_id == session.id)
    )
    assert result.scalar_one_or_none() is None

    # But document should still exist
    result = await async_session.execute(select(RAGDocument).where(RAGDocument.id == document.id))
    assert result.scalar_one_or_none() is not None
