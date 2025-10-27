"""Unit tests for domain models."""

from datetime import datetime

import pytest

from microsoft_agent_framework.domain.models import (
    AgentConfig,
    AgentResponse,
    AgentStatus,
    AgentType,
    ConversationContext,
    ConversationSummary,
    ConversationThread,
    Message,
    MessageRole,
    ThreadMetadata,
)


class TestMessage:
    """Test cases for Message model."""

    def test_message_creation(self):
        """Test creating a message with required fields."""
        message = Message(role=MessageRole.USER, content="Hello, world!")

        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"
        assert isinstance(message.timestamp, datetime)
        assert message.metadata == {}

    def test_message_with_metadata(self):
        """Test creating a message with metadata."""
        metadata = {"source": "test", "priority": "high"}
        message = Message(role=MessageRole.ASSISTANT, content="Response", metadata=metadata)

        assert message.metadata == metadata

    def test_message_with_timestamp(self):
        """Test creating a message with custom timestamp."""
        custom_time = datetime(2023, 1, 1, 12, 0, 0)
        message = Message(role=MessageRole.SYSTEM, content="System message", timestamp=custom_time)

        assert message.timestamp == custom_time

    def test_message_immutability(self):
        """Test that Message is immutable (frozen dataclass)."""
        message = Message(role=MessageRole.USER, content="Test")

        with pytest.raises(AttributeError):
            message.content = "Changed"


class TestAgentConfig:
    """Test cases for AgentConfig model."""

    def test_agent_config_creation(self):
        """Test creating agent config with required fields."""
        config = AgentConfig(
            name="Test Agent",
            agent_type=AgentType.SUPERVISOR,
            instructions="Test instructions",
        )

        assert config.name == "Test Agent"
        assert config.agent_type == AgentType.SUPERVISOR.value
        assert config.instructions == "Test instructions"
        assert config.max_tokens == 4000  # default
        assert config.temperature == 0.7  # default
        assert config.tools == []  # default
        assert config.metadata == {}  # default

    def test_agent_config_with_optional_fields(self):
        """Test creating agent config with all fields."""
        tools = ["search", "email"]
        metadata = {"version": "1.0"}

        config = AgentConfig(
            name="Full Agent",
            agent_type=AgentType.RESEARCH,
            instructions="Full instructions",
            max_tokens=2000,
            temperature=0.5,
            tools=tools,
            metadata=metadata,
        )

        assert config.max_tokens == 2000
        assert config.temperature == 0.5
        assert config.tools == tools
        assert config.metadata == metadata

    def test_agent_config_enum_validation(self):
        """Test agent type enum validation."""
        config = AgentConfig(name="Test", agent_type=AgentType.WRITER, instructions="Test")

        assert config.agent_type == AgentType.WRITER.value


class TestAgentResponse:
    """Test cases for AgentResponse model."""

    def test_agent_response_creation(self):
        """Test creating agent response with required fields."""
        messages = [Message(role=MessageRole.ASSISTANT, content="Response")]

        response = AgentResponse(
            agent_name="Test Agent",
            status=AgentStatus.COMPLETED,
            messages=messages,
            execution_time=1.5,
        )

        assert response.agent_name == "Test Agent"
        assert response.status == AgentStatus.COMPLETED.value
        assert response.messages == messages
        assert response.execution_time == 1.5
        assert response.token_usage is None
        assert response.error is None
        assert response.metadata == {}

    def test_agent_response_with_optional_fields(self):
        """Test creating agent response with all fields."""
        messages = [Message(role=MessageRole.ASSISTANT, content="Response")]
        token_usage = {"prompt_tokens": 100, "completion_tokens": 50}
        metadata = {"model": "gpt-4"}

        response = AgentResponse(
            agent_name="Full Agent",
            status=AgentStatus.ERROR,
            messages=messages,
            execution_time=2.0,
            token_usage=token_usage,
            error="Test error",
            metadata=metadata,
        )

        assert response.token_usage == token_usage
        assert response.error == "Test error"
        assert response.metadata == metadata

    def test_agent_response_status_enum(self):
        """Test agent status enum handling."""
        messages = [Message(role=MessageRole.ASSISTANT, content="Response")]

        for status in AgentStatus:
            response = AgentResponse(agent_name="Test", status=status, messages=messages, execution_time=1.0)
            assert response.status == status.value


