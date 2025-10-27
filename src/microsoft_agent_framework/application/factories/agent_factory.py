"""Agent factory implementations."""

from agent_framework import MCPStdioTool
from agent_framework.azure import AzureOpenAIResponsesClient

from microsoft_agent_framework.config import settings
from microsoft_agent_framework.domain.interfaces import IAgent, IAgentFactory
from microsoft_agent_framework.domain.models import AgentConfig, AgentType
from microsoft_agent_framework.domain.prompts.research_prompt import RESEARCH_PROMPT
from microsoft_agent_framework.domain.prompts.supervisor_prompt import SUPERVISOR_PROMPT
from microsoft_agent_framework.domain.prompts.writer_prompt import WRITER_PROMPT


class AzureAgentFactory(IAgentFactory):
    """Factory for creating Azure OpenAI based agents."""

    def __init__(self):
        self._supported_types = [
            AgentType.SUPERVISOR.value,
            AgentType.RESEARCH.value,
            AgentType.WRITER.value,
        ]
        self._prompt_mapping = {
            AgentType.SUPERVISOR.value: SUPERVISOR_PROMPT,
            AgentType.RESEARCH.value: RESEARCH_PROMPT,
            AgentType.WRITER.value: WRITER_PROMPT,
        }

    def create_agent(self, agent_type: str, config: AgentConfig) -> IAgent:
        """
        Create an agent of the specified type.

        Args:
            agent_type: Type of agent to create
            config: Agent configuration

        Returns:
            Created agent instance

        Raises:
            ValueError: If agent type is not supported
        """
        if agent_type not in self._supported_types:
            raise ValueError(f"Unsupported agent type: {agent_type}")

        # Get Azure OpenAI client
        AzureOpenAIResponsesClient(
            azure_endpoint=settings.azure.endpoint,
            deployment_name=settings.azure.responses_deployment_name,
            api_key=settings.azure.api_key,
            api_version=settings.azure.api_version,
        )

        # Create tools based on agent type
        self._create_tools(agent_type, config)

        # Get prompt for agent type
        self._prompt_mapping.get(agent_type, config.instructions)

        # For now, return our concrete agent implementations
        if agent_type == AgentType.SUPERVISOR.value:
            from microsoft_agent_framework.application.agents.supervisor_agent import (
                SupervisorAgent,
            )

            return SupervisorAgent(config)
        elif agent_type == AgentType.RESEARCH.value:
            from microsoft_agent_framework.application.agents.research_agent import (
                ResearchAgent,
            )

            return ResearchAgent(config)
        elif agent_type == AgentType.WRITER.value:
            from microsoft_agent_framework.application.agents.writer_agent import (
                WriterAgent,
            )

            return WriterAgent(config)
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    def get_supported_types(self) -> list[str]:
        """Get list of supported agent types."""
        return self._supported_types.copy()

    def _create_tools(self, agent_type: str, config: AgentConfig) -> list:
        """Create tools for the agent based on type and configuration."""
        tools = []

        if agent_type == AgentType.RESEARCH.value:
            # Add search tool if API key is available
            if settings.tools.brave_api_key:
                search_tool = MCPStdioTool(
                    name="brave_search",
                    command="npx",
                    args=["-y", "@modelcontextprotocol/server-brave-search"],
                    env={"BRAVE_API_KEY": settings.tools.brave_api_key},
                )
                tools.append(search_tool)

        elif agent_type == AgentType.SUPERVISOR.value:
            # Supervisor gets delegation functions as tools
            # These would be created separately and passed in
            pass

        return tools


class AgentFactoryRegistry:
    """Registry for managing different agent factories."""

    def __init__(self):
        self._factories: dict[str, IAgentFactory] = {}
        self._default_factory: str = "azure"

        # Register default factories
        self.register_factory("azure", AzureAgentFactory())

    def register_factory(self, name: str, factory: IAgentFactory) -> None:
        """Register a new agent factory."""
        self._factories[name] = factory

    def get_factory(self, name: str = None) -> IAgentFactory:
        """
        Get a factory by name.

        Args:
            name: Factory name, uses default if None

        Returns:
            Agent factory instance

        Raises:
            ValueError: If factory not found
        """
        factory_name = name or self._default_factory
        if factory_name not in self._factories:
            raise ValueError(f"Factory '{factory_name}' not found")
        return self._factories[factory_name]

    def create_agent(self, agent_type: str, config: AgentConfig, factory_name: str = None) -> IAgent:
        """
        Create an agent using the specified factory.

        Args:
            agent_type: Type of agent to create
            config: Agent configuration
            factory_name: Factory to use, uses default if None

        Returns:
            Created agent instance
        """
        factory = self.get_factory(factory_name)
        return factory.create_agent(agent_type, config)


# Global factory registry
agent_factory = AgentFactoryRegistry()
