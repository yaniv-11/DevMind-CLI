"""
Reranking module using cross-encoders for better relevance scoring.
Rerankers are more accurate than embeddings at measuring query-document relevance.
"""

from sentence_transformers import CrossEncoder
import numpy as np

_reranker = None

def get_reranker_model():
    """Load BGE reranker (best for code/technical content)."""
    global _reranker
    if _reranker is None:
        print("Loading BAAI/bge-reranker-base for reranking (first time only)...")
        _reranker = CrossEncoder("BAAI/bge-reranker-base", max_length=512)
    return _reranker

def rerank_chunks(query: str, chunks: list[dict], top_k: int = None) -> list[dict]:
    """
    Rerank chunks using cross-encoder for better relevance.
    
    Args:
        query: The search query
        chunks: List of dicts with 'content' and other metadata
        top_k: Optional limit on number of chunks to return
        
    Returns:
        Reranked list of chunks with 'rerank_score' added
    """
    if not chunks:
        return []
    
    reranker = get_reranker_model()
    
    # Prepare pairs for reranking
    pairs = [[query, chunk["content"]] for chunk in chunks]
    
    # Get rerank scores
    scores = reranker.predict(pairs)
    
    # Add scores to chunks
    for i, chunk in enumerate(chunks):
        chunk["rerank_score"] = float(scores[i])
    
    # Sort by rerank score descending
    ranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
    
    # Return top_k if specified
    if top_k:
        ranked = ranked[:top_k]
    
    return ranked

def rerank_and_deduplicate(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """
    Rerank chunks and deduplicate by file location.
    Ensures diversity in retrieved results.
    
    Args:
        query: The search query
        chunks: List of chunks with 'content' and 'file' in metadata
        top_k: Number of chunks to return after deduplication
        
    Returns:
        Deduplicated and reranked chunks
    """
    if not chunks:
        return []
    
    # Rerank all chunks
    ranked = rerank_chunks(query, chunks)
    
    # Deduplicate by file while maintaining top_k
    seen_files = set()
    result = []
    
    for chunk in ranked:
        file_key = chunk.get("metadata", {}).get("file", chunk.get("file", "unknown"))
        
        if file_key not in seen_files:
            seen_files.add(file_key)
            result.append(chunk)
            
            if len(result) >= top_k:
                break
    
    return result
