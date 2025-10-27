#!/usr/bin/env python3
"""
Check evaluation scores against configured thresholds.

This script reads evaluation results and quality gate configuration,
then determines if scores meet the minimum thresholds.

Usage:
    python check_evaluation_scores.py <results_file> [--config <config_file>]

Environment variables:
    RESULTS_FILE: Path to evaluation results JSONL file
    CONFIG_FILE: Path to evaluation configuration JSON file (optional)
"""

import json
import os
import sys
from pathlib import Path


def load_config(config_path: str = ".github/evaluation-config.json") -> dict:
    """Load evaluation configuration from JSON file."""
    try:
        with open(config_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config file: {e}")
        sys.exit(1)


def load_results(results_path: str) -> list[dict]:
    """Load evaluation results from JSONL file."""
    if not Path(results_path).exists():
        print(f"⚠️ Results file not found: {results_path}")
        return []

    results = []
    try:
        with open(results_path) as f:
            for line in f:
                if line.strip():
                    results.append(json.loads(line))
    except json.JSONDecodeError as e:
        print(f"⚠️ Error parsing results file: {e}")

    return results


def extract_scores(results: list[dict]) -> dict:
    """Extract evaluation scores from results."""
    groundedness_scores = []
    relevance_scores = []

    for result in results:
        if "groundedness_score" in result:
            try:
                groundedness_scores.append(float(result["groundedness_score"]))
            except (ValueError, TypeError):
                pass

        if "relevance_score" in result:
            try:
                relevance_scores.append(float(result["relevance_score"]))
            except (ValueError, TypeError):
                pass

    return {
        "groundedness": {
            "scores": groundedness_scores,
            "average": sum(groundedness_scores) / len(groundedness_scores) if groundedness_scores else 0.0,
            "count": len(groundedness_scores),
        },
        "relevance": {
            "scores": relevance_scores,
            "average": sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0,
            "count": len(relevance_scores),
        },
    }


def check_thresholds(scores: dict, config: dict) -> tuple[bool, str]:
    """
    Check if scores meet configured thresholds.

    Returns:
        (passed: bool, message: str)
    """
    quality_gates = config.get("evaluation", {}).get("quality_gates", {})

    if not quality_gates.get("enabled", True):
        return True, "Quality gates disabled"

    metrics = quality_gates.get("metrics", {})
    aggregation = quality_gates.get("aggregation", "average").lower()

    results = {}

    # Check groundedness
    if metrics.get("groundedness", {}).get("enabled", True):
        min_score = metrics["groundedness"].get("min_score", 0.5)
        avg_score = scores["groundedness"]["average"]
        passed = avg_score >= min_score
        results["groundedness"] = {
            "passed": passed,
            "average": round(avg_score, 2),
            "threshold": min_score,
            "count": scores["groundedness"]["count"],
        }

    # Check relevance
    if metrics.get("relevance", {}).get("enabled", True):
        min_score = metrics["relevance"].get("min_score", 0.5)
        avg_score = scores["relevance"]["average"]
        passed = avg_score >= min_score
        results["relevance"] = {
            "passed": passed,
            "average": round(avg_score, 2),
            "threshold": min_score,
            "count": scores["relevance"]["count"],
        }

    # Determine overall pass/fail based on aggregation strategy
    if not results:
        return True, "No metrics to evaluate"

    metric_passes = [r["passed"] for r in results.values()]

    if aggregation == "any":
        overall_passed = any(metric_passes)
    elif aggregation == "all":
        overall_passed = all(metric_passes)
    else:  # average (default)
        overall_passed = all(metric_passes)

    # Generate message
    message_lines = ["📊 Evaluation Quality Gates Results:"]
    message_lines.append("")

    for metric_name, result in results.items():
        status = "✅" if result["passed"] else "❌"
        message_lines.append(
            f"{status} {metric_name.upper()}: {result['average']} "
            f"(threshold: {result['threshold']}, samples: {result['count']})"
        )

    message_lines.append("")
    message_lines.append(f"Aggregation strategy: {aggregation}")

    if overall_passed:
        message_lines.append("✅ All quality gates passed!")
    else:
        message_lines.append("❌ Quality gates failed - some metrics below threshold")

    return overall_passed, "\n".join(message_lines)


def main():
    """Main entry point."""
    # Parse arguments
    results_file = None
    config_file = ".github/evaluation-config.json"

    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--config" and i + 1 < len(sys.argv) - 1:
            config_file = sys.argv[i + 2]
        elif not arg.startswith("--"):
            results_file = arg

    # Try environment variable if not provided as argument
    if not results_file:
        results_file = os.environ.get("RESULTS_FILE", "data/evaluation_results.jsonl")

    # Load config and results
    config = load_config(config_file)
    results = load_results(results_file)

    if not results:
        print("⚠️ No evaluation results found")
        print("::set-output name=passed::false")
        print("::set-output name=message::No evaluation results available")
        sys.exit(0)

    # Extract and check scores
    scores = extract_scores(results)
    passed, message = check_thresholds(scores, config)

    # Print results
    print(message)
    print("")
    print("Details:")
    print(f"  Groundedness: {scores['groundedness']['count']} samples, avg={scores['groundedness']['average']:.2f}")
    print(f"  Relevance: {scores['relevance']['count']} samples, avg={scores['relevance']['average']:.2f}")

    # Set GitHub output
    print(f"::set-output name=passed::{str(passed).lower()}")
    print(f"::set-output name=message::{message}")

    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
