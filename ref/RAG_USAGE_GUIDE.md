# How to Use DevMind's RAG System

## Quick Start

### 1. Index Your Workspace
```bash
cd /path/to/your/project
devmind interact
# Type: /index
```

This scans all `.py`, `.ts`, `.js`, `.md` files and stores them in ChromaDB.

### 2. Ask Questions
```
DevMind > fix the bug in utils.py where process() fails
DevMind > how do I use the generate_config function
DevMind > explain the database schema
```

The RAG system will:
1. Fetch your active file context (if available)
2. Search for semantically similar code chunks
3. Rerank results for best relevance
4. Pass to LLM with full context

## Architecture Overview

### How Data is Stored

**Workspace Index (One Time)**
```
Your Codebase
├── file1.py (500 lines) → 10 chunks
├── file2.ts (300 lines) → 6 chunks
└── ...
                ↓
        Chroma Vector Database
                ↓
    ./store/chroma/chroma.sqlite3
    (embeddings + metadata)
```

**Storage Details**:
- Each file split into 60-line overlapping chunks
- 50% overlap for context preservation
- ~1 chunk per 30 lines of code
- 100 files ≈ 3000 chunks

### How Retrieval Works (2-Stage Pipeline)

```
Your Query: "fix the null pointer exception"
    ↓
Stage 1: FAST RETRIEVAL (AllMiniLM Embedding)
    - Convert query to 384-dim vector
    - Search ChromaDB (cosine similarity)
    - Get top 15 similar code chunks
    - Takes: <50ms
    ↓
Stage 2: ACCURATE RANKING (BGE Reranker)
    - Cross-encode query against each chunk
    - Compute relevance scores
    - Sort by score, deduplicate by file
    - Get top 5 unique files
    - Takes: ~300-500ms
    ↓
Prepared Context (8000 char max):
## File: null_handler.py (L23-45) [Relevance: 0.94]
```
def safe_process(obj):
    if obj is None:
        return None
    ...
```

## File: utils.py (L100-120) [Relevance: 0.87]
```
def process():
    data = fetch_data()
    # Missing null check!
    ...
```
    ↓
LLM Analysis & Solution
```

## Core Components

### 1. Embeddings (backend/store/embeddings.py)

**Model**: All-MiniLM-L6-v2
- 384-dimensional vectors
- ~30MB model size
- Fast & accurate for code

```python
from backend.store.embeddings import embed_text, embed_texts

# Single embedding
vec = embed_text("def hello(): pass")  # Returns list[float] of 384 values

# Batch embeddings (efficient)
vecs = embed_texts(["code1", "code2", "code3"])
```

### 2. Semantic Search (backend/store/vector_store.py)

**Database**: ChromaDB
- Persistent storage at `./store/chroma/`
- Cosine similarity metric
- Metadata: file path, line numbers, language

```python
from backend.store.vector_store import query_chunks

chunks = query_chunks(
    query="ValueError in parsing",
    n_results=15  # Get more for reranking
)

for chunk in chunks:
    print(chunk["content"])           # Code snippet
    print(chunk["metadata"]["file"])  # File path
    print(chunk["distance"])          # 0.2 = very similar
```

### 3. Reranking (backend/store/reranker.py)

**Model**: BAAI/bge-reranker-base
- Cross-encoder (evaluates query-chunk pairs)
- 5-10% better accuracy than embedding similarity
- Final ranking before LLM

```python
from backend.store.reranker import rerank_chunks, rerank_and_deduplicate

# Rerank all chunks
ranked = rerank_chunks(query, chunks, top_k=None)

# Rerank + ensure one chunk per file
final = rerank_and_deduplicate(query, chunks, top_k=5)
```

### 4. Hybrid Search (backend/store/rag_system.py)

Combines all three with intelligent fallbacks:

