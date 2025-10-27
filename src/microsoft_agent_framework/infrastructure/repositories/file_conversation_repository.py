"""File-based implementation of conversation repository."""

import json
from datetime import datetime, timedelta
from pathlib import Path

from microsoft_agent_framework.domain.interfaces.conversation_repository_interface import (
    IConversationRepository,
)
from microsoft_agent_framework.domain.models.conversation_models import (
    ConversationSummary,
    ConversationThread,
)


class FileConversationRepository(IConversationRepository):
    """File-based conversation repository implementation."""

    def __init__(self, storage_dir: str = "conversations"):
        """Initialize with storage directory."""
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)

    def _get_thread_path(self, thread_id: str) -> Path:
        """Get the file path for a thread."""
        return self.storage_dir / f"{thread_id}.json"

    async def save_thread(self, thread: ConversationThread) -> None:
        """Save a conversation thread to file."""
        thread_path = self._get_thread_path(thread.thread_id)
        serialized_data = thread.serialize()

        with open(thread_path, "w", encoding="utf-8") as f:
            json.dump(serialized_data, f, indent=2, ensure_ascii=False)

    async def load_thread(self, thread_id: str) -> ConversationThread | None:
        """Load a conversation thread from file."""
        thread_path = self._get_thread_path(thread_id)

        if not thread_path.exists():
            return None

        try:
            with open(thread_path, encoding="utf-8") as f:
                data = json.load(f)

            return ConversationThread.deserialize(data)
        except (json.JSONDecodeError, KeyError, ValueError):
            # Handle corrupted files
            return None

    async def delete_thread(self, thread_id: str) -> bool:
        """Delete a conversation thread file."""
        thread_path = self._get_thread_path(thread_id)

        if thread_path.exists():
            try:
                thread_path.unlink()
                return True
            except OSError:
                return False

        return False

    async def list_threads(
        self,
        agent_name: str | None = None,
        agent_type: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[ConversationSummary]:
        """List conversation threads with optional filtering."""
        summaries = []

        # Get all JSON files in the storage directory
        json_files = list(self.storage_dir.glob("*.json"))

        # Sort by modification time (newest first)
        json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

        for file_path in json_files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                # Apply filters
                if agent_name and data.get("agent_name") != agent_name:
                    continue
                if agent_type and data.get("agent_type") != agent_type:
                    continue

                # Create summary
                messages = data.get("messages", [])
                last_message = messages[-1] if messages else None

                summary = ConversationSummary(
                    thread_id=data["thread_id"],
                    agent_name=data["agent_name"],
                    agent_type=data["agent_type"],
                    title=data.get("title"),
                    message_count=len(messages),
                    created_at=datetime.fromisoformat(data["created_at"]),
                    updated_at=datetime.fromisoformat(data["updated_at"]),
                    tags=data.get("tags", []),
                    last_message_preview=(last_message["content"][:100] if last_message else None),
                )

                summaries.append(summary)

            except (json.JSONDecodeError, KeyError, ValueError):
                # Skip corrupted files
                continue

        # Apply pagination
        if offset > 0:
            summaries = summaries[offset:]
        if limit:
            summaries = summaries[:limit]

        return summaries

    async def search_threads(
        self,
        query: str,
        agent_name: str | None = None,
        agent_type: str | None = None,
        limit: int | None = None,
    ) -> list[ConversationSummary]:
        """Search conversation threads by content."""
        query_lower = query.lower()
        matching_summaries = []

        # Get all threads first
        all_summaries = await self.list_threads(agent_name=agent_name, agent_type=agent_type)

        for summary in all_summaries:
            # Load the full thread to search message content
            thread = await self.load_thread(summary.thread_id)
            if not thread:
                continue

            # Search in title, messages, and tags
            found = False

            # Check title
            if thread.title and query_lower in thread.title.lower():
                found = True

            # Check tags
            for tag in thread.tags:
                if query_lower in tag.lower():
                    found = True
                    break

            # Check message content
            if not found:
                for message in thread.messages:
                    if query_lower in message.content.lower():
                        found = True
                        break

            if found:
                matching_summaries.append(summary)

        # Apply limit
        if limit:
            matching_summaries = matching_summaries[:limit]

        return matching_summaries

    async def cleanup_old_threads(self, days_old: int = 30) -> int:
        """Clean up threads older than specified days."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        deleted_count = 0

        json_files = list(self.storage_dir.glob("*.json"))

        for file_path in json_files:
            try:
                # Check file modification time
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)

                if file_mtime < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1

            except OSError:
                # Skip files that can't be accessed
                continue

        return deleted_count
