# Evaluation Quality Gates Configuration Guide

This guide explains how to configure and customize evaluation quality gates for the CI/CD pipeline.

## Overview

Quality gates are automated checks that ensure evaluation scores meet minimum thresholds before PRs can be merged. They provide:

- **Automated quality enforcement** - Scores automatically checked against thresholds
- **Customizable targets** - Set your own minimum acceptable scores
- **Visual feedback** - GitHub status checks and PR comments show quality gate status
- **Flexibility** - Enable/disable gates or individual metrics as needed

## Configuration File

The quality gate configuration is stored in `.github/evaluation-config.json`:

```json
{
  "evaluation": {
    "quality_gates": {
      "enabled": true,
      "metrics": {
        "groundedness": {
          "enabled": true,
          "min_score": 0.5
        },
        "relevance": {
          "enabled": true,
          "min_score": 0.5
        }
      },
      "aggregation": "average"
    }
  }
}
```

## Score Ranges

All scores range from **0.0 to 1.0**:
- `0.0` - No evaluation data or completely fails metric
- `0.5` - 50% (default threshold)
- `1.0` - Perfect score

## Configuration Options

### `quality_gates.enabled`

**Type**: `boolean`
**Default**: `true`

Enable or disable quality gates entirely. When disabled, evaluations run but don't block PRs.

```json
"enabled": false  // Quality gates won't block PRs
```

### `metrics.<metric_name>.enabled`

**Type**: `boolean`
**Default**: `true`

Enable/disable individual metrics. Disabled metrics are skipped in quality checks.

```json
"groundedness": {
  "enabled": false  // Groundedness won't be checked
}
```

### `metrics.<metric_name>.min_score`

**Type**: `number` (0.0 to 1.0)
**Default**: `0.5`

Minimum acceptable score for a metric. The evaluation average must meet or exceed this threshold.

```json
"relevance": {
  "min_score": 0.7  // Require 70% or higher relevance
}
```

### `aggregation`

**Type**: `string` - One of: `"average"`, `"any"`, `"all"`
**Default**: `"average"`

How to combine multiple metrics:

#### `"average"` (Default - Most Balanced)
All enabled metrics must meet their thresholds.

```
Example: With groundedness=0.5 and relevance=0.5
- ✅ PASS: groundedness=0.7, relevance=0.6 (both meet thresholds)
- ❌ FAIL: groundedness=0.4, relevance=0.6 (groundedness too low)
```

#### `"any"` (Most Permissive)
At least one enabled metric must meet its threshold.

```
Example: With groundedness=0.5 and relevance=0.5
- ✅ PASS: groundedness=0.4, relevance=0.6 (relevance meets threshold)
- ❌ FAIL: groundedness=0.3, relevance=0.4 (neither meets threshold)
```

#### `"all"` (Most Strict)
All enabled metrics must meet their thresholds (same as "average" but stricter interpretation).

```
Example: With groundedness=0.5 and relevance=0.5
- ✅ PASS: groundedness=0.7, relevance=0.6 (both exceed thresholds)
- ❌ FAIL: groundedness=0.5, relevance=0.4 (relevance at threshold)
```

## Configuration Examples

### Example 1: Strict Quality Requirements

Require high scores for critical metrics:

```json
{
  "evaluation": {
    "quality_gates": {
      "enabled": true,
      "metrics": {
        "groundedness": {
          "enabled": true,
          "min_score": 0.8
        },
        "relevance": {
          "enabled": true,
          "min_score": 0.85
        }
      },
      "aggregation": "all"
    }
  }
}
```

### Example 2: Lenient Quality Requirements

Lower threshold for faster iteration:

```json
{
  "evaluation": {
    "quality_gates": {
      "enabled": true,
      "metrics": {
        "groundedness": {
          "enabled": true,
          "min_score": 0.3
        },
        "relevance": {
          "enabled": true,
          "min_score": 0.3
        }
      },
      "aggregation": "any"
    }
  }
}
```

### Example 3: Disable Quality Gates

Run evaluation without blocking PRs:

```json
{
  "evaluation": {
    "quality_gates": {
      "enabled": false
    }
  }
}
```

