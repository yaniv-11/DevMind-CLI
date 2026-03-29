# backend/agents/context_harvester.py
import os
from backend.graph.state import DevMindState
from backend.store.vector_store import query_chunks

def context_harvester_node(state: DevMindState) -> DevMindState:
    chunks = []

    # Strategy 1: semantic search in ChromaDB if workspace is indexed
    if state.workspace_root:
        query = f"{state.raw_message} {state.task_summary or ''}"
        results = query_chunks(query=query, n_results=6)
        for r in results:
            chunks.append({
                "file": r["metadata"].get("file", "unknown"),
                "lines": f"{r['metadata'].get('line_start')}-{r['metadata'].get('line_end')}",
                "content": r["content"],
                "relevance": round(1 - r["distance"], 3)
            })

    # Strategy 2: always include the active file's surrounding code
    if state.surrounding_code:
        line = state.line_number or 1
        chunks.insert(0, {
            "file": state.file_path or "active_file",
            "lines": f"{max(1, line - 10)}-{line + 10}",
            "content": state.surrounding_code,
            "relevance": 1.0
        })

    # Strategy 3: read full active file as fallback
    if not chunks and state.file_path and os.path.exists(state.file_path):
        try:
            with open(state.file_path, "r") as f:
                content = f.read()
            chunks.append({
                "file": state.file_path,
                "lines": "full",
                "content": content[:4000],
                "relevance": 0.8
            })
        except Exception:
            pass

    # Deduplicate by content
    seen = set()
    unique_chunks = []
    for c in chunks:
        key = c["content"][:100]
        if key not in seen:
            seen.add(key)
            unique_chunks.append(c)

    return state.model_copy(update={"context_chunks": unique_chunks})