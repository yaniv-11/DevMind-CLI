# backend/agents/context_harvester.py
import os
from backend.graph.state import DevMindState
from backend.store.hybrid_rag import hybrid_semantic_keyword_search, format_enhanced_context
from backend.integrations.langsmith_tracker import get_tracker

def context_harvester_node(state: DevMindState) -> DevMindState:
    """
    Enhanced context harvesting using hybrid RAG:
    - Semantic search (AllMiniLM embeddings)
    - Keyword search (BM25)
    - Reranking (cross-encoder)
    - Function/class metadata extraction
    """
    
    tracker = get_tracker()
    
    try:
        # Check if workspace is indexed
        workspace_indexed = False
        if state.workspace_root:
            from backend.store.vector_store import get_collection
            try:
                collection = get_collection()
                workspace_indexed = collection.count() > 0
            except Exception:
                workspace_indexed = False
        
        # Run hybrid search (semantic + keyword + reranking)
        chunks = []
        if state.raw_message:
            query = f"{state.raw_message} {state.task_summary or ''}"
            
            chunks = hybrid_semantic_keyword_search(
                query=query,
                workspace_root=state.workspace_root,
                n_semantic=15,
                n_keyword=15,
                top_k=10,  # Top 10-15 chunks
                weights={"semantic": 0.6, "keyword": 0.4}
            )
            
            # Trace retrieval
            tracker.trace_rag_retrieval(query, chunks)
        
        # Format context with file and function information
        if chunks:
            context_str, context_meta = format_enhanced_context(chunks, max_tokens=8000)
        else:
            context_str = ""
            context_meta = {
                "file_count": 0,
                "function_count": 0,
                "chunk_count": 0,
                "files": [],
                "functions": []
            }
        
        # Convert chunks to structured format for state
        structured_chunks = []
        for chunk in chunks:
            metadata = chunk.get("metadata", {})
            structured_chunks.append({
                "file": metadata.get("file", "unknown"),
                "lines": f"{metadata.get('line_start', 1)}-{metadata.get('line_end', 1)}",
                "content": chunk.get("content", ""),
                "relevance": chunk.get("final_score", 0.5),
                "definitions": metadata.get("definitions", []),
                "chunk_id": chunk.get("id")
            })
        
        return state.model_copy(update={
            "context_chunks": structured_chunks,
            "context_metadata": context_meta,
            "formatted_context": context_str
        })
    
    except Exception as e:
        print(f"Context harvester error: {e}")
        return state.model_copy(update={"context_chunks": []})