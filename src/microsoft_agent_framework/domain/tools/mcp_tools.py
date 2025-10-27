from agent_framework import MCPStdioTool


async def get_search_mcp():
    """Create and return Brave Search MCP tool"""
    return MCPStdioTool(
        name="brave_search",
        command="npx",
        args=["-y", "@modelcontextprotocol/server-brave-search"],
    )


async def get_gmail_mcp():
    """Create and return Gmail MCP tool"""
    return MCPStdioTool(name="gmail", command="npx", args=["-y", "claudepost-mcp-server"])
