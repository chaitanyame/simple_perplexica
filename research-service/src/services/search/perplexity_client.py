"""Perplexity AI search client.

Provides ready-to-consume search results with inline citations.
No additional processing required - Perplexity handles everything.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import BaseModel, Field

from ...core.config import settings


class PerplexityError(Exception):
    """Perplexity API error."""
    pass


@dataclass
class Citation:
    """Citation with URL and position.
    
    Attributes:
        index: Citation number (1-based)
        url: Source URL
        mention_count: Number of times cited in content
    """
    index: int
    url: str
    mention_count: int = 0


class PerplexityResponse(BaseModel):
    """Perplexity API response with citations.
    
    Attributes:
        content: Formatted content with citation markers [1], [2], etc.
        citations: List of source citations
        model: Model used for generation
    """
    
    model_config = {"arbitrary_types_allowed": True}
    
    content: str = Field(..., description="Formatted content with citation markers")
    citations: list[Citation] = Field(default_factory=list, description="Source citations")
    model: str = Field(..., description="Model used (e.g., sonar-pro)")


class PerplexityClient:
    """Client for Perplexity AI search API.
    
    Provides ready-to-consume search results with inline citations [1], [2].
    No additional processing required - results are display-ready.
    
    Example:
        >>> client = PerplexityClient(api_key="your-key")
        >>> result = await client.search("What are AI agents?")
        >>> print(result.content)
        AI agents are autonomous software [1]. They perceive and act [2].
        >>> print(result.citations)
        [Citation(index=1, url="https://...", mention_count=1), ...]
    """
    
    API_URL = "https://api.perplexity.ai/chat/completions"
    DEFAULT_MODEL = "sonar-pro"  # Best for research tasks
    MAX_RETRIES = 3
    BACKOFF_FACTOR = 2
    
    def __init__(
        self,
        api_key: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        model: str = DEFAULT_MODEL
    ):
        """Initialize Perplexity client.
        
        Args:
            api_key: Perplexity API key (defaults to settings.PERPLEXITY_API_KEY)
            http_client: Optional custom HTTP client for testing
            model: Model to use (sonar-pro, sonar, etc.)
            
        Raises:
            ValueError: If no API key provided
        """
        self.api_key = api_key or getattr(settings, 'PERPLEXITY_API_KEY', None)
        if not self.api_key:
            raise ValueError("Perplexity API key required")
        
        self.http_client = http_client or httpx.AsyncClient(timeout=60.0)
        self.model = model
        self._owns_client = http_client is None
    
    async def search(
        self,
        query: str,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        search_domain_filter: list[str] | None = None,
        search_recency_filter: str | None = None
    ) -> PerplexityResponse:
        """Execute search query via Perplexity API.
        
        Args:
            query: Search query
            max_tokens: Maximum response length (default: 4096)
            temperature: Response creativity 0.0-1.0 (default: 0.2 for precision)
            search_domain_filter: Optional domain whitelist (e.g., ["arxiv.org"])
            search_recency_filter: Recency filter ("month", "week", "day", "hour")
            
        Returns:
            PerplexityResponse with content and citations
            
        Raises:
            PerplexityError: On API failure after retries
            
        Example:
            >>> client = PerplexityClient()
            >>> result = await client.search(
            ...     "What are AI agents?",
            ...     search_domain_filter=["arxiv.org", "github.com"],
            ...     search_recency_filter="month"
            ... )
            >>> print(result.content)
        """
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Be precise and comprehensive. Always cite sources."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "return_citations": True,
            "search_recency_filter": search_recency_filter or "month"
        }
        
        # Add optional domain filter
        if search_domain_filter:
            payload["search_domain_filter"] = search_domain_filter
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Exponential backoff retry logic
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.http_client.post(
                    self.API_URL,
                    json=payload,
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                
                return self._parse_response(data)
                
            except Exception as e:
                # If last attempt, raise error
                if attempt == self.MAX_RETRIES - 1:
                    raise PerplexityError(f"Perplexity API failed: {e}")
                
                # Exponential backoff: 1s, 2s, 4s
                wait_time = (self.BACKOFF_FACTOR ** attempt) * 1.0
                await asyncio.sleep(wait_time)
        
        # Should never reach here, but satisfy type checker
        raise PerplexityError("Unexpected error in search")
    
    @staticmethod
    def _parse_response(data: dict[str, Any]) -> PerplexityResponse:
        """Parse Perplexity API response.
        
        Args:
            data: Raw API response JSON
            
        Returns:
            Structured PerplexityResponse with extracted citations
        """
        content = data["choices"][0]["message"]["content"]
        citation_urls = data.get("citations", [])
        
        # Extract citations from [1], [2] markers in content
        citations = PerplexityClient._extract_citations(content, citation_urls)
        
        return PerplexityResponse(
            content=content,
            citations=citations,
            model=data["model"]
        )
    
    @staticmethod
    def _extract_citations(content: str, citation_urls: list[str]) -> list[Citation]:
        """Extract citations from [1], [2] markers in content.
        
        Args:
            content: Content with citation markers like [1], [2]
            citation_urls: List of citation URLs from API response
            
        Returns:
            List of Citation objects with mention counts
            
        Example:
            >>> content = "Fact one [1]. Fact two [2]. Another fact [1]."
            >>> urls = ["https://source1.com", "https://source2.com"]
            >>> citations = PerplexityClient._extract_citations(content, urls)
            >>> citations[0].mention_count
            2  # [1] appears twice
        """
        citations: dict[int, Citation] = {}
        
        # Find all [N] markers using regex
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, content)
        
        for match in matches:
            idx = int(match)
            
            # Validate index is within bounds (1-based indexing)
            if 0 < idx <= len(citation_urls):
                if idx not in citations:
                    citations[idx] = Citation(
                        index=idx,
                        url=citation_urls[idx - 1],  # Convert to 0-based
                        mention_count=0
                    )
                citations[idx].mention_count += 1
        
        # Return sorted by index
        return sorted(citations.values(), key=lambda c: c.index)
    
    async def close(self) -> None:
        """Close HTTP client if owned by this instance."""
        if self._owns_client:
            await self.http_client.aclose()
