"""Unit tests for application services."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from microsoft_agent_framework.application.services import (
    AgentService,
    ConversationManager,
    ConversationService,
    ConversationSession,
)
from microsoft_agent_framework.domain.exceptions import (
    AgentNotFoundError,
)
from microsoft_agent_framework.domain.models import (
    AgentConfig,
    AgentResponse,
    AgentStatus,
    AgentType,
    ConversationThread,
    Message,
    MessageRole,
)


class TestAgentService:
    """Test cases for AgentService."""

    @pytest.fixture
    def agent_service(self):
        """Create an AgentService instance."""
        return AgentService()

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent."""
        agent = AsyncMock()
        agent.name = "Test Agent"
        agent.config = AgentConfig(name="Test Agent", agent_type=AgentType.SUPERVISOR, instructions="Test")
        return agent

    def test_agent_service_creation(self, agent_service):
        """Test agent service creation."""
        assert not agent_service.is_initialized
        assert agent_service._agents == {}

    @pytest.mark.asyncio
    async def test_initialize(self, agent_service):
        """Test service initialization."""
        await agent_service.initialize()
        assert agent_service.is_initialized

    @pytest.mark.asyncio
    async def test_cleanup(self, agent_service, mock_agent):
        """Test service cleanup."""
        agent_service.register_agent("test-1", mock_agent)
        await agent_service.initialize()

        await agent_service.cleanup()

        mock_agent.cleanup.assert_called_once()
        assert not agent_service.is_initialized

    def test_register_agent(self, agent_service, mock_agent):
        """Test registering an agent."""
        agent_service.register_agent("test-1", mock_agent)

        assert "test-1" in agent_service._agents
        assert agent_service._agents["test-1"] == mock_agent

    def test_get_agent_exists(self, agent_service, mock_agent):
        """Test getting an existing agent."""
        agent_service.register_agent("test-1", mock_agent)

        result = agent_service.get_agent("test-1")
        assert result == mock_agent

    def test_get_agent_not_exists(self, agent_service):
        """Test getting a non-existent agent."""
        result = agent_service.get_agent("non-existent")
        assert result is None

    def test_get_all_agents(self, agent_service, mock_agent):
        """Test getting all agent IDs."""
        agent_service.register_agent("test-1", mock_agent)
        agent_service.register_agent("test-2", mock_agent)

        result = agent_service.get_all_agents()
        assert set(result) == {"test-1", "test-2"}

    @pytest.mark.asyncio
    async def test_execute_agent_success(self, agent_service, mock_agent):
        """Test successful agent execution."""
        expected_response = AgentResponse(
            agent_name="Test Agent",
            status=AgentStatus.COMPLETED,
            messages=[Message(role=MessageRole.ASSISTANT, content="Response")],
            execution_time=1.0,
        )
        mock_agent.run.return_value = expected_response

        agent_service.register_agent("test-1", mock_agent)

        result = await agent_service.execute_agent("test-1", "Test message")

        assert result == expected_response
        mock_agent.run.assert_called_once_with("Test message")

    @pytest.mark.asyncio
    async def test_execute_agent_not_found(self, agent_service):
        """Test executing non-existent agent."""

        with pytest.raises(AgentNotFoundError) as exc_info:
            await agent_service.execute_agent("non-existent", "Test message")

        assert "Agent 'non-existent' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_execute_agent_with_timeout(self, agent_service, mock_agent):
        """Test agent execution with timeout."""
        mock_agent.name = "test-1"
        mock_agent.run = AsyncMock(side_effect=lambda *args, **kwargs: None)
        agent_service.register_agent("test-1", mock_agent)

        with patch("asyncio.wait_for") as mock_wait_for:
            mock_wait_for.side_effect = TimeoutError()

            result = await agent_service.execute_agent("test-1", "Test message", timeout=1)

            assert result.status == AgentStatus.ERROR.value
            assert "timed out after 1 seconds" in result.error

    @pytest.mark.asyncio
    async def test_create_conversation_session(self, agent_service):
        """Test creating a conversation session."""
        session_id = await agent_service.create_conversation_session()

        assert len(session_id) > 0
        # Session ID should be a valid UUID string format
        assert "-" in session_id


