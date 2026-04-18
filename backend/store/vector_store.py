# backend/store/vector_store.py
import os
import chromadb
from chromadb.config import Settings as ChromaSettings

_client = None
_collection = None

def get_collection():
    global _client, _collection
    if _collection is not None:
        return _collection

    os.makedirs("./store/chroma", exist_ok=True)

    _client = chromadb.PersistentClient(
        path="./store/chroma",
        settings=ChromaSettings(anonymized_telemetry=False)
    )
    _collection = _client.get_or_create_collection(
        name="devmind_codebase",
        metadata={"hnsw:space": "cosine"}
    )
    return _collection

def upsert_chunks(chunks: list[dict]):
    """
    chunks: list of {id, content, metadata}
    """
    collection = get_collection()
    collection.upsert(
        ids=[c["id"] for c in chunks],
        documents=[c["content"] for c in chunks],
        metadatas=[c.get("metadata", {}) for c in chunks]
    )

def query_chunks(query: str, n_results: int = 6) -> list[dict]:
    collection = get_collection()
    results = collection.query(
        query_texts=[query],
        n_results=n_results
    )
    if not results.get("documents") or not results["documents"][0]:
        return []

    chunks = []
    for i, doc in enumerate(results["documents"][0]):
        chunks.append({
            "content": doc,
            "metadata": results["metadatas"][0][i],
            "distance": results["distances"][0][i]
        })
    return chunks