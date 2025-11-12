"""Pytest fixtures for semantic reranking tests."""

from __future__ import annotations

import pytest
import pytest_asyncio

from src.services.embedding.embedding_service import EmbeddingService


@pytest_asyncio.fixture
async def embedding_service():
    """Provide real embedding service for reranking tests.
    
    Uses CPU-based all-MiniLM-L6-v2 for embeddings and
    ms-marco-MiniLM-L-6-v2 cross-encoder for reranking.
    """
    service = EmbeddingService(
        model_name="all-MiniLM-L6-v2",
        reranker_model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
        device="cpu",
    )
    
    # Ensure models are loaded
    await service.embed_text("test")
    
    return service