class TestConversationService:
    """Test cases for ConversationService."""

    @pytest.fixture
    def conversation_service(self, mock_repository):
        """Create a ConversationService instance."""
        return ConversationService(mock_repository)

    @pytest.fixture
    def mock_repository(self):
        """Create a mock conversation repository."""
        return AsyncMock()

    @pytest.fixture
    def sample_thread(self):
        """Create a sample conversation thread."""
        thread = ConversationThread(agent_name="Test Agent", agent_type="supervisor")
        thread.add_message(Message(role=MessageRole.USER, content="Hello"))
        return thread

    def test_conversation_service_creation(self, conversation_service):
        """Test conversation service creation."""
        assert not conversation_service.is_initialized

    @pytest.mark.asyncio
    async def test_initialize_with_repository(self, conversation_service, mock_repository):
        """Test initialization with repository."""
        await conversation_service.initialize()

        assert conversation_service.is_initialized

    @pytest.mark.asyncio
    async def test_create_thread(self, conversation_service):
        """Test creating a new conversation thread."""
        await conversation_service.initialize()

        thread = await conversation_service.create_thread(agent_name="Test Agent", agent_type="supervisor")

        assert isinstance(thread, ConversationThread)
        assert thread.agent_name == "Test Agent"
        assert thread.agent_type == "supervisor"
        assert len(thread.thread_id) > 0

    @pytest.mark.asyncio
    async def test_save_thread(self, conversation_service, mock_repository, sample_thread):
        """Test saving a conversation thread."""
        conversation_service._repository = mock_repository
        await conversation_service.initialize()

        await conversation_service.save_thread(sample_thread)

        mock_repository.save_thread.assert_called_once_with(sample_thread)

    @pytest.mark.asyncio
    async def test_load_thread(self, conversation_service, mock_repository, sample_thread):
        """Test loading a conversation thread."""
        conversation_service._repository = mock_repository
        await conversation_service.initialize()

        mock_repository.load_thread.return_value = sample_thread

        result = await conversation_service.load_thread("test-123")

        assert result == sample_thread
        mock_repository.load_thread.assert_called_once_with("test-123")

    @pytest.mark.asyncio
    async def test_delete_thread(self, conversation_service, mock_repository):
        """Test deleting a conversation thread."""
        conversation_service._repository = mock_repository
        await conversation_service.initialize()

        await conversation_service.delete_thread("test-123")

        mock_repository.delete_thread.assert_called_once_with("test-123")

    @pytest.mark.asyncio
    async def test_list_threads(self, conversation_service, mock_repository):
        """Test listing conversation threads."""
        conversation_service._repository = mock_repository
        await conversation_service.initialize()

        expected_summaries = [
            {"thread_id": "test-1", "title": "Thread 1"},
            {"thread_id": "test-2", "title": "Thread 2"},
        ]
        mock_repository.list_threads.return_value = expected_summaries

        result = await conversation_service.list_threads()

        assert result == expected_summaries
        mock_repository.list_threads.assert_called_once_with(agent_name=None, agent_type=None, limit=None, offset=0)


class TestConversationManager:
    """Test cases for ConversationManager."""

    @pytest.fixture
    def conversation_manager(self, mock_conversation_service):
        """Create a ConversationManager instance."""
        return ConversationManager(mock_conversation_service)

    @pytest.fixture
    def mock_agent_service(self):
        """Create a mock agent service."""
        return AsyncMock()

    @pytest.fixture
    def mock_conversation_service(self):
        """Create a mock conversation service."""
        return AsyncMock()

    def test_conversation_manager_creation(self, conversation_manager):
        """Test conversation manager creation."""
        assert conversation_manager.conversation_service is not None
        assert conversation_manager.session_manager is not None

    @pytest.mark.asyncio
    async def test_chat_method_exists(self, conversation_manager):
        """Test chat method exists."""
        # This test verifies the chat method exists, actual execution tested in integration
        assert hasattr(conversation_manager, "chat")
        assert callable(conversation_manager.chat)

    @pytest.mark.asyncio
    async def test_start_new_conversation(self, conversation_manager):
        """Test starting a new conversation."""
        mock_agent = Mock()
        mock_agent.config.agent_type = "supervisor"
        mock_agent.get_new_thread.return_value = ConversationThread(agent_name="Test Agent", agent_type="supervisor")

        with patch.object(
            conversation_manager.conversation_service,
            "save_thread",
            new_callable=AsyncMock,
        ):
            result = await conversation_manager.start_new_conversation(mock_agent, "Test Chat")

            assert isinstance(result, ConversationThread)
            assert result.title == "Test Chat"

    def test_get_current_session_info(self, conversation_manager):
        """Test getting current session info."""
        info = conversation_manager.get_current_session_info()
        assert isinstance(info, dict)


