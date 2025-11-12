"""Semantic reranking with diversity, recency, and query-aware adaptations.

This module enhances the basic cross-encoder reranking with advanced features:
- Diversity penalty (MMR) to avoid redundant results
- Recency boost for temporal queries
- Query-aware scoring adaptations

TDD Phase: GREEN - Full implementation to pass all tests.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

import numpy as np
from pydantic import BaseModel, Field

from .embedding_service import EmbeddingService


class QueryType(str, Enum):
    """Query classification types."""

    FACTUAL = "factual"  # What, who, when, where
    COMPARATIVE = "comparative"  # vs, compare, difference
    TEMPORAL = "temporal"  # latest, recent, current
    ANALYTICAL = "analytical"  # how, why, explain
    GENERAL = "general"  # Default


class DocumentWithMetadata(BaseModel):
    """Document with optional metadata for reranking."""

    content: str = Field(..., description="Document text content")
    published_at: datetime | None = Field(None, description="Publication date")
    source_quality: float | None = Field(None, description="Source quality score")


@dataclass
class RecencyConfig:
    """Configuration for recency boost."""

    enabled: bool = True
    weight: float = 0.2  # Weight for recency in final score
    half_life_days: int = 180  # Days for score to decay to 50%
    default_age_days: int = 730  # Assume 2 years old if date missing
    adaptive: bool = False  # Auto-boost weight for temporal queries


@dataclass
class RerankingConfig:
    """Configuration for semantic reranking."""

    diversity_penalty: float = 0.3  # Penalty weight for similar documents
    diversity_threshold: float = 0.85  # Similarity threshold for penalty
    use_mmr: bool = False  # Use Maximal Marginal Relevance algorithm
    query_aware: bool = True  # Adapt scoring to query type
    recency_config: RecencyConfig = None  # Recency boost configuration

    def __post_init__(self):
        """Initialize default recency config if None."""
        if self.recency_config is None:
            self.recency_config = RecencyConfig()


class SemanticReranker:
    """Enhanced semantic reranker with diversity, recency, and query awareness.
    
    This class extends basic cross-encoder reranking with advanced features
    to improve result quality and relevance.
    
    Example:
        >>> reranker = SemanticReranker(embedding_service)
        >>> results = await reranker.rerank_with_diversity(query, documents)
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        config: RerankingConfig = None,
    ) -> None:
        """Initialize semantic reranker.
        
        Args:
            embedding_service: Service for embeddings and base reranking
            config: Reranking configuration
        """
        self.embedding_service = embedding_service
        self.config = config or RerankingConfig()

    async def rerank_with_diversity(
        self,
        query: str,
        documents: list[str] | list[DocumentWithMetadata],
        top_k: int | None = None,
    ) -> list[tuple[int, float]]:
        """Rerank documents with diversity penalty.
        
        Args:
            query: Search query
            documents: List of documents or documents with metadata
            top_k: Return only top-k results
            
        Returns:
            List of (original_index, score) tuples sorted by final score
        """
        # Extract text content from documents
        if documents and isinstance(documents[0], DocumentWithMetadata):
            doc_texts = [doc.content for doc in documents]
        else:
            doc_texts = documents
        
        # Get base relevance scores from cross-encoder
        base_results = await self.embedding_service.rerank(
            query=query,
            documents=doc_texts,
        )
        
        # Create score mapping
        scores = {idx: score for idx, score in base_results}
        
        if not self.config.diversity_penalty or self.config.diversity_penalty == 0:
            # No diversity penalty, return base results
            results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            return results[:top_k] if top_k else results
        
        # Calculate pairwise similarities between documents
        embeddings = await self.embedding_service.embed_batch(doc_texts)
        similarity_matrix = self._calculate_similarity_matrix(embeddings)
        
        # Apply diversity penalty - penalize ALL similar pairs
        # Strategy: Both documents in a similar pair get penalized, but apply
        # stronger penalty to the document with the HIGHER index (assumed to be duplicate)
        # Limit total penalty to prevent scores from dropping too low
        final_scores = {}
        
        for idx in scores.keys():
            base_score = scores[idx]
            penalty = 0.0
            
            # Check similarity to ALL other documents
            for other_idx in scores.keys():
                if other_idx != idx:
                    similarity = similarity_matrix[idx][other_idx]
                    if similarity > self.config.diversity_threshold:
                        excess_similarity = similarity - self.config.diversity_threshold
                        
                        # Penalize both documents, but more heavily penalize the one with higher index
                        # This assumes documents earlier in the list are "originals"
                        if idx > other_idx:
                            # This document comes later - likely duplicate, apply full penalty
                            penalty += self.config.diversity_penalty * excess_similarity
                        else:
                            # This document comes first - likely original, apply lighter penalty
                            penalty += 0.3 * self.config.diversity_penalty * excess_similarity
            
            # Apply penalty but cap it to avoid over-penalization
            # Maximum penalty is 50% of the base score
            max_penalty = 0.5 * base_score
            effective_penalty = min(penalty, max_penalty)
            final_scores[idx] = max(0.0, base_score - effective_penalty)
        
        # Sort by final score
        results = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return results[:top_k] if top_k else results

    async def rerank_with_recency(
        self,
        query: str,
        documents: list[DocumentWithMetadata],
        top_k: int | None = None,
    ) -> list[tuple[int, float]]:
        """Rerank documents with recency boost.
        
        Args:
            query: Search query
            documents: Documents with metadata (requires published_at)
            top_k: Return only top-k results
            
        Returns:
            List of (original_index, score) tuples sorted by final score
        """
        if not self.config.recency_config.enabled:
            # Recency disabled, use base reranking
            doc_texts = [doc.content for doc in documents]
            return await self.embedding_service.rerank(query, doc_texts, top_k)
        
        # Get base relevance scores
        doc_texts = [doc.content for doc in documents]
        base_results = await self.embedding_service.rerank(query, doc_texts)
        base_scores = {idx: score for idx, score in base_results}
        
        # Calculate recency scores
        recency_scores = await self._calculate_recency_scores(documents)
        
        # Combine relevance and recency
        recency_weight = self.config.recency_config.weight
        relevance_weight = 1.0 - recency_weight
        
        final_scores = {}
        for idx in range(len(documents)):
            final_scores[idx] = (
                relevance_weight * base_scores[idx]
                + recency_weight * recency_scores[idx]
            )
        
        # Sort by final score
        results = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return results[:top_k] if top_k else results

    async def rerank_with_mmr(
        self,
        query: str,
        documents: list[str],
        top_k: int,
        lambda_param: float = 0.5,
    ) -> list[tuple[int, float]]:
        """Rerank using Maximal Marginal Relevance (MMR) algorithm.
        
        Args:
            query: Search query
            documents: List of documents
            top_k: Number of diverse documents to select
            lambda_param: Balance between relevance (1.0) and diversity (0.0)
            
        Returns:
            List of (original_index, score) tuples for selected documents
        """
        # Get base relevance scores
        base_results = await self.embedding_service.rerank(query, documents)
        relevance_scores = {idx: score for idx, score in base_results}
        
        # Get document embeddings for similarity calculation
        embeddings = await self.embedding_service.embed_batch(documents)
        similarity_matrix = self._calculate_similarity_matrix(embeddings)
        
        # MMR algorithm: iteratively select documents
        selected = []
        selected_indices = set()
        remaining = set(range(len(documents)))
        
        # Select first document (highest relevance)
        first_idx = max(remaining, key=lambda i: relevance_scores[i])
        selected.append((first_idx, relevance_scores[first_idx]))
        selected_indices.add(first_idx)
        remaining.remove(first_idx)
        
        # Select remaining documents
        while len(selected) < top_k and remaining:
            best_idx = None
            best_score = -float('inf')
            
            for idx in remaining:
                # Calculate relevance component
                relevance = relevance_scores[idx]
                
                # Calculate diversity component (max similarity to selected)
                max_sim = max(similarity_matrix[idx][s_idx] for s_idx in selected_indices)
                
                # MMR score: λ * relevance - (1-λ) * max_similarity
                mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
                
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx
            
            if best_idx is not None:
                selected.append((best_idx, relevance_scores[best_idx]))
                selected_indices.add(best_idx)
                remaining.remove(best_idx)
        
        return selected

    async def rerank_with_query_awareness(
        self,
        query: str,
        documents: list[str],
        top_k: int | None = None,
    ) -> list[tuple[int, float]]:
        """Rerank with query-aware score adaptations.
        
        Args:
            query: Search query
            documents: List of documents
            top_k: Return only top-k results
            
        Returns:
            List of (original_index, score) tuples sorted by adapted scores
        """
        if not self.config.query_aware:
            # Query awareness disabled, use base reranking
            return await self.embedding_service.rerank(query, documents, top_k)
        
        # Detect query type
        query_type = await self.detect_query_type(query)
        
        # Get base relevance scores
        base_results = await self.embedding_service.rerank(query, documents)
        base_scores = {idx: score for idx, score in base_results}
        
        # Apply query-type-specific adaptations
        final_scores = {}
        
        for idx, doc in enumerate(documents):
            base_score = base_scores[idx]
            adapted_score = base_score
            doc_length = len(doc)
            
            # Factual queries: prefer concise answers (penalize verbosity)
            if query_type == QueryType.FACTUAL:
                # Apply multiplicative penalty for long documents
                if doc_length > 200:
                    penalty_factor = 1.0 - min(0.3, (doc_length - 200) / 2000)
                    adapted_score *= penalty_factor
                elif doc_length < 100:
                    # Slight boost for very concise answers
                    adapted_score *= 1.05
            
            # Comparative queries: boost docs mentioning both subjects
            elif query_type == QueryType.COMPARATIVE:
                # Extract comparison subjects (rough heuristic)
                if ' vs ' in query.lower() or ' versus ' in query.lower():
                    subjects = re.split(r'\s+vs\.?\s+|\s+versus\s+', query.lower(), maxsplit=1)
                    if len(subjects) == 2:
                        # Boost if both subjects mentioned in doc
                        doc_lower = doc.lower()
                        has_both = all(subj.strip() in doc_lower for subj in subjects)
                        if has_both:
                            adapted_score *= 1.2  # 20% boost
            
            # Analytical queries: prefer detailed explanations
            elif query_type == QueryType.ANALYTICAL:
                # Boost longer, more detailed documents
                if doc_length > 200:
                    boost_factor = 1.0 + min(0.3, (doc_length - 200) / 2000)
                    adapted_score *= boost_factor
                elif doc_length < 100:
                    # Penalize very short answers
                    adapted_score *= 0.9
            
            final_scores[idx] = adapted_score
        
        # Sort by adapted score
        results = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return results[:top_k] if top_k else results

    async def rerank_with_adaptive_recency(
        self,
        query: str,
        documents: list[DocumentWithMetadata],
        top_k: int | None = None,
    ) -> list[tuple[int, float]]:
        """Rerank with adaptive recency (auto-boost for temporal queries).
        
        Args:
            query: Search query
            documents: Documents with metadata
            top_k: Return only top-k results
            
        Returns:
            List of (original_index, score) tuples sorted by final score
        """
        # Detect if query is temporal
        query_type = await self.detect_query_type(query)
        
        # Temporarily boost recency weight for temporal queries
        original_weight = self.config.recency_config.weight
        
        if query_type == QueryType.TEMPORAL and self.config.recency_config.adaptive:
            # Boost recency weight (e.g., 0.2 -> 0.5)
            self.config.recency_config.weight = min(0.6, original_weight * 2.5)
        
        try:
            # Use regular recency reranking with adjusted weight
            results = await self.rerank_with_recency(query, documents, top_k)
            return results
        finally:
            # Restore original weight
            self.config.recency_config.weight = original_weight

    async def detect_query_type(self, query: str) -> QueryType:
        """Detect query type for adaptive scoring.
        
        Args:
            query: Search query
            
        Returns:
            Detected query type
        """
        query_lower = query.lower()
        
        # Check for temporal keywords
        temporal_keywords = ['latest', 'recent', 'current', 'new', 'trend', 'update', '2024', '2025']
        if any(kw in query_lower for kw in temporal_keywords):
            return QueryType.TEMPORAL
        
        # Check for comparative keywords
        comparative_keywords = [' vs ', ' vs.', ' versus ', 'compare', 'comparison', 'difference between']
        if any(kw in query_lower for kw in comparative_keywords):
            return QueryType.COMPARATIVE
        
        # Check for factual keywords (starts with question words)
        factual_starters = ['what is', 'what are', 'what was', 'what ', 'who is', 'who are', 'who was', 'who ', 'when was', 'when did', 'when ', 'where is', 'where are', 'where was', 'where ']
        if any(query_lower.startswith(starter) for starter in factual_starters):
            return QueryType.FACTUAL
        
        # Check for analytical keywords
        analytical_keywords = ['how does', 'how to', 'how can', 'why is', 'why does', 'why do', 'explain']
        if any(kw in query_lower for kw in analytical_keywords):
            return QueryType.ANALYTICAL
        
        return QueryType.GENERAL

    async def get_effective_recency_weight(self, query: str) -> float:
        """Get effective recency weight (may be boosted for temporal queries).
        
        Args:
            query: Search query
            
        Returns:
            Effective recency weight
        """
        base_weight = self.config.recency_config.weight
        
        if not self.config.recency_config.adaptive:
            return base_weight
        
        # Boost for temporal queries
        query_type = await self.detect_query_type(query)
        if query_type == QueryType.TEMPORAL:
            return min(0.6, base_weight * 2.5)
        
        return base_weight

    async def get_effective_diversity_penalty(self, query: str) -> float:
        """Get effective diversity penalty (adapted to query type).
        
        Args:
            query: Search query
            
        Returns:
            Effective diversity penalty
        """
        base_penalty = self.config.diversity_penalty
        
        if not self.config.query_aware:
            return base_penalty
        
        # Adjust based on query type
        query_type = await self.detect_query_type(query)
        
        # Comparative queries benefit from more diversity
        if query_type == QueryType.COMPARATIVE:
            return min(0.5, base_penalty * 1.5)
        
        # Factual queries prefer focused results (less diversity)
        elif query_type == QueryType.FACTUAL:
            return base_penalty * 0.7
        
        return base_penalty

    async def _calculate_recency_scores(
        self,
        documents: list[DocumentWithMetadata],
    ) -> list[float]:
        """Calculate recency scores using exponential decay.
        
        Args:
            documents: Documents with publication dates
            
        Returns:
            List of recency scores (0.0-1.0)
        """
        now = datetime.utcnow()
        half_life = timedelta(days=self.config.recency_config.half_life_days)
        default_age = timedelta(days=self.config.recency_config.default_age_days)
        
        scores = []
        for doc in documents:
            if doc.published_at is None:
                # Use default age for missing dates
                age = default_age
            else:
                age = now - doc.published_at
            
            # Exponential decay: score = 0.5^(age / half_life)
            # This gives score=1.0 for age=0, score=0.5 for age=half_life
            age_in_half_lives = age.total_seconds() / half_life.total_seconds()
            score = 0.5 ** age_in_half_lives
            
            scores.append(score)
        
        return scores
    
    def _calculate_similarity_matrix(self, embeddings: list[list[float]]) -> np.ndarray:
        """Calculate pairwise cosine similarity matrix.
        
        Args:
            embeddings: List of embedding vectors
            
        Returns:
            NxN similarity matrix
        """
        n = len(embeddings)
        matrix = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix[i][j] = 1.0
                else:
                    # Calculate cosine similarity
                    sim = self.embedding_service.cosine_similarity(embeddings[i], embeddings[j])
                    matrix[i][j] = sim
        
        return matrix
