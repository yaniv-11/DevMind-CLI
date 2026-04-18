"""
Improved RAG system with semantic search, reranking, and better context preparation.
"""

from backend.store.vector_store import query_chunks as chroma_query_chunks
from backend.store.reranker import rerank_and_deduplicate
from backend.store.embeddings import embed_text, similarity_score
import os

def semantic_search(query: str, n_results: int = 10) -> list[dict]:
    """
    Semantic search against indexed codebase.
    Uses ChromaDB for initial retrieval with AllMiniLM embeddings.
    
    Args:
        query: Search query
        n_results: Number of initial results to retrieve before reranking
        
    Returns:
        List of relevant code chunks with metadata and scores
    """
    # Get initial results from ChromaDB (retrieval stage)
    chunks = chroma_query_chunks(query=query, n_results=n_results)
    
    if not chunks:
        return []
    
    # Rerank and deduplicate results (ranking stage)
    reranked = rerank_and_deduplicate(query, chunks, top_k=n_results // 2)
    
    return reranked

def prepare_context_for_llm(chunks: list[dict], max_tokens: int = 8000) -> tuple[str, dict]:
    """
    Prepare retrieved chunks into a formatted context for the LLM.
    
    Args:
        chunks: List of retrieved and reranked chunks
        max_tokens: Maximum tokens for context (rough estimate: 1 token ≈ 4 chars)
        
    Returns:
        Tuple of (formatted_context_string, context_metadata)
    """
    if not chunks:
        return "", {"file_count": 0, "chunk_count": 0}
    
    context_parts = []
    files_included = set()
    total_chars = 0
    char_limit = max_tokens * 4  # Rough conversion
    
    for i, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        file_path = metadata.get("file", chunk.get("file", "unknown"))
        line_start = metadata.get("line_start", 1)
        line_end = metadata.get("line_end", 1)
        
        # Format chunk header
        header = f"## File: {file_path} (L{line_start}-{line_end})"
        content = chunk.get("content", "")
        
        # Add reranking score if available
        score_info = ""
        if "rerank_score" in chunk:
            score_info = f" [Relevance: {chunk['rerank_score']:.3f}]"
        elif "relevance" in chunk:
            score_info = f" [Relevance: {chunk['relevance']:.3f}]"
        
        formatted_chunk = f"{header}{score_info}\n```\n{content}\n```\n"
        
        # Check if adding this chunk would exceed limit
        if total_chars + len(formatted_chunk) > char_limit:
            break
        
        context_parts.append(formatted_chunk)
        files_included.add(file_path)
        total_chars += len(formatted_chunk)
    
    context_str = "\n".join(context_parts)
    
    metadata = {
        "file_count": len(files_included),
        "chunk_count": len(context_parts),
        "files": sorted(list(files_included)),
        "char_count": total_chars,
        "token_estimate": total_chars // 4
    }
    
    return context_str, metadata

def hybrid_search(
    query: str,
    surrounding_code: str = None,
    file_path: str = None,
    workspace_indexed: bool = True,
    top_k: int = 5
) -> dict:
    """
    Hybrid search combining:
    1. Direct code context (if available)
    2. Semantic search from indexed codebase
    
    Args:
        query: User query/request
        surrounding_code: Code context around cursor (highest priority)
        file_path: Active file path
        workspace_indexed: Whether workspace is indexed in ChromaDB
        top_k: Number of top results to return
        
    Returns:
        Dict with 'context' and 'metadata'
    """
    chunks = []
    
    # Priority 1: Active file context (highest relevance)
    if surrounding_code:
        chunks.append({
            "content": surrounding_code,
            "metadata": {
                "file": file_path or "active_file",
                "line_start": 1,
                "line_end": 1,
                "type": "active_context"
            },
            "relevance": 1.0,
            "rerank_score": 1.0  # Highest priority
        })
    
    # Priority 2: Semantic search in indexed workspace
    if workspace_indexed:
        try:
            search_results = semantic_search(query, n_results=top_k * 3)
            chunks.extend(search_results)
        except Exception as e:
            print(f"Semantic search warning: {e}")
    
    # Priority 3: Fallback - read full active file
    if not chunks and file_path and os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            chunks.append({
                "content": content[:4000],
                "metadata": {
                    "file": file_path,
                    "line_start": 1,
                    "line_end": "full",
                    "type": "fallback"
                },
                "relevance": 0.8
            })
        except Exception as e:
            print(f"Fallback read error: {e}")
    
    # Prepare final context
    context_str, context_meta = prepare_context_for_llm(chunks, max_tokens=8000)
    
    return {
        "context": context_str,
        "metadata": context_meta,
        "chunks_used": len(chunks),
        "retrieval_method": "hybrid_search"
    }
