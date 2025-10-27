"""Retry utilities and decorators for enhanced error handling."""

import asyncio
import functools
import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from enum import Enum
from typing import Any, TypeVar

from microsoft_agent_framework.domain.exceptions import (
    AgentTimeoutError,
    APIError,
    AuthenticationError,
    AuthorizationError,
    ConnectionError,
    RateLimitError,
    TimeoutError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RetryStrategy(str, Enum):
    """Available retry strategies."""

    FIXED = "fixed"
    EXPONENTIAL = "exponential"
    LINEAR = "linear"


class RetryPolicy:
    """Configuration for retry behavior."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        retryable_exceptions: set[type[Exception]] | None = None,
        non_retryable_exceptions: set[type[Exception]] | None = None,
    ):
        """
        Initialize retry policy.

        Args:
            max_attempts: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            strategy: Retry strategy to use
            backoff_multiplier: Multiplier for exponential backoff
            jitter: Whether to add random jitter to delays
            retryable_exceptions: Set of exception types that should trigger retries
            non_retryable_exceptions: Set of exception types that should never be retried
        """
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.retryable_exceptions = retryable_exceptions or {
            RateLimitError,
            APIError,
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
            OSError,  # Include network-related errors
        }
        self.non_retryable_exceptions = non_retryable_exceptions or {
            AuthenticationError,
            AuthorizationError,
            ValueError,
            TypeError,
        }

    def should_retry(self, exception: Exception, attempt: int) -> bool:
        """
        Determine if an exception should trigger a retry.

        Args:
            exception: The exception that occurred
            attempt: Current attempt number (0-based)

        Returns:
            True if the operation should be retried
        """
        if attempt >= self.max_attempts:
            return False

        # Check non-retryable exceptions first
        if any(isinstance(exception, exc_type) for exc_type in self.non_retryable_exceptions):
            return False

        # Check retryable exceptions
        return any(isinstance(exception, exc_type) for exc_type in self.retryable_exceptions)

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate the delay before the next retry attempt.

        Args:
            attempt: Current attempt number (0-based)

        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.FIXED:
            delay = self.base_delay
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.base_delay * (attempt + 1)
        else:  # EXPONENTIAL
            delay = self.base_delay * (self.backoff_multiplier**attempt)

        # Apply maximum delay limit
        delay = min(delay, self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            delay *= 0.5 + random.random() * 0.5  # ±25% jitter

        return delay


class RetryContext:
    """Context object passed to retry callbacks."""

    def __init__(
        self,
        attempt: int,
        exception: Exception | None = None,
        elapsed_time: float = 0.0,
        next_delay: float | None = None,
    ):
        self.attempt = attempt
        self.exception = exception
        self.elapsed_time = elapsed_time
        self.next_delay = next_delay


class RetryCallbacks(ABC):
    """Abstract base class for retry callbacks."""

    @abstractmethod
    async def on_retry(self, context: RetryContext) -> None:
        """Called before each retry attempt."""
        pass

    @abstractmethod
    async def on_failure(self, context: RetryContext) -> None:
        """Called when all retry attempts are exhausted."""
        pass


class LoggingRetryCallbacks(RetryCallbacks):
    """Default retry callbacks that log retry attempts."""

    def __init__(self, logger_name: str | None = None):
        self.logger = logging.getLogger(logger_name or __name__)

    async def on_retry(self, context: RetryContext) -> None:
        """Log retry attempt."""
        self.logger.warning(
            f"Retry attempt {context.attempt + 1} after {context.elapsed_time:.2f}s. "
            f"Exception: {context.exception}. Next delay: {context.next_delay:.2f}s"
        )

    async def on_failure(self, context: RetryContext) -> None:
        """Log final failure."""
        self.logger.error(
            f"All retry attempts failed after {context.elapsed_time:.2f}s. Final exception: {context.exception}"
        )


async def retry_async(
    func: Callable[..., Any],
    policy: RetryPolicy,
    callbacks: RetryCallbacks | None = None,
    *args,
    **kwargs,
) -> Any:
    """
    Execute an async function with retry logic.

    Args:
        func: Async function to execute
        policy: Retry policy configuration
        callbacks: Optional callbacks for retry events
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Function result if successful

    Raises:
        The last exception if all retry attempts fail
    """
    callbacks = callbacks or LoggingRetryCallbacks()
    start_time = time.time()
    last_exception = None

    for attempt in range(policy.max_attempts):
        try:
            result = await func(*args, **kwargs)
            if attempt > 0:
                elapsed_time = time.time() - start_time
                logger.info(f"Operation succeeded on attempt {attempt + 1} after {elapsed_time:.2f}s")
            return result

        except Exception as e:
            last_exception = e
            elapsed_time = time.time() - start_time

            if not policy.should_retry(e, attempt):
                await callbacks.on_failure(RetryContext(attempt, e, elapsed_time))
                raise e

            if attempt < policy.max_attempts - 1:  # Not the last attempt
                delay = policy.calculate_delay(attempt)
                context = RetryContext(attempt, e, elapsed_time, delay)
                await callbacks.on_retry(context)
                await asyncio.sleep(delay)

    # All attempts failed
    elapsed_time = time.time() - start_time
    await callbacks.on_failure(RetryContext(policy.max_attempts - 1, last_exception, elapsed_time))
    raise last_exception


def retry_sync(
    func: Callable[..., Any],
    policy: RetryPolicy,
    callbacks: RetryCallbacks | None = None,
    *args,
    **kwargs,
) -> Any:
    """
    Execute a sync function with retry logic.

    Args:
        func: Sync function to execute
        policy: Retry policy configuration
        callbacks: Optional callbacks for retry events
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function

    Returns:
        Function result if successful

    Raises:
        The last exception if all retry attempts fail
    """
    callbacks = callbacks or LoggingRetryCallbacks()
    start_time = time.time()
    last_exception = None

    for attempt in range(policy.max_attempts):
        try:
            result = func(*args, **kwargs)
            if attempt > 0:
                elapsed_time = time.time() - start_time
                logger.info(f"Operation succeeded on attempt {attempt + 1} after {elapsed_time:.2f}s")
            return result

        except Exception as e:
            last_exception = e
            elapsed_time = time.time() - start_time

            if not policy.should_retry(e, attempt):
                # For sync functions, we can't await callbacks, so we use a try/except to handle it gracefully
                try:
                    import asyncio

                    if asyncio.get_running_loop():
                        asyncio.create_task(callbacks.on_failure(RetryContext(attempt, e, elapsed_time)))
                except RuntimeError:
                    # No event loop running, skip async callback
                    pass
                raise e

            if attempt < policy.max_attempts - 1:  # Not the last attempt
                delay = policy.calculate_delay(attempt)
                context = RetryContext(attempt, e, elapsed_time, delay)

                # For sync functions, we can't await callbacks, so we use a try/except to handle it gracefully
                try:
                    import asyncio

                    if asyncio.get_running_loop():
                        asyncio.create_task(callbacks.on_retry(context))
                except RuntimeError:
                    # No event loop running, skip async callback
                    pass

                time.sleep(delay)

    # All attempts failed
    elapsed_time = time.time() - start_time
    try:
        import asyncio

        if asyncio.get_running_loop():
            asyncio.create_task(
                callbacks.on_failure(RetryContext(policy.max_attempts - 1, last_exception, elapsed_time))
            )
    except RuntimeError:
        # No event loop running, skip async callback
        pass
    raise last_exception


def retry_decorator(
    policy: RetryPolicy | None = None,
    callbacks: RetryCallbacks | None = None,
):
    """
    Decorator for adding retry logic to functions.

    Args:
        policy: Retry policy configuration
        callbacks: Optional callbacks for retry events

    Returns:
        Decorated function with retry logic
    """
    if policy is None:
        policy = RetryPolicy()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                return await retry_async(func, policy, callbacks, *args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                return retry_sync(func, policy, callbacks, *args, **kwargs)

            return sync_wrapper

    return decorator


# Predefined retry policies for common scenarios
DEFAULT_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=1.0,
    strategy=RetryStrategy.EXPONENTIAL,
)

AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=5,
    base_delay=0.5,
    max_delay=30.0,
    strategy=RetryStrategy.EXPONENTIAL,
    backoff_multiplier=1.5,
)

CONSERVATIVE_RETRY_POLICY = RetryPolicy(
    max_attempts=2,
    base_delay=2.0,
    strategy=RetryStrategy.FIXED,
    jitter=False,
)

API_RETRY_POLICY = RetryPolicy(
    max_attempts=4,
    base_delay=1.0,
    max_delay=60.0,
    strategy=RetryStrategy.EXPONENTIAL,
    retryable_exceptions={
        RateLimitError,
        APIError,
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        OSError,
    },
    non_retryable_exceptions={
        AuthenticationError,
        AuthorizationError,
        ValueError,
        TypeError,
    },
)

AGENT_RETRY_POLICY = RetryPolicy(
    max_attempts=3,
    base_delay=2.0,
    max_delay=30.0,
    strategy=RetryStrategy.EXPONENTIAL,
    retryable_exceptions={
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
        AgentTimeoutError,
        OSError,
    },
)
