"""Tests for enhanced error handling and exception improvements."""

import time

import pytest

from microsoft_agent_framework.domain.exceptions import (
    AgentConnectionError,
    AgentError,
    AgentExecutionError,
    AgentFrameworkError,
    AgentInitializationError,
    AgentNotFoundError,
    AgentResourceExhaustedError,
    AgentTimeoutError,
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConfigurationError,
    ConfigurationValidationError,
    ConnectionError,
    RateLimitError,
    ResourceExhaustedError,
    TimeoutError,
    ToolConnectionError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
    ToolTimeoutError,
    ValidationError,
)


class TestEnhancedExceptions:
    """Test cases for enhanced exception classes."""

    def test_base_agent_framework_error(self):
        """Test base AgentFrameworkError functionality."""
        error = AgentFrameworkError(
            "Test error",
            error_code="TEST_001",
            details={"key": "value"},
            is_retryable=True,
            retry_after=30.0,
        )

        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.error_code == "TEST_001"
        assert error.details == {"key": "value"}
        assert error.is_retryable is True
        assert error.retry_after == 30.0
        assert isinstance(error.timestamp, float)

        # Test to_dict method
        error_dict = error.to_dict()
        assert error_dict["error_type"] == "AgentFrameworkError"
        assert error_dict["message"] == "Test error"
        assert error_dict["error_code"] == "TEST_001"
        assert error_dict["details"] == {"key": "value"}
        assert error_dict["is_retryable"] is True
        assert error_dict["retry_after"] == 30.0
        assert "timestamp" in error_dict

    def test_agent_timeout_error(self):
        """Test AgentTimeoutError with timeout duration."""
        error = AgentTimeoutError("Agent timed out", timeout_duration=60.0)

        assert error.timeout_duration == 60.0
        assert error.details["timeout_duration"] == 60.0
        assert error.is_retryable is True

    def test_agent_connection_error(self):
        """Test AgentConnectionError is retryable by default."""
        error = AgentConnectionError("Connection failed")

        assert error.is_retryable is True
        assert "Connection failed" in str(error)

    def test_agent_resource_exhausted_error(self):
        """Test AgentResourceExhaustedError with retry_after."""
        error = AgentResourceExhaustedError("Resources exhausted", retry_after=120.0)

        assert error.is_retryable is True
        assert error.retry_after == 120.0

    def test_tool_execution_error(self):
        """Test ToolExecutionError with tool details."""
        error = ToolExecutionError("Tool failed", tool_name="test_tool", execution_time=2.5)

        assert error.tool_name == "test_tool"
        assert error.execution_time == 2.5
        assert error.details["tool_name"] == "test_tool"
        assert error.details["execution_time"] == 2.5
        assert error.is_retryable is True

    def test_tool_timeout_error(self):
        """Test ToolTimeoutError with timeout duration."""
        error = ToolTimeoutError("Tool timed out", timeout_duration=30.0)

        assert error.timeout_duration == 30.0
        assert error.details["timeout_duration"] == 30.0
        assert error.is_retryable is True

    def test_tool_connection_error(self):
        """Test ToolConnectionError is retryable."""
        error = ToolConnectionError("Tool connection failed")

        assert error.is_retryable is True

    def test_rate_limit_error(self):
        """Test RateLimitError with rate limit details."""
        error = RateLimitError(
            "Rate limit exceeded",
            retry_after=60.0,
            rate_limit_type="requests_per_minute",
        )

        assert error.retry_after == 60.0
        assert error.rate_limit_type == "requests_per_minute"
        assert error.details["rate_limit_type"] == "requests_per_minute"
        assert error.is_retryable is True

    def test_connection_error(self):
        """Test ConnectionError is retryable."""
        error = ConnectionError("Network connection failed")

        assert error.is_retryable is True

    def test_timeout_error(self):
        """Test TimeoutError with timeout duration."""
        error = TimeoutError("Operation timed out", timeout_duration=45.0)

        assert error.timeout_duration == 45.0
        assert error.details["timeout_duration"] == 45.0
        assert error.is_retryable is True

    def test_resource_exhausted_error(self):
        """Test ResourceExhaustedError with resource details."""
        error = ResourceExhaustedError("CPU resources exhausted", resource_type="cpu", retry_after=300.0)

        assert error.resource_type == "cpu"
        assert error.retry_after == 300.0
        assert error.details["resource_type"] == "cpu"
        assert error.is_retryable is True

    def test_configuration_validation_error(self):
        """Test ConfigurationValidationError with config details."""
        error = ConfigurationValidationError("Invalid configuration", config_key="api_key", expected_type="string")

        assert error.config_key == "api_key"
        assert error.expected_type == "string"
        assert error.details["config_key"] == "api_key"
        assert error.details["expected_type"] == "string"
        assert error.is_retryable is False

    def test_authentication_error_not_retryable(self):
        """Test AuthenticationError is not retryable by default."""
        error = AuthenticationError("Invalid credentials")

        assert error.is_retryable is False

    def test_authorization_error_not_retryable(self):
        """Test AuthorizationError is not retryable by default."""
        error = AuthorizationError("Access denied")

        assert error.is_retryable is False

    def test_validation_error_not_retryable(self):
        """Test ValidationError is not retryable by default."""
        error = ValidationError("Invalid input format")

        assert error.is_retryable is False


