"""Supervisor agent implementation using the new OOP architecture."""

import time
from typing import Annotated, Any

from agent_framework import ai_function
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential

from microsoft_agent_framework.application.factories import agent_factory
from microsoft_agent_framework.config import settings
from microsoft_agent_framework.domain.exceptions import (
    AgentExecutionError,
    AgentInitializationError,
)
from microsoft_agent_framework.domain.interfaces import IAgent
from microsoft_agent_framework.domain.models import (
    AgentConfig,
    AgentResponse,
    AgentStatus,
    AgentType,
    ConversationThread,
    Message,
    MessageRole,
)
from microsoft_agent_framework.domain.prompts.supervisor_prompt import SUPERVISOR_PROMPT


class SupervisorAgent(IAgent):
    """Supervisor agent that coordinates other agents."""

    def __init__(self, config: AgentConfig):
        self._config = config
        self._azure_agent = None
        self._research_agent = None
        self._writer_agent = None
        self._is_initialized = False
        self._native_threads: dict[str, Any] = {}  # Map thread_id to native Azure agent thread

    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self._config.name

    @property
    def config(self) -> AgentConfig:
        """Get the agent's configuration."""
        return self._config

    async def initialize(self) -> None:
        """Initialize the supervisor agent and sub-agents."""
        if self._is_initialized:
            return

        try:
            # Validate Azure AI Foundry configuration
            if not settings.azure_ai_foundry.is_configured:
                raise AgentInitializationError(
                    "Azure AI Foundry is not configured. Please set PROJECT_ENDPOINT in your .env file."
                )

            # Ensure environment variables are set for Azure AI library
            import os

            if not os.getenv("AZURE_AI_PROJECT_ENDPOINT"):
                os.environ["AZURE_AI_PROJECT_ENDPOINT"] = settings.azure_ai_foundry.project_endpoint

            # Create Azure AI Foundry agent client
            client = AzureAIAgentClient(
                project_endpoint=settings.azure_ai_foundry.project_endpoint,
                model_deployment_name=settings.azure_ai_foundry.model_deployment_name,
                async_credential=DefaultAzureCredential(),
            )

            # Create delegation functions
            delegation_tools = [
                self._create_research_delegation_function(),
                self._create_writer_delegation_function(),
            ]

            # Create the underlying Azure agent in Azure AI Foundry
            self._azure_agent = client.create_agent(
                name=self.name,
                instructions=SUPERVISOR_PROMPT,
                tools=delegation_tools,
            )

            # Initialize sub-agents
            await self._initialize_sub_agents()

            self._is_initialized = True

        except Exception as e:
            raise AgentInitializationError(f"Failed to initialize supervisor agent: {e}") from e

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        if self._research_agent:
            await self._research_agent.cleanup()
        if self._writer_agent:
            await self._writer_agent.cleanup()
        self._is_initialized = False

    async def run(
        self,
        message: str | list[Message],
        thread: ConversationThread | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """Execute the supervisor agent."""
        if not self._is_initialized:
            await self.initialize()

        start_time = time.time()

        try:
            # Convert message format
            input_message = self._convert_message(message)

            # Get or create native Azure agent thread
            native_thread = None
            if thread:
                # Get existing native thread or create new one
                if thread.thread_id in self._native_threads:
                    native_thread = self._native_threads[thread.thread_id]
                else:
                    # Create new native thread from Azure agent
                    native_thread = self._azure_agent.get_new_thread()
                    self._native_threads[thread.thread_id] = native_thread

                # Add user message to custom thread for persistence
                user_message = Message(role=MessageRole.USER, content=input_message)
                thread.add_message(user_message)

            # Execute the Azure agent with native thread
            if native_thread:
                response = await self._azure_agent.run(input_message, thread=native_thread, **kwargs)
            else:
                response = await self._azure_agent.run(input_message, **kwargs)

            # Extract messages from response
            messages = self._extract_messages(response)

            # Add assistant messages to custom thread for persistence
            if thread:
                thread.add_messages(messages)

            execution_time = time.time() - start_time

            return AgentResponse(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                messages=messages,
                execution_time=execution_time,
                metadata={
                    "azure_response": str(response),
                    "thread_id": thread.thread_id if thread else None,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            raise AgentExecutionError(
                f"Supervisor agent execution failed: {e}",
                agent_name=self.name,
                execution_time=execution_time,
            ) from e

    async def _initialize_sub_agents(self) -> None:
        """Initialize research and writer sub-agents."""
        # Create research agent
        research_config = AgentConfig(
            name="Research Agent",
            agent_type=AgentType.RESEARCH,
            instructions="",  # Will use default
        )
        self._research_agent = agent_factory.create_agent(AgentType.RESEARCH.value, research_config)
        await self._research_agent.initialize()

        # Create writer agent
        writer_config = AgentConfig(
            name="Writer Agent",
            agent_type=AgentType.WRITER,
            instructions="",  # Will use default
        )
        self._writer_agent = agent_factory.create_agent(AgentType.WRITER.value, writer_config)
        await self._writer_agent.initialize()

    def _create_research_delegation_function(self):
        """Create research delegation function."""

        @ai_function
        async def delegate_to_research_agent(
            query: Annotated[str, "The research query or topic to investigate using web search"],
        ) -> str:
            """
            Delegate to the Research Agent to gather information from web searches.
            Use this when you need to research topics, find recent information, or gather data.
            """
            if not self._research_agent:
                return "Research agent not available"

            try:
                response = await self._research_agent.run(query)
                # Extract text from our standardized response
                if response.messages:
                    return response.messages[-1].content
                return str(response)
            except Exception as e:
                return f"Research failed: {e}"

        return delegate_to_research_agent

    def _create_writer_delegation_function(self):
        """Create writer delegation function."""

        @ai_function
        async def delegate_to_writer_agent(
            task: Annotated[
                str,
                "The email writing task with all necessary context and requirements",
            ],
        ) -> str:
            """
            Delegate to the Writer Agent to craft professional email drafts.
            Use this after gathering information to create polished email responses.
            """
            if not self._writer_agent:
                return "Writer agent not available"

            try:
                response = await self._writer_agent.run(task)
                # Extract text from our standardized response
                if response.messages:
                    return response.messages[-1].content
                return str(response)
            except Exception as e:
                return f"Writing failed: {e}"

        return delegate_to_writer_agent

    def _convert_message(self, message: str | list[Message]) -> str:
        """Convert message to string format."""
        if isinstance(message, str):
            return message
        elif isinstance(message, list) and message:
            return message[-1].content
        return ""

    def _extract_messages(self, response: Any) -> list[Message]:
        """Extract messages from Azure agent response, filtering out internal delegation details."""
        messages = []

        try:
            if hasattr(response, "messages") and response.messages:
                for msg in response.messages:
                    if hasattr(msg, "contents") and msg.contents:
                        for content in msg.contents:
                            # Skip FunctionCall and FunctionResult content (internal delegation details)
                            # Only keep TextContent which contains actual responses
                            content_type = type(content).__name__

                            if "FunctionCall" in content_type or "FunctionResult" in content_type:
                                # Skip internal delegation steps
                                continue
                            elif hasattr(content, "text"):
                                # This is TextContent - the actual response
                                text = content.text
                                if text:
                                    messages.append(Message(role=MessageRole.ASSISTANT, content=text))
                            else:
                                # For other content types, try to convert to string
                                text_str = str(content)
                                if text_str and not text_str.startswith("<"):
                                    messages.append(Message(role=MessageRole.ASSISTANT, content=text_str))
            else:
                messages.append(Message(role=MessageRole.ASSISTANT, content=str(response)))
        except Exception:
            messages.append(Message(role=MessageRole.ASSISTANT, content=str(response)))

        return messages


def create_supervisor_agent() -> SupervisorAgent:
    """Create a supervisor agent instance."""
    config = AgentConfig(
        name="Supervisor Agent",
        agent_type=AgentType.SUPERVISOR,
        instructions=SUPERVISOR_PROMPT,
    )
    return SupervisorAgent(config)


async def main(task: str):
    """Main entry point for supervisor agent (backward compatibility)."""
    agent = create_supervisor_agent()
    try:
        response = await agent.run(task)
        return response
    finally:
        await agent.cleanup()
