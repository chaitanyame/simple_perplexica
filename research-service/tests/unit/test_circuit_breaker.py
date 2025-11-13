"""Tests for circuit breaker.

Following TDD principles - tests written BEFORE implementation.
"""
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from src.core.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    """Test suite for CircuitBreaker."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_starts_closed(self):
        """Test circuit breaker starts in CLOSED state."""
        # Act
        breaker = CircuitBreaker(failure_threshold=3, timeout=5.0)
        
        # Assert
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_allows_calls_when_closed(self):
        """Test circuit allows function calls in CLOSED state."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=3, timeout=5.0)
        successful_func = AsyncMock(return_value="success")
        
        # Act
        result = await breaker.call(successful_func, "arg1", kwarg1="value1")
        
        # Assert
        assert result == "success"
        successful_func.assert_called_once_with("arg1", kwarg1="value1")
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit opens after reaching failure threshold."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=3, timeout=5.0)
        failing_func = AsyncMock(side_effect=Exception("API Error"))
        
        # Act - Fail 3 times
        for _ in range(3):
            with pytest.raises(Exception, match="API Error"):
                await breaker.call(failing_func)
        
        # Assert
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count == 3
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_rejects_calls_when_open(self):
        """Test circuit immediately rejects calls when OPEN."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=2, timeout=5.0)
        failing_func = AsyncMock(side_effect=Exception("API Error"))
        
        # Act - Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Act - Try calling again (should fail immediately)
        with pytest.raises(Exception, match="Circuit breaker open"):
            await breaker.call(failing_func)
        
        # Assert - Function should NOT be called
        assert failing_func.call_count == 2  # Only called during opening
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_enters_half_open_after_timeout(self):
        """Test circuit enters HALF_OPEN state after timeout expires."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.5)  # Short timeout
        failing_func = AsyncMock(side_effect=Exception("API Error"))
        
        # Act - Open the circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        assert breaker.state == CircuitState.OPEN
        
        # Wait for timeout
        await asyncio.sleep(0.6)
        
        # Try calling - should allow (HALF_OPEN)
        success_func = AsyncMock(return_value="recovered")
        result = await breaker.call(success_func)
        
        # Assert
        assert result == "recovered"
        assert breaker.state == CircuitState.CLOSED  # Success closes it
        assert breaker.failure_count == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_closes_on_success_in_half_open(self):
        """Test successful call in HALF_OPEN closes the circuit."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.5)
        failing_func = AsyncMock(side_effect=Exception("API Error"))
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        # Wait for timeout
        await asyncio.sleep(0.6)
        
        # Act - Successful call in HALF_OPEN
        success_func = AsyncMock(return_value="success")
        result = await breaker.call(success_func)
        
        # Assert
        assert result == "success"
        assert breaker.state == CircuitState.CLOSED
        assert breaker.failure_count == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_reopens_on_failure_in_half_open(self):
        """Test failure in HALF_OPEN reopens the circuit."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=2, timeout=0.5)
        failing_func = AsyncMock(side_effect=Exception("API Error"))
        
        # Open circuit
        for _ in range(2):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
        
        # Wait for timeout
        await asyncio.sleep(0.6)
        
        # Act - Fail in HALF_OPEN
        with pytest.raises(Exception, match="API Error"):
            await breaker.call(failing_func)
        
        # Assert - Should reopen
        assert breaker.state == CircuitState.OPEN
        assert breaker.failure_count >= 2
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_resets_count_on_success(self):
        """Test failure count resets on successful call."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=3, timeout=5.0)
        failing_func = AsyncMock(side_effect=Exception("API Error"))
        success_func = AsyncMock(return_value="success")
        
        # Act - Fail once
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        
        assert breaker.failure_count == 1
        
        # Success should reset
        await breaker.call(success_func)
        
        # Assert
        assert breaker.failure_count == 0
        assert breaker.state == CircuitState.CLOSED
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_increments_failure_count(self):
        """Test failure count increments on each failure."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=5, timeout=5.0)
        failing_func = AsyncMock(side_effect=Exception("API Error"))
        
        # Act & Assert
        for i in range(1, 4):
            with pytest.raises(Exception):
                await breaker.call(failing_func)
            assert breaker.failure_count == i
            assert breaker.state == CircuitState.CLOSED  # Still below threshold
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_circuit_breaker_custom_thresholds(self):
        """Test circuit breaker respects custom threshold and timeout."""
        # Arrange
        breaker = CircuitBreaker(failure_threshold=1, timeout=0.3)
        failing_func = AsyncMock(side_effect=Exception("Error"))
        
        # Act - Single failure should open
        with pytest.raises(Exception):
            await breaker.call(failing_func)
        
        # Assert
        assert breaker.state == CircuitState.OPEN
        
        # Wait for short timeout
        await asyncio.sleep(0.4)
        
        # Should allow retry
        success_func = AsyncMock(return_value="ok")
        result = await breaker.call(success_func)
        assert result == "ok"
