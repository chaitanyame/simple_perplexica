"""
BeautifulSoup-based fallback for content fetching.

This module provides fallback functionality when crawl4ai fails,
converting fetched HTML to markdown format similar to crawl4ai output.
"""

import logging
import asyncio
from typing import Optional

from bs4 import BeautifulSoup
import httpx

from .crawl_urls import CrawlResult

logger = logging.getLogger(__name__)


class BeautifulSoupFallback:
    """
    Fallback web crawler using BeautifulSoup for HTML parsing.
    Provides markdown output similar to crawl4ai for compatibility.
    """

    def __init__(self, timeout: int = 30):
        """
        Initialize BeautifulSoupFallback.

        Args:
            timeout: Timeout in seconds for HTTP requests
        """
        self.timeout = timeout

    async def fetch_as_markdown(
        self, url: str, headers: Optional[dict] = None
    ) -> CrawlResult:
        """
        Fetch a URL and convert HTML content to markdown.

        Args:
            url: URL to fetch
            headers: Optional custom HTTP headers

        Returns:
            CrawlResult with markdown content
        """
        try:
            # Fetch content
            html_content = await self._fetch_html(url, headers)
            if not html_content:
                return CrawlResult(
                    url=url,
                    markdown_content=None,
                    success=False,
                    source="beautifulsoup",
                    error="No HTML content received",
                )

            # Parse and convert to markdown
            markdown = self._convert_to_markdown(html_content)

            if not markdown or markdown.strip() == "":
                return CrawlResult(
                    url=url,
                    markdown_content=None,
                    success=False,
                    source="beautifulsoup",
                    error="Failed to extract text content",
                )

            return CrawlResult(
                url=url,
                markdown_content=markdown,
                success=True,
                source="beautifulsoup",
            )

        except Exception as e:
            logger.error(f"BeautifulSoup fetch error for {url}: {e}")
            return CrawlResult(
                url=url,
                markdown_content=None,
                success=False,
                source="beautifulsoup",
                error=str(e),
            )

    async def _fetch_html(
        self, url: str, headers: Optional[dict] = None
    ) -> Optional[str]:
        """
        Fetch HTML content from URL using httpx.

        Args:
            url: URL to fetch
            headers: Optional custom headers

        Returns:
            HTML content as string, or None if fetch fails
        """
        try:
            default_headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                )
            }
            if headers:
                default_headers.update(headers)

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=default_headers)
                response.raise_for_status()
                return response.text

        except asyncio.TimeoutError:
            logger.warning(f"Timeout fetching {url}")
            return None
        except httpx.HTTPError as e:
            logger.warning(f"HTTP error fetching {url}: {e}")
            return None

    def _convert_to_markdown(self, html_content: str) -> Optional[str]:
        """
        Convert HTML content to markdown format.

        Removes scripts, styles, navigation, headers, footers.
        Preserves heading hierarchy and text formatting.

        Args:
            html_content: Raw HTML content

        Returns:
            Markdown-formatted text, or None if conversion fails
        """
        try:
            soup = BeautifulSoup(html_content, "lxml")

            # Remove unwanted elements
            for tag in soup.find_all(
                ["script", "style", "nav", "header", "footer", "noscript"]
            ):
                tag.decompose()

            # Extract main content
            main_content = soup.find("main") or soup.find("article")
            if main_content:
                content = main_content
            else:
                # Fallback: use body if main/article not found
                content = soup.find("body") or soup

            # Convert to markdown-like format
            markdown = self._extract_markdown(content)

            # Clean up excessive whitespace
            lines = [line.strip() for line in markdown.split("\n")]
            lines = [line for line in lines if line]  # Remove empty lines
            cleaned = "\n\n".join(lines)  # Double newlines between paragraphs

            return cleaned if cleaned else None

        except Exception as e:
            logger.error(f"Error converting HTML to markdown: {e}")
            return None

    def _extract_markdown(self, element) -> str:
        """
        Recursively extract text from HTML elements in markdown format.

        Args:
            element: BeautifulSoup element to process

        Returns:
            Markdown-formatted text
        """
        markdown_parts = []

        for child in element.children:
            if isinstance(child, str):
                text = child.strip()
                if text:
                    markdown_parts.append(text)
            else:
                tag_name = child.name.lower() if hasattr(child, "name") else None

                if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    level = int(tag_name[1])
                    text = child.get_text(strip=True)
                    markdown_parts.append(f"{'#' * level} {text}")

                elif tag_name == "p":
                    text = child.get_text(strip=True)
                    if text:
                        markdown_parts.append(text)

                elif tag_name in ["li"]:
                    text = child.get_text(strip=True)
                    if text:
                        markdown_parts.append(f"- {text}")

                elif tag_name in ["strong", "b"]:
                    text = child.get_text(strip=True)
                    if text:
                        markdown_parts.append(f"**{text}**")

                elif tag_name in ["em", "i"]:
                    text = child.get_text(strip=True)
                    if text:
                        markdown_parts.append(f"*{text}*")

                elif tag_name == "a":
                    text = child.get_text(strip=True)
                    href = child.get("href", "")
                    if text and href:
                        markdown_parts.append(f"[{text}]({href})")
                    elif text:
                        markdown_parts.append(text)

                elif tag_name in ["ul", "ol"]:
                    # Lists are handled by their li children
                    markdown_parts.append(self._extract_markdown(child))

                elif tag_name == "img":
                    alt = child.get("alt", "")
                    src = child.get("src", "")
                    if alt:
                        markdown_parts.append(f"![{alt}]({src})")

                elif tag_name == "code":
                    text = child.get_text(strip=True)
                    if text:
                        markdown_parts.append(f"`{text}`")

                elif tag_name == "pre":
                    text = child.get_text(strip=True)
                    if text:
                        markdown_parts.append(f"```\n{text}\n```")

                else:
                    # For other tags, recursively process children
                    markdown_parts.append(self._extract_markdown(child))

        return "\n".join(markdown_parts)
