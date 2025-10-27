"""Azure OpenAI agent implementation."""

import time
from typing import Any

from microsoft_agent_framework.domain.interfaces import IAgent
from microsoft_agent_framework.domain.models import (
    AgentConfig,
    AgentResponse,
    AgentStatus,
    Message,
    MessageRole,
)


class AzureAgent(IAgent):
    """Wrapper for Azure OpenAI agents implementing our interface."""

    def __init__(self, config: AgentConfig, azure_agent: Any):
        self._config = config
        self._azure_agent = azure_agent
        self._is_initialized = False

    @property
    def name(self) -> str:
        """Get the agent's name."""
        return self._config.name

    @property
    def config(self) -> AgentConfig:
        """Get the agent's configuration."""
        return self._config

    async def run(self, message: str | list[Message], **kwargs: Any) -> AgentResponse:
        """
        Execute the agent with the given message(s).

        Args:
            message: Input message(s) to process
            **kwargs: Additional parameters

        Returns:
            AgentResponse containing the result
        """
        start_time = time.time()

        try:
            # Convert our message format to what the Azure agent expects
            if isinstance(message, str):
                input_message = message
            else:
                # For now, just use the last message content
                input_message = message[-1].content if message else ""

            # Execute the Azure agent
            response = await self._azure_agent.run(input_message, **kwargs)

            # Extract messages from the response
            messages = self._extract_messages(response)

            execution_time = time.time() - start_time

            return AgentResponse(
                agent_name=self.name,
                status=AgentStatus.COMPLETED,
                messages=messages,
                execution_time=execution_time,
                metadata={"azure_response": str(response)},
            )

        except Exception as e:
            execution_time = time.time() - start_time
            return AgentResponse(
                agent_name=self.name,
                status=AgentStatus.ERROR,
                messages=[],
                execution_time=execution_time,
                error=str(e),
            )

    async def initialize(self) -> None:
        """Initialize the agent."""
        if not self._is_initialized:
            # Azure agents don't require explicit initialization
            self._is_initialized = True

    async def cleanup(self) -> None:
        """Cleanup agent resources."""
        # Azure agents don't require explicit cleanup
        self._is_initialized = False

    def _extract_messages(self, response: Any) -> list[Message]:
        """
        Extract messages from Azure agent response.

        Args:
            response: Azure agent response

        Returns:
            List of extracted messages
        """
        messages = []

        try:
            if hasattr(response, "messages") and response.messages:
                for msg in response.messages:
                    if hasattr(msg, "contents") and msg.contents:
                        for content in msg.contents:
                            text = content.text if hasattr(content, "text") else str(content)
                            messages.append(Message(role=MessageRole.ASSISTANT, content=text))
            else:
                # Fallback: treat entire response as content
                messages.append(Message(role=MessageRole.ASSISTANT, content=str(response)))
        except Exception:
            # Fallback: treat entire response as content
            messages.append(Message(role=MessageRole.ASSISTANT, content=str(response)))

        return messages
