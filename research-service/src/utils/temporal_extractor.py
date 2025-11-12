"""Temporal date extraction using dateparser library.

This module provides robust date extraction from text using the battle-tested
dateparser library instead of fragile regex patterns.

Expected accuracy: 75-85% on diverse date formats including:
- Absolute dates (ISO 8601, US, EU formats)
- Relative dates (last week, 3 days ago)
- Natural language (Q4 2024, this year)

Usage:
    >>> extractor = TemporalExtractor()
    >>> dates = extractor.extract("Published on January 15, 2025")
    >>> print(dates[0])
    datetime.datetime(2025, 1, 15, 0, 0)
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

try:
    import dateparser
    import dateparser.search

    DATEPARSER_AVAILABLE = True
except ImportError:
    DATEPARSER_AVAILABLE = False


class TemporalExtractionError(Exception):
    """Exception raised when temporal extraction fails."""

    pass


class TemporalExtractor:
    """Extract and normalize dates from text using dateparser.

    Attributes:
        parser_settings: Configuration for dateparser library

    Example:
        >>> extractor = TemporalExtractor()
        >>> dates = extractor.extract("last week")
        >>> len(dates)
        1
    """

    def __init__(self) -> None:
        """Initialize temporal extractor with dateparser settings."""
        if not DATEPARSER_AVAILABLE:
            raise TemporalExtractionError(
                "dateparser library not installed. "
                "Install with: pip install dateparser"
            )

        # Configure dateparser for best accuracy
        self.parser_settings = {
            "PREFER_DATES_FROM": "past",  # Assume historical dates by default
            "RETURN_AS_TIMEZONE_AWARE": False,  # Use naive datetimes for compatibility
            "RELATIVE_BASE": datetime.now(),  # Base for relative dates
            "STRICT_PARSING": False,  # Allow flexible parsing
            "DATE_ORDER": "DMY",  # EU format preference (handles both US and EU)
            "PREFER_DAY_OF_MONTH": "first",  # For month-year like "November 2025"
        }

    def extract(self, text: str) -> list[datetime]:
        """Extract all dates from text.

        Args:
            text: Input text that may contain dates

        Returns:
            List of datetime objects in chronological order.
            Empty list if no dates found.

        Example:
            >>> extractor = TemporalExtractor()
            >>> dates = extractor.extract("Published January 15, 2025")
            >>> dates[0].year
            2025
        """
        if not text or not text.strip():
            return []

        try:
            all_dates: list[datetime] = []

            # Step 1: Extract quarters (Q1-Q4) manually
            quarter_dates = self._extract_quarters(text)
            if quarter_dates:
                all_dates.extend(quarter_dates)

            # Step 2: Pre-scan for ISO dates (YYYY-MM-DD) with regex
            # dateparser.search sometimes misses these in context
            iso_dates = self._extract_iso_dates(text)
            if iso_dates:
                all_dates.extend(iso_dates)

            # Step 3: Pre-scan for EU dot format (DD.MM.YYYY)
            eu_dates = self._extract_eu_dot_dates(text)
            if eu_dates:
                all_dates.extend(eu_dates)

            # Step 4: Use dateparser.search for natural language dates
            # Only use if no structured dates found yet (prevents false positives)
            if not all_dates:
                results = dateparser.search.search_dates(
                    text, languages=["en"], settings=self.parser_settings
                )

                if results:
                    all_dates.extend([dt for _, dt in results])

            # Step 5: If nothing found, try parsing the entire text as a date
            if not all_dates:
                single_date = dateparser.parse(text, settings=self.parser_settings)
                if single_date:
                    all_dates.append(single_date)

            if not all_dates:
                return []

            # Remove duplicates by date (year, month, day)
            # Ignore time component for deduplication
            seen = set()
            unique_dates = []
            for dt in all_dates:
                date_key = (dt.year, dt.month, dt.day)
                if date_key not in seen:
                    seen.add(date_key)
                    unique_dates.append(dt)

            # Sort chronologically
            unique_dates.sort()

            return unique_dates

        except Exception as e:
            # Log error but don't crash - return empty list
            # In production, use proper logger
            print(f"Warning: Date extraction failed: {e}")
            return []
    
    def _extract_quarters(self, text: str) -> list[datetime]:
        """Extract quarter dates (Q1-Q4) from text.

        Args:
            text: Text containing quarter notation like "Q4 2024"

        Returns:
            List with single datetime for quarter start, or empty list
        """
        import re

        # Match Q1-Q4 followed by year
        pattern = r'\bQ([1-4])\s+(\d{4})\b'
        match = re.search(pattern, text, re.IGNORECASE)

        if not match:
            return []

        quarter = int(match.group(1))
        year = int(match.group(2))

        # Map quarter to starting month
        quarter_months = {1: 1, 2: 4, 3: 7, 4: 10}
        month = quarter_months[quarter]

        return [datetime(year, month, 1)]

    def _extract_iso_dates(self, text: str) -> list[datetime]:
        """Extract ISO 8601 dates (YYYY-MM-DD) using regex.

        Args:
            text: Text containing ISO dates

        Returns:
            List of datetime objects
        """
        import re

        # Match ISO 8601 format: YYYY-MM-DD (no word boundary at end to allow datetime format)
        pattern = r'\b(\d{4})-(\d{2})-(\d{2})'
        matches = re.finditer(pattern, text)

        dates = []
        for match in matches:
            try:
                year = int(match.group(1))
                month = int(match.group(2))
                day = int(match.group(3))

                # Validate date
                if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                    dates.append(datetime(year, month, day))
            except (ValueError, OverflowError):
                # Invalid date, skip
                continue

        return dates

    def _extract_eu_dot_dates(self, text: str) -> list[datetime]:
        """Extract EU dot format dates (DD.MM.YYYY) using regex.

        Args:
            text: Text containing EU dot dates

        Returns:
            List of datetime objects
        """
        import re
        from calendar import monthrange

        # Match DD.MM.YYYY format
        pattern = r'\b(\d{2})\.(\d{2})\.(\d{4})\b'
        matches = re.finditer(pattern, text)

        dates = []
        for match in matches:
            try:
                day = int(match.group(1))
                month = int(match.group(2))
                year = int(match.group(3))

                # Strict validation: check actual max days in month
                if 1900 <= year <= 2100 and 1 <= month <= 12:
                    max_day = monthrange(year, month)[1]
                    if 1 <= day <= max_day:
                        dates.append(datetime(year, month, day))
            except (ValueError, OverflowError):
                # Invalid date, skip
                continue

        return dates

    def normalize_relative(
        self, text: str, base_date: Optional[datetime] = None
    ) -> Optional[datetime]:
        """Normalize relative date expression to absolute datetime.

        Args:
            text: Relative date string (e.g., "last month", "yesterday")
            base_date: Reference date for relative calculation.
                      If None, uses current datetime.

        Returns:
            Absolute datetime or None if parsing fails

        Example:
            >>> extractor = TemporalExtractor()
            >>> base = datetime(2025, 1, 1)
            >>> result = extractor.normalize_relative("last month", base)
            >>> result.month
            12
        """
        if not text or not text.strip():
            return None

        # Update settings with custom base if provided
        settings = self.parser_settings.copy()
        if base_date:
            settings["RELATIVE_BASE"] = base_date

        try:
            # Parse single date expression
            result = dateparser.parse(text, settings=settings)
            return result

        except Exception as e:
            print(f"Warning: Failed to normalize relative date '{text}': {e}")
            return None

    def extract_year(self, text: str) -> Optional[int]:
        """Extract first year mentioned in text.

        Args:
            text: Text that may contain year

        Returns:
            Year as integer or None

        Example:
            >>> extractor = TemporalExtractor()
            >>> extractor.extract_year("GitHub Universe 2023")
            2023
        """
        dates = self.extract(text)
        if dates:
            return dates[0].year
        return None

    def extract_latest_date(self, text: str) -> Optional[datetime]:
        """Extract most recent date from text.

        Args:
            text: Text with possibly multiple dates

        Returns:
            Most recent datetime or None

        Example:
            >>> extractor = TemporalExtractor()
            >>> text = "Created Jan 1, 2024, updated Feb 15, 2024"
            >>> result = extractor.extract_latest_date(text)
            >>> result.month
            2
        """
        dates = self.extract(text)
        if dates:
            return max(dates)
        return None
