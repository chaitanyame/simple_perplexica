"""Search orchestrator with 3-tier cascading fallback."""

import structlog
import asyncio
from typing import Optional, Union, Dict, Any

logger = structlog.get_logger()


class SearchOrchestrator:
    """
    Orchestrate search with 3-tier cascading fallback:
    1. SearxNG (Primary)
    2. SerperDev (Secondary Fallback)
    3. Perplexity (Tertiary Fallback - Complete Answer)
    """

    def __init__(
        self,
        searxng_client,  # Existing SearxNG client
        serperdev_client,  # SerperDev client
        perplexity_client,  # Perplexity client
        settings=None
    ):
        """
        Initialize search orchestrator.

        Args:
            searxng_client: SearxNG search client
            serperdev_client: SerperDev search client
            perplexity_client: Perplexity AI client
            settings: Configuration settings
        """
        self.searxng = searxng_client
        self.serperdev = serperdev_client
        self.perplexity = perplexity_client
        self.settings = settings

    async def search_with_fallback(
        self,
        query: str,
        force_provider: Optional[str] = None
    ) -> Union[Dict[str, Any], object]:
        """
        Execute search with cascading fallback.

        Cascade order:
        1. SearxNG (Primary) - if >= min_results, return
        2. SerperDev (Secondary) - if >= min_results, return
        3. Perplexity (Tertiary) - final fallback, returns complete answer

        Args:
            query: Search query
            force_provider: Optional - "perplexity" to bypass cascade

        Returns:
            Search result (format depends on provider used)
        """

        # ===== DIRECT MODE: Bypass cascade =====
        if force_provider == "perplexity":
            logger.info(
                "search_direct_perplexity",
                query=query[:100]
            )
            return await self._execute_perplexity(query)

        # ===== TIER 1: SearxNG (Primary) =====
        if self.searxng:
            try:
                logger.info("search_tier1_searxng", query=query[:100])

                result = await self.searxng.search(query)

                # Check if we have sufficient results
                result_count = len(result.get("results", []))
                min_results = getattr(self.settings, "searxng_min_results", 3) if self.settings else 3

                if result_count >= min_results:
                    logger.info(
                        "search_success_tier1",
                        source="searxng",
                        result_count=result_count
                    )
                    return {
                        "source": "searxng",
                        "tier": 1,
                        "results": result,
                        "is_final": False  # Needs LLM processing
                    }

                logger.warning(
                    "search_insufficient_tier1",
                    source="searxng",
                    result_count=result_count,
                    threshold=min_results
                )

            except Exception as e:
                logger.error(
                    "search_error_tier1",
                    source="searxng",
                    error=str(e)
                )

        # ===== TIER 2: SerperDev (Secondary Fallback) =====
        if self.serperdev:
            try:
                logger.info("search_tier2_serperdev", query=query[:100])

                result = await self.serperdev.search(query)

                # Check if we have sufficient results
                result_count = len(result.get("results", []))
                min_results = getattr(self.settings, "serperdev_min_results", 3) if self.settings else 3

                if result_count >= min_results:
                    logger.info(
                        "search_success_tier2",
                        source="serperdev",
                        result_count=result_count
                    )
                    return {
                        "source": "serperdev",
                        "tier": 2,
                        "results": result,
                        "is_final": False  # Needs LLM processing
                    }

                logger.warning(
                    "search_insufficient_tier2",
                    source="serperdev",
                    result_count=result_count,
                    threshold=min_results
                )

            except Exception as e:
                logger.error(
                    "search_error_tier2",
                    source="serperdev",
                    error=str(e)
                )

        # ===== TIER 3: Perplexity (Tertiary Fallback - FINAL) =====
        logger.info("search_tier3_perplexity", query=query[:100])
        return await self._execute_perplexity(query)

    async def _execute_perplexity(self, query: str):
        """
        Execute Perplexity search.

        Perplexity returns a COMPLETE answer with citations.
        No LLM processing needed after this.

        Args:
            query: Search query

        Returns:
            PerplexitySearchResult with complete answer
        """

        max_retries = getattr(self.settings, "perplexity_max_retries", 2) if self.settings else 2

        for attempt in range(max_retries + 1):
            try:
                # Call Perplexity API
                response = await self.perplexity.search(query)

                # Map citations to internal Citation model
                from src.utils.perplexity_mapper import PerplexityCitationMapper
                citations = PerplexityCitationMapper.map_citations(response["citations"])

                logger.info(
                    "search_success_tier3",
                    source="perplexity",
                    citation_count=len(citations),
                    content_length=len(response["content"])
                )

                # Return Perplexity result as-is (complete answer, no LLM needed)
                from src.models.perplexity import PerplexitySearchResult
                return PerplexitySearchResult(
                    answer=response["content"],
                    citations=citations,
                    source="perplexity",
                    is_final=True,  # Complete answer, no LLM processing needed
                    usage=response.get("usage", {}),
                    metadata={
                        "tier": 3,
                        "model": response.get("model", "sonar"),
                        "attempt": attempt + 1
                    }
                )

            except Exception as e:
                logger.error(
                    "perplexity_attempt_failed",
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e)
                )

                # Last attempt failed
                if attempt == max_retries:
                    return self._create_error_result(
                        "Unable to complete search request. "
                        "All search services temporarily unavailable. "
                        "Please try again."
                    )

                # Exponential backoff: 1s, 2s, 4s
                wait_time = 2 ** attempt
                logger.info(
                    "perplexity_retry",
                    wait_seconds=wait_time,
                    attempt=attempt + 1
                )
                await asyncio.sleep(wait_time)

        # Should not reach here, but just in case
        return self._create_error_result("Search request failed")

    def _create_error_result(self, message: str):
        """
        Create error result for graceful degradation.

        Args:
            message: Error message to return

        Returns:
            PerplexitySearchResult with error
        """
        from src.models.perplexity import PerplexitySearchResult
        return PerplexitySearchResult(
            answer=message,
            citations=[],
            source="error",
            is_final=True,
            metadata={"error": True}
        )
