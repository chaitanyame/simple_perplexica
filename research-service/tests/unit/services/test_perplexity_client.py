"""Tests for Perplexity AI client.

Following TDD principles - tests written BEFORE implementation.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import Response

from src.services.search.perplexity_client import (
    PerplexityClient,
    PerplexityError,
    PerplexityResponse,
    Citation,
)


@pytest.fixture
def mock_httpx_client():
    """Provide mocked httpx.AsyncClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_perplexity_response():
    """Provide sample Perplexity API response."""
    return {
        "id": "test-id",
        "model": "sonar-pro",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "AI agents are autonomous software systems [1]. They can perceive their environment and take actions [2]. Common examples include chatbots and recommendation systems [1]."
                },
                "finish_reason": "stop"
            }
        ],
        "citations": [
            "https://example.com/ai-agents-overview",
            "https://example.com/how-agents-work"
        ],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 150,
            "total_tokens": 200
        }
    }


class TestPerplexityClient:
    """Test suite for PerplexityClient."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_client_initialization_with_api_key(self):
        """Test client initializes with provided API key."""
        # Act
        client = PerplexityClient(api_key="test-key-123")
        
        # Assert
        assert client.api_key == "test-key-123"
        assert client.model == "sonar-pro"
    
    @pytest.mark.unit
    def test_client_initialization_without_api_key_raises_error(self):
        """Test client raises ValueError if no API key provided."""
        # Act & Assert
        with pytest.raises(ValueError, match="Perplexity API key required"):
            PerplexityClient(api_key=None)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_success_returns_formatted_response(
        self, mock_httpx_client, mock_perplexity_response
    ):
        """Test successful API call returns PerplexityResponse with citations."""
        # Arrange
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = mock_perplexity_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        client = PerplexityClient(api_key="test-key", http_client=mock_httpx_client)
        
        # Act
        result = await client.search("What are AI agents?")
        
        # Assert
        assert isinstance(result, PerplexityResponse)
        assert "AI agents are autonomous" in result.content
        assert len(result.citations) == 2
        assert result.model == "sonar-pro"
        assert result.citations[0].index == 1
        assert result.citations[0].url == "https://example.com/ai-agents-overview"
        assert result.citations[1].index == 2
        assert result.citations[1].url == "https://example.com/how-agents-work"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_sends_correct_payload(self, mock_httpx_client, mock_perplexity_response):
        """Test search sends properly formatted API request."""
        # Arrange
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = mock_perplexity_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        client = PerplexityClient(api_key="test-key", http_client=mock_httpx_client)
        
        # Act
        await client.search(
            query="test query",
            max_tokens=2000,
            temperature=0.3,
            search_recency_filter="week"
        )
        
        # Assert
        call_args = mock_httpx_client.post.call_args
        assert call_args[0][0] == "https://api.perplexity.ai/chat/completions"
        
        payload = call_args[1]["json"]
        assert payload["model"] == "sonar-pro"
        assert payload["max_tokens"] == 2000
        assert payload["temperature"] == 0.3
        assert payload["search_recency_filter"] == "week"
        assert payload["return_citations"] is True
        assert len(payload["messages"]) == 2
        assert payload["messages"][1]["content"] == "test query"
        
        headers = call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_with_domain_filter(self, mock_httpx_client, mock_perplexity_response):
        """Test search includes domain filter when provided."""
        # Arrange
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = mock_perplexity_response
        mock_response.raise_for_status = MagicMock()
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        client = PerplexityClient(api_key="test-key", http_client=mock_httpx_client)
        
        # Act
        await client.search(
            query="test query",
            search_domain_filter=["arxiv.org", "github.com"]
        )
        
        # Assert
        payload = mock_httpx_client.post.call_args[1]["json"]
        assert payload["search_domain_filter"] == ["arxiv.org", "github.com"]
    
    @pytest.mark.unit
    def test_extract_citations_from_content(self):
        """Test citation extraction from [1], [2] markers."""
        # Arrange
        content = "First fact [1]. Second fact [2]. Third fact [1]. Fourth fact [3]."
        citation_urls = [
            "https://source1.com",
            "https://source2.com",
            "https://source3.com"
        ]
        
        # Act
        citations = PerplexityClient._extract_citations(content, citation_urls)
        
        # Assert
        assert len(citations) == 3
        
        # Check citation 1 (mentioned twice)
        assert citations[0].index == 1
        assert citations[0].url == "https://source1.com"
        assert citations[0].mention_count == 2
        
        # Check citation 2 (mentioned once)
        assert citations[1].index == 2
        assert citations[1].url == "https://source2.com"
        assert citations[1].mention_count == 1
        
        # Check citation 3 (mentioned once)
        assert citations[2].index == 3
        assert citations[2].url == "https://source3.com"
        assert citations[2].mention_count == 1
    
    @pytest.mark.unit
    def test_extract_citations_handles_empty_content(self):
        """Test citation extraction with no markers."""
        # Arrange
        content = "No citations here."
        citation_urls = ["https://source1.com"]
        
        # Act
        citations = PerplexityClient._extract_citations(content, citation_urls)
        
        # Assert
        assert len(citations) == 0
    
    @pytest.mark.unit
    def test_extract_citations_handles_invalid_indices(self):
        """Test citation extraction ignores out-of-bounds indices."""
        # Arrange
        content = "Valid [1]. Invalid [5]. Another valid [2]."
        citation_urls = ["https://source1.com", "https://source2.com"]
        
        # Act
        citations = PerplexityClient._extract_citations(content, citation_urls)
        
        # Assert
        assert len(citations) == 2  # Only [1] and [2] are valid
        assert all(c.index <= 2 for c in citations)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_handles_api_error(self, mock_httpx_client):
        """Test PerplexityError raised on API failure after retries."""
        # Arrange
        mock_httpx_client.post = AsyncMock(side_effect=Exception("API connection error"))
        client = PerplexityClient(api_key="test-key", http_client=mock_httpx_client)
        
        # Act & Assert
        with pytest.raises(PerplexityError, match="Perplexity API failed"):
            await client.search("test query")
        
        # Should retry 3 times
        assert mock_httpx_client.post.call_count == 3
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_handles_http_error(self, mock_httpx_client):
        """Test PerplexityError raised on HTTP error status."""
        # Arrange
        mock_response = MagicMock(spec=Response)
        mock_response.raise_for_status.side_effect = Exception("HTTP 429 Rate Limit")
        mock_httpx_client.post = AsyncMock(return_value=mock_response)
        
        client = PerplexityClient(api_key="test-key", http_client=mock_httpx_client)
        
        # Act & Assert
        with pytest.raises(PerplexityError, match="Perplexity API failed"):
            await client.search("test query")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_search_retries_with_exponential_backoff(self, mock_httpx_client, mock_perplexity_response):
        """Test exponential backoff on transient failures."""
        # Arrange
        mock_response = MagicMock(spec=Response)
        mock_response.json.return_value = mock_perplexity_response
        mock_response.raise_for_status = MagicMock()
        
        # Fail twice, then succeed
        mock_httpx_client.post = AsyncMock(
            side_effect=[
                Exception("Timeout"),
                Exception("Timeout"),
                mock_response
            ]
        )
        
        client = PerplexityClient(api_key="test-key", http_client=mock_httpx_client)
        
        # Act
        result = await client.search("test query")
        
        # Assert
        assert isinstance(result, PerplexityResponse)
        assert mock_httpx_client.post.call_count == 3
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_closes_http_client_when_owned(self):
        """Test close method closes HTTP client when owned by instance."""
        # Arrange - Client creates its own HTTP client
        with patch('httpx.AsyncClient') as MockAsyncClient:
            mock_client = AsyncMock()
            MockAsyncClient.return_value = mock_client
            
            client = PerplexityClient(api_key="test-key")
            
            # Act
            await client.close()
            
            # Assert
            mock_client.aclose.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_close_does_not_close_external_client(self, mock_httpx_client):
        """Test close method does NOT close externally-provided HTTP client."""
        # Arrange - External client provided
        client = PerplexityClient(api_key="test-key", http_client=mock_httpx_client)
        
        # Act
        await client.close()
        
        # Assert - Should NOT close external client
        mock_httpx_client.aclose.assert_not_called()
    
    @pytest.mark.unit
    def test_parse_response_with_valid_data(self, mock_perplexity_response):
        """Test _parse_response extracts data correctly."""
        # Act
        result = PerplexityClient._parse_response(mock_perplexity_response)
        
        # Assert
        assert isinstance(result, PerplexityResponse)
        assert "AI agents are autonomous" in result.content
        assert len(result.citations) == 2
        assert result.model == "sonar-pro"
    
    @pytest.mark.unit
    def test_parse_response_without_citations(self):
        """Test _parse_response handles missing citations."""
        # Arrange
        response_data = {
            "model": "sonar-pro",
            "choices": [
                {
                    "message": {
                        "content": "Content without citations."
                    }
                }
            ]
        }
        
        # Act
        result = PerplexityClient._parse_response(response_data)
        
        # Assert
        assert result.content == "Content without citations."
        assert len(result.citations) == 0


class TestCitation:
    """Test suite for Citation dataclass."""
    
    @pytest.mark.unit
    def test_citation_initialization(self):
        """Test Citation initializes with correct fields."""
        # Act
        citation = Citation(index=1, url="https://example.com", mention_count=3)
        
        # Assert
        assert citation.index == 1
        assert citation.url == "https://example.com"
        assert citation.mention_count == 3
    
    @pytest.mark.unit
    def test_citation_default_mention_count(self):
        """Test Citation defaults mention_count to 0."""
        # Act
        citation = Citation(index=1, url="https://example.com")
        
        # Assert
        assert citation.mention_count == 0


class TestPerplexityResponse:
    """Test suite for PerplexityResponse model."""
    
    @pytest.mark.unit
    def test_perplexity_response_initialization(self):
        """Test PerplexityResponse validates fields."""
        # Act
        response = PerplexityResponse(
            content="Test content [1].",
            citations=[Citation(index=1, url="https://example.com", mention_count=1)],
            model="sonar-pro"
        )
        
        # Assert
        assert response.content == "Test content [1]."
        assert len(response.citations) == 1
        assert response.model == "sonar-pro"
    
    @pytest.mark.unit
    def test_perplexity_response_empty_citations(self):
        """Test PerplexityResponse handles empty citations list."""
        # Act
        response = PerplexityResponse(
            content="Test content.",
            citations=[],
            model="sonar-pro"
        )
        
        # Assert
        assert len(response.citations) == 0
