"""Tests for retry logic and error handling."""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from microsoft_agent_framework.domain.exceptions import (
    AgentTimeoutError,
    AuthenticationError,
    ConnectionError,
    RateLimitError,
    TimeoutError,
)
from microsoft_agent_framework.domain.retry import (
    AGENT_RETRY_POLICY,
    AGGRESSIVE_RETRY_POLICY,
    API_RETRY_POLICY,
    CONSERVATIVE_RETRY_POLICY,
    DEFAULT_RETRY_POLICY,
    LoggingRetryCallbacks,
    RetryContext,
    RetryPolicy,
    RetryStrategy,
    retry_async,
    retry_decorator,
)


class TestRetryPolicy:
    """Test cases for RetryPolicy."""

    def test_should_retry_with_retryable_exception(self):
        """Test retry decision with retryable exceptions."""
        policy = RetryPolicy(max_attempts=3)

        # Should retry for retryable exceptions
        assert policy.should_retry(ConnectionError("Connection failed"), 0)
        assert policy.should_retry(TimeoutError("Timeout"), 1)
        assert policy.should_retry(RateLimitError("Rate limited"), 2)

        # Should not retry if max attempts reached
        assert not policy.should_retry(ConnectionError("Connection failed"), 3)

    def test_should_retry_with_non_retryable_exception(self):
        """Test retry decision with non-retryable exceptions."""
        policy = RetryPolicy(max_attempts=3)

        # Should not retry for non-retryable exceptions
        assert not policy.should_retry(AuthenticationError("Auth failed"), 0)
        assert not policy.should_retry(ValueError("Invalid value"), 0)
        assert not policy.should_retry(TypeError("Type error"), 1)

    def test_calculate_delay_fixed_strategy(self):
        """Test delay calculation with fixed strategy."""
        policy = RetryPolicy(base_delay=2.0, strategy=RetryStrategy.FIXED, jitter=False)

        assert policy.calculate_delay(0) == 2.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(5) == 2.0

    def test_calculate_delay_linear_strategy(self):
        """Test delay calculation with linear strategy."""
        policy = RetryPolicy(base_delay=1.0, strategy=RetryStrategy.LINEAR, jitter=False)

        assert policy.calculate_delay(0) == 1.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 3.0

    def test_calculate_delay_exponential_strategy(self):
        """Test delay calculation with exponential strategy."""
        policy = RetryPolicy(
            base_delay=1.0,
            backoff_multiplier=2.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False,
        )

        assert policy.calculate_delay(0) == 1.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 4.0
        assert policy.calculate_delay(3) == 8.0

    def test_calculate_delay_with_max_delay(self):
        """Test delay calculation respects max delay."""
        policy = RetryPolicy(
            base_delay=1.0,
            max_delay=5.0,
            backoff_multiplier=2.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False,
        )

        assert policy.calculate_delay(0) == 1.0
        assert policy.calculate_delay(1) == 2.0
        assert policy.calculate_delay(2) == 4.0
        assert policy.calculate_delay(3) == 5.0  # Capped at max_delay
        assert policy.calculate_delay(10) == 5.0  # Still capped

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        policy = RetryPolicy(base_delay=4.0, strategy=RetryStrategy.FIXED, jitter=True)

        # With jitter, delay should be between 50% and 100% of base delay
        delays = [policy.calculate_delay(0) for _ in range(100)]

        # All delays should be within expected range
        for delay in delays:
            assert 2.0 <= delay <= 4.0  # 50% to 100% of 4.0


class TestRetryCallbacks:
    """Test cases for retry callbacks."""

    @pytest.mark.asyncio
    async def test_logging_retry_callbacks(self):
        """Test logging retry callbacks."""
        callbacks = LoggingRetryCallbacks("test_logger")

        # Test on_retry
        context = RetryContext(
            attempt=1,
            exception=ConnectionError("Test error"),
            elapsed_time=2.5,
            next_delay=4.0,
        )

        # Should not raise any exceptions
        await callbacks.on_retry(context)

        # Test on_failure
        failure_context = RetryContext(attempt=3, exception=TimeoutError("Final error"), elapsed_time=10.0)

        await callbacks.on_failure(failure_context)


class TestRetryAsync:
    """Test cases for async retry functionality."""

    @pytest.mark.asyncio
    async def test_successful_execution_no_retry(self):
        """Test successful execution without retries."""
        mock_func = AsyncMock(return_value="success")
        policy = RetryPolicy(max_attempts=3)

        result = await retry_async(mock_func, policy)

        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_successful_execution_after_retries(self):
        """Test successful execution after some retries."""
        mock_func = AsyncMock()
        mock_func.side_effect = [
            ConnectionError("First failure"),
            TimeoutError("Second failure"),
            "success",
        ]

        policy = RetryPolicy(max_attempts=3, base_delay=0.01)  # Fast retry for testing

        result = await retry_async(mock_func, policy)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_failure_after_max_retries(self):
        """Test failure after exhausting all retries."""
        mock_func = AsyncMock()
        mock_func.side_effect = ConnectionError("Persistent failure")

        policy = RetryPolicy(max_attempts=2, base_delay=0.01)

        with pytest.raises(ConnectionError, match="Persistent failure"):
            await retry_async(mock_func, policy)

        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """Test immediate failure with non-retryable exception."""
        mock_func = AsyncMock()
        mock_func.side_effect = AuthenticationError("Auth failed")

        policy = RetryPolicy(max_attempts=3)

        with pytest.raises(AuthenticationError, match="Auth failed"):
            await retry_async(mock_func, policy)

        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_with_custom_callbacks(self):
        """Test retry with custom callbacks."""
        mock_func = AsyncMock()
        mock_func.side_effect = [ConnectionError("Failure"), "success"]

        mock_callbacks = MagicMock()
        mock_callbacks.on_retry = AsyncMock()
        mock_callbacks.on_failure = AsyncMock()

        policy = RetryPolicy(max_attempts=2, base_delay=0.01)

        result = await retry_async(mock_func, policy, mock_callbacks)

        assert result == "success"
        assert mock_callbacks.on_retry.call_count == 1
        assert mock_callbacks.on_failure.call_count == 0


