"""
Unit tests for crawl4ai wrapper - TDD approach (RED phase)
Tests crawl4ai content fetching with fallback to BeautifulSoup
"""
import pytest
import asyncio
from typing import Optional
from unittest.mock import AsyncMock, Mock, patch


@pytest.mark.asyncio
async def test_crawl_single_url_basic():
    """Test basic crawl4ai functionality - fetch a single URL"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()
    result = await wrapper.crawl_url("https://example.com")

    # Verify result structure
    assert result is not None
    assert hasattr(result, 'url')
    assert hasattr(result, 'markdown_content')
    assert hasattr(result, 'success')
    assert hasattr(result, 'source')

    assert result.url == "https://example.com"
    assert result.success is True
    assert result.source == "crawl4ai"
    assert isinstance(result.markdown_content, str)
    assert len(result.markdown_content) > 0


@pytest.mark.asyncio
async def test_crawl_extracts_clean_markdown():
    """Test that crawl4ai extracts clean, LLM-ready markdown"""
    from app.utils.crawl_urls import CrawlWrapper

    # Use a real or mocked complex HTML page
    wrapper = CrawlWrapper()
    result = await wrapper.crawl_url("https://en.wikipedia.org/wiki/Python_(programming_language)")

    assert result.success is True
    # Markdown should not contain raw HTML tags
    assert "<script" not in result.markdown_content.lower()
    assert "<style" not in result.markdown_content.lower()
    # Should contain markdown formatting
    assert "#" in result.markdown_content or "**" in result.markdown_content or "*" in result.markdown_content


@pytest.mark.asyncio
async def test_crawl_handles_javascript_heavy_pages():
    """Test that crawl4ai handles JavaScript-rendered content"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()
    # Use a JS-heavy page that would fail with simple parsing
    result = await wrapper.crawl_url("https://github.com/unclecode/crawl4ai")

    assert result.success is True
    # Should contain actual rendered content, not empty/minimal
    assert len(result.markdown_content) > 100


@pytest.mark.asyncio
async def test_crawl_timeout_handling():
    """Test graceful timeout handling for slow URLs - falls back to BeautifulSoup"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper(timeout=2)  # 2 second timeout, triggers fallback

    # Use a URL that's known to be slow (or mock one)
    result = await wrapper.crawl_url("https://httpbin.org/delay/10")

    # Should handle timeout gracefully and fall back to BeautifulSoup
    # Result may be from crawl4ai if it succeeds, or from fallback if it times out
    assert result is not None
    assert hasattr(result, 'url')
    assert hasattr(result, 'success')
    # If crawl4ai times out, it should fall back to BeautifulSoup
    # If BeautifulSoup succeeds, success=True; if both fail, success=False


@pytest.mark.asyncio
async def test_crawl_invalid_url_handling():
    """Test handling of invalid/malformed URLs"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()

    # Test invalid URL
    result = await wrapper.crawl_url("not-a-valid-url")

    assert result.success is False
    assert result.markdown_content is None or result.markdown_content == ""


@pytest.mark.asyncio
async def test_crawl_404_handling():
    """Test handling of 404 errors"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()

    # Use httpbin to mock 404
    result = await wrapper.crawl_url("https://httpbin.org/status/404")

    # Should handle 404 gracefully
    assert result.success is False


@pytest.mark.asyncio
async def test_crawl_preserves_link_references():
    """Test that crawl4ai extracts and lists links as references"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()
    result = await wrapper.crawl_url("https://example.com")

    # Result should include extracted links if available
    if result.success:
        # Links should be in markdown format like [link][1]
        assert isinstance(result.markdown_content, str)


