from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from src.config import settings

COLLECTION_NAME = "brand_safety_guidelines"

# Load local sentence-transformer model once at module level.
# WHY: Keeps RAG pipeline fully free with no API cost or billing dependency, independent of Gemini API quota.
_embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def get_client():
    return chromadb.PersistentClient(
        path=str(settings.vector_store_dir)
    )


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME
    )


def embed_text(text: str) -> list[float]:
    """
    Generates embeddings locally using sentence-transformers (all-MiniLM-L6-v2).
    """
    return _embedding_model.encode(text).tolist()


def ingest_guidelines() -> None:
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(name=COLLECTION_NAME)

    guideline_dir = settings.guidelines_dir_path
    files = sorted(guideline_dir.glob("*.txt"))

    if not files:
        raise FileNotFoundError(
            f"No guideline files found in {guideline_dir}"
        )

    for file_path in files:
        text = file_path.read_text(encoding="utf-8").strip()

        if not text:
            continue

        embedding = embed_text(text)

        collection.upsert(
            ids=[file_path.stem],
            documents=[text],
            embeddings=[embedding],
            metadatas=[{"source": file_path.name}],
        )

        print(f"Ingested: {file_path.name}")

    print(f"Total guideline documents: {len(files)}")


if __name__ == "__main__":
    ingest_guidelines()