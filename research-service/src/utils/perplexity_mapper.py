"""Map Perplexity API response to internal Citation model."""

import hashlib
import structlog
from urllib.parse import urlparse
from typing import List

from src.models.citation import Citation

logger = structlog.get_logger()


class PerplexityCitationMapper:
    """Map Perplexity API citations to internal Citation model."""

    @staticmethod
    def map_citations(citation_urls: List[str]) -> List[Citation]:
        """
        Map Perplexity citation URLs to internal Citation objects.

        Since Perplexity returns only URLs, we create minimal Citation objects
        with the URL as both source and title. In a real scenario, we could
        fetch the actual page titles, but for now, we use the domain as title.

        Args:
            citation_urls: List of citation URLs from Perplexity API

        Returns:
            List of Citation objects
        """
        citations = []

        for idx, url in enumerate(citation_urls):
            # Infer authority level from URL
            authority = PerplexityCitationMapper._infer_authority(url)

            # Generate title from URL
            title = PerplexityCitationMapper._extract_title_from_url(url)

            # Calculate relevance based on position (earlier citations = more relevant)
            relevance = max(0.6, 1.0 - (idx * 0.05))

            citations.append(Citation(
                source_id=f"perplexity_{hashlib.md5(url.encode()).hexdigest()[:8]}",
                title=title,
                url=url,
                excerpt="",  # Perplexity doesn't provide excerpts, content in answer
                relevance=relevance,
                authority_level=authority,
                freshness_score=0.8,  # Perplexity uses recent sources
                is_direct_quote=False  # Perplexity synthesizes content
            ))

        logger.info(
            "perplexity_citations_mapped",
            count=len(citations),
            urls=len(citation_urls)
        )

        return citations

    @staticmethod
    def _infer_authority(url: str) -> str:
        """
        Infer citation authority level from URL.

        Returns:
            "primary", "secondary", or "tertiary"
        """
        try:
            domain = urlparse(url).netloc.lower()
        except Exception:
            return "tertiary"

        # Primary sources (official, authoritative)
        primary_indicators = [
            '.gov', '.edu', '.org',
            'docs.', 'developer.', 'official',
            'arxiv.org', 'nature.com', 'science.org',
            'github.com/topics'  # GitHub official topics
        ]

        for indicator in primary_indicators:
            if indicator in domain:
                return "primary"

        # Secondary sources (reputable platforms)
        secondary_indicators = [
            'github.com', 'stackoverflow.com',
            'techcrunch.com', 'wired.com', 'arstechnica.com',
            'medium.com', 'dev.to', 'hackernews',
            'theverge.com', 'engadget.com'
        ]

        for indicator in secondary_indicators:
            if indicator in domain:
                return "secondary"

        # Everything else is tertiary
        return "tertiary"

    @staticmethod
    def _extract_title_from_url(url: str) -> str:
        """
        Generate title from URL.

        In production, this could fetch the actual page title from meta tags.
        For now, we use domain + path.

        Args:
            url: Citation URL

        Returns:
            Human-readable title
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')

            # Extract meaningful path
            path_parts = [p for p in parsed.path.split('/') if p]

            if path_parts:
                # Use last 2 path segments max
                path = ' - '.join(path_parts[-2:]) if len(path_parts) > 1 else path_parts[-1]
                return f"{domain}: {path[:50]}"

            return domain

        except Exception:
            return url[:60]
