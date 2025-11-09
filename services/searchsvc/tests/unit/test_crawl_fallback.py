"""
Unit tests for BeautifulSoup fallback - TDD approach (RED phase)
Tests fallback content fetching when crawl4ai fails
"""
import pytest
from unittest.mock import AsyncMock, patch, Mock


@pytest.mark.asyncio
async def test_fallback_fetch_returns_crawl_result():
    """Test that fallback returns proper CrawlResult"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    # Should not raise, should return CrawlResult even if fetch fails
    result = await fallback.fetch_as_markdown("https://example.com")

    assert result is not None
    assert hasattr(result, 'url')
    assert hasattr(result, 'markdown_content')
    assert hasattr(result, 'success')
    assert hasattr(result, 'source')
    assert result.source == "beautifulsoup"


@pytest.mark.asyncio
async def test_fallback_graceful_error_handling():
    """Test fallback handles errors gracefully"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    # Invalid URL should not crash
    result = await fallback.fetch_as_markdown("not-a-valid-url")

    assert result.success is False
    assert result.source == "beautifulsoup"


@pytest.mark.asyncio
async def test_fallback_timeout_handling():
    """Test fallback handles timeouts"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback(timeout=1)

    # Should handle timeout gracefully
    result = await fallback.fetch_as_markdown("https://httpbin.org/delay/10")

    assert result.success is False or result.markdown_content is None


@pytest.mark.asyncio
async def test_fallback_html_to_markdown_conversion():
    """Test conversion of HTML to markdown"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    # Mock HTML content
    html = "<html><body><h1>Title</h1><p>Content</p></body></html>"
    markdown = fallback._convert_to_markdown(html)

    assert markdown is not None
    assert "Title" in markdown
    assert "Content" in markdown
    assert "#" in markdown  # Should have heading marker


@pytest.mark.asyncio
async def test_fallback_removes_scripts_and_styles():
    """Test that fallback removes script and style tags"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    html = """
    <html>
    <head><style>body { color: red; }</style></head>
    <body>
    <script>alert('test');</script>
    <p>Real content</p>
    </body>
    </html>
    """

    markdown = fallback._convert_to_markdown(html)

    assert markdown is not None
    # Should not contain script content
    assert "alert" not in markdown.lower()
    # Should contain actual content
    assert "Real content" in markdown


@pytest.mark.asyncio
async def test_fallback_preserves_headings():
    """Test that heading hierarchy is preserved"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    html = """
    <html>
    <body>
    <h1>Main Title</h1>
    <h2>Subtitle</h2>
    <p>Content</p>
    </body>
    </html>
    """

    markdown = fallback._convert_to_markdown(html)

    assert markdown is not None
    assert "# Main Title" in markdown or "Main Title" in markdown
    assert "## Subtitle" in markdown or "Subtitle" in markdown


@pytest.mark.asyncio
async def test_fallback_markdown_has_basic_formatting():
    """Test that markdown includes basic formatting"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    html = """
    <html>
    <body>
    <p>Text with <strong>bold</strong> and <em>italic</em></p>
    <a href="https://example.com">link</a>
    </body>
    </html>
    """

    markdown = fallback._convert_to_markdown(html)

    assert markdown is not None
    assert ("**" in markdown or "bold" in markdown)  # Bold formatting
    assert ("*" in markdown or "italic" in markdown)  # Italic formatting


@pytest.mark.asyncio
async def test_fallback_with_custom_timeout():
    """Test that custom timeout is respected"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback_short = BeautifulSoupFallback(timeout=1)
    fallback_long = BeautifulSoupFallback(timeout=60)

    assert fallback_short.timeout == 1
    assert fallback_long.timeout == 60


@pytest.mark.asyncio
async def test_fallback_mocked_fetch(monkeypatch):
    """Test fallback with mocked HTTP fetch"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    # Mock the fetch
    async def mock_fetch(*args, **kwargs):
        return "<html><body><h1>Test</h1><p>Content</p></body></html>"

    monkeypatch.setattr(fallback, "_fetch_html", mock_fetch)

    result = await fallback.fetch_as_markdown("https://example.com")

    assert result.success is True
    assert "Test" in result.markdown_content or "Content" in result.markdown_content


@pytest.mark.asyncio
async def test_crawl_with_fallback_in_wrapper():
    """Test CrawlWrapper's crawl_with_fallback method"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()

    # crawl_with_fallback should use fallback
    result = await wrapper.crawl_with_fallback("https://example.com")

    assert result is not None
    assert hasattr(result, 'url')
    assert hasattr(result, 'markdown_content')
    assert hasattr(result, 'success')


@pytest.mark.asyncio
async def test_fallback_batch_crawl():
    """Test batch crawling with fallback"""
    from app.utils.crawl_urls import CrawlWrapper

    wrapper = CrawlWrapper()

    urls = [
        "https://example.com",
        "https://example.org",
    ]

    results = await wrapper.crawl_batch(urls)

    assert len(results) == len(urls)
    for result in results:
        assert hasattr(result, 'url')
        assert hasattr(result, 'success')


@pytest.mark.asyncio
async def test_fallback_empty_html():
    """Test fallback handles empty HTML"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    html = "<html><body></body></html>"
    markdown = fallback._convert_to_markdown(html)

    # Should return None or empty string for empty content
    assert markdown is None or markdown.strip() == ""


@pytest.mark.asyncio
async def test_fallback_preserves_lists():
    """Test that lists are preserved in markdown"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    html = """
    <html>
    <body>
    <ul>
    <li>Item 1</li>
    <li>Item 2</li>
    </ul>
    </body>
    </html>
    """

    markdown = fallback._convert_to_markdown(html)

    assert markdown is not None
    assert ("Item 1" in markdown and "Item 2" in markdown)
    assert ("-" in markdown or "*" in markdown)  # List marker


@pytest.mark.asyncio
async def test_fallback_handles_links():
    """Test that links are preserved"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    html = """
    <html>
    <body>
    <a href="https://example.com">Example Link</a>
    </body>
    </html>
    """

    markdown = fallback._convert_to_markdown(html)

    assert markdown is not None
    assert "Example Link" in markdown


@pytest.mark.asyncio
async def test_fallback_custom_headers():
    """Test that custom headers can be passed"""
    from app.utils.fallback_beautifulsoup import BeautifulSoupFallback

    fallback = BeautifulSoupFallback()

    # Should accept headers parameter without error
    result = await fallback.fetch_as_markdown(
        "https://example.com",
        headers={"User-Agent": "Mozilla/5.0"}
    )

    assert result is not None
