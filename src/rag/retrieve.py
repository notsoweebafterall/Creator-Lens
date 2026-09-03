import chromadb

from src.config import settings
from src.rag.ingest import (
    COLLECTION_NAME,
    EMBEDDING_MODEL,
    embed_text,
)


def retrieve_guidelines(
    query: str,
    top_k: int = 3,
) -> list[dict]:
    client = chromadb.PersistentClient(
        path=str(settings.vector_store_dir)
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    query_embedding = embed_text(query)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    return [
        {
            "document": document,
            "source": metadata["source"],
            "distance": distance,
        }
        for document, metadata, distance
        in zip(documents, metadatas, distances)
    ]