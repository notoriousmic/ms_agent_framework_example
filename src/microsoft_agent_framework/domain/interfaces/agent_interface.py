"""Agent interface definitions."""

from abc import ABC, abstractmethod
from typing import Any

from ..models.agent_models import AgentConfig, AgentResponse, Message
from ..models.conversation_models import ConversationThread


class IAgent(ABC):
    """Interface for all agent implementations."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Get the agent's name."""
        pass

    @property
    @abstractmethod
    def config(self) -> AgentConfig:
        """Get the agent's configuration."""
        pass

    @abstractmethod
    async def run(
        self,
        message: str | list[Message],
        thread: ConversationThread | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Execute the agent with the given message(s).

        Args:
            message: Input message(s) to process
            thread: Optional conversation thread for context
            **kwargs: Additional parameters

        Returns:
            AgentResponse containing the result
        """
        pass

    def get_new_thread(self) -> ConversationThread:
        """
        Create a new conversation thread for this agent.

        Returns:
            New ConversationThread instance
        """
        return ConversationThread(
            agent_name=self.name,
            agent_type=(
                self.config.agent_type.value
                if hasattr(self.config.agent_type, "value")
                else str(self.config.agent_type)
            ),
        )

    async def deserialize_thread(self, data: dict[str, Any]) -> ConversationThread:
        """
        Deserialize a conversation thread from data.

        Args:
            data: Serialized thread data

        Returns:
            ConversationThread instance
        """
        return ConversationThread.deserialize(data)

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the agent."""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        pass


class IAgentFactory(ABC):
    """Interface for agent factories."""

    @abstractmethod
    def create_agent(self, agent_type: str, config: AgentConfig) -> IAgent:
        """
        Create an agent of the specified type.

        Args:
            agent_type: Type of agent to create
            config: Agent configuration

        Returns:
            Created agent instance
        """
        pass

    @abstractmethod
    def get_supported_types(self) -> list[str]:
        """Get list of supported agent types."""
        pass
