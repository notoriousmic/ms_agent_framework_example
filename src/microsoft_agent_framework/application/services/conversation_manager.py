"""High-level conversation manager with automatic thread handling."""

from microsoft_agent_framework.application.services.conversation_service import (
    ConversationService,
)
from microsoft_agent_framework.application.services.conversation_session import (
    ConversationSession,
)
from microsoft_agent_framework.domain.interfaces import IAgent
from microsoft_agent_framework.domain.models import AgentResponse, ConversationThread


class ConversationManager:
    """Manages conversations with automatic thread handling."""

    def __init__(
        self,
        conversation_service: ConversationService,
        session_manager: ConversationSession | None = None,
    ):
        self.conversation_service = conversation_service
        self.session_manager = session_manager or ConversationSession()

    async def chat(
        self,
        agent: IAgent,
        message: str,
        thread_id: str | None = None,
        new_conversation: bool = False,
        conversation_title: str | None = None,
        auto_save: bool = True,
    ) -> tuple[AgentResponse, ConversationThread]:
        """
        Chat with an agent using automatic thread management.

        Args:
            agent: The agent to chat with
            message: Message to send
            thread_id: Specific thread ID (optional)
            new_conversation: Force create new conversation
            conversation_title: Title for new conversations
            auto_save: Automatically save the thread

        Returns:
            Tuple of (agent_response, conversation_thread)
        """
        agent_type = (
            agent.config.agent_type.value if hasattr(agent.config.agent_type, "value") else str(agent.config.agent_type)
        )

        # Determine which thread to use
        thread = await self._get_or_create_thread(
            agent=agent,
            agent_type=agent_type,
            thread_id=thread_id,
            new_conversation=new_conversation,
            conversation_title=conversation_title,
        )

        # Execute the agent
        response = await agent.run(message, thread=thread)

        # Save thread if auto_save is enabled
        if auto_save:
            await self.conversation_service.save_thread(thread)
            # Update session to track this as current thread
            self.session_manager.set_current_thread_id(agent_type, thread.thread_id)

        return response, thread

    async def smart_chat(
        self,
        message: str,
        agent_type: str,
        force_new: bool = False,
        title: str | None = None,
        auto_save: bool = True,
    ) -> tuple[AgentResponse, str]:
        """
        Smart chat with automatic agent creation and thread management.

        Args:
            message: Message to send
            agent_type: Type of agent to use
            force_new: Force create new conversation
            title: Title for new conversations
            auto_save: Automatically save the thread

        Returns:
            Tuple of (agent_response, thread_id)
        """
        from microsoft_agent_framework.application.factories import agent_factory
        from microsoft_agent_framework.domain.models import AgentConfig, AgentType

        # Create agent
        config = AgentConfig(
            name=f"{agent_type}_agent",
            agent_type=AgentType(agent_type),
            instructions="",
        )
        agent = agent_factory.create_agent(agent_type, config)

        # Use the regular chat method
        response, thread = await self.chat(
            agent=agent,
            message=message,
            new_conversation=force_new,
            conversation_title=title,
            auto_save=auto_save,
        )

        return response, thread.thread_id

    async def _get_or_create_thread(
        self,
        agent: IAgent,
        agent_type: str,
        thread_id: str | None = None,
        new_conversation: bool = False,
        conversation_title: str | None = None,
    ) -> ConversationThread:
        """Get existing thread or create new one."""

        # If specific thread_id provided, use that
        if thread_id:
            thread = await self.conversation_service.load_thread(thread_id)
            if thread:
                return thread
            else:
                raise ValueError(f"Thread {thread_id} not found")

        # If forcing new conversation, create new thread
        if new_conversation:
            return self._create_new_thread(agent, conversation_title)

        # Try to get current session thread
        current_thread_id = self.session_manager.get_current_thread_id(agent_type)
        if current_thread_id:
            thread = await self.conversation_service.load_thread(current_thread_id)
            if thread:
                return thread

        # No existing thread found, create new one
        return self._create_new_thread(agent, conversation_title)

    def _create_new_thread(self, agent: IAgent, title: str | None = None) -> ConversationThread:
        """Create a new conversation thread."""
        thread = agent.get_new_thread()
        if title:
            thread.title = title
        return thread

    async def start_new_conversation(self, agent: IAgent, title: str | None = None) -> ConversationThread:
        """
        Start a new conversation, clearing any current session.

        Args:
            agent: The agent for the conversation
            title: Optional title for the conversation

        Returns:
            New ConversationThread
        """
        agent_type = (
            agent.config.agent_type.value if hasattr(agent.config.agent_type, "value") else str(agent.config.agent_type)
        )

        # Clear current session for this agent type
        self.session_manager.clear_current_thread(agent_type)

        # Create new thread
        thread = self._create_new_thread(agent, title)

        # Save it
        await self.conversation_service.save_thread(thread)

        # Set as current
        self.session_manager.set_current_thread_id(agent_type, thread.thread_id)

        return thread

    async def continue_conversation(
        self, agent: IAgent, thread_id: str, message: str
    ) -> tuple[AgentResponse, ConversationThread]:
        """
        Continue a specific conversation.

        Args:
            agent: The agent to chat with
            thread_id: ID of the thread to continue
            message: Message to send

        Returns:
            Tuple of (agent_response, conversation_thread)
        """
        return await self.chat(agent=agent, message=message, thread_id=thread_id, auto_save=True)

    def get_current_session_info(self) -> dict:
        """Get information about current conversation sessions."""
        return self.session_manager.get_session_info()

    async def get_recent_conversations(self, agent_type: str | None = None, limit: int = 5):
        """Get recent conversation summaries."""
        return await self.conversation_service.list_threads(agent_type=agent_type, limit=limit)
