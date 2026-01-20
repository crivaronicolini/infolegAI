from fastmcp import FastMCP

from app.core.tools import search_boletin_oficial, search_user_documents

mcp = FastMCP("Boletin Oficial RAG")
mcp_app = mcp.http_app()


@mcp.tool()
async def tool_search_boletin_oficial(query: str) -> str:
    return await search_boletin_oficial(query)


@mcp.tool()
async def tool_search_user_documents(query: str) -> str:
    return await search_user_documents(query)
