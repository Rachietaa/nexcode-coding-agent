import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from config.settings import TAVILY_API_KEY

RAG_SERVER_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "rag_server", "server.py")
)


def build_mcp_client(workspace_path: str) -> MultiServerMCPClient:
    """
    Connects to all 3 required MCP servers:
    1. filesystem  — read/write/list local files
    2. tavily      — web search (external resource)
    3. rag         — custom local vector DB with HyDE
    """
    return MultiServerMCPClient(
        {
            # Server 1: Official Filesystem MCP Server
            "filesystem": {
                "transport": "stdio",
                "command": "npx",
                "args": [
                    "-y",
                    "@modelcontextprotocol/server-filesystem",
                    workspace_path,
                ],
            },

            # Server 2: Tavily Web Search
            "tavily": {
                "transport": "stdio",
                "command": "npx",
                "args": ["-y", "tavily-mcp@0.1.4"],
                "env": {
                    **os.environ,
                    "TAVILY_API_KEY": TAVILY_API_KEY or "",
                },
            },

            # Server 3: Custom RAG MCP Server
            "rag": {
                "transport": "stdio",
                "command": "python",
                "args": [RAG_SERVER_PATH],
            },
        }
    )