```python
from backend.store.rag_system import hybrid_search

result = hybrid_search(
    query="how to connect to database",
    surrounding_code="""def __init__(self):
        self.db = connect()
        self.db.""",
    file_path="src/db.py",
    workspace_indexed=True,
    top_k=5
)

print(result["context"])      # Ready for LLM
print(result["metadata"])     # Stats: file count, chunks, etc.
print(result["chunks_used"])  # Number of chunks retrieved
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────┐
│              User Interaction                    │
│  "How do I fix the auth bug in login.py?"      │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│          Hybrid Search (RAG System)              │
├─────────────────────────────────────────────────┤
│                                                  │
│  Priority 1: Active File Context                │
│  ├─ surrounding_code (relevance: 1.0)          │
│  └─ file_path from editor                      │
│                                                  │
│  Priority 2: Semantic Search + Reranking        │
│  ├─ AllMiniLM embedding of query                │
│  ├─ ChromaDB cosine search (top 15)             │
│  ├─ BGE reranker cross-encode                   │
│  └─ Deduplicate by file (top 5)                 │
│                                                  │
│  Priority 3: Fallback                           │
│  └─ Read full active file if no index           │
│                                                  │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│       Context Preparation (Token Limit)         │
│   - Format with file paths, line numbers        │
│   - Include relevance scores                    │
│   - Stop at 8000 chars (~2000 tokens)           │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│           Context Chunks (Formatted)            │
│                                                  │
│ ## File: login.py (L45-80) [Relevance: 0.95]  │
│ ```                                             │
│ def authenticate(user, pwd):                    │
│     if not validate_password(pwd):              │
│         return None                             │
│     return create_token(user)                   │
│ ```                                             │
│                                                  │
│ ## File: auth_utils.py (L10-35) [Rel: 0.88]   │
│ ```                                             │
│ def validate_password(pwd):                     │
│     if len(pwd) < 8:                            │
│         raise ValueError("Too short")           │
│     ...                                         │
│ ```                                             │
└──────────────┬──────────────────────────────────┘
               │
               ↓
┌─────────────────────────────────────────────────┐
│              LLM Processing                      │
│   (Groq llama-3.3-70b-versatile)                │
│                                                  │
│  Input:  Query + Context Chunks                 │
│  Output: Analysis + Fix + Validation            │
└─────────────────────────────────────────────────┘
```

## Storage Details

### ChromaDB Structure

```
./store/chroma/
├── chroma.sqlite3              # Main SQLite database
└── <uuid>/                     # Collection directory
    └── data/
        ├── embeddings.pkl      # Vector embeddings
        ├── header.pkl          # Metadata header
        └── data.pkl            # Document content
```

### Sample Chunk Record

```json
{
  "id": "abc123def456",  // MD5 hash of (file:start:end)
  "content": "def process(data):\n    return data.strip()",
  "metadata": {
    "file": "src/utils.py",
    "line_start": 45,
    "line_end": 47,
    "language": "python"
  }
}
```

## Performance Metrics

### Retrieval Speed
```
Query → Embedding:       ~2ms   (cached after first)
Embedding → ChromaDB:   ~30ms   (depends on index size)
Search → Reranking:    ~400ms   (Cross-encoder inference)
Rerank → LLM:           ~10ms   (formatting)
────────────────────────────────
Total RAG Pipeline:     ~500ms
```

### Accuracy
- Embedding relevance: ⭐⭐⭐⭐ (good)
- Reranking boost: +5-10% better than embedding alone
- Final top-5: ⭐⭐⭐⭐⭐ (excellent)

### Storage
- Per file: ~30-50KB (for indexed chunks)
- Per 100 files: ~3-5MB in ChromaDB
- RAM (models): ~500MB (embedder + reranker)

## Commands

### Index Workspace
```bash
devmind interact
# Then type: /index
```

### Re-index (if files changed)
```bash
/index    # In devmind interact
```

### Check Indexed Status
```python
from backend.store.vector_store import get_collection
collection = get_collection()
print(f"Indexed chunks: {collection.count()}")
```

## Troubleshooting

### Q: Slow first query?
A: First embedding load downloads 30MB model. Subsequent queries use cached model (~2ms).

### Q: Poor search results?
A: 
1. Index more files: `/index` in CLI
2. Increase top_k: Modify `hybrid_search(top_k=10)`
3. Check active file context: Ensure surrounding_code is set
4. Rerank cutoff: Lower rerank threshold in `rerank_chunks()`

### Q: "Collection not found" error?
A: Run `/index` in `devmind interact` to create index.

### Q: Memory issues?
A: 
1. Use CPU-only: Set `CUDA_VISIBLE_DEVICES=""`
2. Batch queries: Don't run in parallel
3. Reduce cache: Clear old embeddings

### Q: Different results each time?
A: Randomness from:
1. Top-k selection (retrieve top-15, rank top-5)
2. Deduplication order
3. Reranker confidence scores

Try setting seed for reproducibility if needed.

## Advanced Usage

### Custom Embedding Model
```python
# In backend/store/embeddings.py
def get_embedding_model():
    global _model
    if _model is None:
        # Change to different model
        _model = SentenceTransformer("all-mpnet-base-v2")  # Higher quality
    return _model
```

### Adjust Retrieval Parameters
```python
# In backend/store/rag_system.py, semantic_search():
chunks = chroma_query_chunks(query=query, n_results=15)  # Get more candidates
reranked = rerank_and_deduplicate(query, chunks, top_k=3)  # Keep fewer
```

### Analyze Retrieval Quality
```python
from backend.store.rag_system import semantic_search

results = semantic_search("your query", n_results=5)
for r in results:
    print(f"{r['metadata']['file']}: {r.get('rerank_score', '?')}")
```

## Next Steps

1. Index workspace: `devmind interact` → `/index`
2. Ask questions naturally
3. Check context relevance in responses
4. Adjust parameters if needed
5. Monitor token usage in logs

The RAG system will improve over time as more context is indexed!
