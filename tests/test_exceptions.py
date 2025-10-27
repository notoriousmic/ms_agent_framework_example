"""Unit tests for domain exceptions and utilities."""

import pytest

from microsoft_agent_framework.domain.exceptions import (
    AgentError,
    AgentExecutionError,
    AgentFrameworkError,
    AgentInitializationError,
    AgentNotFoundError,
    AgentTimeoutError,
    ConfigurationError,
    ToolError,
    ToolExecutionError,
    ToolNotFoundError,
)


class TestExceptions:
    """Test cases for domain exceptions."""

    def test_agent_framework_error_base(self):
        """Test base AgentFrameworkError."""
        error = AgentFrameworkError("Base error")
        assert str(error) == "Base error"
        assert isinstance(error, Exception)

    def test_configuration_error(self):
        """Test ConfigurationError."""
        error = ConfigurationError("Config issue")
        assert str(error) == "Config issue"
        assert isinstance(error, AgentFrameworkError)

    def test_agent_error_base(self):
        """Test base AgentError."""
        error = AgentError("Agent error")
        assert str(error) == "Agent error"
        assert isinstance(error, AgentFrameworkError)

    def test_agent_not_found_error(self):
        """Test AgentNotFoundError."""
        error = AgentNotFoundError("Agent not found")
        assert str(error) == "Agent not found"
        assert isinstance(error, AgentError)

    def test_agent_initialization_error(self):
        """Test AgentInitializationError."""
        error = AgentInitializationError("Init failed")
        assert str(error) == "Init failed"
        assert isinstance(error, AgentError)

    def test_agent_execution_error_basic(self):
        """Test basic AgentExecutionError."""
        error = AgentExecutionError("Execution failed")
        assert str(error) == "Execution failed"
        assert isinstance(error, AgentError)
        assert error.agent_name is None
        assert error.execution_time is None

    def test_agent_execution_error_with_details(self):
        """Test AgentExecutionError with agent details."""
        error = AgentExecutionError("Execution failed", agent_name="Test Agent", execution_time=2.5)
        assert str(error) == "Execution failed"
        assert error.agent_name == "Test Agent"
        assert error.execution_time == 2.5

    def test_agent_timeout_error_basic(self):
        """Test basic AgentTimeoutError."""
        error = AgentTimeoutError("Timeout occurred")
        assert str(error) == "Timeout occurred"
        assert isinstance(error, AgentError)

    def test_agent_timeout_error_with_details(self):
        """Test AgentTimeoutError with additional details."""
        error = AgentTimeoutError(
            "Timeout occurred",
            error_code="TIMEOUT_001",
            details={"agent_name": "Test Agent", "timeout_duration": 30.0},
        )
        assert str(error) == "Timeout occurred"
        assert error.error_code == "TIMEOUT_001"
        assert error.details["agent_name"] == "Test Agent"
        assert error.details["timeout_duration"] == 30.0

    def test_tool_error_base(self):
        """Test base ToolError."""
        error = ToolError("Tool error")
        assert str(error) == "Tool error"
        assert isinstance(error, AgentFrameworkError)

    def test_tool_not_found_error(self):
        """Test ToolNotFoundError."""
        error = ToolNotFoundError("Tool not found")
        assert str(error) == "Tool not found"
        assert isinstance(error, ToolError)

    def test_tool_execution_error_basic(self):
        """Test basic ToolExecutionError."""
        error = ToolExecutionError("Tool execution failed")
        assert str(error) == "Tool execution failed"
        assert isinstance(error, ToolError)

    def test_tool_execution_error_with_details(self):
        """Test ToolExecutionError with tool details."""
        error = ToolExecutionError(
            "Tool execution failed",
            error_code="TOOL_001",
            details={"tool_name": "Search Tool", "execution_time": 1.5},
        )
        assert str(error) == "Tool execution failed"
        assert error.error_code == "TOOL_001"
        assert error.details["tool_name"] == "Search Tool"
        assert error.details["execution_time"] == 1.5

    def test_exception_inheritance_hierarchy(self):
        """Test exception inheritance hierarchy."""
        # Test that all exceptions inherit from the correct base classes
        assert issubclass(ConfigurationError, AgentFrameworkError)
        assert issubclass(AgentError, AgentFrameworkError)
        assert issubclass(AgentNotFoundError, AgentError)
        assert issubclass(AgentInitializationError, AgentError)
        assert issubclass(AgentExecutionError, AgentError)
        assert issubclass(AgentTimeoutError, AgentError)
        assert issubclass(ToolError, AgentFrameworkError)
        assert issubclass(ToolNotFoundError, ToolError)
        assert issubclass(ToolExecutionError, ToolError)

    def test_exception_raising_and_catching(self):
        """Test raising and catching exceptions."""
        # Test raising and catching specific exceptions
        with pytest.raises(AgentNotFoundError) as exc_info:
            raise AgentNotFoundError("Test agent not found")

        assert "Test agent not found" in str(exc_info.value)

        # Test catching by base class
        with pytest.raises(AgentError):
            raise AgentInitializationError("Init failed")

        with pytest.raises(AgentFrameworkError):
            raise ToolExecutionError("Tool failed")

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

    def test_multiple_exception_parameters(self):
        """Test exceptions with multiple parameters."""
        error = AgentExecutionError("Complex failure", agent_name="Complex Agent", execution_time=10.5)

        # Test that all parameters are accessible
        assert str(error) == "Complex failure"
        assert error.agent_name == "Complex Agent"
        assert error.execution_time == 10.5

        # Test that it's still an instance of the base classes
        assert isinstance(error, AgentError)
        assert isinstance(error, AgentFrameworkError)
        assert isinstance(error, Exception)


