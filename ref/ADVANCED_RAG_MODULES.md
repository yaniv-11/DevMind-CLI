# Advanced RAG System - Module Overview

## Module Dependency Graph

```
┌──────────────────────────────────────────────────────────┐
│                   LLM (Groq API)                        │
│              llama-3.3-70b-versatile                     │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│        Context Harvester Agent                           │
│  (backend/agents/context_harvester.py)                  │
│  - Calls hybrid_semantic_keyword_search()               │
│  - Integrates with LangGraph                            │
│  - Tracks with LangSmith                                │
└──────────────────────┬───────────────────────────────────┘
                       │
┌──────────────────────▼───────────────────────────────────┐
│         Hybrid RAG System                                │
│  (backend/store/hybrid_rag.py)                          │
│  - Coordinates semantic + keyword search                │
│  - Normalizes scores                                    │
│  - Reranks combined results                             │
│  - Formats context with metadata                        │
└──┬────────────────┬─────────────────────────────┬────────┘
   │                │                             │
   │                │                             │
   ▼                ▼                             ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
│  Semantic    │  │   Keyword    │  │    Reranker      │
│  Search      │  │   Search     │  │   (BGE)          │
│              │  │   (BM25)     │  │                  │
└──┬───────────┘  └──┬───────────┘  └──────────────────┘
   │                 │
   ▼                 ▼
┌──────────────┐  ┌──────────────┐
│ Embeddings   │  │ BM25 Index   │
│(AllMiniLM)   │  │              │
└──┬───────────┘  └──┬───────────┘
   │                 │
   ▼                 ▼
┌──────────────────────────────────────────┐
│      Vector Store (ChromaDB)             │
│  ./store/chroma/chroma.sqlite3           │
│  - Indexed chunks with embeddings        │
│  - Metadata: file, lines, definitions    │
│  - Cosine similarity search              │
└──────────────────────────────────────────┘
   ▲
   │
   │ Indexing
   │
┌──┴──────────────────────────────────────┐
│         Indexer                         │
│  (backend/store/indexer.py)            │
│  - Walks workspace                      │
│  - Chunks files (60-line overlaps)      │
│  - Extracts function/class metadata     │
│  - Stores in ChromaDB & BM25            │
└──┬───────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────┐
│    Chunk Extractor                       │
│  (backend/store/chunk_extractor.py)     │
│  - Python AST parser                    │
│  - JavaScript regex parser              │
│  - Extracts: functions, methods, classes│
│  - Returns metadata with line numbers   │
└──────────────────────────────────────────┘
   ▲
   │
   │ Applied
   │
┌──┴──────────────────────────────────────┐
│        File Editor                       │
│  (backend/store/file_editor.py)        │
│  - Safe file editing                    │
│  - Automatic backups                    │
│  - Syntax validation                    │
│  - Edit history & rollback              │
│  - Chunk reference tracking             │
└──────────────────────────────────────────┘
   ▲
   │
   │ Monitored
   │
┌──┴──────────────────────────────────────┐
│     LangSmith Tracker                    │
│  (backend/integrations/                 │
│   langsmith_tracker.py)                 │
│  - Traces RAG retrieval                 │
│  - Traces LLM calls                     │
│  - Traces file edits                    │
│  - Reports to dashboard                 │
└──────────────────────────────────────────┘
   │
   ▼
┌──────────────────────────────────────────┐
│    LangSmith Dashboard                   │
│  https://smith.langchain.com/           │
│  - View traces                           │
│  - Monitor tokens/cost                   │
│  - Provide feedback                      │
└──────────────────────────────────────────┘
```

## Module Details

### 1. Backend Store Modules

#### `backend/store/embeddings.py`
- **Purpose**: AllMiniLM-L6-v2 embedding model management
- **Key Functions**:
  - `get_embedding_model()` - Load or return cached model
  - `embed_text(text)` - Single text embedding (384-dim)
  - `embed_texts(texts)` - Batch embedding
  - `similarity_score(e1, e2)` - Cosine similarity
- **Model**: sentence-transformers/all-MiniLM-L6-v2
- **Output**: 384-dimensional vectors
- **Used by**: ChromaDB during indexing and searching

#### `backend/store/vector_store.py` (EXISTING, Enhanced)
- **Purpose**: ChromaDB vector database management
- **Key Functions**:
  - `get_collection()` - Get or create collection
  - `upsert_chunks(chunks)` - Insert/update chunks
  - `query_chunks(query, n_results)` - Semantic search
- **Database**: ./store/chroma/chroma.sqlite3
- **Metadata stored**: file, line_start, line_end, language, definitions
- **Search metric**: Cosine similarity
- **Used by**: Semantic search stage of hybrid RAG

#### `backend/store/bm25_search.py` (NEW)
- **Purpose**: BM25 keyword-based search
- **Key Functions**:
  - `initialize_bm25(chunks)` - Build BM25 index from chunks
  - `keyword_search(query, chunks_db, n_results)` - BM25 scoring
  - `save_bm25_index(filepath)` - Persist index
  - `load_bm25_index(filepath)` - Load from disk
  - `hybrid_keyword_semantic(sem, kw)` - Combine results
