import asyncio
from langchain_google_community import BigQueryVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from .config import DATASET_NAME, LOCATION, PROJECT_ID, TABLE_NAME


class DimensionControlledEmbeddings(GoogleGenerativeAIEmbeddings):
    """Wrapper that injects output_dimensionality into all embed calls."""

    def __init__(self, *args, dimensions: int = 768, **kwargs):
        super().__init__(*args, **kwargs)
        # Use object.__setattr__ to bypass Pydantic's validation
        object.__setattr__(self, "_dimensions", dimensions)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return super().embed_documents(texts, output_dimensionality=self._dimensions)

    def embed_query(self, text: str) -> list[float]:
        return super().embed_query(text, output_dimensionality=self._dimensions)


embedding = DimensionControlledEmbeddings(
    model="models/gemini-embedding-001",
    project=PROJECT_ID,
    dimensions=768,
)

vector_store = BigQueryVectorStore(
    project_id=PROJECT_ID,
    dataset_name=DATASET_NAME,
    table_name=TABLE_NAME,
    location=LOCATION,
    embedding=embedding,
    content_field="content",
    embedding_field="ml_generate_embedding_result",
    embedding_dimension=768,
)


async def boletin_rag(
    question: str,
    top_k: int = 4,
    score_threshold: float | None = None,
) -> str:
    search_kwargs = {"k": top_k}

    # Add score threshold if provided
    if score_threshold is not None:
        search_kwargs["score_threshold"] = score_threshold

    results = await asyncio.to_thread(
        vector_store.similarity_search, question, **search_kwargs
    )

    # Format results for better readability by the agent
    if not results:
        return "No relevant documents found in the Official Bulletin."

    formatted_results = []
    for i, doc in enumerate(results, 1):
        content = doc.page_content
        metadata = doc.metadata if hasattr(doc, "metadata") else {}

        result_str = f"Document {i}:\n{content}"
        if metadata:
            result_str += f"\nMetadata: {metadata}"
        formatted_results.append(result_str)

    return "\n\n---\n\n".join(formatted_results)