class TestExceptionUsagePatterns:
    """Test common exception usage patterns."""

    def test_reraise_with_context(self):
        """Test re-raising exceptions with additional context."""

        def failing_function():
            raise ValueError("Original error")

        def wrapper_function():
            try:
                failing_function()
            except ValueError as e:
                raise AgentExecutionError(f"Agent failed: {str(e)}", agent_name="Wrapper Agent") from e

        with pytest.raises(AgentExecutionError) as exc_info:
            wrapper_function()

        assert "Agent failed: Original error" in str(exc_info.value)
        assert exc_info.value.agent_name == "Wrapper Agent"
        assert isinstance(exc_info.value.__cause__, ValueError)

    def test_exception_in_async_context(self):
        """Test exceptions in async context."""
        import asyncio

        async def async_failing_function():
            await asyncio.sleep(0.001)  # Simulate async work
            raise AgentTimeoutError(
                "Async operation timed out",
                details={"agent_name": "Async Agent", "timeout_duration": 5.0},
            )

        async def test_async_exception():
            with pytest.raises(AgentTimeoutError) as exc_info:
                await async_failing_function()

            assert "Async operation timed out" in str(exc_info.value)
            assert exc_info.value.details["agent_name"] == "Async Agent"
            assert exc_info.value.details["timeout_duration"] == 5.0

        # Run the async test
        asyncio.run(test_async_exception())

    def test_exception_chaining(self):
        """Test exception chaining in complex scenarios."""

        def level_3():
            raise ConnectionError("Network connection failed")

        def level_2():
            try:
                level_3()
            except ConnectionError as e:
                raise ToolExecutionError(
                    "Search tool failed",
                    details={"tool_name": "Web Search", "execution_time": 2.0},
                ) from e

        def level_1():
            try:
                level_2()
            except ToolExecutionError as e:
                raise AgentExecutionError(
                    "Research agent failed",
                    agent_name="Research Agent",
                    execution_time=5.0,
                ) from e

        with pytest.raises(AgentExecutionError) as exc_info:
            level_1()

        # Check the top-level exception
        assert exc_info.value.agent_name == "Research Agent"

        # Check the chained exceptions
        tool_error = exc_info.value.__cause__
        assert isinstance(tool_error, ToolExecutionError)
        assert tool_error.details["tool_name"] == "Web Search"

        connection_error = tool_error.__cause__
        assert isinstance(connection_error, ConnectionError)
        assert "Network connection failed" in str(connection_error)