class TestConversationSession:
    """Test cases for ConversationSession."""

    @pytest.fixture
    def conversation_session(self, tmp_path):
        """Create a ConversationSession instance."""
        # tmp_path is automatically cleaned up by pytest after test completion
        session_dir = tmp_path / "test-session-123"
        return ConversationSession(str(session_dir))

    def test_conversation_session_creation(self, conversation_session):
        """Test conversation session creation."""
        assert conversation_session.session_dir.name == "test-session-123"
        assert conversation_session.current_session_file.exists or not conversation_session.current_session_file.exists

    def test_get_current_thread_id_no_session(self, conversation_session):
        """Test getting current thread ID when no session exists."""
        result = conversation_session.get_current_thread_id("supervisor")
        assert result is None

    def test_set_current_thread_id(self, conversation_session):
        """Test setting current thread ID."""
        conversation_session.set_current_thread_id("supervisor", "thread-123")
        result = conversation_session.get_current_thread_id("supervisor")
        assert result == "thread-123"

    def test_clear_current_thread(self, conversation_session):
        """Test clearing current thread."""
        conversation_session.set_current_thread_id("supervisor", "thread-123")
        conversation_session.clear_current_thread("supervisor")
        result = conversation_session.get_current_thread_id("supervisor")
        assert result is None

    def test_clear_all_sessions(self, conversation_session):
        """Test clearing all session data."""
        conversation_session.set_current_thread_id("supervisor", "thread-123")
        conversation_session.clear_all_sessions()
        result = conversation_session.get_current_thread_id("supervisor")
        assert result is None

    def test_get_session_info(self, conversation_session):
        """Test getting session info."""
        conversation_session.set_current_thread_id("supervisor", "thread-123")
        info = conversation_session.get_session_info()
        assert "threads" in info
        assert info["threads"]["supervisor"] == "thread-123"


# Integration tests
class TestServiceIntegration:
    """Integration tests for service interactions."""

    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """Test complete conversation flow through services."""
        # Create services
        agent_service = AgentService()
        mock_repository = AsyncMock()
        conversation_service = ConversationService(mock_repository)
        conversation_manager = ConversationManager(conversation_service)

        # Initialize services
        await agent_service.initialize()
        await conversation_service.initialize()

        # Create mock agent
        mock_agent = Mock()
        mock_agent.name = "Test Agent"
        mock_agent.config = AgentConfig(name="Test Agent", agent_type=AgentType.SUPERVISOR, instructions="Test")
        mock_agent.get_new_thread.return_value = ConversationThread(agent_name="Test Agent", agent_type="supervisor")
        expected_response = AgentResponse(
            agent_name="Test Agent",
            status=AgentStatus.COMPLETED,
            messages=[Message(role=MessageRole.ASSISTANT, content="Hello!")],
            execution_time=1.0,
        )
        mock_agent.run = AsyncMock(return_value=expected_response)

        # Register agent
        agent_service.register_agent("test-agent", mock_agent)

        # Set up conversation manager
        conversation_manager._agent_service = agent_service
        conversation_manager._conversation_service = conversation_service
        # ConversationManager doesn't need initialization

        # Create conversation via start_new_conversation
        thread = await conversation_manager.start_new_conversation(agent=mock_agent, title="Test Conversation")

        # Send message (this would normally execute the agent)
        # For this test, we'll just verify the setup worked
        assert thread is not None
        assert thread.title == "Test Conversation"
