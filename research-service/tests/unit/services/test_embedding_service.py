"""Tests for Sentence-Transformers embedding service.

Following TDD approach:
1. RED: Write failing tests first
2. GREEN: Implement to pass tests
3. REFACTOR: Clean up code
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import numpy as np
import pytest

from src.services.embedding.embedding_service import (
    EmbeddingError,
    EmbeddingService,
)


class TestEmbeddingServiceInitialization:
    """Test embedding service initialization."""

    @pytest.fixture
    def service(self) -> EmbeddingService:
        """Create an EmbeddingService instance."""
        return EmbeddingService()

    def test_initialize_with_defaults(self, service: EmbeddingService) -> None:
        """Test initialization with default parameters."""
        assert service.model_name == "all-MiniLM-L6-v2"
        assert service.dimension == 384
        assert service.device == "cpu"

    def test_initialize_with_custom_model(self) -> None:
        """Test initialization with custom model."""
        service = EmbeddingService(model_name="paraphrase-MiniLM-L6-v2", device="cuda")

        assert service.model_name == "paraphrase-MiniLM-L6-v2"
        assert service.device == "cuda"


class TestEmbeddingServiceSingleText:
    """Test single text embedding."""

    @pytest.fixture
    def service(self) -> EmbeddingService:
        """Create an EmbeddingService instance."""
        return EmbeddingService()

    @pytest.fixture
    def mock_model(self) -> Mock:
        """Create a mock SentenceTransformer model."""
        model = Mock()
        # Return 384-dimensional vector
        model.encode.return_value = np.random.randn(384).astype(np.float32)
        return model

    @pytest.mark.asyncio
    async def test_embed_single_text_success(
        self, service: EmbeddingService, mock_model: Mock
    ) -> None:
        """Test successful single text embedding."""
        service._model = mock_model
        text = "This is a test document about artificial intelligence."
        embedding = await service.embed_text(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
        mock_model.encode.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_empty_text(self, service: EmbeddingService) -> None:
        """Test embedding empty text raises error."""
        with pytest.raises(EmbeddingError) as exc_info:
            await service.embed_text("")

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_embed_whitespace_only(self, service: EmbeddingService) -> None:
        """Test embedding whitespace-only text raises error."""
        with pytest.raises(EmbeddingError) as exc_info:
            await service.embed_text("   \n\t  ")

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_embed_very_long_text(self, service: EmbeddingService, mock_model: Mock) -> None:
        """Test embedding very long text (should truncate)."""
        service._model = mock_model
        # Create text longer than typical max length (512 tokens)
        long_text = "test " * 1000
        embedding = await service.embed_text(long_text)

        assert len(embedding) == 384
        mock_model.encode.assert_called_once()


class TestEmbeddingServiceBatchText:
    """Test batch text embedding."""

    @pytest.fixture
    def service(self) -> EmbeddingService:
        """Create an EmbeddingService instance."""
        return EmbeddingService()

    @pytest.fixture
    def mock_model(self) -> Mock:
        """Create a mock SentenceTransformer model."""
        model = Mock()
        # Return batch of 384-dimensional vectors
        model.encode.return_value = np.random.randn(3, 384).astype(np.float32)
        return model

    @pytest.mark.asyncio
    async def test_embed_batch_success(self, service: EmbeddingService, mock_model: Mock) -> None:
        """Test successful batch text embedding."""
        service._model = mock_model
        texts = [
            "First document about AI.",
            "Second document about ML.",
            "Third document about data science.",
        ]
        embeddings = await service.embed_batch(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        assert all(isinstance(x, float) for emb in embeddings for x in emb)
        mock_model.encode.assert_called_once_with(
            texts, batch_size=32, show_progress_bar=False, convert_to_numpy=True
        )

    @pytest.mark.asyncio
    async def test_embed_batch_custom_batch_size(
        self, service: EmbeddingService, mock_model: Mock
    ) -> None:
        """Test batch embedding with custom batch size."""
        service._model = mock_model
        texts = ["Doc 1", "Doc 2", "Doc 3"]
        await service.embed_batch(texts, batch_size=16)

        call_kwargs = mock_model.encode.call_args.kwargs
        assert call_kwargs["batch_size"] == 16

    @pytest.mark.asyncio
    async def test_embed_empty_batch(self, service: EmbeddingService) -> None:
        """Test embedding empty batch raises error."""
        with pytest.raises(EmbeddingError) as exc_info:
            await service.embed_batch([])

        assert "empty" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_embed_batch_with_empty_strings(self, service: EmbeddingService) -> None:
        """Test batch with empty strings raises error."""
        with pytest.raises(EmbeddingError) as exc_info:
            await service.embed_batch(["Valid text", "", "Another valid"])

        assert "empty" in str(exc_info.value).lower()


class TestEmbeddingServiceErrorHandling:
    """Test error handling in embedding service."""

    @pytest.fixture
    def service(self) -> EmbeddingService:
        """Create an EmbeddingService instance."""
        return EmbeddingService()

    @pytest.mark.asyncio
    async def test_model_loading_error(self) -> None:
        """Test handling of model loading errors."""
        with patch("src.services.embedding.embedding_service.SentenceTransformer") as mock_st:
            mock_st.side_effect = Exception("Model not found")

            service = EmbeddingService(model_name="invalid-model")
            with pytest.raises(EmbeddingError) as exc_info:
                _ = service.model

            assert "model" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_encoding_error(self, service: EmbeddingService) -> None:
        """Test handling of encoding errors."""
        mock_model = Mock()
        mock_model.encode.side_effect = RuntimeError("CUDA out of memory")
        service._model = mock_model

        with pytest.raises(EmbeddingError) as exc_info:
            await service.embed_text("Test text")

        assert "encode" in str(exc_info.value).lower()


class TestEmbeddingServiceSimilarity:
    """Test similarity computation."""

    @pytest.fixture
    def service(self) -> EmbeddingService:
        """Create an EmbeddingService instance."""
        return EmbeddingService()

    def test_cosine_similarity_identical(self, service: EmbeddingService) -> None:
        """Test cosine similarity of identical vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [1.0, 0.0, 0.0]

        similarity = service.cosine_similarity(vec1, vec2)

        assert abs(similarity - 1.0) < 1e-6

    def test_cosine_similarity_orthogonal(self, service: EmbeddingService) -> None:
        """Test cosine similarity of orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]

        similarity = service.cosine_similarity(vec1, vec2)

        assert abs(similarity - 0.0) < 1e-6

    def test_cosine_similarity_opposite(self, service: EmbeddingService) -> None:
        """Test cosine similarity of opposite vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [-1.0, 0.0, 0.0]

        similarity = service.cosine_similarity(vec1, vec2)

        assert abs(similarity - (-1.0)) < 1e-6

    def test_cosine_similarity_normalized(self, service: EmbeddingService) -> None:
        """Test cosine similarity with non-normalized vectors."""
        vec1 = [2.0, 0.0, 0.0]
        vec2 = [4.0, 0.0, 0.0]

        similarity = service.cosine_similarity(vec1, vec2)

        # Should still be 1.0 for parallel vectors
        assert abs(similarity - 1.0) < 1e-6


