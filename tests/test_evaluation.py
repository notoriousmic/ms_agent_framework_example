"""Unit tests for evaluation service."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from microsoft_agent_framework.application.evaluation_service.eval import (
    call_agent,
    evaluate_responses_cloud,
    generate_responses,
    run_evaluation,
)
from microsoft_agent_framework.domain.models import (
    AgentResponse,
    AgentStatus,
    Message,
    MessageRole,
)


class TestCallAgent:
    """Test cases for the call_agent function."""

    @pytest.mark.asyncio
    async def test_call_agent_success(self):
        """Test successful agent call with response messages."""
        # Create mock response with messages
        mock_response = AgentResponse(
            agent_name="Test Agent",
            status=AgentStatus.COMPLETED,
            messages=[Message(role=MessageRole.ASSISTANT, content="Test response")],
            execution_time=1.0,
        )

        with patch("microsoft_agent_framework.application.evaluation_service.eval.agent_main") as mock_agent_main:
            mock_agent_main.return_value = mock_response

            result = await call_agent("Test query")

            assert result == "Test response"
            mock_agent_main.assert_called_once_with("Test query")

    @pytest.mark.asyncio
    async def test_call_agent_no_messages(self):
        """Test agent call with no messages in response."""
        mock_response = AgentResponse(
            agent_name="Test Agent",
            status=AgentStatus.COMPLETED,
            messages=[],
            execution_time=1.0,
        )

        with patch("microsoft_agent_framework.application.evaluation_service.eval.agent_main") as mock_agent_main:
            mock_agent_main.return_value = mock_response

            result = await call_agent("Test query")

            assert result == str(mock_response)

    @pytest.mark.asyncio
    async def test_call_agent_no_response_messages_attribute(self):
        """Test agent call with response that doesn't have messages attribute."""
        mock_response = "Simple string response"

        with patch("microsoft_agent_framework.application.evaluation_service.eval.agent_main") as mock_agent_main:
            mock_agent_main.return_value = mock_response

            result = await call_agent("Test query")

            assert result == "Simple string response"

    @pytest.mark.asyncio
    async def test_call_agent_empty_content(self):
        """Test agent call with empty content."""
        mock_response = AgentResponse(
            agent_name="Test Agent",
            status=AgentStatus.COMPLETED,
            messages=[Message(role=MessageRole.ASSISTANT, content="")],
            execution_time=1.0,
        )

        with patch("microsoft_agent_framework.application.evaluation_service.eval.agent_main") as mock_agent_main:
            mock_agent_main.return_value = mock_response

            result = await call_agent("Test query")

            assert result == str(mock_response)


class TestGenerateResponses:
    """Test cases for the generate_responses function."""

    @pytest.fixture
    def sample_input_data(self):
        """Create sample input data for testing."""
        return [
            {"query": "What is AI?", "response": "AI is artificial intelligence"},
            {
                "query": "How does ML work?",
                "response": "ML uses algorithms to learn patterns",
            },
        ]

    @pytest.fixture
    def mock_input_file(self, sample_input_data, tmp_path):
        """Create a mock input file."""
        input_file = tmp_path / "test_input.jsonl"
        with open(input_file, "w") as f:
            for item in sample_input_data:
                f.write(json.dumps(item) + "\n")
        return input_file

    @pytest.mark.asyncio
    async def test_generate_responses_success(self, mock_input_file, tmp_path, sample_input_data):
        """Test successful response generation."""
        output_file = tmp_path / "test_output.jsonl"

        with patch("microsoft_agent_framework.application.evaluation_service.eval.call_agent") as mock_call_agent:
            mock_call_agent.side_effect = ["AI response 1", "ML response 2"]

            result_file = await generate_responses(mock_input_file, output_file)

            assert result_file == output_file
            assert output_file.exists()

            # Verify output content
            with open(output_file) as f:
                results = [json.loads(line) for line in f]

            assert len(results) == 2
            assert results[0]["query"] == "What is AI?"
            assert results[0]["response"] == "AI response 1"
            assert results[0]["ground_truth"] == "AI is artificial intelligence"

    @pytest.mark.asyncio
    async def test_generate_responses_with_error(self, mock_input_file, tmp_path):
        """Test response generation with agent errors."""
        output_file = tmp_path / "test_output.jsonl"

        with patch("microsoft_agent_framework.application.evaluation_service.eval.call_agent") as mock_call_agent:
            mock_call_agent.side_effect = [
                "Success response",
                Exception("Agent failed"),
            ]

            result_file = await generate_responses(mock_input_file, output_file)

            assert result_file == output_file
            assert output_file.exists()

            # Verify output content
            with open(output_file) as f:
                results = [json.loads(line) for line in f]

            assert len(results) == 2
            assert results[0]["response"] == "Success response"
            assert "ERROR: Agent failed" in results[1]["response"]


