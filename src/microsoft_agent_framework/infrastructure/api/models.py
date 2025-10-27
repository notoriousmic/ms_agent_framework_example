from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ThreadChatRequest(BaseModel):
    message: str
    agent_type: str = "supervisor"
    save_thread: bool = True


class CreateThreadRequest(BaseModel):
    agent_name: str
    agent_type: str
    title: str | None = None


class EvalRequest(BaseModel):
    query: str | None = None


class IngestDocumentsRequest(BaseModel):
    documents: list[str] | None = None


class ResetMemoryRequest(BaseModel):
    confirm: bool = False


class SmartChatRequest(BaseModel):
    """Request for intelligent chat with automatic thread management."""

    message: str
    agent_type: str = "supervisor"
    force_new: bool = False
    title: str | None = None
    save_conversation: bool = True


class SessionRequest(BaseModel):
    """Request for session management operations."""

    agent_type: str | None = None


class SessionResponse(BaseModel):
    """Response containing session information."""

    sessions: dict
    active_threads: int
