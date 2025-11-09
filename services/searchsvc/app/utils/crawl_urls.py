"""
crawl4ai wrapper for LLM-ready content extraction.

This module provides a wrapper around crawl4ai for fetching and processing web content
into clean, LLM-ready markdown format. It includes fallback to BeautifulSoup if crawl4ai fails.
"""

import logging
import asyncio
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse

try:
    from crawl4ai import AsyncWebCrawler, CrawlResult as Crawl4aiResult
except ImportError:
    AsyncWebCrawler = None
    Crawl4aiResult = None

logger = logging.getLogger(__name__)


@dataclass
class CrawlResult:
    """Result from crawling a URL"""
    url: str
    markdown_content: Optional[str]
    success: bool
    source: str  # "crawl4ai" or "beautifulsoup"
    error: Optional[str] = None


class CrawlWrapper:
    """
    Wrapper around crawl4ai for fetching URLs and converting to LLM-ready markdown.
    Falls back to BeautifulSoup if crawl4ai fails.
    """

    def __init__(
        self,
        timeout: int = 30,
        max_concurrent: int = 3,
        use_fallback: bool = True,
    ):
        """
        Initialize CrawlWrapper.

        Args:
            timeout: Timeout in seconds for each URL fetch
            max_concurrent: Max concurrent URLs to crawl
            use_fallback: Whether to fall back to BeautifulSoup if crawl4ai fails
        """
        self.timeout = timeout
        self.max_concurrent = max_concurrent
        self.use_fallback = use_fallback

    async def crawl_url(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        use_fallback: Optional[bool] = None,
    ) -> CrawlResult:
        """
        Crawl a single URL and return LLM-ready markdown content.

        Args:
            url: URL to crawl
            headers: Optional custom headers
            use_fallback: Override instance setting for this call

        Returns:
            CrawlResult with url, markdown_content, success, and source
        """
        use_fallback = use_fallback if use_fallback is not None else self.use_fallback

        # Try crawl4ai first
        if AsyncWebCrawler is not None:
            result = await self._crawl_with_crawl4ai(url, headers)
            if result.success:
                return result
            elif not use_fallback:
                return result

        # Fallback to BeautifulSoup if enabled
        if use_fallback:
            from .fallback_beautifulsoup import BeautifulSoupFallback

            fallback = BeautifulSoupFallback()
            return await fallback.fetch_as_markdown(url)

        return CrawlResult(
            url=url,
            markdown_content=None,
            success=False,
            source="crawl4ai",
            error="crawl4ai not available and fallback disabled",
        )

    async def _crawl_with_crawl4ai(
        self, url: str, headers: Optional[Dict[str, str]] = None
    ) -> CrawlResult:
        """
        Internal method to crawl using crawl4ai.

        Args:
            url: URL to crawl
            headers: Optional custom headers

        Returns:
            CrawlResult (may have success=False if crawl4ai fails)
        """
        if AsyncWebCrawler is None:
            return CrawlResult(
                url=url,
                markdown_content=None,
                success=False,
                source="crawl4ai",
                error="crawl4ai not installed",
            )

        try:
            # Validate URL
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                return CrawlResult(
                    url=url,
                    markdown_content=None,
                    success=False,
                    source="crawl4ai",
                    error="Invalid URL format",
                )

            async with AsyncWebCrawler() as crawler:
                # Prepare crawl parameters
                crawl_params = {
                    "url": url,
                    "timeout": self.timeout,
                }

                if headers:
                    crawl_params["headers"] = headers

                # Run crawl
                result = await asyncio.wait_for(
                    crawler.arun(**crawl_params),
                    timeout=self.timeout + 5,  # Add buffer for cleanup
                )

                if result is None:
                    return CrawlResult(
                        url=url,
                        markdown_content=None,
                        success=False,
                        source="crawl4ai",
                        error="Crawl returned None",
                    )

                # Extract markdown
                markdown = getattr(result, "markdown", None)
                if markdown:
                    return CrawlResult(
                        url=url,
                        markdown_content=markdown,
                        success=True,
                        source="crawl4ai",
                    )
                else:
                    return CrawlResult(
                        url=url,
                        markdown_content=None,
                        success=False,
                        source="crawl4ai",
                        error="No markdown content in result",
                    )

        except asyncio.TimeoutError:
            logger.warning(f"Crawl timeout for {url}")
            return CrawlResult(
                url=url,
                markdown_content=None,
                success=False,
                source="crawl4ai",
                error="Timeout",
            )
        except Exception as e:
            logger.error(f"Crawl error for {url}: {e}")
            return CrawlResult(
                url=url,
                markdown_content=None,
                success=False,
                source="crawl4ai",
                error=str(e),
            )

    async def crawl_batch(
        self,
        urls: List[str],
        headers: Optional[Dict[str, str]] = None,
        max_concurrent: Optional[int] = None,
    ) -> List[CrawlResult]:
        """
        Crawl multiple URLs with rate limiting.

        Args:
            urls: List of URLs to crawl
            headers: Optional custom headers for all requests
            max_concurrent: Override max concurrent setting for this call

        Returns:
            List of CrawlResult objects
        """
        if not urls:
            return []

        max_concurrent = max_concurrent or self.max_concurrent

        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)

        async def crawl_with_semaphore(url: str) -> CrawlResult:
            async with semaphore:
                return await self.crawl_url(url, headers)

        # Run all crawls concurrently with rate limiting
        results = await asyncio.gather(
            *[crawl_with_semaphore(url) for url in urls],
            return_exceptions=False,
        )

        return results

    async def crawl_with_fallback(self, url: str) -> CrawlResult:
        """
        Crawl a URL with guaranteed fallback to BeautifulSoup.

        This is the recommended method for production use.

        Args:
            url: URL to crawl

        Returns:
            CrawlResult with content from crawl4ai or BeautifulSoup
        """
        return await self.crawl_url(url, use_fallback=True)
