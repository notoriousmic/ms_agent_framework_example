"""Pytest configuration and fixtures for the Microsoft Agent Framework tests."""

import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from microsoft_agent_framework.domain.models import (
    AgentConfig,
    AgentResponse,
    AgentStatus,
    AgentType,
    ConversationThread,
    Message,
    MessageRole,
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_message():
    """Create a sample message for testing."""
    return Message(
        role=MessageRole.USER,
        content="Test message content",
        timestamp=datetime(2023, 1, 1, 12, 0, 0),
        metadata={"test": True},
    )


@pytest.fixture
def sample_agent_config():
    """Create a sample agent configuration for testing."""
    return AgentConfig(
        name="Test Agent",
        agent_type=AgentType.SUPERVISOR,
        instructions="Test instructions for the agent",
        max_tokens=2000,
        temperature=0.5,
        tools=["search", "email"],
        metadata={"version": "1.0", "test": True},
    )


@pytest.fixture
def sample_agent_response():
    """Create a sample agent response for testing."""
    return AgentResponse(
        agent_name="Test Agent",
        status=AgentStatus.COMPLETED,
        messages=[Message(role=MessageRole.ASSISTANT, content="Test response")],
        execution_time=1.5,
        token_usage={"prompt_tokens": 100, "completion_tokens": 50},
        metadata={"model": "gpt-4", "test": True},
    )


@pytest.fixture
def sample_conversation_thread():
    """Create a sample conversation thread for testing."""
    thread = ConversationThread(
        agent_name="Test Agent",
        agent_type="supervisor",
        title="Test Conversation",
        tags=["test", "sample"],
        metadata={"test": True},
    )

    # Add some sample messages
    thread.add_message(Message(role=MessageRole.USER, content="Hello"))
    thread.add_message(Message(role=MessageRole.ASSISTANT, content="Hi there!"))
    thread.add_message(Message(role=MessageRole.USER, content="How are you?"))

    return thread


@pytest.fixture
def mock_agent():
    """Create a mock agent for testing."""
    agent = AsyncMock()
    agent.name = "Mock Agent"
    agent.config = AgentConfig(
        name="Mock Agent",
        agent_type=AgentType.SUPERVISOR,
        instructions="Mock instructions",
    )
    agent.run.return_value = AgentResponse(
        agent_name="Mock Agent",
        status=AgentStatus.COMPLETED,
        messages=[Message(role=MessageRole.ASSISTANT, content="Mock response")],
        execution_time=1.0,
    )
    return agent


@pytest.fixture
def mock_azure_client():
    """Create a mock Azure OpenAI client for testing."""
    client = Mock()
    mock_agent = Mock()
    client.create_agent.return_value = mock_agent
    return client


@pytest.fixture
def mock_conversation_repository():
    """Create a mock conversation repository for testing."""
    repo = AsyncMock()
    repo.save.return_value = None
    repo.load.return_value = None
    repo.delete.return_value = None
    repo.list_all.return_value = []
    return repo


# Test configuration
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "azure: mark test as requiring Azure credentials")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names."""
    for item in items:
        # Mark integration tests
        if "integration" in item.name.lower() or "TestIntegration" in str(item.cls):
            item.add_marker(pytest.mark.integration)

        # Mark slow tests
        if "slow" in item.name.lower() or any(keyword in item.name.lower() for keyword in ["timeout", "large", "bulk"]):
            item.add_marker(pytest.mark.slow)

        # Mark Azure tests
        if any(keyword in item.name.lower() for keyword in ["azure", "cloud", "evaluation"]):
            item.add_marker(pytest.mark.azure)
