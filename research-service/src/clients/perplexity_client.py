"""Perplexity AI Chat Completions Client with Web Search."""

import httpx
import structlog
from typing import Optional

logger = structlog.get_logger()


class PerplexityClient:
    """Client for Perplexity AI chat completions with web search."""

    BASE_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "sonar",
        timeout: int = 30,
        search_context_size: str = "low"
    ):
        """
        Initialize Perplexity client.

        Args:
            api_key: Perplexity API key
            model: Model to use (default: "sonar")
            timeout: Request timeout in seconds
            search_context_size: "low", "medium", or "high" (affects citation depth)
        """
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.search_context_size = search_context_size

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )

    async def search(
        self,
        query: str,
        system_prompt: Optional[str] = None
    ) -> dict:
        """
        Execute search query via Perplexity chat completions.

        Perplexity API returns complete answer with citations already formatted.
        No additional processing needed at our end.

        Args:
            query: User search query
            system_prompt: Optional system prompt (uses default if None)

        Returns:
            {
                "content": str,  # Complete answer from Perplexity
                "citations": list[str],  # Citation URLs from Perplexity
                "model": str,
                "usage": dict
            }
        """

        # Default system prompt optimized for research answers
        if system_prompt is None:
            system_prompt = self._get_default_system_prompt()

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            "web_search_options": {
                "search_context_size": self.search_context_size
            }
        }

        logger.info(
            "perplexity_request",
            query=query[:100],
            model=self.model,
            search_context_size=self.search_context_size
        )

        try:
            response = await self.client.post(
                self.BASE_URL,
                json=payload
            )
            response.raise_for_status()

            result = response.json()

            # Parse response (Perplexity already formats everything)
            parsed = self._parse_response(result)

            logger.info(
                "perplexity_success",
                content_length=len(parsed["content"]),
                citation_count=len(parsed["citations"])
            )

            return parsed

        except httpx.HTTPError as e:
            logger.error("perplexity_error", error=str(e))
            raise

    def _parse_response(self, response: dict) -> dict:
        """
        Parse Perplexity API response.

        Perplexity returns complete answer with citations.
        Response format (OpenAI-compatible chat completions):
        {
            "id": "...",
            "model": "sonar",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": "Complete answer with citations..."
                },
                "finish_reason": "stop"
            }],
            "citations": [
                "https://source1.com",
                "https://source2.com"
            ],
            "usage": {
                "prompt_tokens": 123,
                "completion_tokens": 456,
                "total_tokens": 579
            }
        }
        """

        content = response["choices"][0]["message"]["content"]
        citations = response.get("citations", [])

        return {
            "content": content,
            "citations": citations,
            "model": response.get("model", self.model),
            "usage": response.get("usage", {})
        }

    def _get_default_system_prompt(self) -> str:
        """
        Default system prompt optimized for research-quality answers.
        """
        return """You are an expert research assistant providing comprehensive, well-structured answers.

REQUIREMENTS:
1. Provide detailed, accurate information based on recent, credible sources
2. Structure your response clearly with appropriate formatting
3. Include specific facts, figures, and examples with proper citations
4. Cite sources for all factual claims using the citations provided
5. Use markdown formatting for readability (headers, lists, bold, etc.)
6. Provide a complete, ready-to-consume answer
7. Include all relevant information from the search results

FORBIDDEN:
- Generic statements without citations
- Speculation without clearly labeling it as such

Output a comprehensive, well-structured answer."""

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
