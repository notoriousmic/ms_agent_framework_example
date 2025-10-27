"""FastAPI application using the new OOP architecture and service layer."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from microsoft_agent_framework.application.agents.supervisor_agent import (
    create_supervisor_agent,
)
from microsoft_agent_framework.application.services import (
    AgentService,
    ConversationManager,
    ConversationService,
    ConversationSession,
)
from microsoft_agent_framework.config import settings
from microsoft_agent_framework.domain.exceptions import (
    AgentExecutionError,
    AgentFrameworkError,
    AgentNotFoundError,
    AgentTimeoutError,
    AuthenticationError,
    AuthorizationError,
    ConnectionError,
    RateLimitError,
    ResourceExhaustedError,
    TimeoutError,
    ValidationError,
)
from microsoft_agent_framework.infrastructure.repositories import (
    FileConversationRepository,
)

from .models import (
    ChatRequest,
    CreateThreadRequest,
    EvalRequest,
    IngestDocumentsRequest,
    ResetMemoryRequest,
    SessionRequest,
    SessionResponse,
    SmartChatRequest,
    ThreadChatRequest,
)

# Global service instances
_agent_service: AgentService = None
_conversation_service: ConversationService = None
_conversation_manager: ConversationManager = None
_conversation_session: ConversationSession = None


async def get_agent_service() -> AgentService:
    """Dependency injection for agent service."""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
        await _agent_service.initialize()

        # Register supervisor agent
        supervisor = create_supervisor_agent()
        await supervisor.initialize()
        _agent_service.register_agent("supervisor", supervisor)

    return _agent_service


async def get_conversation_service() -> ConversationService:
    """Dependency injection for conversation service."""
    global _conversation_service
    if _conversation_service is None:
        repository = FileConversationRepository("conversations")
        _conversation_service = ConversationService(repository)
        await _conversation_service.initialize()

    return _conversation_service


async def get_conversation_manager() -> ConversationManager:
    """Dependency injection for conversation manager."""
    global _conversation_manager
    if _conversation_manager is None:
        conversation_service = await get_conversation_service()
        conversation_session = await get_conversation_session()
        _conversation_manager = ConversationManager(conversation_service, conversation_session)

    return _conversation_manager


async def get_conversation_session() -> ConversationSession:
    """Dependency injection for conversation session."""
    global _conversation_session
    if _conversation_session is None:
        _conversation_session = ConversationSession()

    return _conversation_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles startup and shutdown events for the API."""
    # Startup: Initialize services
    try:
        service = await get_agent_service()
        app.state.agent_service = service
        print(f"✅ Agent API started successfully on {settings.app.api_host}:{settings.app.api_port}")
        print(f"🌍 Environment: {settings.app.environment.value}")
        print(f"📚 Documentation: http://{settings.app.api_host}:{settings.app.api_port}/docs")
    except Exception as e:
        print(f"❌ Failed to start Agent API: {e}")
        raise

    yield

    # Shutdown: Cleanup services
    if hasattr(app.state, "agent_service"):
        await app.state.agent_service.cleanup()
    if hasattr(app.state, "conversation_service"):
        await app.state.conversation_service.cleanup()
    print("🔄 Agent API shutdown complete")


app = FastAPI(
    title="Microsoft Agent Framework API",
    description="Multi-agent AI orchestration with supervisor-worker pattern",
    version="0.1.0",
    docs_url="/docs",
    lifespan=lifespan,
)


