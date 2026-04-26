"""
RAG System Module Reference & API Documentation
Quick lookup for all RAG-related modules and their functions.
"""

# ============================================================================
# Module 1: Embeddings (backend/store/embeddings.py)
# ============================================================================
"""
AllMiniLM-L6-v2 Embedding Model Management

Key Features:
- 384-dimensional vectors
- Fast inference (~5000 texts/sec)
- Cached in memory after first load
- Best for code & technical text
"""

def get_embedding_model():
    """
    Load and return the SentenceTransformer model.
    First call downloads ~30MB model. Subsequent calls return cached instance.
    
    Returns:
        SentenceTransformer: The all-MiniLM-L6-v2 model
    """

def embed_text(text: str) -> list[float]:
    """
    Embed a single text string into a 384-dimensional vector.
    
    Args:
        text: Text to embed (code snippet, query, etc.)
        
    Returns:
        list[float]: Vector of size 384
        
    Example:
        >>> vec = embed_text("def hello(): pass")
        >>> len(vec)
        384
        >>> vec[0]
        0.123456
    """

def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed multiple texts efficiently in batch.
    Much faster than calling embed_text() in loop.
    
    Args:
        texts: List of texts to embed
        
    Returns:
        list[list[float]]: List of 384-dim vectors
        
    Example:
        >>> vecs = embed_texts(["code1", "code2", "code3"])
        >>> len(vecs)
        3
        >>> len(vecs[0])
        384
    """

def similarity_score(embedding1: list[float], embedding2: list[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    Useful for comparing code snippets directly without ChromaDB.
    
    Args:
        embedding1: First embedding vector
        embedding2: Second embedding vector
        
    Returns:
        float: Similarity score from 0.0 (dissimilar) to 1.0 (identical)
        
    Example:
        >>> vec1 = embed_text("def foo(): pass")
        >>> vec2 = embed_text("def bar(): pass")
        >>> score = similarity_score(vec1, vec2)
        >>> score
        0.78
    """


# ============================================================================
# Module 2: Vector Store (backend/store/vector_store.py)
# ============================================================================
"""
ChromaDB Vector Database Management

Key Features:
- Persistent storage at ./store/chroma/
- Cosine similarity search
- Efficient bulk operations
- Metadata filtering support
"""

def get_collection():
    """
    Get or create the 'devmind_codebase' ChromaDB collection.
    Initializes persistent client on first call.
    
    Returns:
        chromadb.Collection: Vector database collection
        
    Example:
        >>> collection = get_collection()
        >>> collection.count()
        3250  # Number of indexed chunks
    """

def upsert_chunks(chunks: list[dict]):
    """
    Add or update chunks in the vector database.
    Called by indexer.py during workspace indexing.
    
    Args:
        chunks: List of dicts with keys:
            - id (str): Unique identifier (MD5 hash)
            - content (str): Code snippet text
            - metadata (dict): {file, line_start, line_end, language}
            
    Example:
        >>> chunks = [
        ...     {
        ...         "id": "abc123",
        ...         "content": "def process():\n    pass",
        ...         "metadata": {
        ...             "file": "utils.py",
        ...             "line_start": 10,
        ...             "line_end": 11,
        ...             "language": "python"
        ...         }
        ...     }
        ... ]
        >>> upsert_chunks(chunks)
    """

def query_chunks(query: str, n_results: int = 6) -> list[dict]:
    """
    Search for code chunks similar to query.
    Uses embeddings for semantic search.
    
    Args:
        query: Search query (natural language or code)
        n_results: Number of chunks to return (default: 6, optimal: 10-15)
        
    Returns:
        list[dict]: Chunks with keys:
            - content (str): Code snippet
            - metadata (dict): File path, line numbers, language
            - distance (float): Cosine distance (0=similar, 2=dissimilar)
            
    Example:
        >>> results = query_chunks("fix null pointer", n_results=10)
        >>> for r in results:
        ...     print(f"{r['metadata']['file']}: {r['distance']:.2f}")
        utils.py: 0.35
        auth.py: 0.42
    """


