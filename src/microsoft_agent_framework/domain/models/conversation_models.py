"""Models for conversation persistence and thread management."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from .agent_models import Message


@dataclass(frozen=True)
class ThreadMetadata:
    """Metadata for conversation threads."""

    thread_id: str
    agent_name: str
    agent_type: str
    created_at: datetime
    updated_at: datetime
    title: str | None = None
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class ConversationThread(BaseModel):
    """Represents a conversation thread that can be persisted and resumed."""

    thread_id: str = Field(default_factory=lambda: str(uuid4()))
    agent_name: str
    agent_type: str
    messages: list[Message] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    title: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def add_message(self, message: Message) -> None:
        """Add a single message to the thread."""
        self.messages.append(message)
        self.updated_at = datetime.now(UTC)

    def add_messages(self, messages: list[Message]) -> None:
        """Add multiple messages to the thread."""
        self.messages.extend(messages)
        self.updated_at = datetime.now(UTC)

    def get_messages(self, limit: int | None = None) -> list[Message]:
        """Get messages from the thread."""
        if limit is None:
            return self.messages.copy()
        return self.messages[-limit:] if limit > 0 else []

    def clear_messages(self) -> None:
        """Clear all messages from the thread."""
        self.messages.clear()
        self.updated_at = datetime.now(UTC)

    def serialize(self) -> dict[str, Any]:
        """Serialize the thread to a dictionary for persistence."""
        return {
            "thread_id": self.thread_id,
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "messages": [
                {
                    "role": msg.role if isinstance(msg.role, str) else msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata or {},
                }
                for msg in self.messages
            ],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "title": self.title,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> "ConversationThread":
        """Deserialize a thread from a dictionary."""
        from .agent_models import MessageRole  # Import here to avoid circular imports

        messages = []
        for msg_data in data.get("messages", []):
            messages.append(
                Message(
                    role=MessageRole(msg_data["role"]),
                    content=msg_data["content"],
                    timestamp=datetime.fromisoformat(msg_data["timestamp"]),
                    metadata=msg_data.get("metadata", {}),
                )
            )

        return cls(
            thread_id=data["thread_id"],
            agent_name=data["agent_name"],
            agent_type=data["agent_type"],
            messages=messages,
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            title=data.get("title"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    model_config = ConfigDict(use_enum_values=True)


class ConversationSummary(BaseModel):
    """Summary of a conversation thread."""

    thread_id: str
    agent_name: str
    agent_type: str
    title: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(default_factory=list)
    last_message_preview: str | None = None

    model_config = ConfigDict(use_enum_values=True)
