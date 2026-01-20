from pathlib import Path

from anyio import to_thread
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_community import BigQueryVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pymupdf4llm import PyMuPDF4LLMLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings


class DocsVectorStore:
    def __init__(self, embeddings=None, store=None) -> None:
        self.embeddings = embeddings or GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            api_key=settings.GEMINI_API_KEY,
        )

        self.store: Chroma = store or Chroma(
            collection_name="collection",
            embedding_function=self.embeddings,
            persist_directory=settings.VECTOR_DB_PATH,
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            add_start_index=True,
        )

    @staticmethod
    async def aload_pdf(file_path: Path):
        loader = PyMuPDF4LLMLoader(
            file_path,
            mode="single",
            table_strategy="lines",
        )
        return await loader.aload()

    @property
    def is_empty(self) -> bool:
        if self.store.get()["ids"]:
            return False
        return True

    async def process_pdf(self, file_path: Path) -> None:
        docs: list[Document] = await self.aload_pdf(file_path)
        all_splits: list[Document] = self.text_splitter.split_documents(docs)
        await self.store.aadd_documents(documents=all_splits)

    async def similarity_search(self, *args, **kwargs) -> list[Document]:
        return await to_thread.run_sync(self.store.similarity_search(*args, **kwargs))

    def delete_all_docs(self) -> None:
        self.store.delete_collection()


class BOVectorStore:
    def __init__(self, embeddings=None, store=None) -> None:
        self.embeddings = embeddings or GoogleGenerativeAIEmbeddings(
            model="models/gemini-embedding-001",
            api_key=settings.GEMINI_API_KEY,
            project=settings.GCP_PROJECT_ID,
            dimensions=settings.EMBEDDING_DIM,
        )

        self.store = store or BigQueryVectorStore(
            project_id=settings.GCP_PROJECT_ID,
            dataset_name=settings.BQ_DATASET_NAME,
            table_name=settings.BQ_TABLE_NAME,
            location=settings.BQ_DATASET_LOCATION,
            embedding=embeddings,
            content_field="content",
            embedding_field="ml_generate_embedding_result",
            embedding_dimension=settings.EMBEDDING_DIM,
        )

    async def similarity_search(self, *args, **kwargs) -> list[Document]:
        return await to_thread.run_sync(self.store.similarity_search(*args, **kwargs))


docs_vector_store = DocsVectorStore()
bo_vector_store = BOVectorStore()