# ============================================================================
# Module 3: Reranker (backend/store/reranker.py)
# ============================================================================
"""
Cross-Encoder Reranking for Better Relevance

Key Features:
- Uses BGE reranker model
- 5-10% better accuracy than embedding similarity
- Slower but more accurate than stage 1
- Deduplicates results by file
"""

def get_reranker_model():
    """
    Load and return the BGE reranker cross-encoder model.
    First call downloads ~500MB. Subsequent calls use cached instance.
    
    Returns:
        CrossEncoder: The BAAI/bge-reranker-base model
    """

def rerank_chunks(query: str, chunks: list[dict], top_k: int = None) -> list[dict]:
    """
    Rerank chunks by relevance to query using cross-encoder.
    
    Args:
        query: Search query
        chunks: Initial chunks from ChromaDB
        top_k: Optional limit on returned results
        
    Returns:
        list[dict]: Chunks sorted by rerank_score (descending)
                    Added key: rerank_score (0.0-1.0)
        
    Example:
        >>> initial = query_chunks("authentication bug", n_results=10)
        >>> reranked = rerank_chunks("authentication bug", initial, top_k=5)
        >>> for chunk in reranked:
        ...     print(f"Score: {chunk['rerank_score']:.3f}")
        Score: 0.945
        Score: 0.823
        Score: 0.715
    """

def rerank_and_deduplicate(query: str, chunks: list[dict], top_k: int = 5) -> list[dict]:
    """
    Rerank chunks AND deduplicate to ensure one chunk per file.
    Best for final retrieval stage.
    
    Args:
        query: Search query
        chunks: Initial chunks from ChromaDB
        top_k: Number of unique files in result (default: 5)
        
    Returns:
        list[dict]: Top K chunks from different files, sorted by rerank_score
        
    Example:
        >>> initial = query_chunks("parse json error", n_results=15)
        >>> final = rerank_and_deduplicate("parse json error", initial, top_k=5)
        >>> len(final)
        5  # Maximum 5 different files
    """


# ============================================================================
# Module 4: RAG System (backend/store/rag_system.py)
# ============================================================================
"""
Complete Retrieval Augmented Generation Pipeline

Key Features:
- Two-stage retrieval (fast + accurate)
- Hybrid search with fallbacks
- Context formatting for LLM
- Token limit enforcement
"""

def semantic_search(query: str, n_results: int = 10) -> list[dict]:
    """
    Complete semantic search pipeline: embed → retrieve → rerank.
    
    Args:
        query: Search query
        n_results: Number of results after reranking
        
    Returns:
        list[dict]: Reranked chunks with rerank_score
        
    Example:
        >>> results = semantic_search("database connection pool", n_results=5)
        >>> results[0]["rerank_score"]
        0.92
    """

def prepare_context_for_llm(chunks: list[dict], max_tokens: int = 8000) -> tuple[str, dict]:
    """
    Format retrieved chunks into context string for LLM input.
    Includes file paths, line numbers, and relevance scores.
    
    Args:
        chunks: Retrieved and reranked chunks
        max_tokens: Max tokens to include (~1 token = 4 chars)
        
    Returns:
        tuple: (context_string, metadata_dict)
        
    Example:
        >>> chunks = rerank_and_deduplicate(query, initial)
        >>> context, meta = prepare_context_for_llm(chunks)
        >>> print(context)
        ## File: auth.py (L10-45) [Relevance: 0.95]
        ```
        def authenticate():
            ...
        ```
        
        >>> print(meta)
        {
            'file_count': 3,
            'chunk_count': 3,
            'token_estimate': 1250,
            'files': ['auth.py', 'utils.py', 'db.py']
        }
    """

