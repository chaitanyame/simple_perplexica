"""Sentence-Transformers embedding service.

This module provides text embedding functionality using sentence-transformers
library with the all-MiniLM-L6-v2 model (384 dimensions).
"""

from __future__ import annotations

import asyncio

import numpy as np
from sentence_transformers import SentenceTransformer


class EmbeddingError(Exception):
    """Exception raised for embedding-related errors."""

    pass


class EmbeddingService:
    """Service for generating text embeddings using Sentence-Transformers.

    Attributes:
        model_name: Name of the sentence-transformers model
        dimension: Dimensionality of embeddings (384 for all-MiniLM-L6-v2)
        device: Device for computation ('cpu' or 'cuda')

    Example:
        >>> service = EmbeddingService()
        >>> embedding = await service.embed_text("Hello world")
        >>> len(embedding)
        384
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: str = "cpu",
    ) -> None:
        """Initialize embedding service.

        Args:
            model_name: Name of sentence-transformers model
            device: Device for computation ('cpu' or 'cuda')

        Raises:
            EmbeddingError: If model loading fails
        """
        self.model_name = model_name
        self.device = device
        self.dimension = 384  # all-MiniLM-L6-v2 produces 384D embeddings

        # Load model (lazy-loaded on first access)
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        """Get or load the sentence transformer model.

        Returns:
            Loaded SentenceTransformer model

        Raises:
            EmbeddingError: If model loading fails
        """
        if self._model is None:
            try:
                self._model = SentenceTransformer(self.model_name, device=self.device)
            except Exception as e:
                raise EmbeddingError(f"Failed to load model '{self.model_name}': {e}") from e

        return self._model

    async def embed_text(self, text: str) -> list[float]:
        """Generate embedding for a single text.

        Args:
            text: Input text to embed

        Returns:
            384-dimensional embedding vector

        Raises:
            EmbeddingError: If text is empty or encoding fails

        Example:
            >>> service = EmbeddingService()
            >>> embedding = await service.embed_text("AI research")
            >>> len(embedding)
            384
        """
        # Validate input
        if not text or not text.strip():
            raise EmbeddingError("Text cannot be empty")

        try:
            # Run encoding in thread pool to avoid blocking
            embedding: np.ndarray[tuple[int], np.dtype[np.float32]] = await asyncio.to_thread(
                self.model.encode, text.strip(), convert_to_numpy=True, show_progress_bar=False
            )

            # Convert to list of floats
            result: list[float] = embedding.tolist()
            return result

        except Exception as e:
            raise EmbeddingError(f"Failed to encode text: {e}") from e

    async def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of input texts to embed
            batch_size: Number of texts to process per batch

        Returns:
            List of 384-dimensional embedding vectors

        Raises:
            EmbeddingError: If texts is empty or contains empty strings

        Example:
            >>> service = EmbeddingService()
            >>> embeddings = await service.embed_batch(["text 1", "text 2"])
            >>> len(embeddings)
            2
            >>> len(embeddings[0])
            384
        """
        # Validate input
        if not texts:
            raise EmbeddingError("Text list cannot be empty")

        # Check for empty strings
        for i, text in enumerate(texts):
            if not text or not text.strip():
                raise EmbeddingError(f"Text at index {i} is empty")

        try:
            # Run batch encoding in thread pool
            embeddings: np.ndarray[tuple[int, int], np.dtype[np.float32]] = await asyncio.to_thread(
                self.model.encode,
                texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
            )

            # Convert to list of lists
            result: list[list[float]] = embeddings.tolist()
            return result

        except Exception as e:
            raise EmbeddingError(f"Failed to encode batch: {e}") from e

    def cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First embedding vector
            vec2: Second embedding vector

        Returns:
            Cosine similarity score (-1 to 1)

        Example:
            >>> service = EmbeddingService()
            >>> v1 = [1.0, 0.0, 0.0]
            >>> v2 = [1.0, 0.0, 0.0]
            >>> service.cosine_similarity(v1, v2)
            1.0
        """
        # Convert to numpy arrays
        a = np.array(vec1)
        b = np.array(vec2)

        # Calculate cosine similarity
        dot_product = np.dot(a, b)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)

        # Avoid division by zero
        if norm_a == 0 or norm_b == 0:
            return 0.0

        return float(dot_product / (norm_a * norm_b))
