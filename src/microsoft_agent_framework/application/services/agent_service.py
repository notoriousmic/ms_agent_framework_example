"""Agent service for managing agent lifecycle and execution."""

import asyncio
import logging
from uuid import uuid4

from microsoft_agent_framework.config import settings
from microsoft_agent_framework.domain.exceptions import (
    AgentExecutionError,
    AgentNotFoundError,
    AgentTimeoutError,
)
from microsoft_agent_framework.domain.interfaces import IAgent, IService
from microsoft_agent_framework.domain.models import AgentResponse, AgentStatus, Message
from microsoft_agent_framework.domain.retry import (
    LoggingRetryCallbacks,
    RetryPolicy,
    RetryStrategy,
    retry_async,
)

logger = logging.getLogger(__name__)


class AgentService(IService):
    """Service for managing agents and their execution."""

    def __init__(self):
        self._agents: dict[str, IAgent] = {}
        self._is_initialized = False
        self._retry_policy = self._create_retry_policy()
        self._retry_callbacks = LoggingRetryCallbacks("agent_service")

    def _create_retry_policy(self) -> RetryPolicy:
        """Create retry policy for agent operations."""
        return RetryPolicy(
            max_attempts=settings.resilience.agent_max_attempts,
            base_delay=settings.resilience.agent_base_delay,
            max_delay=settings.resilience.agent_max_delay,
            strategy=RetryStrategy.EXPONENTIAL,
            retryable_exceptions={
                AgentTimeoutError,
                ConnectionError,
                TimeoutError,
                asyncio.TimeoutError,
                OSError,
            },
            non_retryable_exceptions={
                AgentNotFoundError,
                ValueError,
                TypeError,
            },
        )

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._is_initialized

    async def initialize(self) -> None:
        """Initialize the service."""
        if self._is_initialized:
            return

        self._is_initialized = True

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        for agent in self._agents.values():
            await agent.cleanup()
        self._agents.clear()
        self._is_initialized = False

    def register_agent(self, agent_id: str, agent: IAgent) -> None:
        """
        Register an agent with the service.

        Args:
            agent_id: Unique identifier for the agent
            agent: Agent instance to register
        """
        self._agents[agent_id] = agent

    def get_agent(self, agent_id: str) -> IAgent | None:
        """
        Get an agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance or None if not found
        """
        return self._agents.get(agent_id)

    def get_all_agents(self) -> list[str]:
        """Get list of all registered agent IDs."""
        return list(self._agents.keys())

    async def execute_agent(
        self,
        agent_id: str,
        message: str | list[Message],
        timeout: int | None = None,
        enable_retry: bool = True,
    ) -> AgentResponse:
        """
        Execute an agent with the given message.

        Args:
            agent_id: Agent identifier
            message: Input message(s)
            timeout: Execution timeout in seconds
            enable_retry: Whether to enable retry logic

        Returns:
            Agent execution response

        Raises:
            AgentNotFoundError: If agent not found
            AgentExecutionError: If execution fails after retries
            AgentTimeoutError: If execution times out
        """
        agent = self.get_agent(agent_id)
        if not agent:
            raise AgentNotFoundError(f"Agent '{agent_id}' not found")

        timeout = timeout or settings.resilience.agent_execution_timeout

        async def _execute_with_timeout():
            """Execute agent with timeout wrapper."""
            try:
                return await asyncio.wait_for(agent.run(message), timeout=timeout)
            except TimeoutError as e:
                raise AgentTimeoutError(
                    f"Agent '{agent_id}' execution timed out after {timeout} seconds",
                    timeout_duration=timeout,
                ) from e
            except Exception as e:
                logger.error(f"Agent '{agent_id}' execution failed: {e}")
                raise AgentExecutionError(f"Agent '{agent_id}' execution failed: {e}", agent_name=agent.name) from e

        # Execute with or without retry based on configuration and parameter
        if enable_retry and settings.resilience.enable_retries:
            try:
                return await retry_async(_execute_with_timeout, self._retry_policy, self._retry_callbacks)
            except Exception as e:
                # If retry fails, return error response instead of raising
                logger.error(f"Agent '{agent_id}' execution failed after retries: {e}")
                return AgentResponse(
                    agent_name=agent.name,
                    status=AgentStatus.ERROR,
                    messages=[],
                    execution_time=0.0,
                    error=str(e),
                )
        else:
            try:
                return await _execute_with_timeout()
            except Exception as e:
                # Return error response for non-retry execution
                return AgentResponse(
                    agent_name=agent.name,
                    status=AgentStatus.ERROR,
                    messages=[],
                    execution_time=0.0,
                    error=str(e),
                )

    async def create_conversation_session(self) -> str:
        """
        Create a new conversation session.

        Returns:
            Session ID
        """
        return str(uuid4())
