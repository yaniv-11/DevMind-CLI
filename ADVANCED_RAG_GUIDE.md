# Advanced RAG System with BM25, File Editing, and LangSmith Tracking

## Overview

DevMind now features an advanced Retrieval Augmented Generation (RAG) system with:

1. **Hybrid Retrieval** - Semantic + Keyword (BM25) search
2. **Smart Reranking** - Normalized scores + cross-encoder ranking
3. **Function/Method Metadata** - Granular code context with AST parsing
4. **Safe File Editing** - Edit suggestions with chunk references and rollback
5. **LangSmith Integration** - Full tracing and debugging

## Architecture

### 1. Hybrid Retrieval Pipeline

```
User Query
    ↓
┌─────────────────────────────────────────────┐
│      Stage 1: Parallel Search                │
├─────────────────────────────────────────────┤
│                                              │
│  Path A: Semantic Search                    │
│  ├─ AllMiniLM embedding                     │
│  ├─ ChromaDB cosine similarity              │
│  └─ Top 15 results                          │
│                                              │
│  Path B: Keyword Search (BM25)              │
│  ├─ BM25 scoring                            │
│  ├─ Document relevance                      │
│  └─ Top 15 results                          │
│                                              │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│    Stage 2: Combine & Normalize              │
├─────────────────────────────────────────────┤
│  - Merge semantic & keyword results         │
│  - Min-max normalize scores (0-1)           │
│  - Weighted combination (60% semantic,      │
│    40% keyword)                             │
│  - Remove duplicates                        │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│   Stage 3: Cross-Encoder Reranking          │
├─────────────────────────────────────────────┤
│  - BGE reranker pairwise scoring            │
│  - Final relevance scoring                  │
│  - Combined with hybrid score (50/50)       │
└─────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────┐
│   Stage 4: Final Selection (Top 10-15)      │
├─────────────────────────────────────────────┤
│  - Sort by final_score                      │
│  - Include function/class metadata          │
│  - Token limit enforcement (8000 chars)     │
│  - Format with file and line info           │
└─────────────────────────────────────────────┘
    ↓
LLM Processing with Enhanced Context
```

### 2. Function/Method Metadata Extraction

Each chunk now includes:
- **Function/Method Names**: What code constructs are in this chunk
- **Class Context**: Which class this method belongs to
- **Signatures**: Function signatures and decorators (Python)
- **Docstrings**: Available function documentation

Example:

```python
chunk = {
    "content": "def process(data):\n    return data.strip()",
    "metadata": {
        "file": "src/utils.py",
        "line_start": 45,
        "line_end": 47,
        "definitions": ["process"],
        "has_function": True,
        "has_class": False
    }
}
```

### 3. Score Normalization

BM25 scores and semantic scores are on different scales:
- **Semantic**: Usually 0-1 (cosine similarity)
- **BM25**: Usually 0-100+ (document frequency based)

DevMind normalizes both to 0-1 range:

```python
# Min-max normalization
normalized = (score - min) / (max - min)

# Weighted combination
hybrid_score = 0.6 * semantic_normalized + 0.4 * keyword_normalized
```

### 4. Reranking Strategy

Two-stage reranking:

1. **Hybrid Score**: Combines semantic + keyword (see above)
2. **Final Score**: 50% reranker + 50% hybrid
   - Reranker: 0-1 scale (cross-encoder confidence)
   - Hybrid: 0-1 scale (combined semantic+keyword)

This ensures both signal types influence final ranking.

## File Editing System

### Features

- **Safe Editing**: Edit by line range or text matching
- **Automatic Backups**: Before each edit
- **Syntax Validation**: For Python files
- **Chunk Reference**: Track which chunk suggestion came from
- **Edit History**: Full audit trail
- **Rollback**: Restore from backups

### Usage Example

```python
from backend.store.file_editor import FileEditor

editor = FileEditor("/path/to/project")

# Edit by line range
result = editor.edit_chunk(
    file_path="src/utils.py",
    start_line=10,
    end_line=15,
    new_content="def fixed_function():\n    pass",
    description="Fixed null pointer exception",
    chunk_ref="abc123def456"  # Reference to retrieval chunk
)

# Returns:
# {
#     "status": "success",
#     "file": "/path/to/project/src/utils.py",
#     "lines_changed": 6,
#     "backup": "./store/file_backups/utils.py.20260418_143022.bak",
#     "description": "Fixed null pointer exception",
#     "chunk_ref": "abc123def456"
# }
```

### File Editing API

