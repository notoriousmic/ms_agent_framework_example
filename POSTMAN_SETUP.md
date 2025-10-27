# Postman Collection Setup Guide

This guide will help you import and use the Postman collection for the Microsoft Agent Framework API.

## Prerequisites

- [Postman](https://www.postman.com/downloads/) (version 9.0 or higher)
- Microsoft Agent Framework API running (see README.md for setup instructions)

## Setup Instructions

### 1. Import the Collection

**Method A: Direct Import**
1. Open Postman
2. Click **Import** in the top-left corner
3. Select **File** tab
4. Click **Upload Files**
5. Navigate to `Microsoft_Agent_Framework.postman_collection.json` and select it
6. Click **Import**

**Method B: Folder Drag & Drop**
1. Open Postman
2. Drag and drop `Microsoft_Agent_Framework.postman_collection.json` into Postman

### 2. Configure Environment Variables

The collection uses variables that need to be set:

#### Option A: Set Variables Directly in Requests
1. Click on a request in the collection
2. In the URL bar, replace `{{base_url}}` with your actual API URL
3. Replace `{{thread_id}}` with actual thread ID from responses

#### Option B: Create a Postman Environment (Recommended)
1. Click **Environments** in the left sidebar
2. Click **Create Environment**
3. Name it "Microsoft Agent Framework" (or your preference)
4. Add the following variables:

| Variable | Initial Value | Current Value |
|----------|---------------|---------------|
| `base_url` | `http://localhost:8000` | `http://localhost:8000` |
| `thread_id` | `` | (will be set from responses) |

5. Click **Save**
6. Make sure the environment is selected in the top-right corner of Postman

### 3. Start the API

Run the API server:

```bash
uv run python -m microsoft_agent_framework.infrastructure.api.main
```

The API will be available at `http://localhost:8000`

## Agent Architecture

The framework uses a **supervisor-worker pattern**:

```
Supervisor Agent (registered with API)
├── Research Agent (internal, delegated)
├── Writer Agent (internal, delegated)
```

- **Supervisor Agent**: Handles coordination and decides when to delegate tasks
- **Research Agent**: Handles research queries using web search
- **Writer Agent**: Handles writing tasks like drafting emails

When you send a message to the supervisor, it automatically decides whether to:
- Answer directly
- Delegate to Research Agent (for queries requiring web research)
- Delegate to Writer Agent (for writing tasks)
- Or use multiple agents in sequence

## Endpoint Organization

The collection is organized into folders:

### **Health & Info**
- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint

### **Agents**
- `GET /agents` - List all registered agents (only Supervisor appears here; Research and Writer are internal)

### **Chat**
- `POST /chat` - Basic chat (Supervisor automatically delegates as needed)
  - Example: "Research quantum computing" → delegates to Research Agent
  - Example: "Write an email about..." → delegates to Writer Agent
  - Example: "What is AI?" → answers directly
- `POST /chat/smart` - Smart chat with automatic thread management
- `POST /chat/thread` - Chat with explicit thread creation

### **Threads**
- `POST /threads` - Create a new conversation thread
- `GET /threads` - List conversation threads (with filtering)
- `GET /threads/{thread_id}` - Get specific thread details
- `POST /threads/{thread_id}/chat` - Continue conversation in existing thread
- `DELETE /threads/{thread_id}` - Delete a thread

### **Session Management**
- `GET /session` - Get current session information
- `POST /session/clear` - Clear session for specific agent type
- `POST /conversation/new` - Start a new conversation

### **Utilities (Placeholders)**
- `POST /eval` - Evaluation endpoint
- `POST /ingest-documents` - Document ingestion
- `POST /reset-memory` - Reset agent memory

## Usage Examples

### Example 1: Test Agent Delegation

Try these different types of queries to see the supervisor delegate to sub-agents:

**Research Task (delegates to Research Agent):**
```json
{
  "message": "What are the latest developments in artificial intelligence?"
}
```

**Writing Task (delegates to Writer Agent):**
```json
{
  "message": "Write a professional email apologizing for a delayed response and proposing a meeting time."
}
```

**General Query (supervisor answers directly):**
```json
{
  "message": "What is the difference between machine learning and deep learning?"
}
```

**Steps:**
1. Select **Chat > Basic Chat - Research Task** (or any variant)
2. Click **Send**
3. Observe how the supervisor agent processes the request and may delegate to Research or Writer agents
4. Check the response to see which agent handled the task

### Example 2: Basic Chat

1. Select **Chat > Basic Chat**
2. Update the message in the request body
3. Click **Send**
4. View the response in the bottom panel

### Example 3: Create and Continue a Thread

1. Select **Threads > Create Thread**
2. Update the agent name and title if needed
3. Click **Send**
4. Copy the `thread_id` from the response
5. Set the `thread_id` environment variable with this value
6. Select **Threads > Get Thread by ID**
7. Click **Send** to view thread details
8. Select **Threads > Continue Thread Chat**
9. Update the message
10. Click **Send** to continue the conversation

### Example 3: List Threads with Filters

1. Select **Threads > List Threads**
2. Modify query parameters as needed:
   - `agent_type`: Filter by agent type (e.g., "supervisor")
   - `limit`: Number of threads to return (default: 10)
   - `offset`: Pagination offset (default: 0)
3. Click **Send**

## Tips & Best Practices

### Storing Thread IDs
After creating a thread or getting a response with `thread_id`, you can automatically set the environment variable:

1. Go to the request that returns a `thread_id`
2. Click on the **Tests** tab
3. Add this script:
```javascript
if (pm.response.code === 200) {
    let response = pm.response.json();
    pm.environment.set("thread_id", response.thread_id);
}
```
4. Now when you send the request, the `thread_id` will be automatically saved

### Working with Smart Chat
The smart chat endpoint (`/chat/smart`) automatically manages threads:
- Set `force_new: false` to continue existing conversations
- Set `force_new: true` to always create a new thread
- Set `save_conversation: true` to persist the conversation

### Debugging
- Use Postman's **Console** (bottom left) to view request/response details
- Check the **Network** tab to see raw HTTP data
- Use **Pre-request Script** tabs to set up data before requests

## Common Issues

**Issue: "Module not found" error when running API**
- Make sure you're in the project root directory
- Run `uv sync` to install dependencies
- Ensure Python 3.11+ is installed

**Issue: Connection refused**
- Verify the API is running on the correct port (default: 8000)
- Check the `base_url` variable is set correctly
- Ensure no firewall is blocking the connection

**Issue: {{variable}} shows in request URL**
- Select the correct environment in the top-right corner of Postman
- Verify the variable is defined in that environment

## API Documentation

For detailed API documentation, visit:
```
http://localhost:8000/docs
```

This opens an interactive Swagger UI where you can test endpoints directly in your browser.

## Support

For issues or questions:
1. Check the main README.md for project setup
2. Review the API code in `src/microsoft_agent_framework/infrastructure/api/main.py`
3. Check Postman console for error details