class TestExceptionInheritance:
    """Test exception inheritance hierarchy."""

    def test_exception_inheritance(self):
        """Test that all exceptions inherit from correct base classes."""
        # Agent errors
        assert issubclass(AgentError, AgentFrameworkError)
        assert issubclass(AgentNotFoundError, AgentError)
        assert issubclass(AgentInitializationError, AgentError)
        assert issubclass(AgentExecutionError, AgentError)
        assert issubclass(AgentTimeoutError, AgentError)
        assert issubclass(AgentConnectionError, AgentError)
        assert issubclass(AgentResourceExhaustedError, AgentError)

        # Tool errors
        assert issubclass(ToolError, AgentFrameworkError)
        assert issubclass(ToolNotFoundError, ToolError)
        assert issubclass(ToolExecutionError, ToolError)
        assert issubclass(ToolTimeoutError, ToolError)
        assert issubclass(ToolConnectionError, ToolError)

        # API errors
        assert issubclass(APIError, AgentFrameworkError)
        assert issubclass(AuthenticationError, APIError)
        assert issubclass(AuthorizationError, APIError)
        assert issubclass(RateLimitError, APIError)

        # Configuration errors
        assert issubclass(ConfigurationError, AgentFrameworkError)
        assert issubclass(ConfigurationValidationError, ConfigurationError)

        # Other errors
        assert issubclass(ConnectionError, AgentFrameworkError)
        assert issubclass(TimeoutError, AgentFrameworkError)
        assert issubclass(ResourceExhaustedError, AgentFrameworkError)
        assert issubclass(ValidationError, AgentFrameworkError)