class TestRetryDecorator:
    """Test cases for retry decorator."""

    @pytest.mark.asyncio
    async def test_async_function_decorator(self):
        """Test decorator with async function."""
        call_count = 0

        @retry_decorator(RetryPolicy(max_attempts=3, base_delay=0.01))
        async def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        result = await test_func()

        assert result == "success"
        assert call_count == 3

    def test_sync_function_decorator(self):
        """Test decorator with sync function."""
        call_count = 0

        @retry_decorator(RetryPolicy(max_attempts=2, base_delay=0.01))
        def test_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("Temporary failure")
            return "success"

        result = test_func()

        assert result == "success"
        assert call_count == 2


class TestPredefinedPolicies:
    """Test cases for predefined retry policies."""

    def test_default_retry_policy(self):
        """Test default retry policy configuration."""
        policy = DEFAULT_RETRY_POLICY

        assert policy.max_attempts == 3
        assert policy.base_delay == 1.0
        assert policy.strategy == RetryStrategy.EXPONENTIAL
        assert policy.jitter is True

    def test_aggressive_retry_policy(self):
        """Test aggressive retry policy configuration."""
        policy = AGGRESSIVE_RETRY_POLICY

        assert policy.max_attempts == 5
        assert policy.base_delay == 0.5
        assert policy.max_delay == 30.0
        assert policy.backoff_multiplier == 1.5

    def test_conservative_retry_policy(self):
        """Test conservative retry policy configuration."""
        policy = CONSERVATIVE_RETRY_POLICY

        assert policy.max_attempts == 2
        assert policy.base_delay == 2.0
        assert policy.strategy == RetryStrategy.FIXED
        assert policy.jitter is False

    def test_api_retry_policy(self):
        """Test API retry policy configuration."""
        policy = API_RETRY_POLICY

        assert policy.max_attempts == 4
        assert RateLimitError in policy.retryable_exceptions
        assert ConnectionError in policy.retryable_exceptions
        assert AuthenticationError in policy.non_retryable_exceptions

    def test_agent_retry_policy(self):
        """Test agent retry policy configuration."""
        policy = AGENT_RETRY_POLICY

        assert policy.max_attempts == 3
        assert policy.base_delay == 2.0
        assert AgentTimeoutError in policy.retryable_exceptions
        assert ConnectionError in policy.retryable_exceptions


class TestRetryIntegration:
    """Integration tests for retry functionality."""

    @pytest.mark.asyncio
    async def test_retry_with_rate_limit_exception(self):
        """Test retry behavior with rate limit exception."""
        mock_func = AsyncMock()
        rate_limit_error = RateLimitError("Rate limited", retry_after=1.0)
        mock_func.side_effect = [rate_limit_error, "success"]

        policy = API_RETRY_POLICY
        policy.base_delay = 0.01  # Speed up test

        start_time = time.time()
        result = await retry_async(mock_func, policy)
        end_time = time.time()

        assert result == "success"
        assert mock_func.call_count == 2
        # Should have minimal delay due to our test setting
        assert end_time - start_time < 1.0

    @pytest.mark.asyncio
    async def test_retry_with_timeout_error(self):
        """Test retry behavior with timeout error."""
        mock_func = AsyncMock()
        timeout_error = AgentTimeoutError("Agent timed out", timeout_duration=30.0)
        mock_func.side_effect = [timeout_error, timeout_error, "success"]

        policy = AGENT_RETRY_POLICY
        policy.base_delay = 0.01  # Speed up test

        result = await retry_async(mock_func, policy)

        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exceeds_max_attempts(self):
        """Test behavior when retries exceed max attempts."""
        mock_func = AsyncMock()
        mock_func.side_effect = ConnectionError("Persistent connection issue")

        policy = RetryPolicy(max_attempts=2, base_delay=0.01)

        with pytest.raises(ConnectionError, match="Persistent connection issue"):
            await retry_async(mock_func, policy)

        assert mock_func.call_count == 2


@pytest.mark.asyncio
async def test_retry_with_different_strategies():
    """Test retry with different backoff strategies."""

    # Test with different strategies
    strategies = [
        (RetryStrategy.FIXED, [1.0, 1.0, 1.0]),
        (RetryStrategy.LINEAR, [1.0, 2.0, 3.0]),
        (RetryStrategy.EXPONENTIAL, [1.0, 2.0, 4.0]),
    ]

    for strategy, expected_delays in strategies:
        policy = RetryPolicy(base_delay=1.0, strategy=strategy, jitter=False, max_attempts=3)

        actual_delays = [policy.calculate_delay(i) for i in range(3)]
        assert actual_delays == expected_delays


if __name__ == "__main__":
    pytest.main([__file__])
