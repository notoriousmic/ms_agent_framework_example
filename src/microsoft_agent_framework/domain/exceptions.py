"""Domain exceptions and error handling."""

import time
from typing import Any


class AgentFrameworkError(Exception):
    """Base exception for all agent framework errors."""

    def __init__(
        self,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None,
        is_retryable: bool = False,
        retry_after: float | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.is_retryable = is_retryable
        self.retry_after = retry_after
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert exception to dictionary for serialization."""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "error_code": self.error_code,
            "details": self.details,
            "is_retryable": self.is_retryable,
            "retry_after": self.retry_after,
            "timestamp": self.timestamp,
        }


class ConfigurationError(AgentFrameworkError):
    """Raised when there's a configuration issue."""

    pass


class AgentError(AgentFrameworkError):
    """Base exception for agent-related errors."""

    pass


class AgentNotFoundError(AgentError):
    """Raised when an agent is not found."""

    pass


class AgentInitializationError(AgentError):
    """Raised when agent initialization fails."""

    pass


class AgentExecutionError(AgentError):
    """Raised when agent execution fails."""

    def __init__(
        self,
        message: str,
        agent_name: str | None = None,
        execution_time: float | None = None,
        **kwargs,
    ):
        super().__init__(message, **kwargs)
        self.agent_name = agent_name
        self.execution_time = execution_time


class AgentTimeoutError(AgentError):
    """Raised when agent execution times out."""

    def __init__(self, message: str, timeout_duration: float | None = None, **kwargs):
        super().__init__(message, is_retryable=True, **kwargs)
        self.timeout_duration = timeout_duration
        if timeout_duration:
            self.details["timeout_duration"] = timeout_duration


class AgentConnectionError(AgentError):
    """Raised when agent connection fails."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, is_retryable=True, **kwargs)


class AgentResourceExhaustedError(AgentError):
    """Raised when agent resources are exhausted."""

    def __init__(self, message: str, retry_after: float | None = None, **kwargs):
        super().__init__(message, is_retryable=True, retry_after=retry_after, **kwargs)


class ToolError(AgentFrameworkError):
    """Base exception for tool-related errors."""

    pass


class ToolNotFoundError(ToolError):
    """Raised when a tool is not found."""

    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    def __init__(
        self,
        message: str,
        tool_name: str | None = None,
        execution_time: float | None = None,
        **kwargs,
    ):
        super().__init__(message, is_retryable=True, **kwargs)
        self.tool_name = tool_name
        self.execution_time = execution_time
        if tool_name:
            self.details["tool_name"] = tool_name
        if execution_time:
            self.details["execution_time"] = execution_time


class ToolTimeoutError(ToolError):
    """Raised when tool execution times out."""

    def __init__(self, message: str, timeout_duration: float | None = None, **kwargs):
        super().__init__(message, is_retryable=True, **kwargs)
        self.timeout_duration = timeout_duration
        if timeout_duration:
            self.details["timeout_duration"] = timeout_duration


class ToolConnectionError(ToolError):
    """Raised when tool connection fails."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, is_retryable=True, **kwargs)


class ServiceError(AgentFrameworkError):
    """Base exception for service-related errors."""

    pass


class ServiceNotInitializedError(ServiceError):
    """Raised when a service is used before initialization."""

    pass


class RepositoryError(AgentFrameworkError):
    """Base exception for repository-related errors."""

    pass


class EntityNotFoundError(RepositoryError):
    """Raised when an entity is not found in the repository."""

    pass


class ValidationError(AgentFrameworkError):
    """Raised when validation fails."""

    pass


class APIError(AgentFrameworkError):
    """Base exception for API-related errors."""

    pass


class AuthenticationError(APIError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(APIError):
    """Raised when authorization fails."""

    pass


class RateLimitError(APIError):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str,
        retry_after: float | None = None,
        rate_limit_type: str | None = None,
        **kwargs,
    ):
        super().__init__(message, is_retryable=True, retry_after=retry_after, **kwargs)
        self.rate_limit_type = rate_limit_type
        if rate_limit_type:
            self.details["rate_limit_type"] = rate_limit_type


class ConnectionError(AgentFrameworkError):
    """Raised when connection fails."""

    def __init__(self, message: str, **kwargs):
        super().__init__(message, is_retryable=True, **kwargs)


class TimeoutError(AgentFrameworkError):
    """Raised when operation times out."""

    def __init__(self, message: str, timeout_duration: float | None = None, **kwargs):
        super().__init__(message, is_retryable=True, **kwargs)
        self.timeout_duration = timeout_duration
        if timeout_duration:
            self.details["timeout_duration"] = timeout_duration


class ResourceExhaustedError(AgentFrameworkError):
    """Raised when resources are exhausted."""

    def __init__(
        self,
        message: str,
        resource_type: str | None = None,
        retry_after: float | None = None,
        **kwargs,
    ):
        super().__init__(message, is_retryable=True, retry_after=retry_after, **kwargs)
        self.resource_type = resource_type
        if resource_type:
            self.details["resource_type"] = resource_type


class ConfigurationValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        expected_type: str | None = None,
        **kwargs,
    ):
        super().__init__(message, is_retryable=False, **kwargs)
        self.config_key = config_key
        self.expected_type = expected_type
        if config_key:
            self.details["config_key"] = config_key
        if expected_type:
            self.details["expected_type"] = expected_type