class TestExceptionUsagePatterns:
    """Test common exception usage patterns."""

    def test_exception_with_cause(self):
        """Test exceptions with underlying causes."""
        original_error = ValueError("Invalid value")

        try:
            try:
                raise original_error
            except ValueError as e:
                raise AgentExecutionError("Agent failed due to invalid input") from e
        except AgentExecutionError as agent_error:
            assert str(agent_error) == "Agent failed due to invalid input"
            assert agent_error.__cause__ == original_error

    def test_exception_chaining(self):
        """Test exception chaining in complex scenarios."""

        def level_3():
            raise ConnectionError("Network connection failed")

        def level_2():
            try:
                level_3()
            except ConnectionError as e:
                raise ToolExecutionError("Search tool failed", tool_name="web_search", execution_time=2.0) from e

        def level_1():
            try:
                level_2()
            except ToolExecutionError as e:
                raise AgentExecutionError(
                    "Research agent failed",
                    agent_name="research_agent",
                    execution_time=5.0,
                ) from e

        with pytest.raises(AgentExecutionError) as exc_info:
            level_1()

        # Check the top-level exception
        assert exc_info.value.agent_name == "research_agent"

        # Check the chained exceptions
        tool_error = exc_info.value.__cause__
        assert isinstance(tool_error, ToolExecutionError)
        assert tool_error.tool_name == "web_search"

        connection_error = tool_error.__cause__
        assert isinstance(connection_error, ConnectionError)
        assert "Network connection failed" in str(connection_error)

    def test_exception_in_async_context(self):
        """Test exceptions in async context."""
        import asyncio

        async def async_failing_function():
            await asyncio.sleep(0.001)  # Simulate async work
            raise AgentTimeoutError("Async operation timed out", timeout_duration=5.0)

        async def test_async_exception():
            with pytest.raises(AgentTimeoutError) as exc_info:
                await async_failing_function()

            assert "Async operation timed out" in str(exc_info.value)
            assert exc_info.value.timeout_duration == 5.0

        # Run the async test
        asyncio.run(test_async_exception())

    def test_error_context_preservation(self):
        """Test that error context is preserved through retries."""
        start_time = time.time()

        error = AgentExecutionError(
            "Execution failed",
            agent_name="test_agent",
            execution_time=2.5,
            error_code="EXEC_001",
            details={"retry_count": 3, "last_attempt": True},
        )

        # Check that all context is preserved
        assert error.agent_name == "test_agent"
        assert error.execution_time == 2.5
        assert error.error_code == "EXEC_001"
        assert error.details["retry_count"] == 3
        assert error.details["last_attempt"] is True

        # Check timestamp is recent
        assert error.timestamp >= start_time
        assert error.timestamp <= time.time()

    def test_retry_after_header_values(self):
        """Test that retry_after values are properly set."""
        # Test with seconds
        error1 = RateLimitError("Rate limited", retry_after=60.0)
        assert error1.retry_after == 60.0

        # Test with fractional seconds
        error2 = ResourceExhaustedError("Resources exhausted", retry_after=30.5)
        assert error2.retry_after == 30.5

        # Test without retry_after
        error3 = ConnectionError("Connection failed")
        assert error3.retry_after is None


class TestExceptionSerialization:
    """Test exception serialization and deserialization."""

    def test_exception_to_dict(self):
        """Test converting exception to dictionary."""
        error = AgentExecutionError(
            "Agent execution failed",
            agent_name="test_agent",
            execution_time=3.14,
            error_code="EXEC_FAIL",
            details={"attempt": 2, "tool": "search"},
            is_retryable=True,
            retry_after=10.0,
        )

        error_dict = error.to_dict()

        expected_keys = {
            "error_type",
            "message",
            "error_code",
            "details",
            "is_retryable",
            "retry_after",
            "timestamp",
        }
        assert set(error_dict.keys()) == expected_keys

        assert error_dict["error_type"] == "AgentExecutionError"
        assert error_dict["message"] == "Agent execution failed"
        assert error_dict["error_code"] == "EXEC_FAIL"
        assert error_dict["details"] == {"attempt": 2, "tool": "search"}
        assert error_dict["is_retryable"] is True
        assert error_dict["retry_after"] == 10.0
        assert isinstance(error_dict["timestamp"], float)

    def test_exception_json_serializable(self):
        """Test that exception dict is JSON serializable."""
        import json

        error = RateLimitError("Rate limit exceeded", retry_after=60.0, rate_limit_type="requests")

        error_dict = error.to_dict()

        # Should not raise an exception
        json_str = json.dumps(error_dict)

        # Should be able to deserialize
        deserialized = json.loads(json_str)
        assert deserialized["error_type"] == "RateLimitError"
        assert deserialized["retry_after"] == 60.0


if __name__ == "__main__":
    pytest.main([__file__])
