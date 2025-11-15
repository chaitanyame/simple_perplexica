"""Tests for authority scoring configuration validation.

Tests cover:
- Settings field validation
- Configuration ranges
- Boolean toggle validation
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.core.config import Settings


@pytest.mark.unit
@pytest.mark.fast
class TestAuthorityConfigValidation:
    """Test authority scoring configuration validation."""

    def test_authority_scoring_weight_valid_range(self) -> None:
        """Test AUTHORITY_SCORING_WEIGHT accepts valid range (0.0-0.5)."""
        # Valid values
        for weight in [0.0, 0.15, 0.30, 0.5]:
            settings = Settings(AUTHORITY_SCORING_WEIGHT=weight)
            assert settings.AUTHORITY_SCORING_WEIGHT == weight

    def test_authority_scoring_weight_below_minimum(self) -> None:
        """Test AUTHORITY_SCORING_WEIGHT rejects values below 0.0."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(AUTHORITY_SCORING_WEIGHT=-0.1)

        assert "AUTHORITY_SCORING_WEIGHT" in str(exc_info.value)

    def test_authority_scoring_weight_above_maximum(self) -> None:
        """Test AUTHORITY_SCORING_WEIGHT rejects values above 0.5."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(AUTHORITY_SCORING_WEIGHT=0.6)

        assert "AUTHORITY_SCORING_WEIGHT" in str(exc_info.value)

    def test_authority_boost_multiplier_valid_range(self) -> None:
        """Test AUTHORITY_BOOST_MULTIPLIER accepts valid range (1.0-2.0)."""
        # Valid values
        for multiplier in [1.0, 1.3, 1.5, 1.8, 2.0]:
            settings = Settings(AUTHORITY_BOOST_MULTIPLIER=multiplier)
            assert settings.AUTHORITY_BOOST_MULTIPLIER == multiplier

    def test_authority_boost_multiplier_below_minimum(self) -> None:
        """Test AUTHORITY_BOOST_MULTIPLIER rejects values below 1.0."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(AUTHORITY_BOOST_MULTIPLIER=0.9)

        assert "AUTHORITY_BOOST_MULTIPLIER" in str(exc_info.value)

    def test_authority_boost_multiplier_above_maximum(self) -> None:
        """Test AUTHORITY_BOOST_MULTIPLIER rejects values above 2.0."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(AUTHORITY_BOOST_MULTIPLIER=2.1)

        assert "AUTHORITY_BOOST_MULTIPLIER" in str(exc_info.value)

    def test_wikipedia_cache_ttl_valid_range(self) -> None:
        """Test WIKIPEDIA_CACHE_TTL accepts valid range (300-86400)."""
        # Valid values
        for ttl in [300, 1800, 3600, 43200, 86400]:
            settings = Settings(WIKIPEDIA_CACHE_TTL=ttl)
            assert settings.WIKIPEDIA_CACHE_TTL == ttl

    def test_wikipedia_cache_ttl_below_minimum(self) -> None:
        """Test WIKIPEDIA_CACHE_TTL rejects values below 300."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(WIKIPEDIA_CACHE_TTL=299)

        assert "WIKIPEDIA_CACHE_TTL" in str(exc_info.value)

    def test_wikipedia_cache_ttl_above_maximum(self) -> None:
        """Test WIKIPEDIA_CACHE_TTL rejects values above 86400."""
        with pytest.raises(ValidationError) as exc_info:
            Settings(WIKIPEDIA_CACHE_TTL=86401)

        assert "WIKIPEDIA_CACHE_TTL" in str(exc_info.value)


