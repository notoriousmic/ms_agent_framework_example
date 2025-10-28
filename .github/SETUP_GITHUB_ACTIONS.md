# GitHub Actions CI/CD Setup Guide

This guide explains how to configure GitHub Actions to run tests and evaluation on your repository.

## Required GitHub Secrets

To enable the CI/CD pipelines, add the following secrets to your GitHub repository:

### 1. Go to Repository Settings
- Navigate to **Settings** → **Secrets and variables** → **Actions**
- Click **New repository secret**

### 2. Add the Following Secrets

#### Azure OpenAI Configuration (Required)

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AZURE_OPENAI_API_KEY` | Your Azure OpenAI API key | `sk-...` |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL | `https://your-resource.openai.azure.com/` |
| `AZURE_OPENAI_API_VERSION` | API version (must be 2025-03-01-preview or later) | `2025-03-01-preview` |
| `AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME` | Deployment name for GPT model | `gpt-4o-deployment` |

**Where to find these:**
- Azure Portal → Cognitive Services resource → Keys and Endpoint
- Note: The API Key is one of the two keys shown (Key 1 or Key 2)

#### Azure AI Foundry Configuration (Required for Evaluation)

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `AZURE_AI_PROJECT_ENDPOINT` | Azure AI Foundry project endpoint | `https://your-resource.services.ai.azure.com/api/projects/your-project-id` |
| `AZURE_AI_MODEL_DEPLOYMENT_NAME` | Model deployment name for agents | `gpt-4o-deployment` |
| `AZURE_TENANT_ID` | The tenant ID the ai foundry resides in | `ID` |
| `AZURE_CLIENT_SECRET` | Secret used for pipeline authentication to ai foundry to upload evaluation | `CLIENT_SECRET` |
| `AZURE_CLIENT_ID` | User ID related to the role used for pipeline authentication in order to ai foundry to upload evaluation | `CLIENT_SECRET` |

**Where to find these:**
- Azure AI Foundry Portal → Your Project → Settings → Project details
- Copy the full project endpoint URL from "Project connection string"

#### Observability Configuration (Optional but Recommended)

| Secret Name | Description |
|-------------|-------------|
| `APPLICATIONINSIGHTS_CONNECTION_STRING` | Application Insights connection string for tracing |

**Where to find this:**
- Azure Portal → Application Insights resource → Properties → Connection String

#### External Tools (Optional)

| Secret Name | Description |
|-------------|-------------|
| `BRAVE_API_KEY` | Brave Search API key for research agent |

**Where to get this:**
- https://api.search.brave.com - Sign up and get your API key

## Workflows Overview

### 1. Test Workflow (`test.yml`)

**Triggers:**
- On push to `main` or `master` branches
- On pull requests to `main` or `master` branches

**Steps:**
1. Install Python 3.11, 3.12, and 3.13 (matrix strategy)
2. Install project dependencies with `uv`
3. Lint code with Ruff
4. Run unit tests with pytest

**Status Badge:**
Add to your README.md:
```markdown
[![Test Agent API](https://github.com/YOUR_USERNAME/ms_agent_framework/actions/workflows/test.yml/badge.svg)](https://github.com/YOUR_USERNAME/ms_agent_framework/actions)
```

### 2. Evaluation Workflow (`evaluation.yml`)

**Triggers:**
- On push to `main` or `master` branches
- Daily schedule (2 AM UTC)
- Manual trigger via GitHub Actions UI

**Steps:**
1. Install Python 3.12 with latest dependencies
2. Run multi-agent system evaluation:
   - Processes 10 test queries through supervisor agent
   - Delegates to research and writer agents as needed
   - Submits results to Azure AI Foundry cloud evaluation
3. **Check Evaluation Scores** against configured quality gates:
   - Compares Groundedness and Relevance scores to minimum thresholds
   - Default: 50% minimum score (configurable)
   - Posts GitHub status check (pass/fail)
4. Upload evaluation results as artifact
5. Comment on PR with evaluation summary and quality gate status

