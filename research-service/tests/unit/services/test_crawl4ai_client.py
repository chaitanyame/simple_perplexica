"""Tests for Crawl4AI web crawler client.

Following TDD approach:
1. RED: Write failing tests first
2. GREEN: Implement to pass tests
3. REFACTOR: Clean up code
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.services.crawl.crawl4ai_client import (
    Crawl4AIClient,
    CrawledPage,
    CrawlError,
)


class TestCrawl4AIClientInitialization:
    """Test Crawl4AI client initialization."""

    @pytest.fixture
    def client(self) -> Crawl4AIClient:
        """Create a Crawl4AIClient instance."""
        return Crawl4AIClient()

    def test_initialize_with_defaults(self, client: Crawl4AIClient) -> None:
        """Test initialization with default parameters."""
        assert client.headless is True
        assert client.browser_type == "chromium"
        assert client.max_concurrent == 3
        assert client.timeout == 30

    def test_initialize_with_custom_params(self) -> None:
        """Test initialization with custom parameters."""
        client = Crawl4AIClient(
            headless=False,
            browser_type="firefox",
            max_concurrent=5,
            timeout=60,
        )

        assert client.headless is False
        assert client.browser_type == "firefox"
        assert client.max_concurrent == 5
        assert client.timeout == 60


class TestCrawl4AIClientSingleURL:
    """Test single URL crawling."""

    @pytest.fixture
    def client(self) -> Crawl4AIClient:
        """Create a Crawl4AIClient instance."""
        return Crawl4AIClient()

    @pytest.fixture
    def mock_crawl_result(self) -> Mock:
        """Create a mock CrawlResult from Crawl4AI."""
        result = Mock()
        result.success = True
        result.url = "https://example.com"
        result.html = "<html><body><h1>Test</h1><p>Content here.</p></body></html>"
        result.cleaned_html = "<h1>Test</h1><p>Content here.</p>"
        result.markdown = "# Test\n\nContent here."
        result.media = {"images": [{"src": "image.jpg", "alt": "Test"}]}
        result.links = {"internal": ["https://example.com/page"], "external": []}
        result.metadata = {"title": "Test Page", "description": "Test"}
        result.error_message = None
        return result

    @pytest.mark.asyncio
    async def test_crawl_url_success(self, client: Crawl4AIClient, mock_crawl_result: Mock) -> None:
        """Test successful URL crawling."""
        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_crawl_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            result = await client.crawl_url("https://example.com")

            assert isinstance(result, CrawledPage)
            assert result.url == "https://example.com"
            assert result.html == mock_crawl_result.html
            assert result.markdown == mock_crawl_result.markdown
            assert result.success is True
            assert len(result.images) > 0
            assert result.metadata["title"] == "Test Page"

    @pytest.mark.asyncio
    async def test_crawl_url_with_css_selector(
        self, client: Crawl4AIClient, mock_crawl_result: Mock
    ) -> None:
        """Test crawling with CSS selector filtering."""
        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_crawl_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            result = await client.crawl_url("https://example.com", css_selector="article.content")

            assert result.success is True
            # Verify CrawlerRunConfig was created with css_selector
            mock_crawler.arun.assert_called_once()
            call_kwargs = mock_crawler.arun.call_args.kwargs
            assert "config" in call_kwargs

    @pytest.mark.asyncio
    async def test_crawl_url_with_wait_for(
        self, client: Crawl4AIClient, mock_crawl_result: Mock
    ) -> None:
        """Test crawling with wait_for condition."""
        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_crawl_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            result = await client.crawl_url("https://example.com", wait_for="css:.loaded")

            assert result.success is True

    @pytest.mark.asyncio
    async def test_crawl_url_failure(self, client: Crawl4AIClient) -> None:
        """Test handling of crawl failure."""
        mock_result = Mock()
        mock_result.success = False
        mock_result.error_message = "Connection timeout"
        mock_result.url = "https://example.com"
        mock_result.html = ""
        mock_result.markdown = ""

        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            with pytest.raises(CrawlError) as exc_info:
                await client.crawl_url("https://example.com")

            assert "Connection timeout" in str(exc_info.value)


class TestCrawl4AIClientMultipleURLs:
    """Test multiple URL crawling."""

    @pytest.fixture
    def client(self) -> Crawl4AIClient:
        """Create a Crawl4AIClient instance."""
        return Crawl4AIClient()

    @pytest.mark.asyncio
    async def test_crawl_multiple_urls_success(self, client: Crawl4AIClient) -> None:
        """Test successful crawling of multiple URLs."""
        mock_results = []
        for i in range(3):
            result = Mock()
            result.success = True
            result.url = f"https://example.com/page{i}"
            result.html = f"<html><body>Page {i}</body></html>"
            result.cleaned_html = f"<body>Page {i}</body>"
            result.markdown = f"# Page {i}"
            result.media = {"images": []}
            result.links = {"internal": [], "external": []}
            result.metadata = {"title": f"Page {i}"}
            result.error_message = None
            mock_results.append(result)

        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun_many.return_value = mock_results
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            urls = [f"https://example.com/page{i}" for i in range(3)]
            results = await client.crawl_multiple_urls(urls)

            assert len(results) == 3
            assert all(isinstance(r, CrawledPage) for r in results)
            assert all(r.success for r in results)
            assert results[0].url == "https://example.com/page0"
            assert results[2].url == "https://example.com/page2"

    @pytest.mark.asyncio
    async def test_crawl_multiple_urls_with_failures(self, client: Crawl4AIClient) -> None:
        """Test crawling multiple URLs with some failures."""
        mock_results = [
            Mock(
                success=True,
                url="https://example.com/page0",
                html="<html><body>Success</body></html>",
                cleaned_html="<body>Success</body>",
                markdown="Success",
                media={"images": []},
                links={"internal": [], "external": []},
                metadata={"title": "Success"},
                error_message=None,
            ),
            Mock(
                success=False,
                url="https://example.com/page1",
                html="",
                cleaned_html="",
                markdown="",
                media={"images": []},
                links={"internal": [], "external": []},
                metadata={},
                error_message="404 Not Found",
            ),
            Mock(
                success=True,
                url="https://example.com/page2",
                html="<html><body>Success 2</body></html>",
                cleaned_html="<body>Success 2</body>",
                markdown="Success 2",
                media={"images": []},
                links={"internal": [], "external": []},
                metadata={"title": "Success 2"},
                error_message=None,
            ),
        ]

        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun_many.return_value = mock_results
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            urls = [f"https://example.com/page{i}" for i in range(3)]
            results = await client.crawl_multiple_urls(urls, skip_failed=True)

            # Should return all results, including failures
            assert len(results) == 3
            assert results[0].success is True
            assert results[1].success is False
            assert results[2].success is True


class TestCrawl4AIClientErrorHandling:
    """Test error handling in Crawl4AI client."""

    @pytest.fixture
    def client(self) -> Crawl4AIClient:
        """Create a Crawl4AIClient instance."""
        return Crawl4AIClient()

    @pytest.mark.asyncio
    async def test_invalid_url(self, client: Crawl4AIClient) -> None:
        """Test handling of invalid URL."""
        with pytest.raises(CrawlError) as exc_info:
            await client.crawl_url("not-a-valid-url")

        assert "invalid url" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_timeout_error(self, client: Crawl4AIClient) -> None:
        """Test handling of timeout errors."""
        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.side_effect = TimeoutError("Request timeout")
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            with pytest.raises(CrawlError) as exc_info:
                await client.crawl_url("https://example.com")

            assert "timeout" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_network_error(self, client: Crawl4AIClient) -> None:
        """Test handling of network errors."""
        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.side_effect = Exception("Network unreachable")
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            with pytest.raises(CrawlError) as exc_info:
                await client.crawl_url("https://example.com")

            assert "network unreachable" in str(exc_info.value).lower()


class TestCrawledPageDataclass:
    """Test CrawledPage dataclass."""

    def test_create_crawled_page(self) -> None:
        """Test creating a CrawledPage instance."""
        page = CrawledPage(
            url="https://example.com",
            html="<html><body>Test</body></html>",
            markdown="# Test",
            success=True,
            images=[{"src": "image.jpg", "alt": "Test"}],
            links=["https://example.com/page"],
            metadata={"title": "Test Page"},
            error_message=None,
        )

        assert page.url == "https://example.com"
        assert page.success is True
        assert len(page.images) == 1
        assert page.metadata["title"] == "Test Page"

    def test_crawled_page_with_error(self) -> None:
        """Test CrawledPage with error."""
        page = CrawledPage(
            url="https://example.com",
            html="",
            markdown="",
            success=False,
            images=[],
            links=[],
            metadata={},
            error_message="404 Not Found",
        )

        assert page.success is False
        assert page.error_message == "404 Not Found"


class TestCrawl4AIClientExtraction:
    """Test content extraction features."""

    @pytest.fixture
    def client(self) -> Crawl4AIClient:
        """Create a Crawl4AIClient instance."""
        return Crawl4AIClient()

    @pytest.mark.asyncio
    async def test_extract_with_word_threshold(self, client: Crawl4AIClient) -> None:
        """Test extraction with word count threshold."""
        mock_result = Mock()
        mock_result.success = True
        mock_result.url = "https://example.com"
        mock_result.html = "<html><body>Test content</body></html>"
        mock_result.cleaned_html = "Test content"
        mock_result.markdown = "Test content"
        mock_result.media = {"images": []}
        mock_result.links = {"internal": [], "external": []}
        mock_result.metadata = {"title": "Test"}
        mock_result.error_message = None

        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            result = await client.crawl_url("https://example.com", word_count_threshold=50)

            assert result.success is True

    @pytest.mark.asyncio
    async def test_extract_images(self, client: Crawl4AIClient) -> None:
        """Test image extraction from page."""
        mock_result = Mock()
        mock_result.success = True
        mock_result.url = "https://example.com"
        mock_result.html = "<html><body><img src='test.jpg'></body></html>"
        mock_result.cleaned_html = "<img src='test.jpg'>"
        mock_result.markdown = "![](test.jpg)"
        mock_result.media = {
            "images": [
                {"src": "https://example.com/test.jpg", "alt": "Test image"},
                {"src": "https://example.com/logo.png", "alt": "Logo"},
            ]
        }
        mock_result.links = {"internal": [], "external": []}
        mock_result.metadata = {"title": "Images"}
        mock_result.error_message = None

        with patch("src.services.crawl.crawl4ai_client.AsyncWebCrawler") as mock_crawler_class:
            mock_crawler = AsyncMock()
            mock_crawler.arun.return_value = mock_result
            mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

            result = await client.crawl_url("https://example.com")

            assert len(result.images) == 2
            assert result.images[0]["src"] == "https://example.com/test.jpg"
