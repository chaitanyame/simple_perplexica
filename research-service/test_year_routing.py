"""Test year-specific query routing to SerperDev for precise temporal filtering.

This test verifies that:
1. Queries with specific years are detected
2. They are routed to SerperDev (not SearxNG)
3. Precise year filtering is applied via tbs parameter
4. Results are marked with higher relevance (0.85)
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.search_agent import SearchAgent, SearchAgentDeps, SubQuery
from src.services.llm.openrouter_client import OpenRouterClient


@pytest.mark.asyncio
async def test_year_specific_routing_to_serperdev():
    """Test that year-specific queries route to SerperDev for precise filtering."""

    # Mock dependencies
    llm_client = MagicMock(spec=OpenRouterClient)

    # Mock SerperDev response
    mock_serper_response = MagicMock()
    mock_serper_response.status_code = 200
    mock_serper_response.json.return_value = {
        "organic": [
            {
                "title": "AI Developments in 2023",
                "link": "https://example.com/ai-2023",
                "snippet": "Major AI developments from 2023...",
            },
            {
                "title": "2023 AI Research Highlights",
                "link": "https://example.com/research-2023",
                "snippet": "Key research breakthroughs in 2023...",
            },
        ]
    }

    deps = SearchAgentDeps(
        llm_client=llm_client,
        tracer=None,
        db=None,
        searxng_client=None,
        serperdev_api_key="test_api_key",  # Required for routing
        crawl_client=None,
        document_processor=None,
        embedding_service=None,
    )

    agent = SearchAgent(deps=deps)

    # Test sub-query with specific year
    sub_query = SubQuery(
        query="AI developments 2023",
        intent="factual",
        priority=1,
        temporal_scope="any",
        specific_year=2023,  # This triggers SerperDev routing
        language="en",
    )

    # Mock the SerperDev HTTP call
    with patch("httpx.AsyncClient") as mock_client:
        mock_context = AsyncMock()
        mock_context.__aenter__.return_value.post = AsyncMock(return_value=mock_serper_response)
        mock_client.return_value = mock_context

        # Execute search
        results = await agent._search_source(sub_query)

        # Verify results
        assert len(results) == 2
        assert results[0].title == "AI Developments in 2023"
        assert results[0].relevance == 0.85  # Higher relevance for year-specific
        assert results[1].title == "2023 AI Research Highlights"

        # Verify SerperDev was called with correct year filter
        call_args = mock_context.__aenter__.return_value.post.call_args
        assert call_args is not None
        json_payload = call_args.kwargs["json"]
        assert json_payload["q"] == "AI developments 2023"
        assert json_payload["tbs"] == "cdr:1,cd_min:1/1/2023,cd_max:12/31/2023"

        print("✅ Year-specific routing test passed!")
        print(f"   Query: {sub_query.query}")
        print(f"   Year: {sub_query.specific_year}")
        print(f"   Results: {len(results)}")
        print(f"   Relevance: {results[0].relevance}")


@pytest.mark.asyncio
async def test_non_year_query_uses_searxng():
    """Test that queries without specific years still use SearxNG."""

    # Mock dependencies
    llm_client = MagicMock(spec=OpenRouterClient)

    # Mock SearxNG client
    mock_searxng = MagicMock()
    mock_searxng.search = AsyncMock(
        return_value=[
            {
                "title": "General AI Article",
                "url": "https://example.com/ai",
                "content": "General AI information...",
            }
        ]
    )

    deps = SearchAgentDeps(
        llm_client=llm_client,
        tracer=None,
        db=None,
        searxng_client=mock_searxng,
        serperdev_api_key="test_api_key",
        crawl_client=None,
        document_processor=None,
        embedding_service=None,
    )

    agent = SearchAgent(deps=deps)

    # Test sub-query WITHOUT specific year
    sub_query = SubQuery(
        query="AI developments",
        intent="factual",
        priority=1,
        temporal_scope="any",
        specific_year=None,  # No year → should use SearxNG
        language="en",
    )

    # Execute search
    results = await agent._search_source(sub_query)

    # Verify SearxNG was used
    assert len(results) == 1
    assert results[0].title == "General AI Article"
    assert results[0].relevance == 0.7  # Standard relevance
    assert mock_searxng.search.called

    print("✅ Non-year query SearxNG test passed!")
    print(f"   Query: {sub_query.query}")
    print(f"   Year: {sub_query.specific_year}")
    print(f"   Results: {len(results)}")


if __name__ == "__main__":
    print("🧪 Testing Year-Specific Query Routing\n")
    asyncio.run(test_year_specific_routing_to_serperdev())
    print()
    asyncio.run(test_non_year_query_uses_searxng())
    print("\n✅ All routing tests passed!")