class TestConversationThread:
    """Test cases for ConversationThread model."""

    def test_conversation_thread_creation(self):
        """Test creating conversation thread with required fields."""
        thread = ConversationThread(agent_name="Test Agent", agent_type="supervisor")

        assert thread.agent_name == "Test Agent"
        assert thread.agent_type == "supervisor"
        assert len(thread.thread_id) > 0  # UUID generated
        assert thread.messages == []
        assert isinstance(thread.created_at, datetime)
        assert isinstance(thread.updated_at, datetime)
        assert thread.title is None
        assert thread.tags == []
        assert thread.metadata == {}

    def test_add_message(self):
        """Test adding a single message to thread."""
        thread = ConversationThread(agent_name="Test Agent", agent_type="supervisor")
        message = Message(role=MessageRole.USER, content="Hello")
        original_updated = thread.updated_at

        thread.add_message(message)

        assert len(thread.messages) == 1
        assert thread.messages[0] == message
        assert thread.updated_at > original_updated

    def test_add_messages(self):
        """Test adding multiple messages to thread."""
        thread = ConversationThread(agent_name="Test Agent", agent_type="supervisor")
        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there"),
        ]

        thread.add_messages(messages)

        assert len(thread.messages) == 2
        assert thread.messages == messages

    def test_get_messages(self):
        """Test retrieving messages from thread."""
        thread = ConversationThread(agent_name="Test Agent", agent_type="supervisor")
        messages = [Message(role=MessageRole.USER, content=f"Message {i}") for i in range(5)]
        thread.add_messages(messages)

        # Test getting all messages
        all_messages = thread.get_messages()
        assert len(all_messages) == 5
        assert all_messages == messages

        # Test getting limited messages
        limited = thread.get_messages(limit=3)
        assert len(limited) == 3
        assert limited == messages[-3:]  # Should get last 3

        # Test getting 0 messages
        empty = thread.get_messages(limit=0)
        assert len(empty) == 0

    def test_clear_messages(self):
        """Test clearing all messages from thread."""
        thread = ConversationThread(agent_name="Test Agent", agent_type="supervisor")
        messages = [Message(role=MessageRole.USER, content="Test")]
        thread.add_messages(messages)
        original_updated = thread.updated_at

        thread.clear_messages()

        assert len(thread.messages) == 0
        assert thread.updated_at > original_updated

    def test_serialize_deserialize(self):
        """Test serialization and deserialization of thread."""
        # Create thread with data
        thread = ConversationThread(
            agent_name="Test Agent",
            agent_type="supervisor",
            title="Test Thread",
            tags=["test", "demo"],
            metadata={"version": "1.0"},
        )
        message = Message(role=MessageRole.USER, content="Hello")
        thread.add_message(message)

        # Serialize
        serialized = thread.serialize()

        # Verify serialized structure
        assert serialized["agent_name"] == "Test Agent"
        assert serialized["agent_type"] == "supervisor"
        assert serialized["title"] == "Test Thread"
        assert serialized["tags"] == ["test", "demo"]
        assert serialized["metadata"] == {"version": "1.0"}
        assert len(serialized["messages"]) == 1
        assert serialized["messages"][0]["role"] == "user"
        assert serialized["messages"][0]["content"] == "Hello"

        # Deserialize
        deserialized = ConversationThread.deserialize(serialized)

        # Verify deserialized object
        assert deserialized.agent_name == thread.agent_name
        assert deserialized.agent_type == thread.agent_type
        assert deserialized.title == thread.title
        assert deserialized.tags == thread.tags
        assert deserialized.metadata == thread.metadata
        assert len(deserialized.messages) == 1
        assert deserialized.messages[0].role == MessageRole.USER
        assert deserialized.messages[0].content == "Hello"


