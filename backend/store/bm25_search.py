"""
BM25 Keyword Search Module
Uses BM25 for fast keyword-based retrieval alongside semantic search.
Combines lexical and semantic matching for better coverage.
"""

from rank_bm25 import BM25Okapi
from typing import Optional
import pickle
import os

_bm25_model = None
_documents = []
_chunk_ids = []

def initialize_bm25(chunks: list[dict]):
    """
    Build BM25 index from chunks.
    Called after indexing workspace.
    
    Args:
        chunks: List of chunks with 'id' and 'content' keys
    """
    global _bm25_model, _documents, _chunk_ids
    
    # Tokenize documents
    corpus = [chunk["content"].lower().split() for chunk in chunks]
    
    _bm25_model = BM25Okapi(corpus)
    _documents = [chunk["content"] for chunk in chunks]
    _chunk_ids = [chunk["id"] for chunk in chunks]
    
    print(f"BM25 index initialized with {len(chunks)} documents")

def keyword_search(
    query: str,
    chunks_db: dict,
    n_results: int = 15
) -> list[dict]:
    """
    Search using BM25 keyword matching.
    Fast lexical search complementary to semantic search.
    
    Args:
        query: Search query (natural language or keywords)
        chunks_db: Dict mapping chunk_id to chunk data (from ChromaDB)
        n_results: Number of results to return
        
    Returns:
        list[dict]: Chunks with 'bm25_score' added
        
    Example:
        >>> results = keyword_search("authentication database error", chunks_db)
        >>> for r in results:
        ...     print(r["bm25_score"])
        42.5
        38.2
        35.1
    """
    if not _bm25_model or not _documents:
        return []
    
    # Tokenize query
    query_tokens = query.lower().split()
    
    # Get scores
    scores = _bm25_model.get_scores(query_tokens)
    
    # Get top indices
    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:n_results]
    
    results = []
    for idx in top_indices:
        if scores[idx] > 0:  # Only include if score > 0
            chunk_id = _chunk_ids[idx]
            if chunk_id in chunks_db:
                chunk = chunks_db[chunk_id].copy()
                chunk["bm25_score"] = float(scores[idx])
                results.append(chunk)
    
    return results

def save_bm25_index(filepath: str = "./store/bm25_index.pkl"):
    """
    Save BM25 index to disk for persistence.
    
    Args:
        filepath: Path to save index
    """
    global _bm25_model, _documents, _chunk_ids
    
    if _bm25_model is None:
        return
    
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    
    data = {
        "model": _bm25_model,
        "documents": _documents,
        "chunk_ids": _chunk_ids
    }
    
    with open(filepath, "wb") as f:
        pickle.dump(data, f)
    
    print(f"BM25 index saved to {filepath}")

def load_bm25_index(filepath: str = "./store/bm25_index.pkl") -> bool:
    """
    Load BM25 index from disk.
    
    Args:
        filepath: Path to load index from
        
    Returns:
        bool: True if loaded successfully
    """
    global _bm25_model, _documents, _chunk_ids
    
    if not os.path.exists(filepath):
        return False
    
    try:
        with open(filepath, "rb") as f:
            data = pickle.load(f)
        
        _bm25_model = data["model"]
        _documents = data["documents"]
        _chunk_ids = data["chunk_ids"]
        
        print(f"BM25 index loaded from {filepath} ({len(_chunk_ids)} chunks)")
        return True
    except Exception as e:
        print(f"Error loading BM25 index: {e}")
        return False

def hybrid_keyword_semantic(
    semantic_chunks: list[dict],
    keyword_chunks: list[dict]
) -> list[dict]:
    """
    Combine semantic and keyword search results.
    Removes duplicates, keeps higher score.
    
    Args:
        semantic_chunks: Results from semantic_search()
        keyword_chunks: Results from keyword_search()
        
    Returns:
        list[dict]: Combined chunks with both scores
    """
    combined = {}
    
    # Add semantic results
    for chunk in semantic_chunks:
        chunk_id = chunk["id"]
        combined[chunk_id] = {
            **chunk,
            "semantic_score": chunk.get("rerank_score", 0),
            "keyword_score": 0
        }
    
    # Add keyword results
    for chunk in keyword_chunks:
        chunk_id = chunk["id"]
        if chunk_id in combined:
            combined[chunk_id]["keyword_score"] = chunk.get("bm25_score", 0)
        else:
            combined[chunk_id] = {
                **chunk,
                "semantic_score": 0,
                "keyword_score": chunk.get("bm25_score", 0)
            }
    
    return list(combined.values())
