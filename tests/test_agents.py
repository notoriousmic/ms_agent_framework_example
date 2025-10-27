"""Unit tests for agent implementations."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from microsoft_agent_framework.application.agents.research_agent import ResearchAgent
from microsoft_agent_framework.application.agents.supervisor_agent import (
    SupervisorAgent,
)
from microsoft_agent_framework.application.agents.writer_agent import WriterAgent
from microsoft_agent_framework.domain.exceptions import (
    AgentExecutionError,
    AgentInitializationError,
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


class TestSupervisorAgent:
    """Test cases for SupervisorAgent."""

    @pytest.fixture
    def agent_config(self):
        """Create a test agent config."""
        return AgentConfig(
            name="Test Supervisor",
            agent_type=AgentType.SUPERVISOR,
            instructions="Test instructions",
        )

    @pytest.fixture
    def supervisor_agent(self, agent_config):
        """Create a SupervisorAgent instance."""
        return SupervisorAgent(agent_config)

    def test_supervisor_agent_creation(self, supervisor_agent, agent_config):
        """Test supervisor agent creation."""
        assert supervisor_agent.name == agent_config.name
        assert supervisor_agent.config == agent_config
        assert not supervisor_agent._is_initialized

    def test_supervisor_agent_properties(self, supervisor_agent, agent_config):
        """Test supervisor agent properties."""
        assert supervisor_agent.name == "Test Supervisor"
        assert supervisor_agent.config.agent_type == AgentType.SUPERVISOR.value

    @pytest.mark.asyncio
    async def test_initialize_success(self, supervisor_agent):
        """Test successful initialization."""
        with patch(
            "microsoft_agent_framework.application.agents.supervisor_agent.AzureAIAgentClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_agent = Mock()
            mock_client.create_agent.return_value = mock_agent
            mock_client_class.return_value = mock_client

            with patch.object(
                supervisor_agent, "_initialize_sub_agents", new_callable=AsyncMock
            ) as mock_init_sub_agents:
                await supervisor_agent.initialize()

                assert supervisor_agent._is_initialized
                assert supervisor_agent._azure_agent == mock_agent
                mock_init_sub_agents.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_failure(self, supervisor_agent):
        """Test initialization failure."""
        with patch(
            "microsoft_agent_framework.application.agents.supervisor_agent.AzureAIAgentClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            with pytest.raises(AgentInitializationError) as exc_info:
                await supervisor_agent.initialize()

            assert "Failed to initialize supervisor agent" in str(exc_info.value)
            assert not supervisor_agent._is_initialized

    @pytest.mark.asyncio
    async def test_cleanup(self, supervisor_agent):
        """Test agent cleanup."""
        # Mock sub-agents
        mock_research = AsyncMock()
        mock_writer = AsyncMock()
        supervisor_agent._research_agent = mock_research
        supervisor_agent._writer_agent = mock_writer
        supervisor_agent._is_initialized = True

        await supervisor_agent.cleanup()

        mock_research.cleanup.assert_called_once()
        mock_writer.cleanup.assert_called_once()
        assert not supervisor_agent._is_initialized

    @pytest.mark.asyncio
    async def test_run_with_string_message(self, supervisor_agent):
        """Test running agent with string message."""
        with patch.object(supervisor_agent, "initialize", new_callable=AsyncMock):
            with patch.object(supervisor_agent, "_azure_agent") as mock_azure_agent:
                mock_response = Mock()
                mock_azure_agent.run = AsyncMock(return_value=mock_response)

                with patch.object(supervisor_agent, "_extract_messages") as mock_extract:
                    expected_messages = [Message(role=MessageRole.ASSISTANT, content="Response")]
                    mock_extract.return_value = expected_messages

                    result = await supervisor_agent.run("Test message")

                    assert isinstance(result, AgentResponse)
                    assert result.agent_name == supervisor_agent.name
                    assert result.status == AgentStatus.COMPLETED.value
                    assert result.messages == expected_messages
                    assert result.execution_time > 0

    @pytest.mark.asyncio
    async def test_run_with_thread(self, supervisor_agent):
        """Test running agent with conversation thread."""
        thread = ConversationThread(agent_name="Test Agent", agent_type="supervisor")

        with patch.object(supervisor_agent, "initialize", new_callable=AsyncMock):
            with patch.object(supervisor_agent, "_azure_agent") as mock_azure_agent:
                mock_response = Mock()
                mock_azure_agent.run = AsyncMock(return_value=mock_response)

                with patch.object(supervisor_agent, "_extract_messages") as mock_extract:
                    expected_messages = [Message(role=MessageRole.ASSISTANT, content="Response")]
                    mock_extract.return_value = expected_messages

                    result = await supervisor_agent.run("Test message", thread=thread)

                    assert result.metadata["thread_id"] == thread.thread_id
                    assert len(thread.messages) == 2  # User message + assistant messages

    @pytest.mark.asyncio
    async def test_run_execution_error(self, supervisor_agent):
        """Test execution error handling."""
        with patch.object(supervisor_agent, "initialize", new_callable=AsyncMock):
            with patch.object(supervisor_agent, "_azure_agent") as mock_azure_agent:
                mock_azure_agent.run.side_effect = Exception("Execution failed")

                with pytest.raises(AgentExecutionError) as exc_info:
                    await supervisor_agent.run("Test message")

                assert "Supervisor agent execution failed" in str(exc_info.value)
                assert exc_info.value.agent_name == supervisor_agent.name

    def test_convert_message_string(self, supervisor_agent):
        """Test converting string message."""
        result = supervisor_agent._convert_message("Test message")
        assert result == "Test message"

    def test_convert_message_list(self, supervisor_agent):
        """Test converting message list."""
        messages = [
            Message(role=MessageRole.USER, content="First"),
            Message(role=MessageRole.ASSISTANT, content="Second"),
        ]
        result = supervisor_agent._convert_message(messages)
        assert result == "Second"  # Should return last message content

    def test_convert_message_empty_list(self, supervisor_agent):
        """Test converting empty message list."""
        result = supervisor_agent._convert_message([])
        assert result == ""

    def test_extract_messages_with_contents(self, supervisor_agent):
        """Test extracting messages from response with contents."""
        mock_content = Mock()
        mock_content.text = "Response text"

        mock_message = Mock()
        mock_message.contents = [mock_content]

        mock_response = Mock()
        mock_response.messages = [mock_message]

        result = supervisor_agent._extract_messages(mock_response)

        assert len(result) == 1
        assert result[0].role == MessageRole.ASSISTANT
        assert result[0].content == "Response text"

    def test_extract_messages_fallback(self, supervisor_agent):
        """Test extracting messages with fallback to string conversion."""
        mock_response = Mock()
        mock_response.messages = None

        result = supervisor_agent._extract_messages(mock_response)

        assert len(result) == 1
        assert result[0].role == MessageRole.ASSISTANT
        assert result[0].content == str(mock_response)


class TestResearchAgent:
    """Test cases for ResearchAgent."""

    @pytest.fixture
    def agent_config(self):
        """Create a test agent config."""
        return AgentConfig(
            name="Test Research Agent",
            agent_type=AgentType.RESEARCH,
            instructions="Test research instructions",
        )

    @pytest.fixture
    def research_agent(self, agent_config):
        """Create a ResearchAgent instance."""
        return ResearchAgent(agent_config)

    def test_research_agent_creation(self, research_agent, agent_config):
        """Test research agent creation."""
        assert research_agent.name == agent_config.name
        assert research_agent.config == agent_config
        assert not research_agent._is_initialized

    @pytest.mark.asyncio
    async def test_initialize_success(self, research_agent):
        """Test successful initialization."""
        with patch(
            "microsoft_agent_framework.application.agents.research_agent.AzureAIAgentClient"
        ) as mock_client_class:
            mock_client = Mock()
            mock_agent = Mock()
            mock_client.create_agent.return_value = mock_agent
            mock_client_class.return_value = mock_client

            with patch("microsoft_agent_framework.application.agents.research_agent.MCPStdioTool"):
                await research_agent.initialize()

                assert research_agent._is_initialized
                assert research_agent._azure_agent == mock_agent

    @pytest.mark.asyncio
    async def test_initialize_failure(self, research_agent):
        """Test initialization failure."""
        with patch(
            "microsoft_agent_framework.application.agents.research_agent.AzureAIAgentClient"
        ) as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            with pytest.raises(AgentInitializationError) as exc_info:
                await research_agent.initialize()

            assert "Failed to initialize research agent" in str(exc_info.value)
            assert not research_agent._is_initialized

    @pytest.mark.asyncio
    async def test_cleanup(self, research_agent):
        """Test agent cleanup."""
        research_agent._is_initialized = True
        await research_agent.cleanup()
        assert not research_agent._is_initialized

    @pytest.mark.asyncio
    async def test_run_success(self, research_agent):
        """Test successful agent run."""
        with patch.object(research_agent, "initialize", new_callable=AsyncMock):
            with patch.object(research_agent, "_azure_agent") as mock_azure_agent:
                mock_response = Mock()
                mock_azure_agent.run = AsyncMock(return_value=mock_response)

                with patch.object(research_agent, "_extract_messages") as mock_extract:
                    expected_messages = [Message(role=MessageRole.ASSISTANT, content="Research result")]
                    mock_extract.return_value = expected_messages

                    result = await research_agent.run("Research query")

                    assert isinstance(result, AgentResponse)
                    assert result.agent_name == research_agent.name
                    assert result.status == AgentStatus.COMPLETED.value
                    assert result.messages == expected_messages


class TestWriterAgent:
    """Test cases for WriterAgent."""

    @pytest.fixture
    def agent_config(self):
        """Create a test agent config."""
        return AgentConfig(
            name="Test Writer Agent",
            agent_type=AgentType.WRITER,
            instructions="Test writer instructions",
        )

    @pytest.fixture
    def writer_agent(self, agent_config):
        """Create a WriterAgent instance."""
        return WriterAgent(agent_config)

    def test_writer_agent_creation(self, writer_agent, agent_config):
        """Test writer agent creation."""
        assert writer_agent.name == agent_config.name
        assert writer_agent.config == agent_config
        assert not writer_agent._is_initialized

    @pytest.mark.asyncio
    async def test_initialize_success(self, writer_agent):
        """Test successful initialization."""
        with patch("microsoft_agent_framework.application.agents.writer_agent.AzureAIAgentClient") as mock_client_class:
            mock_client = Mock()
            mock_agent = Mock()
            mock_client.create_agent.return_value = mock_agent
            mock_client_class.return_value = mock_client

            await writer_agent.initialize()

            assert writer_agent._is_initialized
            assert writer_agent._azure_agent == mock_agent

    @pytest.mark.asyncio
    async def test_initialize_failure(self, writer_agent):
        """Test initialization failure."""
        with patch("microsoft_agent_framework.application.agents.writer_agent.AzureAIAgentClient") as mock_client_class:
            mock_client_class.side_effect = Exception("Connection failed")

            with pytest.raises(AgentInitializationError) as exc_info:
                await writer_agent.initialize()

            assert "Failed to initialize writer agent" in str(exc_info.value)
            assert not writer_agent._is_initialized

    @pytest.mark.asyncio
    async def test_cleanup(self, writer_agent):
        """Test agent cleanup."""
        writer_agent._is_initialized = True
        await writer_agent.cleanup()
        assert not writer_agent._is_initialized

    @pytest.mark.asyncio
    async def test_run_success(self, writer_agent):
        """Test successful agent run."""
        with patch.object(writer_agent, "initialize", new_callable=AsyncMock):
            with patch.object(writer_agent, "_azure_agent") as mock_azure_agent:
                mock_response = Mock()
                mock_azure_agent.run = AsyncMock(return_value=mock_response)

                with patch.object(writer_agent, "_extract_messages") as mock_extract:
                    expected_messages = [Message(role=MessageRole.ASSISTANT, content="Email draft")]
                    mock_extract.return_value = expected_messages

                    result = await writer_agent.run("Write an email")

                    assert isinstance(result, AgentResponse)
                    assert result.agent_name == writer_agent.name
                    assert result.status == AgentStatus.COMPLETED.value
                    assert result.messages == expected_messages

    @pytest.mark.asyncio
    async def test_run_execution_error(self, writer_agent):
        """Test execution error handling."""
        with patch.object(writer_agent, "initialize", new_callable=AsyncMock):
            with patch.object(writer_agent, "_azure_agent") as mock_azure_agent:
                mock_azure_agent.run = AsyncMock(side_effect=Exception("Writing failed"))

                with pytest.raises(AgentExecutionError) as exc_info:
                    await writer_agent.run("Write an email")

                assert "Writer agent execution failed" in str(exc_info.value)
                assert exc_info.value.agent_name == writer_agent.name


class TestAgentIntegration:
    """Integration tests for agent interactions."""

    @pytest.mark.asyncio
    async def test_supervisor_delegation_to_research(self):
        """Test supervisor delegating to research agent."""
        config = AgentConfig(name="Test Supervisor", agent_type=AgentType.SUPERVISOR, instructions="Test")
        supervisor = SupervisorAgent(config)

        # Mock the research agent
        mock_research = AsyncMock()
        mock_research.run.return_value = AgentResponse(
            agent_name="Research Agent",
            status=AgentStatus.COMPLETED,
            messages=[Message(role=MessageRole.ASSISTANT, content="Research result")],
            execution_time=1.0,
        )
        supervisor._research_agent = mock_research

        # Test delegation function
        delegation_func = supervisor._create_research_delegation_function()
        result = await delegation_func("Test query")

        assert result == "Research result"
        mock_research.run.assert_called_once_with("Test query")

    @pytest.mark.asyncio
    async def test_supervisor_delegation_to_writer(self):
        """Test supervisor delegating to writer agent."""
        config = AgentConfig(name="Test Supervisor", agent_type=AgentType.SUPERVISOR, instructions="Test")
        supervisor = SupervisorAgent(config)

        # Mock the writer agent
        mock_writer = AsyncMock()
        mock_writer.run.return_value = AgentResponse(
            agent_name="Writer Agent",
            status=AgentStatus.COMPLETED,
            messages=[Message(role=MessageRole.ASSISTANT, content="Email draft")],
            execution_time=1.0,
        )
        supervisor._writer_agent = mock_writer

        # Test delegation function
        delegation_func = supervisor._create_writer_delegation_function()
        result = await delegation_func("Write email task")

        assert result == "Email draft"
        mock_writer.run.assert_called_once_with("Write email task")

    @pytest.mark.asyncio
    async def test_delegation_error_handling(self):
        """Test error handling in delegation functions."""
        config = AgentConfig(name="Test Supervisor", agent_type=AgentType.SUPERVISOR, instructions="Test")
        supervisor = SupervisorAgent(config)

        # Test with None research agent
        supervisor._research_agent = None
        delegation_func = supervisor._create_research_delegation_function()
        result = await delegation_func("Test query")
        assert result == "Research agent not available"

        # Test with failing research agent
        mock_research = AsyncMock()
        mock_research.run.side_effect = Exception("Research failed")
        supervisor._research_agent = mock_research

        delegation_func = supervisor._create_research_delegation_function()
        result = await delegation_func("Test query")
        assert "Research failed" in result
