"""Service for managing conversation threads."""

from microsoft_agent_framework.domain.interfaces import (
    IConversationRepository,
    IService,
)
from microsoft_agent_framework.domain.models import (
    ConversationSummary,
    ConversationThread,
)


class ConversationService(IService):
    """Service for managing conversation threads."""

    def __init__(self, repository: IConversationRepository):
        self._repository = repository
        self._is_initialized = False

    @property
    def is_initialized(self) -> bool:
        """Check if service is initialized."""
        return self._is_initialized

    async def initialize(self) -> None:
        """Initialize the service."""
        self._is_initialized = True

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        self._is_initialized = False

    async def create_thread(self, agent_name: str, agent_type: str, title: str | None = None) -> ConversationThread:
        """Create a new conversation thread."""
        thread = ConversationThread(agent_name=agent_name, agent_type=agent_type, title=title)
        await self._repository.save_thread(thread)
        return thread

    async def save_thread(self, thread: ConversationThread) -> None:
        """Save a conversation thread."""
        await self._repository.save_thread(thread)

    async def load_thread(self, thread_id: str) -> ConversationThread | None:
        """Load a conversation thread by ID."""
        return await self._repository.load_thread(thread_id)

    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a conversation thread."""
        return await self._repository.delete_thread(thread_id)

    async def list_threads(
        self,
        agent_name: str | None = None,
        agent_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ConversationSummary]:
        """List conversation threads with optional filtering."""
        return await self._repository.list_threads(
            agent_name=agent_name, agent_type=agent_type, limit=limit, offset=offset
        )

    async def search_threads(
        self,
        query: str,
        agent_name: str | None = None,
        agent_type: str | None = None,
        limit: int | None = None,
    ) -> list[ConversationSummary]:
        """Search conversation threads by content."""
        return await self._repository.search_threads(
            query=query, agent_name=agent_name, agent_type=agent_type, limit=limit
        )

    async def cleanup_old_threads(self, days_old: int = 30) -> int:
        """Clean up threads older than specified days."""
        return await self._repository.cleanup_old_threads(days_old)

    async def get_thread_summary(self, thread_id: str) -> ConversationSummary | None:
        """Get a summary of a specific thread."""
        thread = await self.load_thread(thread_id)
        if not thread:
            return None

        last_message = thread.messages[-1] if thread.messages else None

        return ConversationSummary(
            thread_id=thread.thread_id,
            agent_name=thread.agent_name,
            agent_type=thread.agent_type,
            title=thread.title,
            message_count=len(thread.messages),
            created_at=thread.created_at,
            updated_at=thread.updated_at,
            tags=thread.tags,
            last_message_preview=last_message.content[:100] if last_message else None,
        )