```python
# Read file or specific lines
editor.read_file("src/app.py")
editor.read_file("src/app.py", start_line=10, end_line=20)

# Edit by lines
editor.edit_chunk(
    "src/app.py",
    start_line=10,
    end_line=15,
    new_content="...",
    description="...",
    chunk_ref="..."
)

# Edit by text replacement
editor.replace_text(
    "src/app.py",
    old_text="old code here",
    new_text="new code here",
    description="...",
    chunk_ref="..."
)

# Validate Python syntax
editor.validate_syntax("src/app.py")

# Rollback
editor.rollback_to_backup("./store/file_backups/app.py.20260418_143022.bak")

# Get edit history
editor.get_edit_history("src/app.py")
editor.get_edit_history()  # All files

# Get summary of pending edits
editor.get_pending_edits_summary()
```

### Integration with LLM Suggestions

When LLM suggests code changes:

```python
# 1. LLM provides suggestion with chunk reference
llm_response = """
Looking at the auth issue in auth.py (chunks [1] and [2])...
I suggest the following fix:

OLD CODE (src/auth.py, L45-50):
```python
def authenticate(user, pwd):
    if not validate(pwd):
        return None
```

NEW CODE:
```python
def authenticate(user, pwd):
    if not user or not pwd:
        return None
    if not validate(pwd):
        return None
```
"""

# 2. User/system applies the edit with chunk reference
result = editor.edit_chunk(
    "src/auth.py",
    start_line=45,
    end_line=50,
    new_content="def authenticate(user, pwd):\n    if not user or not pwd:\n        return None\n    if not validate(pwd):\n        return None",
    description="Added user/pwd validation",
    chunk_ref="abc123"  # Reference to chunk [1]
)

# 3. File is modified with full traceability
# → Backup created
# → Edit recorded with chunk_ref
# → Syntax validated
# → History tracked

# 4. View what was edited
history = editor.get_edit_history("src/auth.py")
# Shows: When, what, by which chunk, where backup is
```

## LangSmith Integration

### Setup