@pytest.mark.unit
@pytest.mark.fast
class TestAuthorityBooleanToggles:
    """Test authority scoring boolean configuration."""

    def test_enable_authority_scoring_accepts_boolean(self) -> None:
        """Test ENABLE_AUTHORITY_SCORING accepts True/False."""
        settings_enabled = Settings(ENABLE_AUTHORITY_SCORING=True)
        assert settings_enabled.ENABLE_AUTHORITY_SCORING is True

        settings_disabled = Settings(ENABLE_AUTHORITY_SCORING=False)
        assert settings_disabled.ENABLE_AUTHORITY_SCORING is False

    def test_enable_pattern_authority_accepts_boolean(self) -> None:
        """Test ENABLE_PATTERN_AUTHORITY accepts True/False."""
        settings_enabled = Settings(ENABLE_PATTERN_AUTHORITY=True)
        assert settings_enabled.ENABLE_PATTERN_AUTHORITY is True

        settings_disabled = Settings(ENABLE_PATTERN_AUTHORITY=False)
        assert settings_disabled.ENABLE_PATTERN_AUTHORITY is False

    def test_enable_wikipedia_authority_accepts_boolean(self) -> None:
        """Test ENABLE_WIKIPEDIA_AUTHORITY accepts True/False."""
        settings_enabled = Settings(ENABLE_WIKIPEDIA_AUTHORITY=True)
        assert settings_enabled.ENABLE_WIKIPEDIA_AUTHORITY is True

        settings_disabled = Settings(ENABLE_WIKIPEDIA_AUTHORITY=False)
        assert settings_disabled.ENABLE_WIKIPEDIA_AUTHORITY is False

    def test_boolean_toggles_accept_various_types(self) -> None:
        """Test boolean toggles accept various types (Pydantic coercion)."""
        # Test ENABLE_AUTHORITY_SCORING accepts string "true"
        settings1 = Settings(ENABLE_AUTHORITY_SCORING="true")
        assert settings1.ENABLE_AUTHORITY_SCORING is True

        # Test ENABLE_PATTERN_AUTHORITY accepts integer 1
        settings2 = Settings(ENABLE_PATTERN_AUTHORITY=1)
        assert settings2.ENABLE_PATTERN_AUTHORITY is True

        # Test ENABLE_WIKIPEDIA_AUTHORITY accepts integer 0
        settings3 = Settings(ENABLE_WIKIPEDIA_AUTHORITY=0)
        assert settings3.ENABLE_WIKIPEDIA_AUTHORITY is False


@pytest.mark.unit
@pytest.mark.fast
class TestAuthorityConfigDefaults:
    """Test default values for authority configuration."""

    def test_default_authority_scoring_weight(self) -> None:
        """Test default AUTHORITY_SCORING_WEIGHT is 0.15."""
        settings = Settings()
        assert settings.AUTHORITY_SCORING_WEIGHT == 0.15

    def test_default_authority_boost_multiplier(self) -> None:
        """Test default AUTHORITY_BOOST_MULTIPLIER is 1.3."""
        settings = Settings()
        assert settings.AUTHORITY_BOOST_MULTIPLIER == 1.3

    def test_default_enable_authority_scoring(self) -> None:
        """Test default ENABLE_AUTHORITY_SCORING is True."""
        settings = Settings()
        assert settings.ENABLE_AUTHORITY_SCORING is True

    def test_default_enable_pattern_authority(self) -> None:
        """Test default ENABLE_PATTERN_AUTHORITY is True."""
        settings = Settings()
        assert settings.ENABLE_PATTERN_AUTHORITY is True

    def test_default_enable_wikipedia_authority(self) -> None:
        """Test default ENABLE_WIKIPEDIA_AUTHORITY is True."""
        settings = Settings()
        assert settings.ENABLE_WIKIPEDIA_AUTHORITY is True

    def test_default_wikipedia_cache_ttl(self) -> None:
        """Test default WIKIPEDIA_CACHE_TTL is 3600."""
        settings = Settings()
        assert settings.WIKIPEDIA_CACHE_TTL == 3600