class TestEmbeddingServiceModelCaching:
    """Test model caching behavior."""

    def test_model_loaded_once(self) -> None:
        """Test that model is loaded only once per instance."""
        with patch("src.services.embedding.embedding_service.SentenceTransformer") as mock_st:
            mock_model = Mock()
            mock_st.return_value = mock_model

            service = EmbeddingService()

            # Access model multiple times
            _ = service.model
            _ = service.model
            _ = service.model

            # Should only be called once
            mock_st.assert_called_once()

    def test_different_instances_different_models(self) -> None:
        """Test that different instances can have different models."""
        with patch("src.services.embedding.embedding_service.SentenceTransformer") as mock_st:
            mock_model1 = Mock()
            mock_model2 = Mock()
            mock_st.side_effect = [mock_model1, mock_model2]

            service1 = EmbeddingService(model_name="model1")
            service2 = EmbeddingService(model_name="model2")

            assert service1.model != service2.model
            assert mock_st.call_count == 2


class TestEmbeddingServiceDimensions:
    """Test embedding dimension validation."""

    @pytest.fixture
    def service(self) -> EmbeddingService:
        """Create an EmbeddingService instance."""
        return EmbeddingService()

    @pytest.mark.asyncio
    async def test_embedding_dimension_384(self, service: EmbeddingService) -> None:
        """Test that embeddings have correct dimension (384)."""
        mock_model = Mock()
        mock_model.encode.return_value = np.random.randn(384).astype(np.float32)
        service._model = mock_model

        embedding = await service.embed_text("Test")

        assert len(embedding) == 384
        assert service.dimension == 384
