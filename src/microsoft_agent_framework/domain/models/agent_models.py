"""Domain models for agents and related entities."""

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentType(Enum):
    """Types of agents in the system."""

    SUPERVISOR = "supervisor"
    RESEARCH = "research"
    WRITER = "writer"


class MessageRole(Enum):
    """Message roles in conversations."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class AgentStatus(Enum):
    """Agent execution status."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass(frozen=True)
class Message:
    """Immutable message value object."""

    role: MessageRole
    content: str
    timestamp: datetime = None
    metadata: dict[str, Any] | None = None

    def __post_init__(self):
        if self.timestamp is None:
            object.__setattr__(self, "timestamp", datetime.now(UTC))
        if self.metadata is None:
            object.__setattr__(self, "metadata", {})


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    model_config = ConfigDict(use_enum_values=True)

    name: str
    agent_type: AgentType
    instructions: str
    max_tokens: int | None = 4000
    temperature: float | None = 0.7
    tools: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AgentResponse(BaseModel):
    """Response from an agent execution."""

    model_config = ConfigDict(use_enum_values=True)

    agent_name: str
    status: AgentStatus
    messages: list[Message]
    execution_time: float
    token_usage: dict[str, int] | None = None
    error: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationContext(BaseModel):
    """Context for a conversation."""

    conversation_id: str
    messages: list[Message] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