@pytest.mark.unit
@pytest.mark.fast
class TestAuthorityConfigCombinations:
    """Test combinations of authority configuration settings."""

    def test_authority_disabled_with_custom_weight(self) -> None:
        """Test authority can be disabled even with custom weight."""
        settings = Settings(ENABLE_AUTHORITY_SCORING=False, AUTHORITY_SCORING_WEIGHT=0.30)
        assert settings.ENABLE_AUTHORITY_SCORING is False
        assert settings.AUTHORITY_SCORING_WEIGHT == 0.30

    def test_all_authority_features_enabled(self) -> None:
        """Test all authority features can be enabled simultaneously."""
        settings = Settings(
            ENABLE_AUTHORITY_SCORING=True,
            ENABLE_PATTERN_AUTHORITY=True,
            ENABLE_WIKIPEDIA_AUTHORITY=True,
        )
        assert settings.ENABLE_AUTHORITY_SCORING is True
        assert settings.ENABLE_PATTERN_AUTHORITY is True
        assert settings.ENABLE_WIKIPEDIA_AUTHORITY is True

    def test_all_authority_features_disabled(self) -> None:
        """Test all authority features can be disabled simultaneously."""
        settings = Settings(
            ENABLE_AUTHORITY_SCORING=False,
            ENABLE_PATTERN_AUTHORITY=False,
            ENABLE_WIKIPEDIA_AUTHORITY=False,
        )
        assert settings.ENABLE_AUTHORITY_SCORING is False
        assert settings.ENABLE_PATTERN_AUTHORITY is False
        assert settings.ENABLE_WIKIPEDIA_AUTHORITY is False

    def test_selective_feature_enabling(self) -> None:
        """Test selective enabling of authority features."""
        # Pattern only
        settings_pattern = Settings(
            ENABLE_AUTHORITY_SCORING=True,
            ENABLE_PATTERN_AUTHORITY=True,
            ENABLE_WIKIPEDIA_AUTHORITY=False,
        )
        assert settings_pattern.ENABLE_PATTERN_AUTHORITY is True
        assert settings_pattern.ENABLE_WIKIPEDIA_AUTHORITY is False

        # Wikipedia only
        settings_wikipedia = Settings(
            ENABLE_AUTHORITY_SCORING=True,
            ENABLE_PATTERN_AUTHORITY=False,
            ENABLE_WIKIPEDIA_AUTHORITY=True,
        )
        assert settings_wikipedia.ENABLE_PATTERN_AUTHORITY is False
        assert settings_wikipedia.ENABLE_WIKIPEDIA_AUTHORITY is True

    def test_custom_weight_and_multiplier(self) -> None:
        """Test custom weight and multiplier values."""
        settings = Settings(AUTHORITY_SCORING_WEIGHT=0.25, AUTHORITY_BOOST_MULTIPLIER=1.8)
        assert settings.AUTHORITY_SCORING_WEIGHT == 0.25
        assert settings.AUTHORITY_BOOST_MULTIPLIER == 1.8

    def test_minimum_valid_configuration(self) -> None:
        """Test minimum valid configuration (all minimums)."""
        settings = Settings(
            AUTHORITY_SCORING_WEIGHT=0.0, AUTHORITY_BOOST_MULTIPLIER=1.0, WIKIPEDIA_CACHE_TTL=300
        )
        assert settings.AUTHORITY_SCORING_WEIGHT == 0.0
        assert settings.AUTHORITY_BOOST_MULTIPLIER == 1.0
        assert settings.WIKIPEDIA_CACHE_TTL == 300

    def test_maximum_valid_configuration(self) -> None:
        """Test maximum valid configuration (all maximums)."""
        settings = Settings(
            AUTHORITY_SCORING_WEIGHT=0.5, AUTHORITY_BOOST_MULTIPLIER=2.0, WIKIPEDIA_CACHE_TTL=86400
        )
        assert settings.AUTHORITY_SCORING_WEIGHT == 0.5
        assert settings.AUTHORITY_BOOST_MULTIPLIER == 2.0
        assert settings.WIKIPEDIA_CACHE_TTL == 86400


@pytest.mark.unit
@pytest.mark.fast
class TestAuthorityConfigTypeValidation:
    """Test type validation for authority configuration."""

    def test_weight_accepts_string_convertible(self) -> None:
        """Test AUTHORITY_SCORING_WEIGHT accepts string (Pydantic coercion)."""
        settings = Settings(AUTHORITY_SCORING_WEIGHT="0.15")
        assert settings.AUTHORITY_SCORING_WEIGHT == 0.15
        assert isinstance(settings.AUTHORITY_SCORING_WEIGHT, float)

    def test_multiplier_accepts_string_convertible(self) -> None:
        """Test AUTHORITY_BOOST_MULTIPLIER accepts string (Pydantic coercion)."""
        settings = Settings(AUTHORITY_BOOST_MULTIPLIER="1.5")
        assert settings.AUTHORITY_BOOST_MULTIPLIER == 1.5
        assert isinstance(settings.AUTHORITY_BOOST_MULTIPLIER, float)

    def test_cache_ttl_rejects_float(self) -> None:
        """Test WIKIPEDIA_CACHE_TTL rejects float values."""
        with pytest.raises(ValidationError):
            Settings(WIKIPEDIA_CACHE_TTL=3600.5)

    def test_cache_ttl_accepts_string_convertible(self) -> None:
        """Test WIKIPEDIA_CACHE_TTL accepts string (Pydantic coercion)."""
        settings = Settings(WIKIPEDIA_CACHE_TTL="3600")
        assert settings.WIKIPEDIA_CACHE_TTL == 3600
        assert isinstance(settings.WIKIPEDIA_CACHE_TTL, int)

    def test_weight_accepts_int_convertible(self) -> None:
        """Test AUTHORITY_SCORING_WEIGHT accepts integer (converts to float)."""
        settings = Settings(AUTHORITY_SCORING_WEIGHT=0)
        assert settings.AUTHORITY_SCORING_WEIGHT == 0.0
        assert isinstance(settings.AUTHORITY_SCORING_WEIGHT, float)

    def test_multiplier_accepts_int_convertible(self) -> None:
        """Test AUTHORITY_BOOST_MULTIPLIER accepts integer (converts to float)."""
        settings = Settings(AUTHORITY_BOOST_MULTIPLIER=1)
        assert settings.AUTHORITY_BOOST_MULTIPLIER == 1.0
        assert isinstance(settings.AUTHORITY_BOOST_MULTIPLIER, float)
