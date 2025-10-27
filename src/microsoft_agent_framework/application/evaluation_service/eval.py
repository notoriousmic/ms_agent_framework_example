"""
Evaluation script for multi-agent framework using Azure AI Foundry Cloud Evaluation.

This script:
1. Loads queries from qr_data.jsonl
2. Calls the multi-agent system (supervisor + research + writer agents) for each query
3. Evaluates responses using Azure AI Foundry cloud evaluators (Groundedness, Relevance)
4. Uploads results to Azure AI Foundry portal for visualization
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    Evaluation,
    EvaluatorConfiguration,
    EvaluatorIds,
    InputDataset,
)
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

from microsoft_agent_framework.application.agents.supervisor_agent import (
    main as agent_main,
)

load_dotenv()


async def call_agent(query: str) -> str:
    """
    Call the multi-agent system with a query.

    Args:
        query: User query to send to the supervisor agent

    Returns:
        String response from the agent system
    """
    response = await agent_main(query)

    # Extract text from the agent response
    if hasattr(response, "messages") and response.messages:
        content = response.messages[-1].content
        if content:
            return content
    return str(response)


async def generate_responses(input_file: Path, output_file: Path):
    """
    Generate responses from the multi-agent system for each query in the input file.

    Args:
        input_file: Path to JSONL file with queries and ground truth responses
        output_file: Path to save JSONL file with actual agent responses

    Returns:
        Path to the output file
    """
    print(f"Loading queries from: {input_file}")
    print("Generating agent responses...\n")

    results = []

    with open(input_file) as f:
        for idx, line in enumerate(f, 1):
            data = json.loads(line)
            query = data["query"]
            ground_truth = data["response"]

            print(f"[{idx}] Processing query: {query[:80]}...")

            try:
                # Call the actual multi-agent system
                response = await call_agent(query)
                print(f"    ✓ Got response ({len(response)} chars)")

                results.append({"query": query, "response": response, "ground_truth": ground_truth})

            except Exception as e:
                print(f"    ✗ Error: {str(e)}")
                # Add empty response on error
                results.append(
                    {
                        "query": query,
                        "response": f"ERROR: {str(e)}",
                        "ground_truth": ground_truth,
                    }
                )

    # Save results
    print(f"\nSaving results to: {output_file}")
    with open(output_file, "w") as f:
        for result in results:
            f.write(json.dumps(result) + "\n")

    return output_file


def evaluate_responses_cloud(output_file: Path):
    """
    Evaluate the generated responses using Azure AI Foundry Cloud Evaluation.

    Args:
        output_file: Path to JSONL file with agent responses and ground truth

    Returns:
        Evaluation result object from Azure AI Foundry
    """
    print(f"\n{'=' * 80}")
    print("AZURE AI FOUNDRY CLOUD EVALUATION")
    print(f"{'=' * 80}\n")

    # Setup Azure AI Foundry project client
    project_endpoint = os.environ.get("PROJECT_ENDPOINT")
    if not project_endpoint:
        print("⚠ PROJECT_ENDPOINT not set. Cannot use cloud evaluation.")
        print("  Please set PROJECT_ENDPOINT in your .env file.")
        print("  Get it from: Azure AI Foundry portal > Project Settings > Project connection string\n")
        return None

    print("Connecting to Azure AI Foundry project...")
    print(f"  Endpoint: {project_endpoint}\n")

    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
    )

    # Upload dataset to Azure AI Foundry
    print("Uploading evaluation dataset...")
    dataset_name = "agent_evaluation_dataset"
    # Use timestamp for unique version
    dataset_version = datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        data_id = project_client.datasets.upload_file(
            name=dataset_name, version=dataset_version, file_path=str(output_file)
        ).id
        print(f"  ✓ Dataset uploaded with ID: {data_id}\n")
    except Exception as e:
        print(f"  ✗ Failed to upload dataset: {str(e)}\n")
        return None

    # Configure cloud evaluators
    model_deployment = os.environ["AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"]

    print("Configuring cloud evaluators:")
    print("  - Groundedness: Measures if response is grounded in the ground truth context")
    print("  - Relevance: Measures how relevant the response is to the query\n")

    evaluators = {
        "groundedness": EvaluatorConfiguration(
            id=EvaluatorIds.GROUNDEDNESS.value,
            init_params={"deployment_name": model_deployment},
            data_mapping={
                "query": "${data.query}",
                "context": "${data.ground_truth}",
                "response": "${data.response}",
            },
        ),
        "relevance": EvaluatorConfiguration(
            id=EvaluatorIds.RELEVANCE.value,
            init_params={"deployment_name": model_deployment},
            data_mapping={
                "query": "${data.query}",
                "response": "${data.response}",
            },
        ),
    }

    # Submit cloud evaluation
    print("Submitting cloud evaluation job...")
    evaluation = Evaluation(
        display_name="Multi-Agent System Evaluation",
        description="Evaluation of supervisor + research + writer agent responses",
        data=InputDataset(id=data_id),
        evaluators=evaluators,
    )

    try:
        evaluation_response = project_client.evaluations.create(
            evaluation,
            headers={
                "model-endpoint": os.environ["AZURE_OPENAI_ENDPOINT"],
                "api-key": os.environ["AZURE_OPENAI_API_KEY"],
            },
        )

        print("  ✓ Evaluation job submitted successfully!\n")
        print(f"{'=' * 80}")
        print("VIEW RESULTS IN AZURE AI FOUNDRY")
        print(f"{'=' * 80}")

        # The response object structure varies - try different attributes
        eval_id = None
        if hasattr(evaluation_response, "id"):
            eval_id = evaluation_response.id
        elif hasattr(evaluation_response, "name"):
            eval_id = evaluation_response.name
        elif isinstance(evaluation_response, dict) and "id" in evaluation_response:
            eval_id = evaluation_response["id"]

        if eval_id:
            print(f"Evaluation ID: {eval_id}")

        if hasattr(evaluation_response, "status"):
            print(f"Status: {evaluation_response.status}")

        # Construct portal URL
        subscription_id = os.environ.get("AZURE_SUBSCRIPTION_ID", "")
        resource_group = os.environ.get("RESOURCE_GROUP_NAME", "")
        project_name = os.environ.get("PROJECT_NAME", "")

        if subscription_id and resource_group and project_name:
            portal_url = "https://ai.azure.com/build/evaluation"
            if eval_id:
                portal_url += f"/{eval_id}"
            portal_url += (
                f"?wsid=/subscriptions/{subscription_id}/resourceGroups/{resource_group}"
                f"/providers/Microsoft.MachineLearningServices/workspaces/{project_name}"
            )
            print(f"\nPortal URL: {portal_url}")
        else:
            # Fallback to general evaluations page
            print("\nGo to Azure AI Foundry portal > Evaluation tab to view results")

        print(f"{'=' * 80}\n")

        return evaluation_response

    except Exception as e:
        print(f"  ✗ Failed to submit evaluation: {str(e)}\n")
        import traceback

        traceback.print_exc()
        return None


def run_evaluation(
    input_file: str = "data/qr_data.jsonl",
    output_file: str = "data/evaluation_results.jsonl",
    skip_generation: bool = False,
):
    """
    Run cloud evaluation on the multi-agent system.

    Args:
        input_file: Path to JSONL file with queries and ground truth
        output_file: Path to save agent responses before evaluation
        skip_generation: If True, skip response generation and use existing output_file

    Returns:
        Evaluation result object
    """
    # Convert to Path objects and resolve to absolute paths
    input_path = Path(input_file)
    output_path = Path(output_file)

    if not input_path.exists():
        # Try relative to project root
        project_root = Path(__file__).parent.parent.parent.parent.parent
        input_path = project_root / input_file
        output_path = project_root / output_file

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    # Step 1: Generate responses from multi-agent system
    if not skip_generation:
        print(f"{'=' * 80}")
        print("STEP 1: GENERATING AGENT RESPONSES")
        print(f"{'=' * 80}\n")

        loop = asyncio.get_event_loop()
        output_path = loop.run_until_complete(generate_responses(input_path, output_path))
    else:
        print(f"Skipping response generation, using existing file: {output_path}")

    # Step 2: Submit cloud evaluation to Azure AI Foundry
    print(f"\n{'=' * 80}")
    print("STEP 2: CLOUD EVALUATION")
    print(f"{'=' * 80}\n")

    result = evaluate_responses_cloud(output_path)

    if result:
        print(f"\n{'=' * 80}")
        print("EVALUATION SUBMITTED SUCCESSFULLY")
        print(f"{'=' * 80}")
        print("\nCheck Azure AI Foundry portal for results.")
        print("The evaluation will run in the cloud and results will appear in the portal.\n")
    else:
        print(f"\n{'=' * 80}")
        print("EVALUATION SUBMISSION FAILED")
        print(f"{'=' * 80}")
        print("\nPlease check your Azure AI Foundry configuration and try again.\n")

    return result


if __name__ == "__main__":
    # Run evaluation on qr_data.jsonl
    # Set skip_generation=True if you already have evaluation_results.jsonl
    results = run_evaluation(
        input_file="data/qr_data.jsonl",
        output_file="data/evaluation_results.jsonl",
        skip_generation=False,
    )