**What Gets Evaluated:**
- **Queries**: 10 diverse test queries covering writing, research, and general tasks
- **Metrics**: Groundedness and Relevance from Azure AI Foundry
- **Quality Gates**: Minimum score thresholds enforced per configuration
- **Results**: Stored in Azure AI Foundry portal for analysis

**Quality Gates Configuration:**
- Configured in `.github/evaluation-config.json`
- Default: Groundedness ≥ 50%, Relevance ≥ 50%
- Fully customizable - adjust thresholds per your requirements
- See [Evaluation Quality Gates Guide](./EVALUATION_QUALITY_GATES.md) for details

**View Results:**
- GitHub Actions → Evaluation workflow → Check step logs for score details
- GitHub PR → Quality gate status shown as workflow check
- Azure AI Foundry Portal → Your Project → Evaluation tab

## Security Considerations

### Secret Management Best Practices

1. **Never commit secrets** to the repository
2. **Use GitHub's built-in secrets** for sensitive values
3. **Rotate API keys** periodically
4. **Use least privilege** - only grant necessary permissions
5. **Audit secret access** in GitHub Activity Log

### Workflow Security

- Workflows can only access secrets that are explicitly referenced
- `ENABLE_SENSITIVE_DATA=false` in evaluation workflow to avoid logging sensitive information
- Evaluation results are artifacts available to repository maintainers only

## Troubleshooting

### "Warning: Unable to process image" when viewing workflow

This is a display issue, not a failure. The workflow succeeded; GitHub just had trouble rendering the badge.

### Secrets Not Found Error

1. Verify all required secrets are added in Settings → Secrets
2. Check secret names exactly match the workflow file
3. Secrets are case-sensitive

### Evaluation Fails with "Azure AI Foundry is not configured"

Missing `AZURE_AI_PROJECT_ENDPOINT` or `AZURE_AI_MODEL_DEPLOYMENT_NAME` secrets. Add them and retry.

### Tests Pass but Evaluation Skipped

This can happen if the evaluation workflow is disabled. Enable it in:
- Settings → Actions → General → Workflow permissions → Select "Read and write permissions"

### Quality Gates Failed

If evaluation scores are below thresholds:

1. Check the "Check Evaluation Scores Against Quality Gates" step in workflow logs
2. See detailed score breakdown (groundedness, relevance averages)
3. Either:
   - Lower thresholds in `.github/evaluation-config.json`
   - Improve agent responses to increase scores
   - See [Evaluation Quality Gates Guide](./EVALUATION_QUALITY_GATES.md)

### How to Adjust Quality Gate Thresholds

1. Edit `.github/evaluation-config.json`
2. Modify `min_score` values under metrics:
   ```json
   "groundedness": {
     "min_score": 0.6  // Changed from 0.5 to 0.6
   }
   ```
3. Commit and push - next evaluation will use new thresholds

## Cost Considerations

- **Test Workflow**: Runs on every push/PR (free tier includes 2,000 minutes/month)
- **Evaluation Workflow**: Runs on main branch push and daily schedule
  - Evaluation uses Azure OpenAI API calls (incurs Azure costs)
  - Consider limiting frequency or running on-demand only
  - Daily schedule can be disabled by editing `evaluation.yml`

## Advanced Configuration

### Running Evaluation Only for Specific Events

Edit `evaluation.yml` to trigger only on-demand:

```yaml
on:
  workflow_dispatch:  # Only manual trigger
```

### Disabling Daily Evaluation

Remove or comment out the schedule section:

```yaml
# schedule:
#   - cron: '0 2 * * *'
```

### Custom Evaluation Queries

Edit `data/qr_data.jsonl` to add or modify test queries:

```jsonl
{"query": "Your custom query here", "response": "Expected response"}
```

## Next Steps

1. ✅ Add all required secrets to GitHub
2. ✅ Push to main branch to trigger test workflow
3. ✅ Monitor workflow results in Actions tab
4. ✅ Check evaluation results in Azure AI Foundry portal
5. ✅ Configure optional notifications or integrations

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Azure OpenAI Documentation](https://learn.microsoft.com/en-us/azure/ai-services/openai/)
- [Azure AI Foundry Documentation](https://learn.microsoft.com/en-us/azure/ai-studio/)
- [Project README](../README.md)
