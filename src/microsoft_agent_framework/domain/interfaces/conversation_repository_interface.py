"""Repository interface for conversation persistence."""

from abc import ABC, abstractmethod

from microsoft_agent_framework.domain.models.conversation_models import (
    ConversationSummary,
    ConversationThread,
)


class IConversationRepository(ABC):
    """Interface for conversation persistence operations."""

    @abstractmethod
    async def save_thread(self, thread: ConversationThread) -> None:
        """Save a conversation thread."""
        pass

    @abstractmethod
    async def load_thread(self, thread_id: str) -> ConversationThread | None:
        """Load a conversation thread by ID."""
        pass

    @abstractmethod
    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a conversation thread."""
        pass

    @abstractmethod
    async def list_threads(
        self,
        agent_name: str | None = None,
        agent_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ConversationSummary]:
        """List conversation threads with optional filtering."""
        pass

    @abstractmethod
    async def search_threads(
        self,
        query: str,
        agent_name: str | None = None,
        agent_type: str | None = None,
        limit: int | None = None,
    ) -> list[ConversationSummary]:
        """Search conversation threads by content."""
        pass

    @abstractmethod
    async def cleanup_old_threads(self, days_old: int = 30) -> int:
        """Clean up threads older than specified days."""
        pass