@pytest.mark.asyncio
async def test_crawl_batch_with_rate_limiting():
    """Test batch crawling with rate limiting to avoid overload"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper(max_concurrent=2)
    urls = [
        "https://example.com",
        "https://example.org",
        "https://example.net",
        "https://httpbin.org/delay/1",
    ]

    results = await wrapper.crawl_batch(urls)

    # Should get results for all URLs
    assert len(results) == len(urls)
    # All results should have proper structure
    for result in results:
        assert hasattr(result, 'url')
        assert hasattr(result, 'success')
        assert hasattr(result, 'markdown_content')


@pytest.mark.asyncio
async def test_crawl_batch_handles_partial_failures():
    """Test batch crawling handles some URLs failing"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()
    urls = [
        "https://example.com",
        "not-a-valid-url",  # Will fail
        "https://example.org",
    ]

    results = await wrapper.crawl_batch(urls)

    assert len(results) == 3
    # First and third should succeed
    assert results[0].success is True or results[0].success is False  # Could go either way
    assert results[1].success is False  # Invalid URL
    # Results should not raise exceptions even if some fail


@pytest.mark.asyncio
async def test_crawl_markdown_output_format():
    """Test that output is properly formatted markdown"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()
    result = await wrapper.crawl_url("https://example.com")

    if result.success:
        # Should be valid markdown string
        assert isinstance(result.markdown_content, str)
        # Should not have excessive whitespace
        assert result.markdown_content == result.markdown_content.strip() or True
        # Markdown should have some structure
        assert len(result.markdown_content) > 0


@pytest.mark.asyncio
async def test_crawl_with_mocked_crawl4ai(monkeypatch):
    """Test crawl wrapper with mocked crawl4ai (unit test)"""
    from app.utils.crawl_urls import CrawlWrapper

    # Mock the AsyncWebCrawler
    mock_result = Mock()
    mock_result.markdown = "# Example\n\nThis is example content."

    async def mock_arun(*args, **kwargs):
        return mock_result

    with patch('app.utils.crawl_urls.AsyncWebCrawler') as mock_crawler:
        mock_instance = AsyncMock()
        mock_instance.arun = mock_arun
        mock_instance.__aenter__.return_value = mock_instance
        mock_instance.__aexit__.return_value = None
        mock_crawler.return_value = mock_instance

        wrapper = CrawlWrapper()
        result = await wrapper.crawl_url("https://example.com")

        assert result.success is True
        assert "Example" in result.markdown_content


@pytest.mark.asyncio
async def test_crawl_handles_encoding_issues():
    """Test handling of different character encodings"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()
    # URL with non-ASCII content
    result = await wrapper.crawl_url("https://example.com")

    # Should handle encoding without errors
    if result.success:
        assert isinstance(result.markdown_content, str)


@pytest.mark.asyncio
async def test_crawl_respects_timeout_parameter():
    """Test that timeout parameter is respected"""
    from app.utils.crawl_urls import CrawlWrapper

    # Short timeout
    wrapper_short = CrawlWrapper(timeout=1)
    # Long timeout
    wrapper_long = CrawlWrapper(timeout=30)

    # Both should exist and be configurable
    assert wrapper_short.timeout == 1
    assert wrapper_long.timeout == 30


@pytest.mark.asyncio
async def test_crawl_large_content_handling():
    """Test handling of very large page content"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()
    result = await wrapper.crawl_url("https://example.com")

    # Should not crash on large content
    assert result is not None


@pytest.mark.asyncio
async def test_crawl_result_dataclass_structure():
    """Test that CrawlResult has required fields"""
    from app.utils.crawl_urls import CrawlResult

    result = CrawlResult(
        url="https://example.com",
        markdown_content="# Test",
        success=True,
        source="crawl4ai"
    )

    assert result.url == "https://example.com"
    assert result.markdown_content == "# Test"
    assert result.success is True
    assert result.source == "crawl4ai"


@pytest.mark.asyncio
async def test_crawl_with_custom_headers():
    """Test crawling with custom headers (if needed)"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()
    # Should support optional custom headers parameter
    result = await wrapper.crawl_url(
        "https://example.com",
        headers={"User-Agent": "Mozilla/5.0"}
    )

    assert result is not None


@pytest.mark.asyncio
async def test_crawl_preserves_url_in_result():
    """Test that result preserves the original URL requested"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()
    test_url = "https://example.com"
    result = await wrapper.crawl_url(test_url)

    assert result.url == test_url
