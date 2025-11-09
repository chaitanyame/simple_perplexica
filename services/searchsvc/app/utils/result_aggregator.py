"""
Result aggregation for multi-query search.

Handles:
- Deduplication of URLs across queries
- Diversity filtering to prevent one query dominating results
- Per-query result limiting
- Quality-based result ordering
"""

import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class ResultAggregator:
    """
    Aggregates results from multiple search queries.

    Handles deduplication, diversity filtering, and per-query limiting.
    """

    def __init__(self, max_per_domain: int = 3):
        """
        Initialize ResultAggregator.

        Args:
            max_per_domain: Maximum results from any single domain
        """
        self.max_per_domain = max_per_domain

    def deduplicate(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate URLs, keeping the best version of each.

        Args:
            results: List of search results

        Returns:
            Deduplicated results
        """
        seen_urls = {}

        for result in results:
            url = result.get("url", "").lower()

            if not url:
                continue

            # Normalize URL (remove trailing slash, etc.)
            normalized_url = url.rstrip("/")

            if normalized_url not in seen_urls:
                seen_urls[normalized_url] = result
            else:
                # Keep the result with more/better content
                existing = seen_urls[normalized_url]
                existing_content_len = len(existing.get("pageContent", ""))
                new_content_len = len(result.get("pageContent", ""))

                if new_content_len > existing_content_len:
                    seen_urls[normalized_url] = result

        return list(seen_urls.values())

    def apply_diversity_filter(
        self, results: List[Dict[str, Any]], max_per_domain: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Apply diversity filtering to prevent one domain from dominating.

        Args:
            results: List of results
            max_per_domain: Max results from any domain (uses instance default if not provided)

        Returns:
            Diversity-filtered results
        """
        max_per_domain = max_per_domain or self.max_per_domain
        domain_counts = {}
        filtered_results = []

        for result in results:
            url = result.get("url", "")
            if not url:
                continue

            # Extract domain
            try:
                domain = urlparse(url).netloc
            except Exception:
                domain = "unknown"

            # Check if we've hit the max for this domain
            count = domain_counts.get(domain, 0)
            if count < max_per_domain:
                filtered_results.append(result)
                domain_counts[domain] = count + 1

        return filtered_results

    def limit_per_query(
        self,
        results_per_query: Dict[str, List[Dict[str, Any]]],
        limit_per_query: int = 5,
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Limit results per query to ensure balanced coverage.

        Args:
            results_per_query: Dict mapping query to its results
            limit_per_query: Max results per query

        Returns:
            Limited results per query
        """
        limited = {}

        for query, results in results_per_query.items():
            # Take top N results for this query
            limited[query] = results[:limit_per_query]

        return limited

    def aggregate(
        self,
        results_per_query: Dict[str, List[Dict[str, Any]]],
        strategy: str = "single",
        total_limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Aggregate results from multiple queries into a single list.

        Args:
            results_per_query: Dict mapping query to its results
            strategy: "single" or "multi" - affects aggregation strategy
            total_limit: Max total results to return

        Returns:
            Aggregated and sorted results
        """
        if strategy == "single" and len(results_per_query) == 1:
            # Single query case
            all_results = list(results_per_query.values())[0]
        else:
            # Multi-query case - balance results
            all_results = []

            # Calculate per-query limit for balanced coverage
            num_queries = len(results_per_query)
            if num_queries > 0:
                per_query_limit = max(2, total_limit // num_queries)
            else:
                per_query_limit = total_limit

            for query, results in results_per_query.items():
                # Limit per query
                limited = results[:per_query_limit]
                all_results.extend(limited)

        # Apply deduplication
        deduped = self.deduplicate(all_results)

        # Apply diversity filtering
        diverse = self.apply_diversity_filter(deduped)

        # Sort by content quality (longer content is better indicator)
        sorted_results = sorted(
            diverse,
            key=lambda r: len(r.get("pageContent", "")),
            reverse=True,
        )

        # Limit total results
        return sorted_results[:total_limit]

    def aggregate_multi_query(
        self,
        results_by_query: Dict[str, List[Dict[str, Any]]],
        total_limit: int = 10,
        per_query_limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Specialized aggregation for multi-query search.

        Ensures diverse coverage across all queries.

        Args:
            results_by_query: Results from each sub-query
            total_limit: Max total results
            per_query_limit: Max results per sub-query

        Returns:
            Aggregated results with diversity
        """
        # Limit per query first
        limited = self.limit_per_query(results_by_query, limit_per_query=per_query_limit)

        # Combine all results
        all_results = []
        for results in limited.values():
            all_results.extend(results)

        # Deduplicate across all queries
        deduped = self.deduplicate(all_results)

        # Apply diversity filter
        diverse = self.apply_diversity_filter(deduped)

        # Sort by quality
        sorted_results = sorted(
            diverse,
            key=lambda r: (len(r.get("pageContent", "")), r.get("title", "")),
            reverse=True,
        )

        return sorted_results[:total_limit]

    def merge_and_rerank(
        self,
        results_per_query: Dict[str, List[Dict[str, Any]]],
        scores_per_url: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        Merge results and rerank by provided scores.

        Used after embedding-based reranking.

        Args:
            results_per_query: Results from each query
            scores_per_url: Relevance scores for each URL

        Returns:
            Results sorted by reranking score
        """
        # Flatten results
        all_results = []
        url_to_result = {}

        for results in results_per_query.values():
            for result in results:
                url = result.get("url", "")
                if url:
                    all_results.append(result)
                    url_to_result[url] = result

        # Deduplicate
        deduped = self.deduplicate(all_results)

        # Sort by reranking scores
        scored_results = []
        for result in deduped:
            url = result.get("url", "")
            score = scores_per_url.get(url, 0.0)
            scored_results.append((result, score))

        # Sort by score descending
        scored_results.sort(key=lambda x: x[1], reverse=True)

        return [r[0] for r in scored_results]
