"""
Hybrid RAG System with Semantic + Keyword Search
Combines AllMiniLM semantic search with BM25 keyword search.
Normalizes scores and reranks for top 10-15 chunks.
"""

from backend.store.rag_system import semantic_search
from backend.store.bm25_search import keyword_search, hybrid_keyword_semantic
from backend.store.reranker import rerank_chunks
from backend.store.chunk_extractor import create_enhanced_chunk, format_chunk_with_definitions
from backend.store.vector_store import get_collection
import numpy as np


def normalize_scores(chunks: list[dict], score_key: str) -> list[dict]:
    """
    Normalize scores to 0-1 range (min-max normalization).
    
    Args:
        chunks: List of chunks with score_key
        score_key: Key name containing scores (e.g., 'semantic_score')
        
    Returns:
        Chunks with normalized scores (0-1)
    """
    scores = [c.get(score_key, 0) for c in chunks]
    
    if not scores or max(scores) == min(scores):
        return chunks
    
    min_score = min(scores)
    max_score = max(scores)
    range_score = max_score - min_score
    
    normalized = []
    for chunk in chunks:
        score = chunk.get(score_key, 0)
        normalized_score = (score - min_score) / range_score if range_score > 0 else 0
        chunk_copy = chunk.copy()
        chunk_copy[f"{score_key}_normalized"] = normalized_score
        normalized.append(chunk_copy)
    
    return normalized


def combine_hybrid_scores(chunks: list[dict], weights: dict = None) -> list[dict]:
    """
    Combine semantic and keyword scores into hybrid score.
    
    Args:
        chunks: Combined chunks with semantic_score and keyword_score
        weights: Dict with 'semantic' and 'keyword' weights (default: 0.6, 0.4)
        
    Returns:
        Chunks with 'hybrid_score' added
    """
    if weights is None:
        weights = {"semantic": 0.6, "keyword": 0.4}
    
    # Normalize each score type
    chunks = normalize_scores(chunks, "semantic_score")
    chunks = normalize_scores(chunks, "keyword_score")
    
    # Combine
    for chunk in chunks:
        semantic = chunk.get("semantic_score_normalized", 0)
        keyword = chunk.get("keyword_score_normalized", 0)
        
        chunk["hybrid_score"] = (
            weights["semantic"] * semantic + 
            weights["keyword"] * keyword
        )
    
    return chunks


def hybrid_semantic_keyword_search(
    query: str,
    workspace_root: str = None,
    n_semantic: int = 15,
    n_keyword: int = 15,
    top_k: int = 10,
    weights: dict = None
) -> list[dict]:
    """
    Complete hybrid search: semantic + keyword with reranking.
    
    Args:
        query: Search query
        workspace_root: Path to workspace (for fallback)
        n_semantic: Initial semantic results to retrieve
        n_keyword: Initial keyword results to retrieve
        top_k: Final results to return
        weights: Score weights for combining (default: semantic=0.6, keyword=0.4)
        
    Returns:
        list[dict]: Top K chunks with metadata and scores
        
    Example:
        >>> results = hybrid_semantic_keyword_search(
        ...     "fix authentication bug",
        ...     top_k=10
        ... )
        >>> len(results)
        10
        >>> results[0]["hybrid_score"]
        0.87
    """
    if weights is None:
        weights = {"semantic": 0.6, "keyword": 0.4}
    
    semantic_chunks = []
    keyword_chunks = []
    
    try:
        # Stage 1: Semantic Search
        semantic_chunks = semantic_search(query, n_results=n_semantic)
    except Exception as e:
        print(f"Semantic search warning: {e}")
    
    try:
        # Stage 2: Keyword Search
        # Get all chunks from ChromaDB for BM25 search
        collection = get_collection()
        if collection.count() > 0:
            all_chunks = collection.get(include=["documents", "metadatas"])
            chunks_dict = {}
            
            for i, chunk_id in enumerate(all_chunks["ids"]):
                chunks_dict[chunk_id] = {
                    "id": chunk_id,
                    "content": all_chunks["documents"][i],
                    "metadata": all_chunks["metadatas"][i]
                }
            
            keyword_chunks = keyword_search(query, chunks_dict, n_results=n_keyword)
    except Exception as e:
        print(f"Keyword search warning: {e}")
    
    # Stage 3: Combine Results
    if not semantic_chunks and not keyword_chunks:
        return []
    
    combined = hybrid_keyword_semantic(semantic_chunks, keyword_chunks)
    
    # Stage 4: Normalize and Combine Scores
    combined = combine_hybrid_scores(combined, weights)
    
    # Stage 5: Rerank Combined Results
    try:
        combined = rerank_chunks(query, combined, top_k=None)
        
        # Add hybrid score to reranker score
        for chunk in combined:
            hybrid = chunk.get("hybrid_score", 0)
            rerank = chunk.get("rerank_score", 0.5)
            # Weighted combination
            chunk["final_score"] = 0.5 * rerank + 0.5 * hybrid
    except Exception as e:
        print(f"Reranking warning: {e}")
        # Fallback to hybrid score only
        for chunk in combined:
            chunk["final_score"] = chunk.get("hybrid_score", 0)
    
    # Stage 6: Sort by final score and return top_k
    final = sorted(
        combined,
        key=lambda x: x.get("final_score", 0),
        reverse=True
    )[:top_k]
    
    return final


def format_enhanced_context(chunks: list[dict], max_tokens: int = 8000) -> tuple[str, dict]:
    """
    Format chunks with function/class context and score information.
    
    Args:
        chunks: Retrieved and reranked chunks
        max_tokens: Max tokens for context
        
    Returns:
        tuple: (formatted_context, metadata)
    """
    context_parts = []
    files_included = set()
    functions_included = set()
    total_chars = 0
    char_limit = max_tokens * 4
    
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        file_path = metadata.get("file", "unknown")
        line_start = metadata.get("line_start", 1)
        line_end = metadata.get("line_end", 1)
        
        # Build header with definitions
        definitions = chunk.get("definitions", [])
        def_info = ""
        
        if definitions:
            def_names = []
            for d in definitions:
                if d["type"] == "method":
                    def_names.append(f"{d['parent']}.{d['name']}")
                    functions_included.add(f"{d['parent']}.{d['name']}")
                else:
                    def_names.append(d["name"])
                    functions_included.add(d["name"])
            
            if def_names:
                def_info = f" | Functions: {', '.join(def_names)}"
        
        # Score info
        score_info = ""
        if "final_score" in chunk:
            score_info = f" [Score: {chunk['final_score']:.3f}]"
        elif "rerank_score" in chunk:
            score_info = f" [Score: {chunk['rerank_score']:.3f}]"
        
        header = f"## [{i}] {file_path} (L{line_start}-{line_end}){def_info}{score_info}"
        content = chunk.get("content", "")
        
        formatted_chunk = f"{header}\n```\n{content}\n```\n"
        
        if total_chars + len(formatted_chunk) > char_limit:
            break
        
        context_parts.append(formatted_chunk)
        files_included.add(file_path)
        total_chars += len(formatted_chunk)
    
    context_str = "\n".join(context_parts)
    
    metadata_info = {
        "file_count": len(files_included),
        "function_count": len(functions_included),
        "chunk_count": len(context_parts),
        "files": sorted(list(files_included)),
        "functions": sorted(list(functions_included)),
        "char_count": total_chars,
        "token_estimate": total_chars // 4
    }
    
    return context_str, metadata_info
