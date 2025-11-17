from langchain.agents import create_agent
from langchain.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

from .tools import boletin_rag

llm = ChatGoogleGenerativeAI(model="gemini-flash-latest")


@tool
async def boletin_rag_tool(
    question: str,
    top_k: int = 4,
    score_threshold: float | None = None,
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


agent_system_prompt = (
    "You are a helpful legal assistant for the Argentinian Official Bulletin. "
    "Answer from your internal knowledge when possible, but if you need authoritative or up-to-date context, "
    "call the boletin_rag tool."
)

agent = create_agent(
    llm,
    [boletin_rag_tool],
    system_prompt=agent_system_prompt,
)
