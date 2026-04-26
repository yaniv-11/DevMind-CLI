# DevMind RAG System Architecture

## Overview
DevMind uses a sophisticated Retrieval Augmented Generation (RAG) system to provide context-aware code analysis. The system combines semantic search with reranking to deliver the most relevant code chunks to the LLM.

## Data Flow Architecture

```
User Query
    ↓
[RAG System - Hybrid Search]
    ├─ Strategy 1: Active File Context (highest priority)
    │  └─ Surrounding code from editor (relevance: 1.0)
    │
    ├─ Strategy 2: Semantic Search + Reranking
    │  ├─ Query Embedding (AllMiniLM-L6-v2)
    │  ├─ ChromaDB Vector Search (cosine similarity)
    │  ├─ Initial Retrieval (top 10-15 chunks)
    │  ├─ Cross-Encoder Reranking (BAAI/bge-reranker-base)
    │  └─ Deduplicated Results (top 5 unique files)
    │
    └─ Strategy 3: Fallback (if no indexed workspace)
       └─ Full file read (relevance: 0.8)
    ↓
[Context Preparation]
    ├─ Format with file paths and line numbers
    ├─ Include relevance scores
    ├─ Token limit enforcement (8000 char ≈ 2000 tokens)
    └─ Deduplicate by file location
    ↓
[LLM Processing]
    ├─ Code Analysis
    ├─ Bug Detection
    ├─ Solution Generation
    └─ Validation
```

## Storage Structure (Chroma)

### Database Location
```
./store/chroma/
├── chroma.sqlite3          # Main database
└── <uuid>/                 # Collection data
    └── data/
        ├── embeddings      # Vector embeddings
        └── documents       # Chunk content
```

### Data Schema for Each Chunk
```json
{
  "id": "md5_hash",
  "content": "actual code snippet",
  "metadata": {
    "file": "src/module.py",
    "line_start": 45,
    "line_end": 105,
    "language": "python"
  }
}
```

### Indexing Process
1. **File Discovery**: Walk workspace, find `.py`, `.ts`, `.js`, `.md` files
2. **Chunking**: Split into 60-line overlapping chunks (50% overlap)
3. **Embedding**: Convert content to AllMiniLM vectors
4. **Storage**: Upsert to ChromaDB with metadata
5. **Indexing Rate**: ~1000 chunks per indexed file

## Component Details

### 1. Embedding Model (AllMiniLM-L6-v2)
**File**: `backend/store/embeddings.py`

```
Model: sentence-transformers/all-MiniLM-L6-v2
Vector Dimension: 384
Speed: ~5000 sentences/sec
Accuracy: Near-BERT quality with 1/10 of params
Best For: Code, technical docs, semantic similarity
```

**Usage**:
```python
from backend.store.embeddings import embed_text, embed_texts

# Single text
embedding = embed_text("def hello(): pass")  # List of 384 floats

# Multiple texts (batched)
embeddings = embed_texts(["code1", "code2", ...])

# Similarity scoring
score = similarity_score(embedding1, embedding2)  # 0.0 to 1.0
```

### 2. Semantic Search (ChromaDB)
**File**: `backend/store/vector_store.py`

**Query Process**:
```python
from backend.store.vector_store import query_chunks

chunks = query_chunks(
    query="how to fix TypeError",
    n_results=10
)
# Returns: [{"content": "...", "metadata": {...}, "distance": 0.15}, ...]
```

**Distance Metric**: Cosine Similarity
- Lower distance = higher relevance
- Range: 0.0 (identical) to 2.0 (opposite)
- Typical relevant chunks: 0.2 - 0.6

### 3. Reranking (Cross-Encoder)
**File**: `backend/store/reranker.py`

```
Model: BAAI/bge-reranker-base
Type: Cross-Encoder (pairwise relevance)
Accuracy: 5-10% better than embedding similarity
Speed: ~200 pairs/sec
Best For: Final ranking after initial retrieval
```

**Reranking Process**:
```python
from backend.store.reranker import rerank_chunks, rerank_and_deduplicate

# Rerank all chunks
ranked = rerank_chunks(query, chunks, top_k=5)

# Rerank + deduplicate by file
final = rerank_and_deduplicate(query, chunks, top_k=5)
# Returns chunks sorted by rerank_score, one per file max
```

**Two-Stage Retrieval Pattern**:
```
Stage 1: Fast Retrieval
  Query → AllMiniLM Embedding → Cosine Search (ChromaDB) → Top 10-15

Stage 2: Accurate Ranking
  Top 10-15 → Cross-Encoder → Rerank → Top 5 (dedup'd)
```