class TestEvaluateResponsesCloud:
    """Test cases for the evaluate_responses_cloud function."""

    @pytest.fixture
    def mock_output_file(self, tmp_path):
        """Create a mock output file."""
        output_file = tmp_path / "test_results.jsonl"
        sample_data = [
            {
                "query": "What is AI?",
                "response": "AI is artificial intelligence",
                "ground_truth": "AI stands for Artificial Intelligence",
            }
        ]
        with open(output_file, "w") as f:
            for item in sample_data:
                f.write(json.dumps(item) + "\n")
        return output_file

    def test_evaluate_responses_cloud_no_endpoint(self, mock_output_file):
        """Test evaluation when PROJECT_ENDPOINT is not set."""
        with patch.dict("os.environ", {}, clear=True):
            result = evaluate_responses_cloud(mock_output_file)
            assert result is None

    @patch("microsoft_agent_framework.application.evaluation_service.eval.AIProjectClient")
    def test_evaluate_responses_cloud_success(self, mock_client_class, mock_output_file):
        """Test successful cloud evaluation."""
        # Mock environment variables
        env_vars = {
            "PROJECT_ENDPOINT": "https://test.endpoint.com",
            "AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_OPENAI_ENDPOINT": "https://openai.endpoint.com",
            "AZURE_OPENAI_API_KEY": "test-key",
            "AZURE_SUBSCRIPTION_ID": "test-sub-id",
            "RESOURCE_GROUP_NAME": "test-rg",
            "PROJECT_NAME": "test-project",
        }

        with patch.dict("os.environ", env_vars):
            # Mock client and responses
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock dataset upload
            mock_dataset = Mock()
            mock_dataset.id = "test-dataset-id"
            mock_client.datasets.upload_file.return_value = mock_dataset

            # Mock evaluation creation
            mock_evaluation_response = Mock()
            mock_evaluation_response.id = "test-eval-id"
            mock_evaluation_response.status = "running"
            mock_client.evaluations.create.return_value = mock_evaluation_response

            result = evaluate_responses_cloud(mock_output_file)

            assert result == mock_evaluation_response
            mock_client.datasets.upload_file.assert_called_once()
            mock_client.evaluations.create.assert_called_once()

    @patch("microsoft_agent_framework.application.evaluation_service.eval.AIProjectClient")
    def test_evaluate_responses_cloud_upload_failure(self, mock_client_class, mock_output_file):
        """Test evaluation with dataset upload failure."""
        env_vars = {
            "PROJECT_ENDPOINT": "https://test.endpoint.com",
            "AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME": "test-deployment",
        }

        with patch.dict("os.environ", env_vars):
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            mock_client.datasets.upload_file.side_effect = Exception("Upload failed")

            result = evaluate_responses_cloud(mock_output_file)

            assert result is None

    @patch("microsoft_agent_framework.application.evaluation_service.eval.AIProjectClient")
    def test_evaluate_responses_cloud_evaluation_failure(self, mock_client_class, mock_output_file):
        """Test evaluation with evaluation creation failure."""
        env_vars = {
            "PROJECT_ENDPOINT": "https://test.endpoint.com",
            "AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_OPENAI_ENDPOINT": "https://openai.endpoint.com",
            "AZURE_OPENAI_API_KEY": "test-key",
        }

        with patch.dict("os.environ", env_vars):
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            # Mock successful dataset upload
            mock_dataset = Mock()
            mock_dataset.id = "test-dataset-id"
            mock_client.datasets.upload_file.return_value = mock_dataset

            # Mock evaluation creation failure
            mock_client.evaluations.create.side_effect = Exception("Evaluation failed")

            result = evaluate_responses_cloud(mock_output_file)

            assert result is None


