"""
Embedding model using AllMiniLM for semantic search.
AllMiniLM provides better embeddings than default Chroma embeddings.
"""

from sentence_transformers import SentenceTransformer
import numpy as np

_model = None

def get_embedding_model():
    """Load AllMiniLM model (lightweight but high quality)."""
    global _model
    if _model is None:
        print("Loading AllMiniLM-L6-v2 embedding model (first time only)...")
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model

def embed_text(text: str) -> list[float]:
    """Embed a single text string."""
    model = get_embedding_model()
    embedding = model.encode(text, convert_to_numpy=False)
    return embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed multiple text strings efficiently."""
    model = get_embedding_model()
    embeddings = model.encode(texts, convert_to_numpy=False)
    return [e.tolist() if hasattr(e, 'tolist') else list(e) for e in embeddings]

def similarity_score(embedding1: list[float], embedding2: list[float]) -> float:
    """Calculate cosine similarity between two embeddings."""
    arr1 = np.array(embedding1)
    arr2 = np.array(embedding2)
    
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(np.dot(arr1, arr2) / (norm1 * norm2))
