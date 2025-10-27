"""Research agent implementation using the new OOP architecture."""

import logging
import time
from typing import Any

from agent_framework import MCPStdioTool
from agent_framework.azure import AzureAIAgentClient
from azure.identity.aio import DefaultAzureCredential

from microsoft_agent_framework.config import settings
from microsoft_agent_framework.domain.exceptions import (
    AgentExecutionError,
    AgentInitializationError,
    ConnectionError,
    TimeoutError,
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
from microsoft_agent_framework.domain.prompts.research_prompt import RESEARCH_PROMPT
from microsoft_agent_framework.domain.retry import (
    LoggingRetryCallbacks,
    RetryPolicy,
    RetryStrategy,
    retry_async,
)

logger = logging.getLogger(__name__)


class ResearchAgent(IAgent):
    """Research agent with web search capabilities."""

    def __init__(self, config: AgentConfig):
        self._config = config
        self._azure_agent = None
        self._is_initialized = False
        self._native_threads: dict[str, Any] = {}  # Map thread_id to native Azure agent thread
        self._retry_policy = self._create_retry_policy()
        self._retry_callbacks = LoggingRetryCallbacks("research_agent")

    def _create_retry_policy(self) -> RetryPolicy:
        """Create retry policy for research agent operations."""
        return RetryPolicy(
            max_attempts=settings.resilience.agent_max_attempts,
            base_delay=settings.resilience.agent_base_delay,
            max_delay=settings.resilience.agent_max_delay,
            strategy=RetryStrategy.EXPONENTIAL,
            retryable_exceptions={
                ConnectionError,
                TimeoutError,
                OSError,
                Exception,  # Catch-all for Azure SDK and network exceptions
            },
            non_retryable_exceptions={
                AgentInitializationError,
                ValueError,
                TypeError,
            },
        )

    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self._config.name

    @property
    def config(self) -> AgentConfig:
        """Get the agent's configuration."""
        return self._config

    async def initialize(self) -> None:
        """Initialize the research agent."""
        if self._is_initialized:
            return

        try:
            # Validate Azure AI Foundry configuration
            if not settings.azure_ai_foundry.is_configured:
                raise AgentInitializationError(
                    "Azure AI Foundry is not configured. Please set PROJECT_ENDPOINT in your .env file."
                )

            # Create tools
            tools = self._create_tools()

            # Create Azure AI Foundry agent client
            client = AzureAIAgentClient(
                project_endpoint=settings.azure_ai_foundry.project_endpoint,
                model_deployment_name=settings.azure_ai_foundry.model_deployment_name,
                async_credential=DefaultAzureCredential(),
            )

            # Create the underlying Azure agent in Azure AI Foundry
            self._azure_agent = client.create_agent(
                name=self.name,
                instructions=RESEARCH_PROMPT,
                tools=tools,
            )

            self._is_initialized = True

        except Exception as e:
            raise AgentInitializationError(f"Failed to initialize research agent: {e}") from e

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        self._is_initialized = False

    async def run(
        self,
        message: str | list[Message],
        thread: ConversationThread | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """Execute the research agent."""
        if not self._is_initialized:
            await self.initialize()

        start_time = time.time()

        async def _execute_research():
            """Inner function for research agent execution with retry support."""
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
            try:
                if native_thread:
                    response = await self._azure_agent.run(input_message, thread=native_thread, **kwargs)
                else:
                    response = await self._azure_agent.run(input_message, **kwargs)
                return response
            except Exception as e:
                logger.error(f"Research agent execution failed: {e}")
                # Re-raise with more specific error types for better retry handling
                if "timeout" in str(e).lower():
                    raise TimeoutError(f"Research agent execution timed out: {e}") from e
                elif "connection" in str(e).lower() or "network" in str(e).lower():
                    raise ConnectionError(f"Research agent connection failed: {e}") from e
                else:
                    raise AgentExecutionError(f"Research agent execution failed: {e}") from e

        try:
            # Execute with retry if enabled
            if settings.resilience.enable_retries:
                response = await retry_async(_execute_research, self._retry_policy, self._retry_callbacks)
            else:
                response = await _execute_research()

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
                    "retry_enabled": settings.resilience.enable_retries,
                },
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Research agent execution failed after retries: {e}")

            # Still raise the exception for proper error handling upstream
            raise AgentExecutionError(
                f"Research agent execution failed: {e}",
                agent_name=self.name,
                execution_time=execution_time,
            ) from e

    def _create_tools(self) -> list:
        """Create tools for the research agent."""
        tools = []

        # Add search tool if API key is available
        if settings.tools.brave_api_key:
            search_tool = MCPStdioTool(
                name="brave_search",
                command="npx",
                args=["-y", "@modelcontextprotocol/server-brave-search"],
                env={"BRAVE_API_KEY": settings.tools.brave_api_key},
            )
            tools.append(search_tool)

        return tools

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


def create_research_agent() -> ResearchAgent:
    """Create a research agent instance (backward compatibility)."""
    config = AgentConfig(
        name="Research Agent",
        agent_type=AgentType.RESEARCH,
        instructions=RESEARCH_PROMPT,
    )
    return ResearchAgent(config)
