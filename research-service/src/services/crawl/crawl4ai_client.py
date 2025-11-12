"""Crawl4AI web crawler client for content extraction.

This module provides async web crawling using Crawl4AI library
for extracting content from web pages.

Features:
- Async web crawling with Crawl4AI
- Single and multiple URL support
- Content filtering with CSS selectors
- Image and link extraction
- Metadata extraction
- Error handling and retries
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import structlog
from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig

logger = structlog.get_logger(__name__)


class CrawlError(Exception):
    """Exception raised when web crawling fails."""

    pass


@dataclass
class CrawledPage:
    """Crawled page with content and metadata."""

    url: str
    html: str
    markdown: str
    success: bool
    images: list[dict[str, Any]] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class Crawl4AIClient:
    """Web crawler client using Crawl4AI for content extraction.

    Supports:
    - Single and multiple URL crawling
    - CSS selector filtering
    - Wait conditions for dynamic content
    - Image and link extraction
    - Metadata extraction

    Example:
        >>> client = Crawl4AIClient()
        >>> result = await client.crawl_url("https://example.com")
        >>> print(result.markdown[:100])
        >>> print(f"Found {len(result.images)} images")
    """

    def __init__(
        self,
        headless: bool = True,
        browser_type: str = "chromium",
        max_concurrent: int = 3,
        timeout: int = 30,
    ):
        """Initialize Crawl4AI client.

        Args:
            headless: Run browser in headless mode (default: True)
            browser_type: Browser to use - chromium, firefox, webkit (default: chromium)
            max_concurrent: Maximum concurrent crawls (default: 3)
            timeout: Request timeout in seconds (default: 30)
        """
        self.headless = headless
        self.browser_type = browser_type
        self.max_concurrent = max_concurrent
        self.timeout = timeout

        logger.info(
            "Crawl4AIClient initialized",
            headless=headless,
            browser_type=browser_type,
            max_concurrent=max_concurrent,
            timeout=timeout,
        )

    async def crawl_url(
        self,
        url: str,
        css_selector: str | None = None,
        wait_for: str | None = None,
        word_count_threshold: int | None = None,
    ) -> CrawledPage:
        """Crawl a single URL and extract content.

        Args:
            url: URL to crawl
            css_selector: Optional CSS selector to filter content
            wait_for: Optional wait condition (e.g., "css:.loaded")
            word_count_threshold: Minimum word count for content blocks

        Returns:
            CrawledPage with content and metadata

        Raises:
            CrawlError: If crawling fails
        """
        # Validate URL
        if not self._is_valid_url(url):
            raise CrawlError(f"Invalid URL: {url}")

        logger.info(f"Crawling URL: {url}", css_selector=css_selector, wait_for=wait_for)

        try:
            # Create browser config
            browser_config = BrowserConfig(
                browser_type=self.browser_type,
                headless=self.headless,
                verbose=False,
            )

            # Create crawler run config with intelligent content extraction
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                css_selector=css_selector,
                wait_for=wait_for,
                word_count_threshold=word_count_threshold or 200,  # Filter short nav blocks
                # Crawl4AI's built-in intelligence to filter navigation/menus
                excluded_tags=['nav', 'header', 'footer', 'aside', 'form'],  # Remove navigation elements
                remove_forms=True,  # Remove forms (search boxes, etc.)
                remove_overlay_elements=True,  # Remove popups/overlays
                magic=True,  # Enable Crawl4AI's intelligent content extraction
            )

            # Crawl with context manager
            async with AsyncWebCrawler(config=browser_config) as crawler:
                result = await crawler.arun(url=url, config=run_config)

                if not result.success:
                    error_msg = result.error_message or "Unknown crawl error"
                    logger.error(f"Crawl failed: {error_msg}", url=url)
                    raise CrawlError(f"Failed to crawl {url}: {error_msg}")

                # Extract images
                images = []
                if result.media and "images" in result.media:
                    images = result.media["images"]

                # Extract links
                links = []
                if result.links:
                    if isinstance(result.links, dict):
                        # Flatten internal and external links
                        links.extend(result.links.get("internal", []))
                        links.extend(result.links.get("external", []))
                    elif isinstance(result.links, list):
                        links = result.links

                # Extract metadata
                metadata = result.metadata if result.metadata else {}

                logger.info(
                    "Crawl successful",
                    url=result.url,
                    html_length=len(result.html),
                    images=len(images),
                    links=len(links),
                )

                return CrawledPage(
                    url=result.url,
                    html=result.html,
                    markdown=result.markdown or "",
                    success=True,
                    images=images,
                    links=links,
                    metadata=metadata,
                    error_message=None,
                )

        except TimeoutError as e:
            logger.error(f"Timeout crawling URL: {e}", url=url)
            raise CrawlError(f"Timeout crawling {url}: {e}") from e
        except Exception as e:
            logger.error(f"Error crawling URL: {e}", url=url)
            raise CrawlError(f"Error crawling {url}: {e}") from e

    async def crawl_multiple_urls(
        self,
        urls: list[str],
        css_selector: str | None = None,
        wait_for: str | None = None,
        skip_failed: bool = True,
    ) -> list[CrawledPage]:
        """Crawl multiple URLs concurrently.

        Args:
            urls: List of URLs to crawl
            css_selector: Optional CSS selector to filter content
            wait_for: Optional wait condition
            skip_failed: If True, continue on failures (default: True)

        Returns:
            List of CrawledPage results

        Raises:
            CrawlError: If crawling fails and skip_failed is False
        """
        logger.info(f"Crawling {len(urls)} URLs", skip_failed=skip_failed)

        try:
            # Create browser config
            browser_config = BrowserConfig(
                browser_type=self.browser_type,
                headless=self.headless,
                verbose=False,
            )

            # Create crawler run config
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                css_selector=css_selector,
                wait_for=wait_for,
            )

            # Crawl with context manager
            async with AsyncWebCrawler(config=browser_config) as crawler:
                results = await crawler.arun_many(urls=urls, config=run_config)

                crawled_pages = []
                for result in results:
                    # Extract images
                    images = []
                    if result.media and "images" in result.media:
                        images = result.media["images"]

                    # Extract links
                    links = []
                    if result.links:
                        if isinstance(result.links, dict):
                            links.extend(result.links.get("internal", []))
                            links.extend(result.links.get("external", []))
                        elif isinstance(result.links, list):
                            links = result.links

                    # Extract metadata
                    metadata = result.metadata if result.metadata else {}

                    crawled_page = CrawledPage(
                        url=result.url,
                        html=result.html,
                        markdown=result.markdown or "",
                        success=result.success,
                        images=images,
                        links=links,
                        metadata=metadata,
                        error_message=result.error_message if not result.success else None,
                    )
                    crawled_pages.append(crawled_page)

                    if result.success:
                        logger.info(f"Crawled successfully: {result.url}")
                    else:
                        logger.warning(
                            f"Crawl failed: {result.url}",
                            error=result.error_message,
                        )

                successful = sum(1 for p in crawled_pages if p.success)
                logger.info(
                    f"Crawled {len(urls)} URLs",
                    successful=successful,
                    failed=len(urls) - successful,
                )

                return crawled_pages

        except Exception as e:
            logger.error(f"Error crawling multiple URLs: {e}")
            raise CrawlError(f"Error crawling multiple URLs: {e}") from e

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if URL is valid, False otherwise
        """
        # Simple URL validation
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # or IP
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        return bool(url_pattern.match(url))