@app.exception_handler(AgentNotFoundError)
async def agent_not_found_exception_handler(request: Request, exc: AgentNotFoundError):
    """Handle agent not found exceptions."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Agent Not Found",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(AgentTimeoutError)
async def agent_timeout_exception_handler(request: Request, exc: AgentTimeoutError):
    """Handle agent timeout exceptions."""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(int(exc.retry_after))

    return JSONResponse(
        status_code=504,  # Gateway Timeout
        headers=headers,
        content={
            "error": "Agent Timeout",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(RateLimitError)
async def rate_limit_exception_handler(request: Request, exc: RateLimitError):
    """Handle rate limit exceptions."""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(int(exc.retry_after))
    headers["X-RateLimit-Limit"] = "1000"  # Example limit
    headers["X-RateLimit-Remaining"] = "0"

    return JSONResponse(
        status_code=429,  # Too Many Requests
        headers=headers,
        content={
            "error": "Rate Limit Exceeded",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "retry_after": exc.retry_after,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request: Request, exc: AuthenticationError):
    """Handle authentication exceptions."""
    return JSONResponse(
        status_code=401,  # Unauthorized
        content={
            "error": "Authentication Error",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(AuthorizationError)
async def authorization_exception_handler(request: Request, exc: AuthorizationError):
    """Handle authorization exceptions."""
    return JSONResponse(
        status_code=403,  # Forbidden
        content={
            "error": "Authorization Error",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handle validation exceptions."""
    return JSONResponse(
        status_code=400,  # Bad Request
        content={
            "error": "Validation Error",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(ResourceExhaustedError)
async def resource_exhausted_exception_handler(request: Request, exc: ResourceExhaustedError):
    """Handle resource exhausted exceptions."""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(int(exc.retry_after))

    return JSONResponse(
        status_code=503,  # Service Unavailable
        headers=headers,
        content={
            "error": "Resource Exhausted",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "retry_after": exc.retry_after,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(ConnectionError)
async def connection_exception_handler(request: Request, exc: ConnectionError):
    """Handle connection exceptions."""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(int(exc.retry_after))

    return JSONResponse(
        status_code=502,  # Bad Gateway
        headers=headers,
        content={
            "error": "Connection Error",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(TimeoutError)
async def timeout_exception_handler(request: Request, exc: TimeoutError):
    """Handle timeout exceptions."""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(int(exc.retry_after))

    return JSONResponse(
        status_code=504,  # Gateway Timeout
        headers=headers,
        content={
            "error": "Timeout Error",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(AgentExecutionError)
async def agent_execution_exception_handler(request: Request, exc: AgentExecutionError):
    """Handle agent execution exceptions."""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(int(exc.retry_after))

    return JSONResponse(
        status_code=500,  # Internal Server Error
        headers=headers,
        content={
            "error": "Agent Execution Error",
            "message": exc.message,
            "agent_name": exc.agent_name,
            "execution_time": exc.execution_time,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "timestamp": exc.timestamp,
        },
    )


@app.exception_handler(AgentFrameworkError)
async def agent_framework_exception_handler(request: Request, exc: AgentFrameworkError):
    """Handle custom agent framework exceptions."""
    headers = {}
    if exc.retry_after:
        headers["Retry-After"] = str(int(exc.retry_after))

    return JSONResponse(
        status_code=500,  # Internal Server Error
        headers=headers,
        content={
            "error": "Agent Framework Error",
            "message": exc.message,
            "error_code": exc.error_code,
            "details": exc.details,
            "is_retryable": exc.is_retryable,
            "timestamp": exc.timestamp,
        },
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Welcome to Microsoft Agent Framework API",
        "version": "0.1.0",
        "environment": settings.app.environment.value,
        "documentation": "/docs",
        "health": "/health",
    }


@app.get("/health")
async def health_check(agent_service: AgentService = Depends(get_agent_service)):  # noqa: B008
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service_initialized": agent_service.is_initialized,
        "registered_agents": agent_service.get_all_agents(),
        "environment": settings.app.environment.value,
    }


@app.get("/readiness")
# Put readiness logic here
async def readiness_check(agent_service: AgentService = Depends(get_agent_service)):  # noqa: B008
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "service_initialized": agent_service.is_initialized,
        "registered_agents": agent_service.get_all_agents(),
        "environment": settings.app.environment.value,
    }


@app.post("/chat")
async def chat(request: ChatRequest, agent_service: AgentService = Depends(get_agent_service)) -> dict[str, Any]:  # noqa: B008
    """
    Chat with the supervisor agent.

    The supervisor agent coordinates research and writing tasks by delegating
    to specialized sub-agents as needed.
    """
    try:
        response = await agent_service.execute_agent("supervisor", request.message, timeout=settings.app.agent_timeout)

        # Convert to the expected format for backward compatibility
        return {
            "response": {
                "agent_name": response.agent_name,
                "status": (response.status if isinstance(response.status, str) else response.status.value),
                "messages": [
                    {
                        "role": (msg.role if isinstance(msg.role, str) else msg.role.value),
                        "contents": [{"text": msg.content}],
                        "author_name": response.agent_name,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                    for msg in response.messages
                ],
                "execution_time": response.execution_time,
                "token_usage": response.token_usage,
                "metadata": response.metadata,
            }
        }

    except AgentFrameworkError:
        # Let our custom exception handlers deal with it
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during chat: {str(e)}") from e


@app.post("/chat/smart")
async def smart_chat(
    request: SmartChatRequest,
    conversation_manager: ConversationManager = Depends(get_conversation_manager),  # noqa: B008
) -> dict[str, Any]:
    """
    Smart chat with automatic thread management.

    This endpoint provides the same seamless experience as the CLI:
    - Automatically continues existing conversations
    - Creates new threads when needed
    - Manages session state transparently
    """
    try:
        response, thread_id = await conversation_manager.smart_chat(
            message=request.message,
            agent_type=request.agent_type,
            force_new=request.force_new,
            title=request.title,
        )

        return {
            "response": {
                "agent_name": response.agent_name,
                "status": (response.status if isinstance(response.status, str) else response.status.value),
                "messages": [
                    {
                        "role": (msg.role if isinstance(msg.role, str) else msg.role.value),
                        "contents": [{"text": msg.content}],
                        "author_name": response.agent_name,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                    for msg in response.messages
                ],
                "execution_time": response.execution_time,
                "token_usage": response.token_usage,
                "metadata": response.metadata,
            },
            "thread_id": thread_id,
            "is_new_conversation": request.force_new or not thread_id,
            "conversation_saved": request.save_conversation,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during smart chat: {str(e)}") from e


@app.post("/eval")
async def eval(request: EvalRequest):
    """
    Evaluation endpoint (placeholder for future implementation).
    """
    return {
        "message": "Evaluation request received",
        "query": request.query,
        "status": "placeholder",
    }


@app.post("/ingest-documents")
async def ingest_documents(request: IngestDocumentsRequest):
    """
    Document ingestion endpoint (placeholder for future implementation).
    """
    return {
        "message": "Document ingestion request received",
        "document_count": len(request.documents) if request.documents else 0,
        "status": "placeholder",
    }


@app.post("/reset-memory")
async def reset_memory(request: ResetMemoryRequest):
    """
    Reset agent memory endpoint (placeholder for future implementation).
    """
    if not request.confirm:
        raise HTTPException(status_code=400, detail="Memory reset requires confirmation")

    return {
        "message": "Memory reset request received",
        "confirmed": request.confirm,
        "status": "placeholder",
    }


@app.get("/agents")
async def list_agents(agent_service: AgentService = Depends(get_agent_service)):  # noqa: B008
    """List all registered agents."""
    return {
        "agents": agent_service.get_all_agents(),
        "total": len(agent_service.get_all_agents()),
    }


@app.post("/chat/thread")
async def chat_with_thread(
    request: ThreadChatRequest,
    agent_service: AgentService = Depends(get_agent_service),  # noqa: B008
    conversation_service: ConversationService = Depends(get_conversation_service),  # noqa: B008
) -> dict[str, Any]:
    """
    Chat with an agent using a conversation thread.

    Creates a new thread if none exists and optionally saves the conversation.
    """
    try:
        from microsoft_agent_framework.application.factories import agent_factory
        from microsoft_agent_framework.domain.models import AgentConfig, AgentType

        # Create agent
        config = AgentConfig(
            name=f"{request.agent_type}_agent",
            agent_type=AgentType(request.agent_type),
            instructions="",
        )
        agent = agent_factory.create_agent(request.agent_type, config)

        # Create new thread
        thread = agent.get_new_thread()

        # Execute agent with thread
        response = await agent.run(request.message, thread=thread)

        # Save thread if requested
        if request.save_thread:
            await conversation_service.save_thread(thread)

        # Convert to response format
        return {
            "response": {
                "agent_name": response.agent_name,
                "status": (response.status if isinstance(response.status, str) else response.status.value),
                "messages": [
                    {
                        "role": (msg.role if isinstance(msg.role, str) else msg.role.value),
                        "contents": [{"text": msg.content}],
                        "author_name": response.agent_name,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                    for msg in response.messages
                ],
                "execution_time": response.execution_time,
                "token_usage": response.token_usage,
                "metadata": response.metadata,
            },
            "thread_id": thread.thread_id,
            "thread_saved": request.save_thread,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error during chat: {str(e)}") from e


@app.post("/threads")
async def create_thread(
    request: CreateThreadRequest,
    conversation_service: ConversationService = Depends(get_conversation_service),  # noqa: B008
):
    """Create a new conversation thread."""
    try:
        thread = await conversation_service.create_thread(
            agent_name=request.agent_name,
            agent_type=request.agent_type,
            title=request.title,
        )

        return {
            "thread_id": thread.thread_id,
            "agent_name": thread.agent_name,
            "agent_type": thread.agent_type,
            "title": thread.title,
            "created_at": thread.created_at.isoformat(),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create thread: {str(e)}") from e


@app.get("/threads")
async def list_threads(
    agent_name: str | None = None,
    agent_type: str | None = None,
    limit: int = 10,
    offset: int = 0,
    conversation_service: ConversationService = Depends(get_conversation_service),  # noqa: B008
):
    """List conversation threads."""
    try:
        summaries = await conversation_service.list_threads(
            agent_name=agent_name, agent_type=agent_type, limit=limit, offset=offset
        )

        return {
            "threads": [
                {
                    "thread_id": s.thread_id,
                    "agent_name": s.agent_name,
                    "agent_type": s.agent_type,
                    "title": s.title,
                    "message_count": s.message_count,
                    "created_at": s.created_at.isoformat(),
                    "updated_at": s.updated_at.isoformat(),
                    "tags": s.tags,
                    "last_message_preview": s.last_message_preview,
                }
                for s in summaries
            ],
            "total": len(summaries),
            "limit": limit,
            "offset": offset,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list threads: {str(e)}") from e


@app.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),  # noqa: B008
):
    """Get a specific conversation thread."""
    try:
        thread = await conversation_service.load_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        return {
            "thread_id": thread.thread_id,
            "agent_name": thread.agent_name,
            "agent_type": thread.agent_type,
            "title": thread.title,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
            "tags": thread.tags,
            "metadata": thread.metadata,
            "messages": [
                {
                    "role": msg.role if isinstance(msg.role, str) else msg.role.value,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "metadata": msg.metadata or {},
                }
                for msg in thread.messages
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get thread: {str(e)}") from e


@app.post("/threads/{thread_id}/chat")
async def continue_thread_chat(
    thread_id: str,
    request: ChatRequest,
    agent_service: AgentService = Depends(get_agent_service),  # noqa: B008
    conversation_service: ConversationService = Depends(get_conversation_service),  # noqa: B008
):
    """Continue a conversation in an existing thread."""
    try:
        # Load thread
        thread = await conversation_service.load_thread(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")

        # Get agent
        agent = agent_service.get_agent("supervisor")
        if not agent:
            raise HTTPException(status_code=500, detail="Agent not available")

        # Execute agent with thread
        response = await agent.run(request.message, thread=thread)

        # Save updated thread
        await conversation_service.save_thread(thread)

        return {
            "response": {
                "agent_name": response.agent_name,
                "status": (response.status if isinstance(response.status, str) else response.status.value),
                "messages": [
                    {
                        "role": (msg.role if isinstance(msg.role, str) else msg.role.value),
                        "contents": [{"text": msg.content}],
                        "author_name": response.agent_name,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                    for msg in response.messages
                ],
                "execution_time": response.execution_time,
                "token_usage": response.token_usage,
                "metadata": response.metadata,
            },
            "thread_id": thread.thread_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to continue thread chat: {str(e)}") from e


@app.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: str,
    conversation_service: ConversationService = Depends(get_conversation_service),  # noqa: B008
):
    """Delete a conversation thread."""
    try:
        success = await conversation_service.delete_thread(thread_id)
        if not success:
            raise HTTPException(status_code=404, detail="Thread not found")

        return {"message": "Thread deleted successfully", "thread_id": thread_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete thread: {str(e)}") from e


@app.get("/session")
async def get_session(
    conversation_session: ConversationSession = Depends(get_conversation_session),  # noqa: B008
) -> SessionResponse:
    """Get current session information."""
    try:
        session_info = conversation_session.get_session_info()
        threads = session_info.get("threads", {})
        active_count = len([t for t in threads.values() if t])

        return SessionResponse(sessions=threads, active_threads=active_count)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get session info: {str(e)}") from e


@app.post("/session/clear")
async def clear_session(
    request: SessionRequest,
    conversation_session: ConversationSession = Depends(get_conversation_session),  # noqa: B008
):
    """Clear current session (optionally for specific agent type)."""
    try:
        if request.agent_type:
            conversation_session.clear_current_thread(request.agent_type)
            return {"message": f"Session cleared for {request.agent_type}"}
        else:
            conversation_session.clear_all_sessions()
            return {"message": "All sessions cleared"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear session: {str(e)}") from e


@app.post("/conversation/new")
async def start_new_conversation(
    request: SmartChatRequest,
    conversation_manager: ConversationManager = Depends(get_conversation_manager),  # noqa: B008
):
    """Start a new conversation, clearing the current session for this agent type."""
    try:
        response, thread_id = await conversation_manager.start_new_conversation(
            agent_type=request.agent_type, message=request.message, title=request.title
        )

        return {
            "response": {
                "agent_name": response.agent_name,
                "status": (response.status if isinstance(response.status, str) else response.status.value),
                "messages": [
                    {
                        "role": (msg.role if isinstance(msg.role, str) else msg.role.value),
                        "contents": [{"text": msg.content}],
                        "author_name": response.agent_name,
                        "timestamp": msg.timestamp.isoformat(),
                    }
                    for msg in response.messages
                ],
                "execution_time": response.execution_time,
                "token_usage": response.token_usage,
                "metadata": response.metadata,
            },
            "thread_id": thread_id,
            "is_new_conversation": True,
            "previous_session_cleared": True,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start new conversation: {str(e)}") from e


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.app.api_host, port=settings.app.api_port)
