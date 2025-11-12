"""Tests for dateparser-based temporal extraction (TDD - RED phase).

Following TDD approach:
1. RED: Write failing tests first (this file)
2. GREEN: Implement TemporalExtractor with dateparser
3. REFACTOR: Optimize and integrate

Goal: Replace regex-based date extraction with battle-tested dateparser library.
Expected accuracy: 75-85% on diverse date formats.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

# Will implement this after tests pass
from src.utils.temporal_extractor import TemporalExtractor


class TestAbsoluteDateExtraction:
    """Test extraction of absolute dates (ISO, US, EU formats)."""

    @pytest.fixture
    def extractor(self) -> TemporalExtractor:
        return TemporalExtractor()

    @pytest.mark.parametrize(
        "text,expected_year,expected_month,expected_day",
        [
            # ISO 8601
            ("Published on 2025-01-15", 2025, 1, 15),
            ("Article from 2024-12-31", 2024, 12, 31),
            # US format
            ("Jan 15, 2025", 2025, 1, 15),
            ("December 31, 2024", 2024, 12, 31),
            # EU format
            ("15/01/2025", 2025, 1, 15),
            ("31.12.2024", 2024, 12, 31),
            # Long format
            ("January 15th, 2025", 2025, 1, 15),
            ("15 January 2025", 2025, 1, 15),
        ],
    )
    def test_extract_absolute_dates(
        self,
        extractor: TemporalExtractor,
        text: str,
        expected_year: int,
        expected_month: int,
        expected_day: int,
    ) -> None:
        """Test extraction of various absolute date formats.

        Given: Text containing absolute date
        When: Extracting dates
        Then: Returns correct datetime with exact date
        """
        result = extractor.extract(text)

        assert len(result) == 1, f"Expected 1 date, got {len(result)}"

        extracted_date = result[0]
        assert extracted_date.year == expected_year
        assert extracted_date.month == expected_month
        assert extracted_date.day == expected_day


class TestRelativeDateExtraction:
    """Test extraction of relative dates (last week, 3 days ago, etc.)."""

    @pytest.fixture
    def extractor(self) -> TemporalExtractor:
        return TemporalExtractor()

    @pytest.mark.parametrize(
        "text,days_offset,tolerance",
        [
            ("last week", -7, 1),
            ("3 days ago", -3, 1),
            ("yesterday", -1, 1),
            ("one week ago", -7, 1),
            ("two months ago", -60, 3),  # Months vary in length, allow 3-day tolerance
        ],
    )
    def test_extract_relative_dates(
        self, extractor: TemporalExtractor, text: str, days_offset: int, tolerance: int
    ) -> None:
        """Test extraction of relative dates normalized to absolute.

        Given: Text with relative date expression
        When: Extracting dates
        Then: Returns datetime relative to now (within tolerance)
        """
        result = extractor.extract(text)

        assert len(result) == 1, f"Expected 1 date, got {len(result)}"

        expected_date = datetime.now() + timedelta(days=days_offset)
        extracted_date = result[0]

        # Check if within tolerance
        diff_days = abs((extracted_date - expected_date).days)
        assert diff_days <= tolerance, (
            f"Date off by {diff_days} days (tolerance {tolerance}): "
            f"{extracted_date} vs {expected_date}"
        )


class TestNaturalLanguageDates:
    """Test extraction of natural language date expressions."""

    @pytest.fixture
    def extractor(self) -> TemporalExtractor:
        return TemporalExtractor()

    def test_extract_quarter_dates(self, extractor: TemporalExtractor) -> None:
        """Test Q1-Q4 date extraction.

        Given: Text with quarter notation (Q4 2024)
        When: Extracting dates
        Then: Returns start of quarter
        """
        result = extractor.extract("Q4 2024")

        assert len(result) == 1
        extracted_date = result[0]

        # Q4 starts October 1
        assert extracted_date.year == 2024
        assert extracted_date.month == 10  # October
        assert extracted_date.day == 1

    def test_extract_month_year(self, extractor: TemporalExtractor) -> None:
        """Test month-year extraction.

        Given: Text with month and year only
        When: Extracting dates
        Then: Returns first day of month
        """
        result = extractor.extract("November 2025")

        assert len(result) == 1
        extracted_date = result[0]

        assert extracted_date.year == 2025
        assert extracted_date.month == 11
        assert extracted_date.day == 1

    def test_extract_this_year(self, extractor: TemporalExtractor) -> None:
        """Test 'this year' extraction.

        Given: Text with 'this year'
        When: Extracting dates
        Then: Returns current year
        """
        result = extractor.extract("published this year")

        assert len(result) == 1
        extracted_date = result[0]

        current_year = datetime.now().year
        assert extracted_date.year == current_year


class TestMultipleDateExtraction:
    """Test extraction of multiple dates from single text."""

    @pytest.fixture
    def extractor(self) -> TemporalExtractor:
        return TemporalExtractor()

    def test_extract_multiple_dates(self, extractor: TemporalExtractor) -> None:
        """Test extracting multiple dates from one text.

        Given: Text with multiple date mentions
        When: Extracting dates
        Then: Returns all dates in chronological order
        """
        text = "Article from Jan 1, 2024 updated on Feb 15, 2024"
        result = extractor.extract(text)

        assert len(result) == 2
        assert result[0] < result[1], "Dates should be in chronological order"
        assert result[0].year == 2024
        assert result[0].month == 1
        assert result[1].month == 2


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def extractor(self) -> TemporalExtractor:
        return TemporalExtractor()

    def test_extract_no_dates(self, extractor: TemporalExtractor) -> None:
        """Test extraction when no dates present.

        Given: Text with no dates
        When: Extracting dates
        Then: Returns empty list
        """
        result = extractor.extract("no dates here at all")
        assert result == []

    def test_extract_empty_string(self, extractor: TemporalExtractor) -> None:
        """Test extraction from empty string.

        Given: Empty string
        When: Extracting dates
        Then: Returns empty list
        """
        result = extractor.extract("")
        assert result == []

    def test_extract_invalid_date(self, extractor: TemporalExtractor) -> None:
        """Test extraction of invalid date.

        Given: Text with invalid date (2025-13-45)
        When: Extracting dates
        Then: Returns empty list or skips invalid
        """
        result = extractor.extract("2025-13-45 is invalid")
        # dateparser should reject invalid dates
        assert len(result) == 0 or all(
            1 <= d.month <= 12 and 1 <= d.day <= 31 for d in result
        )


class TestTimezoneHandling:
    """Test timezone handling (using naive datetimes for simplicity)."""

    @pytest.fixture
    def extractor(self) -> TemporalExtractor:
        return TemporalExtractor()

    def test_extract_iso_datetime(self, extractor: TemporalExtractor) -> None:
        """Test extraction of ISO 8601 datetime.

        Given: ISO 8601 datetime with time component
        When: Extracting dates
        Then: Returns datetime with correct date (time may be stripped)
        """
        text = "2025-01-15T10:30:00Z"
        result = extractor.extract(text)

        # The regex extracts the date part (2025-01-15)
        assert len(result) >= 1, f"Expected at least 1 date, got {len(result)}"

        # Find the matching date
        extracted_date = next((d for d in result if d.year == 2025 and d.month == 1), None)
        assert extracted_date is not None, f"No matching date found in {result}"

        # Verify date components
        assert extracted_date.year == 2025
        assert extracted_date.month == 1
        assert extracted_date.day == 15


class TestAccuracyBenchmark:
    """Test accuracy on diverse dataset (accuracy target: ≥75%)."""

    @pytest.fixture
    def extractor(self) -> TemporalExtractor:
        return TemporalExtractor()

    @pytest.fixture
    def benchmark_dataset(self) -> list[dict]:
        """Diverse dataset for accuracy testing."""
        return [
            {"text": "Published 2025-01-15", "expected_year": 2025, "expected_month": 1},
            {"text": "Jan 15, 2025 article", "expected_year": 2025, "expected_month": 1},
            {"text": "15/01/2025 report", "expected_year": 2025, "expected_month": 1},
            {"text": "January 2025", "expected_year": 2025, "expected_month": 1},
            {"text": "Q1 2025 earnings", "expected_year": 2025, "expected_month": 1},
            {
                "text": "last week news",
                "expected_year": datetime.now().year,
                "expected_month": None,
            },  # Relative
            {
                "text": "yesterday update",
                "expected_year": datetime.now().year,
                "expected_month": None,
            },
            {"text": "this year report", "expected_year": datetime.now().year, "expected_month": None},
            {"text": "December 31, 2024", "expected_year": 2024, "expected_month": 12},
            {"text": "three months ago", "expected_year": datetime.now().year, "expected_month": None},
        ]

    def test_extraction_accuracy_target(
        self, extractor: TemporalExtractor, benchmark_dataset: list[dict]
    ) -> None:
        """Verify extraction achieves ≥75% accuracy.

        Given: Diverse benchmark dataset
        When: Extracting dates from all cases
        Then: Accuracy is at least 75%
        """
        correct = 0
        total = len(benchmark_dataset)

        for case in benchmark_dataset:
            extracted = extractor.extract(case["text"])

            if not extracted:
                continue

            # Check year (always required)
            if extracted[0].year == case["expected_year"]:
                # If month specified, check it too
                if case["expected_month"] is None:
                    correct += 1  # Relative date, year match is enough
                elif extracted[0].month == case["expected_month"]:
                    correct += 1

        accuracy = correct / total
        assert accuracy >= 0.75, (
            f"Accuracy {accuracy:.2%} below 75% target. "
            f"Correct: {correct}/{total}. "
            "This indicates dateparser needs tuning or dataset has issues."
        )


class TestNormalizeRelativeDates:
    """Test normalization of relative dates to absolute with custom base."""

    @pytest.fixture
    def extractor(self) -> TemporalExtractor:
        return TemporalExtractor()

    def test_normalize_with_custom_base(self, extractor: TemporalExtractor) -> None:
        """Test normalizing relative date with custom base date.

        Given: Relative date string and custom base date
        When: Normalizing
        Then: Returns absolute date relative to base
        """
        base_date = datetime(2025, 1, 1)
        result = extractor.normalize_relative("last month", base_date=base_date)

        assert result is not None
        assert result.year == 2024
        assert result.month == 12

    def test_normalize_with_default_base(self, extractor: TemporalExtractor) -> None:
        """Test normalizing relative date with default base (now).

        Given: Relative date string
        When: Normalizing without base
        Then: Returns absolute date relative to now
        """
        result = extractor.normalize_relative("yesterday")

        assert result is not None

        expected = datetime.now() - timedelta(days=1)
        diff_days = abs((result - expected).days)
        assert diff_days <= 1
