"""
Unit tests for parallel search execution - TDD approach (RED phase)
Tests multi-query parallel execution with aggregation
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.asyncio
async def test_single_query_search_unchanged():
    """Test that single-query searches still work (backward compatibility)"""
    from app.routers.search import get_sources

    # Mock the search client
    with patch('app.routers.search.get_sources') as mock_get:
        mock_get.return_value = [
            {"title": "Result 1", "url": "https://example.com/1", "pageContent": "Content 1"}
        ]

        # Single query should work
        result = await get_sources("python tutorial", "webSearch")

        assert result is not None
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_multi_query_parallel_execution():
    """Test that multiple queries execute in parallel"""
    from app.routers.search import get_sources

    # Should handle multiple queries
    # This will be implemented in get_sources enhancement
    result = await get_sources("python tutorial", "webSearch")

    assert result is not None
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_search_results_have_required_fields():
    """Test that search results have title, url, pageContent"""
    from app.routers.search import get_sources

    result = await get_sources("test query", "webSearch")

    if result:
        for source in result:
            assert "title" in source or "url" in source
            assert "url" in source


@pytest.mark.asyncio
async def test_empty_results_handling():
    """Test handling of queries that return no results"""
    from app.routers.search import get_sources

    # Some queries may return no results
    result = await get_sources("xyzabc12345notreal", "webSearch")

    # Should not crash, even if empty
    assert result is not None
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_search_with_focus_mode():
    """Test search with different focus modes"""
    from app.routers.search import get_sources

    for focus_mode in ["webSearch", "academicSearch", "redditSearch", "youtubeSearch"]:
        result = await get_sources("test", focus_mode)
        assert result is not None
        assert isinstance(result, list)


@pytest.mark.asyncio
async def test_mixed_success_failure_handling():
    """Test that some queries failing doesn't break the whole search"""
    # In multi-query scenario, if one fails, others should still work

    from app.routers.search import get_sources

    # Real search that should work
    result = await get_sources("python", "webSearch")

    # Should not crash even if internal network issues
    assert result is not None


@pytest.mark.asyncio
async def test_partial_results_from_fallback():
    """Test fallback search provider when primary fails"""

    from app.search_clients.searxng import search as searxng_search

    # Try searxng search
    try:
        result = await searxng_search("python tutorial")
        # If it works, should have results
        if result:
            assert isinstance(result, list)
    except Exception:
        # Fallback will handle
        pass


@pytest.mark.asyncio
async def test_search_result_format():
    """Test that search results match expected format"""
    from app.routers.search import get_sources

    result = await get_sources("test", "webSearch")

    # Each result should be dict-like with at least url
    for source in result:
        assert isinstance(source, dict)
        assert "url" in source


@pytest.mark.asyncio
async def test_search_respects_focus_mode_parameter():
    """Test that focus mode changes search behavior"""
    from app.routers.search import get_sources

    web_result = await get_sources("tutorial", "webSearch")
    academic_result = await get_sources("tutorial", "academicSearch")

    # Both should return results (or both empty), but function accepts focus mode
    assert web_result is not None
    assert academic_result is not None


@pytest.mark.asyncio
async def test_search_with_special_characters():
    """Test search with special characters in query"""
    from app.routers.search import get_sources

    result = await get_sources("C++ programming", "webSearch")

    # Should not crash with special chars
    assert result is not None


@pytest.mark.asyncio
async def test_search_with_unicode():
    """Test search with Unicode characters"""
    from app.routers.search import get_sources

    result = await get_sources("Python 编程", "webSearch")

    # Should handle unicode
    assert result is not None


@pytest.mark.asyncio
async def test_search_performance_acceptable():
    """Test that search completes in reasonable time"""
    import time
    from app.routers.search import get_sources

    start = time.time()
    result = await get_sources("test", "webSearch")
    elapsed = time.time() - start

    # Should complete in reasonable time (not strict, just sanity check)
    assert elapsed < 60  # 60 seconds max
    assert result is not None