def hybrid_search(
    query: str,
    surrounding_code: str = None,
    file_path: str = None,
    workspace_indexed: bool = True,
    top_k: int = 5
) -> dict:
    """
    Complete hybrid RAG pipeline with all three strategies.
    
    Priority:
    1. Active file context (highest)
    2. Semantic search + reranking
    3. Fallback full file read (lowest)
    
    Args:
        query: User question/request
        surrounding_code: Code around cursor (from editor)
        file_path: Path to active file
        workspace_indexed: Whether workspace is in ChromaDB
        top_k: Number of final results
        
    Returns:
        dict with keys:
            - context (str): Formatted context for LLM
            - metadata (dict): Retrieval statistics
            - chunks_used (int): Number of chunks retrieved
            - retrieval_method (str): Strategy used
        
    Example:
        >>> result = hybrid_search(
        ...     query="fix the race condition in process()",
        ...     surrounding_code="def process():\n    lock.acquire()\n    ...",
        ...     file_path="src/processor.py",
        ...     workspace_indexed=True,
        ...     top_k=5
        ... )
        >>> print(result["context"])
        ## File: processor.py (L50-80) [Relevance: 1.0]
        ```
        def process():
            ...
        ```
        ...
        
        >>> print(result["metadata"]["file_count"])
        3
    """


# ============================================================================
# Module 5: Context Harvester (backend/agents/context_harvester.py)
# ============================================================================
"""
Integration point between RAG and LangGraph state.
Uses hybrid_search to populate context_chunks in state.
"""

def context_harvester_node(state: DevMindState) -> DevMindState:
    """
    LangGraph node that runs RAG system and updates state.
    Called during agent graph execution.
    
    Input State Properties:
        - raw_message (str): User query
        - task_summary (str): Inferred task
        - workspace_root (str): Root directory
        - surrounding_code (str): Code around cursor
        - file_path (str): Active file path
        
    Output State Update:
        - context_chunks (list[dict]): Retrieved chunks
        
    Example:
        >>> state = DevMindState(
        ...     raw_message="fix the bug",
        ...     surrounding_code="def broken():\n    pass"
        ... )
        >>> new_state = context_harvester_node(state)
        >>> len(new_state.context_chunks)
        3
        >>> new_state.context_chunks[0]["file"]
        "src/broken.py"
    """


# ============================================================================
# Performance Benchmarks
# ============================================================================
"""
Typical latencies (on CPU):

Operation                    Time      Notes
────────────────────────────────────────────────────────
Embed single text           ~2-5ms    First load ~500ms
Embed batch (10)            ~20ms     Amortized 2ms/text
ChromaDB search (1000 chunks) ~30ms   Cosine similarity
Rerank 15 chunks            ~300ms    Cross-encoder inference
Full RAG pipeline           ~500ms    Total time to context

Memory Usage:
────────────────────────────────────────────────────────
Embedding model (AllMiniLM)  ~100MB   384-dim vectors
Reranker model (BGE)         ~400MB   Cross-encoder
ChromaDB (10K chunks)        ~50MB    Vectors + metadata
────────────────────────────
Total RAM                    ~550MB   Combined models
"""


# ============================================================================
# Configuration & Tuning
# ============================================================================
"""
Key Parameters to Tune:

In backend/store/rag_system.py:
  - semantic_search(n_results=10)      # Initial retrieval
  - rerank_and_deduplicate(top_k=5)    # Final results
  - prepare_context_for_llm(max_tokens=8000)  # Token limit

In backend/store/indexer.py:
  - chunk_size = 60              # Lines per chunk
  - overlap = 50%                # Chunk overlap
  - ALLOWED_EXTS                 # File types

In backend/agents/context_harvester.py:
  - top_k: int = 5               # Final chunks after dedup

Tuning Strategy:
1. Baseline: Use defaults
2. If poor results: Increase n_results to 15-20
3. If slow: Reduce top_k or disable reranker
4. If memory issues: Use smaller models (all-MiniLM-L6-v2 is already small)
5. If missing files: Increase ALLOWED_EXTS
"""