class TestConversationSummary:
    """Test cases for ConversationSummary model."""

    def test_conversation_summary_creation(self):
        """Test creating conversation summary."""
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        updated_at = datetime(2023, 1, 1, 13, 0, 0)

        summary = ConversationSummary(
            thread_id="test-123",
            agent_name="Test Agent",
            agent_type="supervisor",
            title="Test Conversation",
            message_count=5,
            created_at=created_at,
            updated_at=updated_at,
            tags=["test"],
            last_message_preview="Last message...",
        )

        assert summary.thread_id == "test-123"
        assert summary.agent_name == "Test Agent"
        assert summary.agent_type == "supervisor"
        assert summary.title == "Test Conversation"
        assert summary.message_count == 5
        assert summary.created_at == created_at
        assert summary.updated_at == updated_at
        assert summary.tags == ["test"]
        assert summary.last_message_preview == "Last message..."


class TestConversationContext:
    """Test cases for ConversationContext model."""

    def test_conversation_context_creation(self):
        """Test creating conversation context."""
        context = ConversationContext(conversation_id="test-123")

        assert context.conversation_id == "test-123"
        assert context.messages == []
        assert context.metadata == {}
        assert isinstance(context.created_at, datetime)
        assert isinstance(context.updated_at, datetime)

    def test_conversation_context_with_data(self):
        """Test creating conversation context with data."""
        messages = [Message(role=MessageRole.USER, content="Test")]
        metadata = {"key": "value"}
        created_at = datetime(2023, 1, 1, 12, 0, 0)

        context = ConversationContext(
            conversation_id="test-123",
            messages=messages,
            metadata=metadata,
            created_at=created_at,
        )

        assert context.messages == messages
        assert context.metadata == metadata
        assert context.created_at == created_at


class TestEnums:
    """Test cases for enum classes."""

    def test_agent_type_enum(self):
        """Test AgentType enum values."""
        assert AgentType.SUPERVISOR.value == "supervisor"
        assert AgentType.RESEARCH.value == "research"
        assert AgentType.WRITER.value == "writer"

        # Test all enum members
        all_types = list(AgentType)
        assert len(all_types) == 3
        assert AgentType.SUPERVISOR in all_types
        assert AgentType.RESEARCH in all_types
        assert AgentType.WRITER in all_types

    def test_message_role_enum(self):
        """Test MessageRole enum values."""
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"
        assert MessageRole.SYSTEM.value == "system"

        # Test all enum members
        all_roles = list(MessageRole)
        assert len(all_roles) == 3

    def test_agent_status_enum(self):
        """Test AgentStatus enum values."""
        assert AgentStatus.IDLE.value == "idle"
        assert AgentStatus.RUNNING.value == "running"
        assert AgentStatus.COMPLETED.value == "completed"
        assert AgentStatus.ERROR.value == "error"

        # Test all enum members
        all_statuses = list(AgentStatus)
        assert len(all_statuses) == 4


class TestThreadMetadata:
    """Test cases for ThreadMetadata dataclass."""

    def test_thread_metadata_creation(self):
        """Test creating thread metadata."""
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        updated_at = datetime(2023, 1, 1, 13, 0, 0)

        metadata = ThreadMetadata(
            thread_id="test-123",
            agent_name="Test Agent",
            agent_type="supervisor",
            created_at=created_at,
            updated_at=updated_at,
            title="Test Thread",
            tags=["test", "demo"],
            metadata={"version": "1.0"},
        )

        assert metadata.thread_id == "test-123"
        assert metadata.agent_name == "Test Agent"
        assert metadata.agent_type == "supervisor"
        assert metadata.created_at == created_at
        assert metadata.updated_at == updated_at
        assert metadata.title == "Test Thread"
        assert metadata.tags == ["test", "demo"]
        assert metadata.metadata == {"version": "1.0"}

    def test_thread_metadata_immutability(self):
        """Test that ThreadMetadata is immutable (frozen dataclass)."""
        created_at = datetime(2023, 1, 1, 12, 0, 0)
        updated_at = datetime(2023, 1, 1, 13, 0, 0)

        metadata = ThreadMetadata(
            thread_id="test-123",
            agent_name="Test Agent",
            agent_type="supervisor",
            created_at=created_at,
            updated_at=updated_at,
        )

        with pytest.raises(AttributeError):
            metadata.title = "Changed"
