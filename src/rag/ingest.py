from pathlib import Path

import chromadb
from google import genai

from src.config import settings


COLLECTION_NAME = "brand_safety_guidelines"
EMBEDDING_MODEL = "gemini-embedding-2"


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
    client = genai.Client(api_key=settings.gemini_api_key)

    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text,
    )

    return response.embeddings[0].values


def ingest_guidelines() -> None:
    collection = get_collection()

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