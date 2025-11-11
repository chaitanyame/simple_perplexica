"""Search mode configurations for query optimization.

Defines three search modes with different trade-offs between speed and depth:
- SPEED: Fast results, minimal processing (5 sources, 15s timeout, no crawling)
- BALANCED: Default mode with good quality (10 sources, 30s timeout, selective crawling)
- DEEP: Comprehensive research (20 sources, 60s timeout, full crawling + RAG)

Each mode configures:
- max_sources: Number of sources to retrieve and rank
- timeout: Maximum execution time in seconds
- enable_reranking: Whether to use cross-encoder semantic reranking
- enable_crawling: Whether to crawl and extract full content
- enable_rag: Whether to retrieve from historical research (ResearchAgent only)
- semantic_weight: Weight for semantic score in RRF (0.0-1.0)
- keyword_weight: Weight for keyword score in RRF (0.0-1.0)
"""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple


class SearchModeConfig(NamedTuple):
    """Configuration for a search mode.
    
    Attributes:
        max_sources: Maximum number of sources to retrieve (5-20)
        timeout: Maximum execution time in seconds (15-60)
        enable_reranking: Use cross-encoder semantic reranking
        enable_crawling: Crawl URLs to extract full content
        enable_rag: Retrieve from historical research (ResearchAgent)
        semantic_weight: Weight for vector similarity in hybrid search (0.0-1.0)
        keyword_weight: Weight for FTS in hybrid search (0.0-1.0)
    """
    
    max_sources: int
    timeout: int
    enable_reranking: bool
    enable_crawling: bool
    enable_rag: bool
    semantic_weight: float
    keyword_weight: float


class SearchMode(str, Enum):
    """Search mode enumeration.
    
    Values:
        SPEED: Fast results with minimal processing
        BALANCED: Default mode balancing speed and quality
        DEEP: Comprehensive research with full processing
    """
    
    SPEED = "speed"
    BALANCED = "balanced"
    DEEP = "deep"
    
    @property
    def config(self) -> SearchModeConfig:
        """Get configuration for this search mode.
        
        Returns:
            SearchModeConfig with mode-specific settings
            
        Example:
            >>> mode = SearchMode.BALANCED
            >>> config = mode.config
            >>> config.max_sources
            10
        """
        return SEARCH_MODE_CONFIGS[self]
    
    @property
    def description(self) -> str:
        """Get human-readable description of this mode.
        
        Returns:
            Description string for UI display
        """
        return SEARCH_MODE_DESCRIPTIONS[self]


# Mode configurations
SEARCH_MODE_CONFIGS: dict[SearchMode, SearchModeConfig] = {
    SearchMode.SPEED: SearchModeConfig(
        max_sources=5,
        timeout=15,
        enable_reranking=False,  # Skip for speed
        enable_crawling=False,   # Use snippets only
        enable_rag=False,        # No historical retrieval
        semantic_weight=0.7,     # Favor semantic for quick relevance
        keyword_weight=0.3,
    ),
    SearchMode.BALANCED: SearchModeConfig(
        max_sources=10,
        timeout=45,              # Increased from 30s to accommodate crawling
        enable_reranking=True,   # Enable for quality
        enable_crawling=True,    # Crawl high-relevance sources
        enable_rag=True,         # Use historical context
        semantic_weight=0.6,     # Balanced weights
        keyword_weight=0.4,
    ),
    SearchMode.DEEP: SearchModeConfig(
        max_sources=20,
        timeout=60,
        enable_reranking=True,   # Full semantic analysis
        enable_crawling=True,    # Crawl all sources
        enable_rag=True,         # Full RAG pipeline
        semantic_weight=0.5,     # Equal weights for comprehensive results
        keyword_weight=0.5,
    ),
}

# Mode descriptions for UI
SEARCH_MODE_DESCRIPTIONS: dict[SearchMode, str] = {
    SearchMode.SPEED: "⚡ Fast results (5 sources, 15s, snippets only)",
    SearchMode.BALANCED: "⚖️ Balanced quality & speed (10 sources, 45s, selective crawling)",
    SearchMode.DEEP: "🔍 Deep research (20 sources, 60s, full content + history)",
}


def get_mode_from_string(mode_str: str | None) -> SearchMode:
    """Convert string to SearchMode enum.
    
    Args:
        mode_str: Mode string ("speed", "balanced", "deep") or None
        
    Returns:
        SearchMode enum value (defaults to BALANCED if invalid)
        
    Example:
        >>> get_mode_from_string("deep")
        <SearchMode.DEEP: 'deep'>
        >>> get_mode_from_string(None)
        <SearchMode.BALANCED: 'balanced'>
    """
    if mode_str is None:
        return SearchMode.BALANCED
    
    try:
        return SearchMode(mode_str.lower())
    except ValueError:
        return SearchMode.BALANCED
