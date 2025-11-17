from typing import Optional

from mcp import types
from mcp.server.fastmcp import FastMCP

from .tools import boletin_rag

mcp = FastMCP("Boletin Oficial RAG")


@mcp.tool()
async def boletin_rag_tool(
    question: str,
    top_k: int = 4,
    score_threshold: Optional[float] = None,
) -> str:
    """
    Search the Argentinian Official Bulletin for relevant context to answer a question.

    Use this tool when you need authoritative or up-to-date information from the Official Bulletin.

    Args:
        question: The search query or question to find relevant documents for.
        top_k: Number of most relevant documents to retrieve (default: 4).
               Use lower values (1-2) for focused, specific queries.
               Use higher values (5-10) for broader research or complex questions.
        score_threshold: Optional minimum relevance score (0.0-1.0).
                        Only return documents with similarity scores above this threshold.
                        Higher values (e.g., 0.7-0.9) return only very relevant matches.

    Returns:
        A list of relevant document excerpts from the Official Bulletin.
    """
    return await boletin_rag(
        question=question, top_k=top_k, score_threshold=score_threshold
    )


@mcp.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    List all available MCP tools with their schemas.
    
    This handler is called when a client requests the list of available tools.
    """
    return [
        types.Tool(
            name="boletin_rag_tool",
            description="Search the Argentinian Official Bulletin for relevant context to answer a question. "
                       "Use this tool when you need authoritative or up-to-date information from the Official Bulletin.",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "The search query or question to find relevant documents for.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Number of most relevant documents to retrieve (default: 4). "
                                     "Use lower values (1-2) for focused queries, higher values (5-10) for broader research.",
                        "default": 4,
                    },
                    "score_threshold": {
                        "type": "number",
                        "description": "Optional minimum relevance score (0.0-1.0). "
                                     "Only return documents with similarity scores above this threshold.",
                        "default": None,
                    },
                },
                "required": ["question"],
            },
        )
    ]
