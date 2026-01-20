async def search_user_documents(query: str) -> str:
    """Uses similarity search to retrieve chunks of the user's documents to help answer a query.
    Only use this tool to search information relevant to the query.
    Do not use it to engage in casual conversation.
    Args:
        query:str
            A query written by you to answer the user's query.
    Returns:
        chunks: str
            The found document chunks with their source filenames that will help answer the query.
    """
    logger.debug("retrieve_context called", query=query[:100])
    bind_contextvars(rag_query=query[:100])

    if docs_vector_store.is_empty:
        logger.debug("vector store is empty")
        bind_contextvars(vector_store_empty=True)
        return "The document vector store is currently empty. Notify the user and suggest to upload documents."

    logger.debug("performing similarity search")
    retrieved_docs = await docs_vector_store.similarity_search(query, k=4)
    logger.debug("retrieved documents", count=len(retrieved_docs))

    sources: list[str] = []
    serialized_docs: list[str] = []
    for doc in retrieved_docs:
        source_filename: str = doc.metadata.get("source", "unknown").split("/")[-1]
        sources.append(source_filename)
        logger.debug(
            "document retrieved",
            source=source_filename,
            preview=doc.page_content[:100],
        )
        serialized_docs.append(
            f"Source: {source_filename}\nContent: {doc.page_content}"
        )

    bind_contextvars(documents_retrieved=len(retrieved_docs), document_sources=sources)
    return "\n\n".join(serialized_docs)


async def search_boletin_oficial(query: str) -> str:
    """Uses similarity search to retrieve relevant Boletin Oficial chunks.
    Only use this tool to search information relevant to the query.
    Do not use it to engage in casual conversation.
    Args:
        query:str
            A query written by you to answer the user's query about Boletin Oficial statements.
    Returns:
        chunks: str
            The found Boletin Oficial chunks with their source that will help answer the query.
    """
    logger.debug("retrieve_context called", bo_query=query[:100])
    bind_contextvars(bo_query=query[:100])

    logger.debug("performing similarity search")
    retrieved_docs = await bo_vector_store.similarity_search(query, k=4)
    logger.debug("retrieved documents", count=len(retrieved_docs))

    sources: list[str] = []
    serialized_docs: list[str] = []
    for doc in retrieved_docs:
        source_filename: str = doc.metadata.get("source", "unknown").split("/")[-1]
        sources.append(source_filename)
        logger.debug(
            "document retrieved",
            source=source_filename,
            preview=doc.page_content[:100],
        )
        serialized_docs.append(
            f"Source: {source_filename}\nContent: {doc.page_content}"
        )

    bind_contextvars(documents_retrieved=len(retrieved_docs), document_sources=sources)
    return "\n\n".join(serialized_docs)