- **Algorithm**: Okapi BM25 (rank-bm25 library)
- **Scores**: Document frequency based (0-100+)
- **Used by**: Keyword search stage of hybrid RAG

#### `backend/store/chunk_extractor.py` (NEW)
- **Purpose**: Extract functions, methods, classes with metadata
- **Key Classes**:
  - `PythonCodeExtractor` - AST-based Python extraction
  - `JavaScriptCodeExtractor` - Regex-based JS/TS extraction
- **Key Functions**:
  - `extract_definitions(content, filepath)` - Extract all definitions
  - `extract_chunk_metadata(content, filepath)` - Per-chunk extraction
  - `create_enhanced_chunk(chunk, filepath, content)` - Add metadata
  - `format_chunk_with_definitions(chunk)` - Format for display
- **Extracts**: Class, Function, Method definitions with:
  - Name, line numbers, parent class
  - Docstrings, decorators, signatures
- **Used by**: Indexer during chunk creation

#### `backend/store/reranker.py` (EXISTING, from Phase 1)
- **Purpose**: Cross-encoder based reranking
- **Key Functions**:
  - `get_reranker_model()` - Load or return cached reranker
  - `rerank_chunks(query, chunks, top_k)` - Score and sort
  - `rerank_and_deduplicate(query, chunks, top_k)` - Rank + unique files
- **Model**: BAAI/bge-reranker-base (cross-encoder)
- **Scores**: 0-1 range (confidence)
- **Used by**: Final reranking stage of hybrid RAG

#### `backend/store/rag_system.py` (EXISTING, from Phase 1)
- **Purpose**: Legacy RAG pipeline (superseded by hybrid_rag.py)
- **Status**: Available but context_harvester uses hybrid_rag.py now
- **Can be used**: For fallback or specific use cases

#### `backend/store/hybrid_rag.py` (NEW)
- **Purpose**: Complete hybrid semantic + keyword retrieval pipeline
- **Key Functions**:
  - `hybrid_semantic_keyword_search(query, ...)` - Main function
    - Stage 1: Parallel semantic + keyword search
    - Stage 2: Combine results (remove dups)
    - Stage 3: Normalize scores (0-1)
    - Stage 4: Weighted combo (60% sem + 40% kw)
    - Stage 5: Rerank with cross-encoder
    - Stage 6: Final score and sort
  - `normalize_scores(chunks, score_key)` - Min-max normalization
  - `combine_hybrid_scores(chunks, weights)` - Weighted blend
  - `format_enhanced_context(chunks, max_tokens)` - Format for LLM
- **Returns**: 10-15 chunks with final_score and definitions
- **Used by**: Context harvester agent

#### `backend/store/indexer.py` (EXISTING, Enhanced)
- **Purpose**: Workspace indexing and chunk creation
- **Key Functions**:
  - `chunk_file(filepath, content)` - Split into 60-line chunks
  - `index_workspace(workspace_root)` - Index entire codebase
- **Enhancement**: Now extracts function/class metadata
- **Metadata added to chunks**:
  - definitions: List of function/class names
  - has_function, has_class: Boolean flags
- **Used by**: Initial workspace indexing

#### `backend/store/file_editor.py` (NEW)
- **Purpose**: Safe file editing with history and rollback
- **Key Methods**:
  - `read_file(file_path, start_line, end_line)` - Read with optional range
  - `edit_chunk(file_path, start_line, end_line, new_content, ...)` - Edit lines
  - `replace_text(file_path, old_text, new_text, ...)` - Find & replace
  - `validate_syntax(file_path)` - Check Python syntax
  - `rollback_to_backup(backup_path)` - Restore from backup
  - `get_edit_history(file_path, limit)` - View edits
  - `get_pending_edits_summary()` - Summary of changes
- **Features**:
  - Automatic backups in ./store/file_backups/
  - Chunk reference tracking (for traceability)
  - Full edit history
  - Rollback capability
  - Python syntax validation
- **Used by**: Agents applying LLM suggestions

### 2. Agent Modules

#### `backend/agents/context_harvester.py` (EXISTING, Enhanced)
- **Purpose**: Retrieve relevant code context for queries
- **Key Function**:
  - `context_harvester_node(state)` - LangGraph node
- **Enhancement**: Now uses hybrid_semantic_keyword_search
- **Inputs from state**:
  - raw_message: User query
  - task_summary: Inferred task
  - workspace_root: Codebase path
  - surrounding_code: Code context (optional)
  - file_path: Active file (optional)
- **Outputs to state**:
  - context_chunks: Retrieved chunks with metadata
  - context_metadata: Retrieval statistics
  - formatted_context: Ready-to-send context string
- **Features**:
  - Hybrid search (semantic + keyword)
  - Function/class context
  - LangSmith tracking
  - Token limiting (8000 chars)
- **Used by**: DevMind agent graph

### 3. Integration Modules

