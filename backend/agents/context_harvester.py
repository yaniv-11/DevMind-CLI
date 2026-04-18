# backend/agents/context_harvester.py
import os
from backend.graph.state import DevMindState
from backend.store.rag_system import hybrid_search

def context_harvester_node(state: DevMindState) -> DevMindState:
    """
    Enhanced context harvesting using hybrid RAG approach:
    1. Prioritize active file context (highest relevance)
    2. Semantic search in indexed codebase with reranking
    3. Fallback to full file reading if needed
    """
    
    # Check if workspace is indexed
    workspace_indexed = False
    if state.workspace_root:
        from backend.store.vector_store import get_collection
        try:
            collection = get_collection()
            workspace_indexed = collection.count() > 0
        except Exception:
            workspace_indexed = False
    
    # Run hybrid search (combines direct context + semantic search + reranking)
    result = hybrid_search(
        query=f"{state.raw_message} {state.task_summary or ''}",
        surrounding_code=state.surrounding_code,
        file_path=state.file_path,
        workspace_indexed=workspace_indexed,
        top_k=5
    )
    
    # Convert formatted context to chunks list for compatibility
    chunks = []
    
    if result["context"]:
        # Parse the formatted context back into structured chunks
        # This maintains backward compatibility with existing code
        lines = result["context"].split("\n")
        current_chunk = None
        current_content = []
        
        for line in lines:
            if line.startswith("## File:"):
                # Save previous chunk
                if current_chunk:
                    current_chunk["content"] = "\n".join(current_content).strip()
                    if current_chunk["content"]:
                        chunks.append(current_chunk)
                
                # Parse new chunk header: "## File: {path} (L{start}-{end}) [Relevance: {score}]"
                import re
                match = re.search(r'File: (.+?) \(L(\d+)-(\d+)\)', line)
                relevance_match = re.search(r'Relevance: ([\d.]+)', line)
                
                current_chunk = {
                    "file": match.group(1) if match else "unknown",
                    "lines": f"{match.group(2)}-{match.group(3)}" if match else "unknown",
                    "content": "",
                    "relevance": float(relevance_match.group(1)) if relevance_match else 0.5
                }
                current_content = []
            
            elif line.startswith("```"):
                # Skip code fence markers
                continue
            elif current_chunk is not None:
                current_content.append(line)
        
        # Save last chunk
        if current_chunk:
            current_chunk["content"] = "\n".join(current_content).strip()
            if current_chunk["content"]:
                chunks.append(current_chunk)
    
    return state.model_copy(update={"context_chunks": chunks})