class TestRunEvaluation:
    """Test cases for the run_evaluation function."""

    @pytest.fixture
    def mock_input_file(self, tmp_path):
        """Create a mock input file."""
        input_file = tmp_path / "qr_data.jsonl"
        sample_data = [{"query": "What is AI?", "response": "AI is artificial intelligence"}]
        with open(input_file, "w") as f:
            for item in sample_data:
                f.write(json.dumps(item) + "\n")
        return input_file

    @pytest.mark.asyncio
    async def test_run_evaluation_success(self, tmp_path, mock_input_file):
        """Test successful evaluation run."""
        output_file = tmp_path / "evaluation_results.jsonl"

        with patch("microsoft_agent_framework.application.evaluation_service.eval.generate_responses"):
            with patch(
                "microsoft_agent_framework.application.evaluation_service.eval.evaluate_responses_cloud"
            ) as mock_evaluate:
                with patch("asyncio.get_event_loop") as mock_loop:
                    mock_async_loop = Mock()
                    mock_loop.return_value = mock_async_loop
                    mock_async_loop.run_until_complete.return_value = output_file

                    mock_evaluation_result = Mock()
                    mock_evaluate.return_value = mock_evaluation_result

                    result = run_evaluation(
                        input_file=str(mock_input_file),
                        output_file=str(output_file),
                        skip_generation=False,
                    )

                    assert result == mock_evaluation_result
                    mock_async_loop.run_until_complete.assert_called_once()
                    mock_evaluate.assert_called_once_with(output_file)

    def test_run_evaluation_skip_generation(self, tmp_path, mock_input_file):
        """Test evaluation run with skipped generation."""
        output_file = tmp_path / "existing_results.jsonl"
        # Create the output file to simulate existing results
        with open(output_file, "w") as f:
            f.write('{"query": "test", "response": "test"}\n')

        with patch(
            "microsoft_agent_framework.application.evaluation_service.eval.evaluate_responses_cloud"
        ) as mock_evaluate:
            mock_evaluation_result = Mock()
            mock_evaluate.return_value = mock_evaluation_result

            result = run_evaluation(
                input_file=str(mock_input_file),
                output_file=str(output_file),
                skip_generation=True,
            )

            assert result == mock_evaluation_result
            mock_evaluate.assert_called_once_with(Path(output_file))

    def test_run_evaluation_file_not_found(self):
        """Test evaluation run with non-existent input file."""
        with pytest.raises(FileNotFoundError) as exc_info:
            run_evaluation(input_file="non_existent.jsonl", output_file="output.jsonl")

        assert "Input file not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_run_evaluation_with_project_root_fallback(self, tmp_path):
        """Test evaluation run with project root fallback for file paths."""
        # Create files in a subdirectory to simulate project structure
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        input_file = data_dir / "qr_data.jsonl"

        sample_data = [{"query": "What is AI?", "response": "AI is artificial intelligence"}]
        with open(input_file, "w") as f:
            for item in sample_data:
                f.write(json.dumps(item) + "\n")

        with patch("pathlib.Path.cwd") as mock_cwd:
            # Mock current working directory to be our test path
            mock_cwd.return_value = tmp_path

            with patch("microsoft_agent_framework.application.evaluation_service.eval.generate_responses"):
                with patch(
                    "microsoft_agent_framework.application.evaluation_service.eval.evaluate_responses_cloud"
                ) as mock_evaluate:
                    with patch("asyncio.get_event_loop") as mock_loop:
                        mock_async_loop = Mock()
                        mock_loop.return_value = mock_async_loop
                        mock_async_loop.run_until_complete.return_value = tmp_path / "data" / "evaluation_results.jsonl"

                        mock_evaluation_result = Mock()
                        mock_evaluate.return_value = mock_evaluation_result

                        # Use relative path that doesn't exist initially
                        result = run_evaluation(
                            input_file="data/qr_data.jsonl",
                            output_file="data/evaluation_results.jsonl",
                        )

                        assert result == mock_evaluation_result


class TestEvaluationIntegration:
    """Integration tests for evaluation workflow."""

    @pytest.mark.asyncio
    async def test_full_evaluation_workflow(self, tmp_path):
        """Test the complete evaluation workflow."""
        # Create input file
        input_file = tmp_path / "test_data.jsonl"
        sample_data = [{"query": "What is machine learning?", "response": "ML is a subset of AI"}]
        with open(input_file, "w") as f:
            for item in sample_data:
                f.write(json.dumps(item) + "\n")

        output_file = tmp_path / "results.jsonl"

        # Mock the agent call to return a predictable response
        with patch("microsoft_agent_framework.application.evaluation_service.eval.call_agent") as mock_call_agent:
            mock_call_agent.return_value = "Machine learning is a method of AI"

            # Generate responses
            result_file = await generate_responses(input_file, output_file)

            assert result_file.exists()

            # Verify the generated content
            with open(result_file) as f:
                results = [json.loads(line) for line in f]

            assert len(results) == 1
            assert results[0]["query"] == "What is machine learning?"
            assert results[0]["response"] == "Machine learning is a method of AI"
            assert results[0]["ground_truth"] == "ML is a subset of AI"

    def test_evaluation_error_handling(self):
        """Test error handling in evaluation functions."""
        # Test with invalid path objects
        invalid_path = Path("non_existent_directory/file.jsonl")

        # The evaluate_responses_cloud function should handle missing environment gracefully
        with patch.dict("os.environ", {}, clear=True):
            result = evaluate_responses_cloud(invalid_path)
            assert result is None