#### `backend/integrations/langsmith_tracker.py` (NEW)
- **Purpose**: Tracing and monitoring with LangSmith
- **Key Class**: `LangSmithTracker`
  - `trace_rag_retrieval(query, results)` - Log retrieval
  - `trace_llm_call(model, messages, response)` - Log LLM call
  - `trace_file_edit(file_path, edit_type, result)` - Log edit
  - `log_metric(name, value)` - Custom metrics
  - `create_run(run_name, metadata)` - Create trace run
- **Key Decorator**: `@traced` - Trace any function
- **Key Function**: `get_tracker()` - Get global instance
- **Dashboard**: https://smith.langchain.com/
- **Environment**: Reads LANGSMITH_API_KEY
- **Used by**: Context harvester and other agents

## Data Structures

### Chunk Schema

```python
chunk = {
    "id": "md5_hash",  # Unique identifier
    "content": "source code here",
    "metadata": {
        "file": "src/utils.py",
        "line_start": 10,
        "line_end": 45,
        "language": "py",
        "definitions": ["process", "validate"],  # Functions/methods
        "has_function": True,
        "has_class": False
    },
    # Scores from different stages
    "semantic_score": 0.82,      # Embedding similarity
    "keyword_score": 25.5,        # BM25 score
    "semantic_score_normalized": 0.82,
    "keyword_score_normalized": 0.63,
    "hybrid_score": 0.73,        # Combined
    "rerank_score": 0.91,        # Cross-encoder
    "final_score": 0.82          # Final ranking score
}
```

### State Schema

```python
class DevMindState:
    raw_message: str                    # User query
    task_summary: str                   # Inferred task
    workspace_root: str                 # Codebase path
    file_path: str                      # Active file
    surrounding_code: str               # Code context
    
    context_chunks: list[dict]          # Retrieved chunks
    context_metadata: dict              # Retrieval stats
    formatted_context: str              # Ready for LLM
    
    intent: str                         # Detected intent
    response: dict                      # Response to user
```

## Processing Flow

### Request to Response

```
1. User Query
   "fix the null pointer bug in login.py"

2. Context Harvester
   - Calls hybrid_semantic_keyword_search()
   - Returns 10 chunks

3. Format Context
   - format_enhanced_context(chunks)
   - Shows: file path, line numbers, functions

4. LLM Processing
   - Analyzes context with query
   - Generates response with suggestions

5. LangSmith Tracking
   - Logs: query, chunks, LLM response
   - Available on dashboard

6. File Editor
   - User applies suggestion
   - edit_chunk() with chunk_ref
   - Backup created, history recorded

7. Validation
   - validate_syntax() checks Python
   - Returns success/failure

8. LangSmith Logs Edit
   - Logs: file, changes, backup
   - Shows relationship to original chunks
```

## Performance Characteristics

| Component | Time | Notes |
|-----------|------|-------|
| Semantic search | ~30ms | ChromaDB |
| Keyword search | ~20ms | BM25 |
| Score combination | <1ms | Linear |
| Reranking | ~400ms | Cross-encoder |
| Context format | ~5ms | String building |
| **Total retrieval** | **~500ms** | All stages |
| File read | ~5ms | Small files |
| File edit | ~10ms | + backup creation |
| **Total edit** | **~50ms** | Write + validation |

## Resource Usage

```
Memory:
- AllMiniLM model: ~100MB
- BGE Reranker: ~400MB
- BM25 index: ~50MB (10k chunks)
- ChromaDB: ~100MB (10k chunks)
────────────────────────────────
Total: ~650MB

Disk:
- ChromaDB: ~100MB (10k chunks)
- BM25 index: ~50MB
- Backups: Grows with edits
────────────────────────────────
Total: ~200MB+ (depends on usage)
```

## Integration Points

### With LangGraph (existing)
- Context harvester node runs hybrid search
- Feeds into reasoning agent
- Used by code writer and validator

### With LLM (Groq)
- Sends formatted context
- Receives suggestions
- Tracked by LangSmith

### With File System
- Reads code files
- Writes edited files
- Creates backups
- Maintains history

### With ChromaDB
- Stores indexed chunks
- Performs semantic search
- Returns embeddings

### With LangSmith
- All operations traced
- Available on dashboard
- Enables debugging and monitoring

## Extension Points

### Add New Search Type
- Implement in `hybrid_rag.py`
- Add normalization
- Include in weighted combination

### Support New Language
- Add extractor in `chunk_extractor.py`
- Handle AST or regex parsing
- Return consistent schema

### Custom Reranker
- Replace in `hybrid_rag.py`
- Maintain 0-1 score range
- Keep function signature

### Custom File Editor
- Extend `FileEditor` class
- Implement additional validation
- Maintain backup safety

## Documentation Map

- **[QUICK_START_ADVANCED_RAG.md](QUICK_START_ADVANCED_RAG.md)** - Get started quickly
- **[ADVANCED_RAG_GUIDE.md](ADVANCED_RAG_GUIDE.md)** - Complete guide
- **[RAG_ARCHITECTURE.md](RAG_ARCHITECTURE.md)** - Technical details
- **[RAG_API_REFERENCE.md](RAG_API_REFERENCE.md)** - API documentation
- **This file** - Module overview and relationships
