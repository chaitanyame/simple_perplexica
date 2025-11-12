"""Temporal validation utilities for search results.

Big Tech Approach - Phase 1: Post-retrieval temporal validation
- Extract dates from URLs, content, metadata
- Validate if sources match query's temporal intent
- Penalize mismatched sources in ranking
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from src.agents.search_agent import SearchSource

logger = structlog.get_logger(__name__)


class TemporalValidator:
    """Validates temporal relevance of search sources."""
    
    def __init__(self):
        """Initialize temporal validator."""
        # Common date patterns in URLs and content
        self.url_patterns = [
            r'/(\d{4})/(\d{2})/(\d{2})/',  # /2023/11/15/
            r'/(\d{4})/(\d{2})/',           # /2023/11/
            r'/(\d{4})/',                   # /2023/
            r'-(\d{4})-(\d{2})-(\d{2})',   # -2023-11-15
            r'_(\d{4})_(\d{2})_(\d{2})',   # _2023_11_15
        ]
        
        self.content_patterns = [
            r'Published:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',  # Published: November 15, 2023
            r'(\d{4}-\d{2}-\d{2})',                             # 2023-11-15
            r'([A-Z][a-z]+\s+\d{1,2},\s+\d{4})',               # November 15, 2023
            r'(\d{1,2}\s+[A-Z][a-z]+\s+\d{4})',                # 15 November 2023
        ]
        
        # Month name to number mapping
        self.months = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4,
            'may': 5, 'june': 6, 'july': 7, 'august': 8,
            'september': 9, 'october': 10, 'november': 11, 'december': 12,
            'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
            'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12
        }
    
    def extract_year_from_url(self, url: str) -> int | None:
        """Extract year from URL pattern.
        
        Args:
            url: URL to parse
            
        Returns:
            Year if found, None otherwise
            
        Example:
            >>> validator.extract_year_from_url("https://example.com/2023/11/article")
            2023
        """
        for pattern in self.url_patterns:
            match = re.search(pattern, url)
            if match:
                year_str = match.group(1)
                year = int(year_str)
                # Sanity check: 1990-2030
                if 1990 <= year <= 2030:
                    logger.debug(f"📅 Extracted year {year} from URL: {url[:80]}")
                    return year
        return None
    
    def extract_year_from_content(self, content: str) -> int | None:
        """Extract publication year from content.
        
        Args:
            content: Content text to parse
            
        Returns:
            Year if found, None otherwise
        """
        if not content:
            return None
        
        # Try each pattern
        for pattern in self.content_patterns:
            match = re.search(pattern, content[:1000])  # Check first 1000 chars
            if match:
                date_str = match.group(1)
                # Try to extract year
                year_match = re.search(r'\d{4}', date_str)
                if year_match:
                    year = int(year_match.group(0))
                    if 1990 <= year <= 2030:
                        logger.debug(f"📅 Extracted year {year} from content")
                        return year
        
        return None
    
    def extract_publication_date(self, source: SearchSource) -> int | None:
        """Extract publication year from source (URL + content).
        
        Args:
            source: Search source to analyze
            
        Returns:
            Publication year if found, None otherwise
        """
        # Priority 1: URL pattern (most reliable)
        year_from_url = self.extract_year_from_url(source.url)
        if year_from_url:
            return year_from_url
        
        # Priority 2: Content parsing
        content = source.content or source.snippet
        year_from_content = self.extract_year_from_content(content)
        if year_from_content:
            return year_from_content
        
        return None
    
    def validate_temporal_match(
        self,
        source: SearchSource,
        target_year: int | None = None,
        temporal_scope: str = "any"
    ) -> tuple[bool, float, str]:
        """Validate if source matches temporal intent.
        
        Args:
            source: Search source to validate
            target_year: Specific year expected (e.g., 2023)
            temporal_scope: Temporal scope (recent/past_year/any)
            
        Returns:
            Tuple of (is_valid, penalty_multiplier, reason)
            - is_valid: Whether source passes validation
            - penalty_multiplier: Ranking penalty (0.0-1.0, 1.0 = no penalty)
            - reason: Human-readable validation reason
            
        Example:
            >>> is_valid, penalty, reason = validator.validate_temporal_match(
            ...     source, target_year=2025, temporal_scope="recent"
            ... )
            >>> print(f"Valid: {is_valid}, Penalty: {penalty}, Reason: {reason}")
        """
        # Extract publication year
        pub_year = self.extract_publication_date(source)
        
        if pub_year is None:
            # Cannot determine date - apply light penalty for recent queries
            if temporal_scope == "recent" or target_year is not None:
                return (True, 0.9, "⚠️ No date found, applying light penalty")
            return (True, 1.0, "✓ No date found, no temporal constraint")
        
        # Specific year validation
        if target_year is not None:
            year_diff = abs(pub_year - target_year)
            
            if year_diff == 0:
                return (True, 1.0, f"✓ Exact year match: {pub_year}")
            elif year_diff == 1:
                return (True, 0.8, f"⚠️ Off by 1 year: {pub_year} vs {target_year}")
            elif year_diff <= 2:
                return (True, 0.5, f"⚠️ Off by {year_diff} years: {pub_year} vs {target_year}")
            else:
                return (False, 0.2, f"❌ Wrong year: {pub_year} vs {target_year} (diff: {year_diff})")
        
        # Temporal scope validation
        current_year = datetime.now().year
        age_years = current_year - pub_year
        
        if temporal_scope == "recent":
            if age_years == 0:
                return (True, 1.0, f"✓ Current year: {pub_year}")
            elif age_years == 1:
                return (True, 0.7, f"⚠️ 1 year old: {pub_year}")
            elif age_years <= 2:
                return (True, 0.4, f"⚠️ {age_years} years old: {pub_year}")
            else:
                return (False, 0.1, f"❌ Too old ({age_years} years): {pub_year}")
        
        elif temporal_scope == "past_year":
            if age_years <= 1:
                return (True, 1.0, f"✓ Within past year: {pub_year}")
            elif age_years <= 2:
                return (True, 0.6, f"⚠️ Slightly old: {pub_year}")
            else:
                return (False, 0.2, f"❌ Too old: {pub_year}")
        
        # No temporal constraint
        return (True, 1.0, f"✓ Any date acceptable: {pub_year}")
    
    def filter_and_rerank_sources(
        self,
        sources: list[SearchSource],
        target_year: int | None = None,
        temporal_scope: str = "any",
        strict_filtering: bool = False
    ) -> list[SearchSource]:
        """Filter and re-rank sources based on temporal relevance.
        
        Args:
            sources: List of search sources
            target_year: Specific year if mentioned in query
            temporal_scope: Temporal scope from query decomposition
            strict_filtering: If True, remove invalid sources; if False, just penalize
            
        Returns:
            Filtered and re-ranked sources
        """
        logger.info(
            f"🔍 Temporal validation: target_year={target_year}, "
            f"scope={temporal_scope}, strict={strict_filtering}"
        )
        
        validated_sources = []
        removed_count = 0
        
        for source in sources:
            is_valid, penalty, reason = self.validate_temporal_match(
                source, target_year, temporal_scope
            )
            
            # Log validation result
            logger.info(
                f"  [{source.title[:50]}...] "
                f"Penalty: {penalty:.2f} - {reason}"
            )
            
            # Strict filtering: remove invalid sources
            if strict_filtering and not is_valid:
                removed_count += 1
                continue
            
            # Apply penalty to relevance score
            source.relevance *= penalty
            source.final_score *= penalty
            validated_sources.append(source)
        
        if removed_count > 0:
            logger.warning(f"⚠️ Removed {removed_count} temporally invalid sources")
        
        # Re-sort by adjusted scores
        validated_sources.sort(key=lambda s: s.final_score, reverse=True)
        
        logger.info(
            f"✅ Temporal validation complete: {len(validated_sources)} sources retained"
        )
        
        return validated_sources
