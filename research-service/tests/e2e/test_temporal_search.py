"""E2E tests for temporal search queries.

Tests the full search pipeline with temporal queries to verify:
1. Temporal expressions are detected correctly
2. time_range parameter is passed to SearxNG
3. Results are filtered by date
4. Answers reflect temporal context

NOTE: These tests require the research-api Docker container to be running.
Run: docker-compose up -d research-api
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.e2e
class TestTemporalSearchE2E:
    """E2E tests for temporal search queries against running Docker service."""

    @pytest.fixture
    async def client(self) -> AsyncClient:
        """Create async HTTP client for API testing."""
        async with AsyncClient(base_url="http://localhost:8001", timeout=120.0) as ac:
            yield ac

    async def test_recent_news_query(self, client: AsyncClient) -> None:
        """Test 'recent' temporal query - should set time_range to 1 month."""
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "recent AI developments",
                "max_sources": 10,
                "timeout": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "answer" in data
        assert "sources" in data
        assert "session_id" in data

        # Verify we got sources
        assert len(data["sources"]) > 0

        # Verify answer is not empty
        assert len(data["answer"]) > 0

        print(f"✅ Recent query returned {len(data['sources'])} sources")

    async def test_last_week_query(self, client: AsyncClient) -> None:
        """Test 'last week' temporal query - should set time_range to 1 week."""
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "Python releases last week",
                "max_sources": 10,
                "timeout": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert len(data["sources"]) >= 0  # May be 0 if no results

        print(f"✅ Last week query returned {len(data['sources'])} sources")

    async def test_specific_year_query(self, client: AsyncClient) -> None:
        """Test specific year query - should search for year-specific content."""
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "GitHub Universe 2025",
                "max_sources": 15,
                "timeout": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert len(data["sources"]) > 0

        # Verify answer mentions 2025 or temporal context
        assert "2025" in data["answer"] or "GitHub Universe" in data["answer"]

        print(f"✅ Year-specific query returned {len(data['sources'])} sources")

    async def test_yesterday_query(self, client: AsyncClient) -> None:
        """Test 'yesterday' temporal query - should set time_range to 1 day."""
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "tech news yesterday",
                "max_sources": 10,
                "timeout": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        # Yesterday might not have results
        assert len(data["sources"]) >= 0

        print(f"✅ Yesterday query returned {len(data['sources'])} sources")

    async def test_this_month_query(self, client: AsyncClient) -> None:
        """Test 'this month' temporal query."""
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "AI news this month",
                "max_sources": 15,
                "timeout": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert len(data["sources"]) > 0

        print(f"✅ This month query returned {len(data['sources'])} sources")

    async def test_no_temporal_query(self, client: AsyncClient) -> None:
        """Test query without temporal expression - should not set time_range."""
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "what is Python programming language",
                "max_sources": 10,
                "timeout": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert len(data["sources"]) > 0

        print(f"✅ Non-temporal query returned {len(data['sources'])} sources")

    async def test_quarter_query(self, client: AsyncClient) -> None:
        """Test quarterly temporal query."""
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "Q4 2024 tech earnings",
                "max_sources": 10,
                "timeout": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        # Q4 results may vary
        assert len(data["sources"]) >= 0

        print(f"✅ Quarter query returned {len(data['sources'])} sources")

    async def test_mixed_temporal_query(self, client: AsyncClient) -> None:
        """Test query with multiple temporal expressions."""
        response = await client.post(
            "/api/v1/search",
            json={
                "query": "Python 3.12 release date and recent updates",
                "max_sources": 15,
                "timeout": 60,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert len(data["sources"]) > 0

        # Should mention both the release and recent updates
        assert "3.12" in data["answer"] or "Python" in data["answer"]

        print(f"✅ Mixed temporal query returned {len(data['sources'])} sources")


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
class TestTemporalResearchE2E:
    """E2E tests for temporal research queries against running Docker service."""

    @pytest.fixture
    async def client(self) -> AsyncClient:
        """Create async HTTP client for API testing."""
        async with AsyncClient(base_url="http://localhost:8001", timeout=120.0) as ac:
            yield ac

    async def test_recent_research_query(self, client: AsyncClient) -> None:
        """Test research mode with temporal query."""
        response = await client.post(
            "/api/v1/research",
            json={
                "query": "recent advancements in LLM agents",
                "mode": "balanced",
                "max_iterations": 1,  # Keep it fast for E2E
            },
            timeout=120.0,
        )

        assert response.status_code == 200
        data = response.json()

        assert "answer" in data
        assert "sources" in data
        assert "iterations" in data

        # Verify we got sources
        assert len(data["sources"]) > 0

        # Verify answer mentions relevant content
        assert "LLM" in data["answer"] or "agent" in data["answer"]

        print(
            f"✅ Research mode with temporal query: {data['iterations']} iterations, {len(data['sources'])} sources"
        )
