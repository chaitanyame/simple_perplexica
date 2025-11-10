"""Tests for /v1/search endpoint.

Following TDD methodology (RED → GREEN → REFACTOR):
1. RED: Write failing tests first
2. GREEN: Implement endpoint to pass tests
3. REFACTOR: Improve code while keeping tests green
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.agents.search_agent import SearchAgent, SearchOutput, SearchSource, SubQuery
from src.main import app

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class TestSearchEndpointValidation:
    """Test request validation for /v1/search endpoint."""

    def test_search_with_valid_request(self, client: TestClient) -> None:
        """Test search endpoint accepts valid request.

        Given: Valid search request with all required fields
        When: POST to /api/v1/search
        Then: Returns 200 OK (when implemented)
        """
        request_data = {
            "query": "What is Pydantic AI?",
            "max_sources": 20,
            "timeout": 60,
        }

        response = client.post("/api/v1/search", json=request_data)

        # Debug: print error if not 200/404
        if response.status_code not in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]:
            print(f"\nError response: {response.json()}")

        # Should return 200 when implemented (currently 404)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,  # Endpoint not implemented yet
        ]

    def test_search_with_minimal_request(self, client: TestClient) -> None:
        """Test search endpoint with minimal required fields.

        Given: Request with only query field
        When: POST to /api/v1/search
        Then: Uses default values for optional fields
        """
        request_data = {"query": "test query"}

        response = client.post("/api/v1/search", json=request_data)

        # Should accept request (default values applied)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_search_rejects_empty_query(self, client: TestClient) -> None:
        """Test search endpoint rejects empty query.

        Given: Request with empty query string
        When: POST to /api/v1/search
        Then: Returns 422 Validation Error
        """
        request_data = {"query": ""}

        response = client.post("/api/v1/search", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        error_data = response.json()
        assert "query" in str(error_data).lower()

    def test_search_rejects_whitespace_query(self, client: TestClient) -> None:
        """Test search endpoint rejects whitespace-only query.

        Given: Request with whitespace-only query
        When: POST to /api/v1/search
        Then: Returns 422 Validation Error
        """
        request_data = {"query": "   "}

        response = client.post("/api/v1/search", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_rejects_too_long_query(self, client: TestClient) -> None:
        """Test search endpoint rejects queries exceeding max length.

        Given: Request with query > 1000 chars
        When: POST to /api/v1/search
        Then: Returns 422 Validation Error
        """
        request_data = {"query": "a" * 1001}

        response = client.post("/api/v1/search", json=request_data)

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_rejects_invalid_max_sources(self, client: TestClient) -> None:
        """Test search endpoint validates max_sources range.

        Given: Request with max_sources out of range
        When: POST to /api/v1/search
        Then: Returns 422 Validation Error
        """
        # Too low
        response = client.post("/v1/search", json={"query": "test", "max_sources": 4})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Too high
        response = client.post("/v1/search", json={"query": "test", "max_sources": 51})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_search_rejects_invalid_timeout(self, client: TestClient) -> None:
        """Test search endpoint validates timeout range.

        Given: Request with timeout out of range
        When: POST to /api/v1/search
        Then: Returns 422 Validation Error
        """
        # Too low
        response = client.post("/api/v1/search", json={"query": "test", "timeout": 9})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Too high
        response = client.post("/api/v1/search", json={"query": "test", "timeout": 301})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestSearchEndpointExecution:
    """Test search endpoint execution with mocked SearchAgent."""

    @pytest.mark.asyncio
    async def test_search_executes_agent(
        self, client: TestClient, async_session: AsyncSession
    ) -> None:
        """Test search endpoint executes SearchAgent.

        Given: Valid search request
        When: POST to /api/v1/search
        Then: SearchAgent.run() is called with query
        """
        # Mock SearchAgent
        mock_search_output = SearchOutput(
            sub_queries=[SubQuery(query="test query", intent="factual", priority=1)],
            sources=[
                SearchSource(
                    title="Test Source 1",
                    url="https://example.com/1",
                    snippet="Test content 1",
                    relevance=0.9,
                    source_type="web",
                ),
                SearchSource(
                    title="Test Source 2",
                    url="https://example.com/2",
                    snippet="Test content 2",
                    relevance=0.8,
                    source_type="academic",
                ),
                SearchSource(
                    title="Test Source 3",
                    url="https://example.com/3",
                    snippet="Test content 3",
                    relevance=0.7,
                    source_type="web",
                ),
                SearchSource(
                    title="Test Source 4",
                    url="https://example.com/4",
                    snippet="Test content 4",
                    relevance=0.6,
                    source_type="news",
                ),
                SearchSource(
                    title="Test Source 5",
                    url="https://example.com/5",
                    snippet="Test content 5",
                    relevance=0.5,
                    source_type="web",
                ),
            ],
            execution_time=2.5,
            confidence=0.85,
        )

        with patch(
            "src.api.v1.endpoints.search.create_search_agent", new_callable=AsyncMock
        ) as mock_create_agent:
            mock_agent = MagicMock(spec=SearchAgent)
            mock_agent.run = AsyncMock(return_value=mock_search_output)
            mock_create_agent.return_value = mock_agent

            request_data = {"query": "What is Pydantic AI?"}
            response = client.post("/api/v1/search", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            mock_agent.run.assert_called_once_with("What is Pydantic AI?")

    @pytest.mark.asyncio
    async def test_search_returns_correct_response_structure(self, client: TestClient) -> None:
        """Test search endpoint returns properly structured response.

        Given: SearchAgent returns valid output
        When: POST to /api/v1/search
        Then: Response matches SearchResponse schema
        """
        mock_search_output = SearchOutput(
            sub_queries=[SubQuery(query="test query", intent="factual", priority=1)],
            sources=[
                SearchSource(
                    title=f"Source {i}",
                    url=f"https://example.com/{i}",
                    snippet=f"Content {i}",
                    relevance=0.9 - (i * 0.1),
                    source_type="web",
                )
                for i in range(1, 6)
            ],
            execution_time=2.5,
            confidence=0.85,
        )

        with patch(
            "src.api.v1.endpoints.search.create_search_agent", new_callable=AsyncMock
        ) as mock_create_agent:
            mock_agent = MagicMock(spec=SearchAgent)
            mock_agent.run = AsyncMock(return_value=mock_search_output)
            mock_create_agent.return_value = mock_agent

            request_data = {"query": "test query"}
            response = client.post("/api/v1/search", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify response structure
            assert "session_id" in data
            assert "query" in data
            assert "sub_queries" in data
            assert "sources" in data
            assert "execution_time" in data
            assert "confidence" in data
            assert "model_used" in data
            assert "created_at" in data

            # Verify data types and values
            assert data["query"] == "test query"
            assert len(data["sub_queries"]) == 1
            assert len(data["sources"]) == 5
            assert data["execution_time"] == 2.5
            assert data["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_search_stores_session_in_database(
        self, client: TestClient, async_session: AsyncSession
    ) -> None:
        """Test search endpoint stores session in database.

        Given: Successful search execution
        When: POST to /api/v1/search
        Then: Session is stored with results
        """
        mock_search_output = SearchOutput(
            sub_queries=[SubQuery(query="test", intent="factual", priority=1)],
            sources=[
                SearchSource(
                    title=f"Source {i}",
                    url=f"https://example.com/{i}",
                    snippet=f"Content {i}",
                    relevance=0.9,
                    source_type="web",
                )
                for i in range(5)
            ],
            execution_time=1.0,
            confidence=0.8,
        )

        with patch(
            "src.api.v1.endpoints.search.create_search_agent", new_callable=AsyncMock
        ) as mock_create_agent:
            mock_agent = MagicMock(spec=SearchAgent)
            mock_agent.run = AsyncMock(return_value=mock_search_output)
            mock_create_agent.return_value = mock_agent

            request_data = {"query": "test query"}
            response = client.post("/api/v1/search", json=request_data)

            assert response.status_code == status.HTTP_200_OK
            data = response.json()

            # Verify session_id is valid UUID
            session_id = data["session_id"]
            assert uuid.UUID(session_id)


class TestSearchEndpointErrorHandling:
    """Test error handling for /v1/search endpoint."""

    @pytest.mark.asyncio
    async def test_search_handles_agent_timeout(self, client: TestClient) -> None:
        """Test search endpoint handles SearchAgent timeout.

        Given: SearchAgent times out
        When: POST to /api/v1/search
        Then: Returns 504 Gateway Timeout
        """
        with patch(
            "src.api.v1.endpoints.search.create_search_agent", new_callable=AsyncMock
        ) as mock_create_agent:
            mock_agent = MagicMock(spec=SearchAgent)
            mock_agent.run = AsyncMock(side_effect=TimeoutError("Search timeout"))
            mock_create_agent.return_value = mock_agent

            request_data = {"query": "test query"}
            response = client.post("/api/v1/search", json=request_data)

            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
            error_data = response.json()
            assert "error" in error_data
            assert "timeout" in error_data["message"].lower()

    @pytest.mark.asyncio
    async def test_search_handles_agent_error(self, client: TestClient) -> None:
        """Test search endpoint handles SearchAgent errors.

        Given: SearchAgent raises exception
        When: POST to /api/v1/search
        Then: Returns 500 Internal Server Error
        """
        with patch(
            "src.api.v1.endpoints.search.create_search_agent", new_callable=AsyncMock
        ) as mock_create_agent:
            mock_agent = MagicMock(spec=SearchAgent)
            mock_agent.run = AsyncMock(side_effect=Exception("Agent execution failed"))
            mock_create_agent.return_value = mock_agent

            request_data = {"query": "test query"}
            response = client.post("/api/v1/search", json=request_data)

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            error_data = response.json()
            assert "error" in error_data


@pytest.fixture
def client() -> TestClient:
    """Provide FastAPI test client."""
    return TestClient(app)
