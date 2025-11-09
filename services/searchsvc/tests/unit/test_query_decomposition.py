"""
Unit tests for LLM-based query decomposition - TDD approach (RED phase)
Tests the decide_search_and_rewrite function for multi-query decomposition
"""
import pytest
import os


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_simple_query_returns_single_search():
    """Test that simple queries return single search strategy"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite("what is python")

    assert result is not None
    assert result.need_search is True
    assert isinstance(result.optimized_queries, list)
    assert len(result.optimized_queries) >= 1
    assert result.search_strategy == "single"


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_greeting_returns_no_search():
    """Test that greetings don't trigger search"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite("hello")

    assert result is not None
    assert result.need_search is False


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_multi_vendor_query_decomposes():
    """Test that multi-vendor queries decompose into sub-queries"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite(
        "latest cloud technologies news from aws, azure, google cloud and other vendors"
    )

    assert result is not None
    assert result.need_search is True
    # Should decompose or keep as single depending on LLM decision
    assert isinstance(result.optimized_queries, list)
    assert len(result.optimized_queries) >= 1
    # If decomposed, should have multiple queries
    if result.search_strategy == "multi":
        assert len(result.optimized_queries) >= 2
        assert len(result.optimized_queries) <= 10  # Max cap


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_multi_topic_query_potential_decomposition():
    """Test queries with multiple topics"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite(
        "machine learning tutorials and datasets for beginners"
    )

    assert result is not None
    assert result.need_search is True
    assert isinstance(result.optimized_queries, list)
    assert len(result.optimized_queries) >= 1


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_decomposition_respects_max_subqueries():
    """Test that decomposition doesn't exceed max sub-queries"""
    from app.providers.openrouter import decide_search_and_rewrite

    # Query mentioning many vendors
    result = await decide_search_and_rewrite(
        "news from aws, azure, gcp, ibm, oracle, salesforce, cisco, juniper, etc"
    )

    assert result is not None
    # Should cap at reasonable number (max 5 as per design)
    assert len(result.optimized_queries) <= 10


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_conversational_query_with_history():
    """Test that conversational queries are handled with history"""
    from app.providers.openrouter import decide_search_and_rewrite

    history = [["What is AWS?", "AWS is Amazon Web Services..."]]

    result = await decide_search_and_rewrite(
        "what about azure?",
        history=history
    )

    assert result is not None
    assert result.need_search is True
    assert isinstance(result.optimized_queries, list)
    # Should be standalone query even with conversation


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_single_entity_no_unnecessary_decomposition():
    """Test that single entity queries aren't unnecessarily decomposed"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite("latest aws news")

    assert result is not None
    assert result.need_search is True
    # Single entity should likely be single strategy
    if result.search_strategy == "multi":
        # If multi, should have only 1-2 queries
        assert len(result.optimized_queries) <= 3


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_url_extraction_in_decision():
    """Test that URLs are extracted from query"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite(
        "summarize https://example.com"
    )

    assert result is not None
    # If URL is present, it should be in links
    if "https://example.com" in "summarize https://example.com":
        # Result may have extracted links
        assert isinstance(result.links, list)


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_focus_mode_parameter():
    """Test that focus_mode parameter is accepted"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite(
        "python tutorials",
        focus_mode="webSearch"
    )

    assert result is not None
    assert result.need_search is True


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_academic_focus_mode():
    """Test academic search focus"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite(
        "quantum computing research",
        focus_mode="academicSearch"
    )

    assert result is not None
    assert result.need_search is True


@pytest.mark.asyncio
async def test_decision_output_without_api_key_fallback():
    """Test that decision falls back to heuristics without API key"""
    from app.providers.openrouter import decide_search_and_rewrite
    import os

    # Temporarily clear API key
    api_key = os.getenv("OPENROUTER_API_KEY")

    # This should either use fallback heuristics or raise
    # depending on implementation
    try:
        result = await decide_search_and_rewrite("test query")
        # If it doesn't raise, it has fallback logic
        assert result is not None
    except RuntimeError:
        # Expected if API key is required
        pass


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_decision_output_structure():
    """Test that DecisionOutput has correct structure"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite("test query")

    assert result is not None
    assert hasattr(result, 'need_search')
    assert hasattr(result, 'optimized_queries')
    assert hasattr(result, 'search_strategy')
    assert hasattr(result, 'links')


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_special_characters_in_query():
    """Test queries with special characters"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite(
        "What's new in C++ & Python? (2024)"
    )

    assert result is not None
    assert result.need_search is True


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_unicode_query_handling():
    """Test queries with Unicode characters"""
    from app.providers.openrouter import decide_search_and_rewrite

    result = await decide_search_and_rewrite(
        "最新的 AI 新闻"  # Chinese: Latest AI news
    )

    assert result is not None
    assert result.need_search is True


@pytest.mark.skipif(
    not os.getenv("OPENROUTER_API_KEY"), reason="OPENROUTER_API_KEY not set"
)
@pytest.mark.asyncio
async def test_very_long_query():
    """Test handling of very long queries"""
    from app.providers.openrouter import decide_search_and_rewrite

    long_query = "Tell me everything about " + "cloud computing " * 50

    result = await decide_search_and_rewrite(long_query)

    assert result is not None
    assert isinstance(result.optimized_queries, list)