1. **Get API Key**: Sign up at [LangSmith](https://smith.langchain.com/)
2. **Set Environment Variable**:
   ```bash
   export LANGSMITH_API_KEY=your_key_here
   ```
3. **Automatic Tracking**: DevMind automatically traces all operations

### What Gets Tracked

#### RAG Retrieval
```
- Query text
- Number of chunks retrieved
- Top relevance score
- Files included
- Search type (semantic/keyword/hybrid)
```

#### LLM Calls
```
- Model used (Groq llama-3.3-70b)
- Input message count
- Response length
- Processing time
- Tokens used (if available)
```

#### File Edits
```
- File path edited
- Edit type (chunk or text replacement)
- Status (success/failure)
- Chunk reference (for traceability)
- Backup location
```

### Usage

```python
from backend.integrations.langsmith_tracker import get_tracker, traced

# Get tracker instance
tracker = get_tracker("DevMind")

# Track RAG retrieval
tracker.trace_rag_retrieval(query, results)

# Track LLM call
tracker.trace_llm_call("llama-3.3-70b", messages, response)

# Track file edit
tracker.trace_file_edit("src/app.py", "chunk", edit_result)

# Decorator-based tracing
@traced
def my_function(query):
    # Automatically traced
    return process(query)
```

### LangSmith Dashboard

View traces at: https://smith.langchain.com/

Features:
- **Trace Timeline**: See execution flow
- **Token Usage**: Monitor costs
- **Error Analysis**: Debug failures
- **Latency Metrics**: Performance tracking
- **User Feedback**: Rate suggestions (👍 👎)

## Configuration

### Tuning Hybrid Search

In `backend/store/hybrid_rag.py`:

```python
results = hybrid_semantic_keyword_search(
    query="your query",
    n_semantic=15,      # Initial semantic results
    n_keyword=15,       # Initial keyword results
    top_k=10,           # Final results (10-15 recommended)
    weights={
        "semantic": 0.6,  # 60% weight to semantic
        "keyword": 0.4    # 40% weight to keyword
    }
)
```

**Adjust weights based on your needs**:
- Higher `semantic` if you have better embeddings
- Higher `keyword` if your queries are keyword-heavy
- Balanced (0.5/0.5) for general use

### Tuning BM25 Search

BM25 algorithm parameters (in `rank_bm25`):

```python
# Default: k1=1.5, b=0.75 (works well for code)
# k1: Controls term frequency saturation (higher = more saturation)
# b: Controls length normalization (0=no normalization, 1=full)

# For code:
# - Default works well
# - Consider k1=2.0 for more term frequency emphasis
```

### Chunk Size and Overlap

In `backend/store/indexer.py`:

```python
def chunk_file(filepath: str, content: str, chunk_size: int = 60):
    # chunk_size: Lines per chunk (default: 60)
    # step: Overlap size (default: 30, which is 50% overlap)
    
    # For better function-level retrieval:
    # - Decrease chunk_size to ~40 (smaller, more granular)
    # - Increase overlap to ~20 (more context)
```

## Performance

### Speed

| Operation | Time | Notes |
|-----------|------|-------|
| Semantic search | ~30ms | ChromaDB cosine |
| Keyword search | ~20ms | BM25 scoring |
| Score normalization | <1ms | Linear operation |
| Reranking | ~400ms | Cross-encoder inference |
| File read/write | ~5-50ms | Depends on file size |
| **Total RAG** | **~500ms** | All stages combined |

### Accuracy

| Stage | Accuracy | Improvement |
|-------|----------|------------|
| Semantic alone | ⭐⭐⭐⭐ | Baseline |
| Keyword alone | ⭐⭐⭐ | -1 star (narrow) |
| Hybrid (combined) | ⭐⭐⭐⭐⭐ | +1 star (covers both) |
| + Reranking | ⭐⭐⭐⭐⭐ | Consistent (no change) |
| + Function metadata | ⭐⭐⭐⭐⭐ | Better relevance |

### Memory

```
Models:
- AllMiniLM: ~100MB
- BGE Reranker: ~400MB
- BM25 Index: ~50MB (for 10k chunks)
────────────────
Total: ~550MB
```

## Examples

### Complete Workflow

```python
from backend.store.hybrid_rag import hybrid_semantic_keyword_search, format_enhanced_context
from backend.store.file_editor import FileEditor
from backend.integrations.langsmith_tracker import get_tracker

# 1. Retrieve context
query = "fix authentication bug in login"
chunks = hybrid_semantic_keyword_search(query, top_k=10)

# 2. Format for LLM
context, metadata = format_enhanced_context(chunks)
print(f"Found {metadata['function_count']} functions in {metadata['chunk_count']} chunks")

# 3. Send to LLM (with context)
llm_response = call_llm(context + "\n\nQuery: " + query)

# 4. Extract suggestion and apply
editor = FileEditor("/path/to/project")
result = editor.edit_chunk(
    "src/auth.py",
    start_line=45,
    end_line=50,
    new_content=suggested_code,
    description="Fix auth bug",
    chunk_ref=chunks[0]["id"]
)

# 5. Validate
validation = editor.validate_syntax("src/auth.py")
print(f"Syntax: {validation['status']}")

# 6. Track in LangSmith
tracker = get_tracker()
tracker.trace_rag_retrieval(query, chunks)
tracker.trace_file_edit("src/auth.py", "chunk", result)
```

## Troubleshooting

### Poor Hybrid Search Results

**Issue**: Results not relevant

**Solutions**:
1. Check BM25 index is built (run `/index`)
2. Increase `top_k` in hybrid_semantic_keyword_search
3. Adjust weights toward better-performing modality
4. Check chunk_size (too large = missing functions)

### File Edit Failures

**Issue**: Edit not applied

**Solutions**:
1. Check file path is relative to workspace
2. Verify line numbers are correct (use `editor.read_file()`)
3. Check for special characters in new_content
4. Use `replace_text` instead of `edit_chunk` if lines changed

### LangSmith Not Tracking

**Issue**: No traces appearing in dashboard

**Solutions**:
1. Set `LANGSMITH_API_KEY` environment variable
2. Check API key is valid
3. Verify project name matches
4. Check network connectivity to smith.langchain.com

### Out of Memory

**Issue**: Models causing memory issues

**Solutions**:
1. Disable reranking if not critical
2. Use smaller models (all-MiniLM already small)
3. Reduce batch sizes for embedding
4. Monitor with `nvidia-smi` (GPU) or `top` (CPU)

## API Reference

See [RAG_API_REFERENCE.md](RAG_API_REFERENCE.md) for detailed API documentation.

## Further Reading

- [RAG Architecture](RAG_ARCHITECTURE.md) - Technical details
- [RAG Usage Guide](RAG_USAGE_GUIDE.md) - User guide
- [BM25 Explained](https://en.wikipedia.org/wiki/Okapi_BM25) - Algorithm details
- [LangSmith Docs](https://docs.smith.langchain.com/) - Monitoring setup