### 4. Hybrid Search & Context Prep
**File**: `backend/store/rag_system.py`

**Priority Order**:
1. **Active File Context** (relevance: 1.0)
   - Code around cursor
   - Highest priority
   - Always included if available

2. **Semantic Search** (relevance: 0.5-0.9)
   - Query embedding → ChromaDB search → Reranking
   - 5 top results after deduplication
   - Relevance based on cross-encoder scores

3. **Fallback** (relevance: 0.8)
   - Full file read if workspace not indexed
   - Emergency backup strategy

**Context Formatting**:
```markdown
## File: src/utils.py (L10-45) [Relevance: 0.92]
```
code here
```

## File: src/helpers.py (L50-80) [Relevance: 0.85]
```
more code
```
```

**Token Limiting**:
- Max: 8000 characters (~2000 tokens)
- Stops adding chunks when limit exceeded
- Maintains quality over quantity

### 5. Integration with Context Harvester
**File**: `backend/agents/context_harvester.py`

Replaces old semantic search with new RAG pipeline:
- Calls `hybrid_search()`
- Parses formatted context into chunks
- Maintains backward compatibility
- Tracks retrieval metrics

## Performance Characteristics

| Stage | Model | Speed | Accuracy |
|-------|-------|-------|----------|
| Embedding | AllMiniLM-L6-v2 | ~5000 texts/sec | ⭐⭐⭐⭐⭐ |
| Search | ChromaDB (cosine) | <50ms for 1000 chunks | ⭐⭐⭐⭐ |
| Reranking | BGE Reranker | ~200 pairs/sec | ⭐⭐⭐⭐⭐ |
| Total RAG | Hybrid pipeline | ~500-1000ms | ⭐⭐⭐⭐⭐ |

## Configuration

### Tuning Parameters

**In `backend/store/rag_system.py`**:
- `n_results`: Initial retrieval count (default: 10-15)
- `top_k`: Final results after dedup (default: 5)
- `max_tokens`: Context token limit (default: 8000)

**In `backend/store/indexer.py`**:
- `chunk_size`: Lines per chunk (default: 60)
- `overlap`: Chunk overlap % (default: 50%)
- `ALLOWED_EXTS`: File types to index

### Model Selection

**Current Models**:
- Embedding: `all-MiniLM-L6-v2` (fast, good quality)
- Reranker: `BAAI/bge-reranker-base` (best for code)

**Alternative Options**:
- Embedding: `all-mpnet-base-v2` (slower, higher accuracy)
- Reranker: `cross-encoder/ms-marco-MiniLMv2-L12-H384-P8` (faster)

## Example Usage

```python
from backend.store.rag_system import hybrid_search
from backend.graph.state import DevMindState

state = DevMindState(
    raw_message="How to fix AttributeError in utils.py",
    file_path="src/utils.py",
    surrounding_code="def process():\n    obj.attribute",
    workspace_root="/project"
)

# Run hybrid search
result = hybrid_search(
    query=f"{state.raw_message} {state.task_summary or ''}",
    surrounding_code=state.surrounding_code,
    file_path=state.file_path,
    workspace_indexed=True,
    top_k=5
)

# Access results
print(result["context"])          # Formatted context for LLM
print(result["metadata"])         # Retrieval stats
print(result["chunks_used"])      # Number of chunks
```

## Troubleshooting

### Slow Embedding
- First load downloads model (~30MB) - expected slow
- Subsequent calls cached in memory
- Consider pre-warm by running `python -m backend.store.embeddings`

### Poor Relevance
- Check workspace is indexed: `devmind interact` → `/index`
- Verify chunk size: increase `chunk_size` if code is fragmented
- Adjust `top_k` parameter in `hybrid_search()`

### Memory Issues
- Models use ~500MB RAM (embedder + reranker)
- Consider CPU-only mode if GPU unavailable
- Load balancing: cache embeddings in Chroma

### ChromaDB Not Found
- Ensure workspace indexed: `/index` command in CLI
- Check `./store/chroma/` directory exists
- Fallback to full file read if index missing

## Future Improvements

1. **Adaptive Retrieval**: Dynamic top_k based on query complexity
2. **Query Expansion**: Rephrase queries for better retrieval
3. **Chunk Optimization**: Dynamic chunking by code structure
4. **Caching**: Cache frequent queries + embeddings
5. **Multi-Model**: Ensemble multiple rerankers
6. **Fine-tuning**: Custom models on codebase-specific data
7. **Streaming**: Stream context to LLM as chunks arrive