### Example 4: Check Only Relevance

Only evaluate relevance, ignore groundedness:

```json
{
  "evaluation": {
    "quality_gates": {
      "enabled": true,
      "metrics": {
        "groundedness": {
          "enabled": false
        },
        "relevance": {
          "enabled": true,
          "min_score": 0.6
        }
      },
      "aggregation": "average"
    }
  }
}
```

## How It Works in CI/CD

When a PR is created:

1. **Evaluation runs** - 10 test queries run through the multi-agent system
2. **Scores collected** - Azure AI Foundry computes Groundedness and Relevance
3. **Quality check** - `.github/scripts/check_evaluation_scores.py` compares scores to thresholds
4. **Status posted** - GitHub status check shows pass/fail
5. **PR comment** - Comment shows quality gate status and configuration link

### Quality Gate Status in PR

You'll see a comment like:

```
## 📊 Multi-Agent System Evaluation Results

Total Queries Evaluated: 10
Quality Gate Status: ✅ PASSED - All quality gates met

...

Quality Gate Details
See the "Check Evaluation Scores Against Quality Gates" step in the workflow logs for detailed score breakdowns.
```

### GitHub Status Check

A status check appears on your PR:
- ✅ **Quality Gate Check / Evaluation** - All thresholds met
- ❌ **Quality Gate Check / Evaluation** - Some thresholds not met

## Modifying Configuration

### Step 1: Edit `.github/evaluation-config.json`

```bash
# Edit the config file
nano .github/evaluation-config.json

# Or use your editor
code .github/evaluation-config.json
```

### Step 2: Adjust Thresholds

```json
{
  "evaluation": {
    "quality_gates": {
      "metrics": {
        "groundedness": {
          "min_score": 0.65  // Changed from 0.5 to 0.65
        },
        "relevance": {
          "min_score": 0.65  // Changed from 0.5 to 0.65
        }
      }
    }
  }
}
```

### Step 3: Commit and Push

```bash
git add .github/evaluation-config.json
git commit -m "Adjust evaluation quality gate thresholds to 65%"
git push
```

### Step 4: Next PR Will Use New Thresholds

The evaluation will automatically use your new configuration on the next PR.

## Understanding Evaluation Scores

The evaluation uses Azure AI Foundry cloud evaluators:

### Groundedness
Measures whether the agent's response is grounded in the provided context or search results.

- **High groundedness** (>0.7): Response closely follows provided information
- **Medium groundedness** (0.4-0.7): Response uses some provided information
- **Low groundedness** (<0.4): Response not based on provided context

### Relevance
Measures how relevant the response is to the query.

- **High relevance** (>0.7): Response directly addresses the query
- **Medium relevance** (0.4-0.7): Response partially addresses the query
- **Low relevance** (<0.4): Response doesn't address the query

## Troubleshooting

### Quality gates failed but I don't see details

1. Go to the workflow run in GitHub Actions
2. Expand "Check Evaluation Scores Against Quality Gates" step
3. View detailed score breakdown

### I want to disable quality gates temporarily

Edit `.github/evaluation-config.json`:

```json
"enabled": false
```

Quality gates won't block PRs, but evaluation still runs.

### The thresholds are too strict

Lower the `min_score` values:

```json
"groundedness": {
  "min_score": 0.3  // Reduced from 0.5
}
```

### The thresholds are too lenient

Increase the `min_score` values:

```json
"relevance": {
  "min_score": 0.8  // Increased from 0.5
}
```

## Best Practices

1. **Start lenient** - Begin with 0.4-0.5 thresholds and increase over time
2. **Iterate gradually** - Raise thresholds 0.05-0.10 at a time
3. **Monitor trends** - Check daily evaluation runs to see if thresholds are realistic
4. **Use aggregation wisely**:
   - Use `"average"` for most balanced approach
   - Use `"any"` for fast iteration
   - Use `"all"` for strict quality requirements

## Related Documentation

- [GitHub Actions Setup Guide](./SETUP_GITHUB_ACTIONS.md)
- [README - CI/CD Pipeline](../README.md#cicd-pipeline)
- [Evaluation Configuration Script](.github/scripts/check_evaluation_scores.py)
