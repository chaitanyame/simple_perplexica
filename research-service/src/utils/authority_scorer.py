"""Source authority scoring utilities.

Provides multi-layered authority scoring for search sources:
1. Pattern-based authority detection (*.gov, *.edu, official domains)
2. Wikipedia citation proxy (query-contextual authority signals)
3. Curated domain scoring with tier-based classification

Usage:
    >>> scorer = AuthorityScorer(settings)
    >>> score = await scorer.calculate_authority_score(source, query)
    >>> print(f"Authority: {score:.2f}")
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from urllib.parse import urlparse

import httpx
import structlog

if TYPE_CHECKING:
    from src.agents.search_agent import SearchSource
    from src.core.config import Settings

logger = structlog.get_logger(__name__)


class AuthorityScorer:
    """Calculate source authority scores using multiple signals."""

    # Tier 1: Official/Primary sources (score: 1.0)
    OFFICIAL_DOMAINS = {
        # Government & Education
        ".gov",
        ".edu",
        ".mil",
        # Official documentation
        "docs.microsoft.com",
        "cloud.google.com",
        "aws.amazon.com",
        "developer.apple.com",
        "developer.mozilla.org",
        "docs.python.org",
        "docs.oracle.com",
        "docs.docker.com",
        "kubernetes.io",
        # Academic & Research
        "arxiv.org",
        "nature.com",
        "science.org",
        "ieee.org",
        "acm.org",
        "scholar.google.com",
        "researchgate.net",
        "semanticscholar.org",
        # Standards bodies
        "w3.org",
        "ietf.org",
        "iso.org",
        "ecma-international.org",
    }

    # Tier 2: Reputable sources (score: 0.85)
    REPUTABLE_DOMAINS = {
        # Major tech companies
        "github.com",
        "stackoverflow.com",
        "microsoft.com",
        "google.com",
        "amazon.com",
        "ibm.com",
        "oracle.com",
        "redhat.com",
        # Major news outlets
        "reuters.com",
        "bloomberg.com",
        "nytimes.com",
        "wsj.com",
        "bbc.com",
        "theguardian.com",
        # Tech news
        "techcrunch.com",
        "arstechnica.com",
        "wired.com",
        "theverge.com",
        "zdnet.com",
        "cnet.com",
    }

    # Tier 3: Community/Developer resources (score: 0.70)
    COMMUNITY_DOMAINS = {
        "medium.com",
        "dev.to",
        "hackernoon.com",
        "towardsdatascience.com",
        "reddit.com",
        "youtube.com",
    }

    # Pattern-based authority indicators
    AUTHORITY_PATTERNS = [
        "docs.",
        "developer.",
        "official",
        ".org/docs",
        "documentation",
        "/reference",
        "/api",
    ]

    def __init__(self, settings: Settings):
        """Initialize authority scorer.

        Args:
            settings: Application settings with authority scoring config
        """
        self.settings = settings
        self.wikipedia_cache: dict[str, set[str]] = {}
        self.http_client = httpx.AsyncClient(timeout=10.0)

    async def calculate_authority_score(
        self, source: SearchSource, query: str | None = None
    ) -> float:
        """Calculate comprehensive authority score for a source.

        Combines multiple authority signals:
        1. Pattern-based detection (*.gov, *.edu, official domains)
        2. Wikipedia citation proxy (if query provided)
        3. Domain tier classification

        Args:
            source: Search source to score
            query: Optional query for Wikipedia contextual authority

        Returns:
            Authority score (0.0-1.0), higher = more authoritative

        Example:
            >>> score = await scorer.calculate_authority_score(source, "python async")
            >>> print(f"Authority: {score:.2f}")  # 0.95
        """
        if not self.settings.ENABLE_AUTHORITY_SCORING:
            return 0.0

        scores = []

        # 1. Pattern-based authority
        if self.settings.ENABLE_PATTERN_AUTHORITY:
            pattern_score = self._calculate_pattern_authority(source)
            scores.append(pattern_score)
            logger.debug(
                "Pattern authority calculated",
                url=source.url,
                score=pattern_score,
            )

        # 2. Wikipedia citation proxy (query-contextual)
        if self.settings.ENABLE_WIKIPEDIA_AUTHORITY and query:
            wiki_score = await self._calculate_wikipedia_authority(source, query)
            scores.append(wiki_score)
            logger.debug(
                "Wikipedia authority calculated",
                url=source.url,
                query=query,
                score=wiki_score,
            )

        # Return max score (best authority signal wins)
        return max(scores) if scores else 0.0

    def _calculate_pattern_authority(self, source: SearchSource) -> float:
        """Calculate authority score using pattern matching.

        Args:
            source: Search source to score

        Returns:
            Authority score (0.0-1.0)
        """
        url_lower = source.url.lower()
        domain = self._extract_domain(source.url)

        # Check official domains (Tier 1)
        for official_domain in self.OFFICIAL_DOMAINS:
            if official_domain.startswith("."):
                # TLD check
                if domain.endswith(official_domain):
                    return 1.0
            else:
                # Exact domain or subdomain
                if domain == official_domain or domain.endswith(f".{official_domain}"):
                    return 1.0

        # Check reputable domains (Tier 2)
        for reputable_domain in self.REPUTABLE_DOMAINS:
            if domain == reputable_domain or domain.endswith(f".{reputable_domain}"):
                return 0.85

        # Check community domains (Tier 3)
        for community_domain in self.COMMUNITY_DOMAINS:
            if domain == community_domain or domain.endswith(f".{community_domain}"):
                return 0.70

        # Check authority patterns in URL
        for pattern in self.AUTHORITY_PATTERNS:
            if pattern in url_lower:
                return 0.75

        # Check if high relevance (proxy for authority)
        if source.relevance >= 0.85:
            return 0.60

        # Default: no special authority
        return 0.0

    async def _calculate_wikipedia_authority(self, source: SearchSource, query: str) -> float:
        """Calculate authority using Wikipedia citation proxy.

        Checks if source domain is cited by Wikipedia articles related to the query.

        Args:
            source: Search source to score
            query: User query for context

        Returns:
            Authority score (1.0 if cited by Wikipedia, 0.0 otherwise)
        """
        try:
            # Check cache first
            if query in self.wikipedia_cache:
                cited_domains = self.wikipedia_cache[query]
            else:
                # Fetch Wikipedia citations for query
                cited_domains = await self._fetch_wikipedia_citations(query)
                self.wikipedia_cache[query] = cited_domains

            # Check if source domain is cited
            source_domain = self._extract_domain(source.url)
            if source_domain in cited_domains:
                logger.info(
                    "Source cited by Wikipedia",
                    domain=source_domain,
                    query=query,
                )
                return 1.0

            return 0.0

        except Exception as e:
            logger.warning(
                "Wikipedia authority check failed",
                error=str(e),
                query=query,
            )
            return 0.0

    async def _fetch_wikipedia_citations(self, query: str) -> set[str]:
        """Fetch domains cited by Wikipedia articles for query.

        Args:
            query: Search query

        Returns:
            Set of domains cited in Wikipedia articles
        """
        try:
            # Search Wikipedia for query
            search_url = "https://en.wikipedia.org/w/api.php"
            search_params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": 3,  # Top 3 articles
            }

            search_response = await self.http_client.get(search_url, params=search_params)
            search_data = search_response.json()

            if "query" not in search_data or "search" not in search_data["query"]:
                return set()

            cited_domains = set()

            # For each article, extract external links (citations)
            for article in search_data["query"]["search"][:3]:
                page_id = article["pageid"]

                # Get external links from article
                links_params = {
                    "action": "query",
                    "prop": "extlinks",
                    "pageids": page_id,
                    "format": "json",
                    "ellimit": 50,  # Max 50 links per article
                }

                links_response = await self.http_client.get(search_url, params=links_params)
                links_data = links_response.json()

                if "query" not in links_data or "pages" not in links_data["query"]:
                    continue

                # Extract domains from external links
                page_data = links_data["query"]["pages"].get(str(page_id), {})
                external_links = page_data.get("extlinks", [])

                for link in external_links:
                    url = link.get("*", "")
                    domain = self._extract_domain(url)
                    if domain:
                        cited_domains.add(domain)

            logger.info(
                "Wikipedia citations fetched",
                query=query,
                num_domains=len(cited_domains),
                sample_domains=list(cited_domains)[:5],
            )

            return cited_domains

        except Exception as e:
            logger.error(
                "Failed to fetch Wikipedia citations",
                error=str(e),
                query=query,
            )
            return set()

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL.

        Args:
            url: URL string

        Returns:
            Domain (e.g., "example.com")
        """
        try:
            parsed = urlparse(url)
            return parsed.netloc.lower()
        except Exception:
            return ""

    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
