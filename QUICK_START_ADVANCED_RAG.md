# Quick Start: Advanced RAG Features

## Installation (2 minutes)

```bash
cd /path/to/DevMind
pip install -r requirements.txt
```

**New packages installed**:
- `rank-bm25` - BM25 keyword search
- `langsmith` - Tracing and monitoring (optional)

## Setup (5 minutes)

### 1. Index Your Codebase

```bash
devmind interact
# In the prompt:
/index
# Wait for indexing to complete
```

This extracts:
- All code files (.py, .ts, .js, .jsx, .tsx, .go, .java, .cpp, .c, .md)
- Functions, methods, classes with metadata
- Line numbers and signatures
- BM25 keyword index

### 2. Optional: Enable LangSmith Tracing

```bash
export LANGSMITH_API_KEY=your_api_key_here
```

Then restart DevMind. All operations will be traced and visible at https://smith.langchain.com

## Usage Examples

### Example 1: Find Bug in Authentication

```
DevMind > fix the login bug where null password crashes the app
```

**What happens**:
1. **Semantic search** finds code about login/password
2. **Keyword search** finds mentions of "null", "password", "crash"
3. **Combined and reranked** returns top 10 chunks
4. **Enhanced with metadata**: Shows which functions are in each chunk
5. **LLM analyzes** with full context
6. **LangSmith tracks** the entire flow

**Output includes**:
```
Found context in 3 functions:
  [1] auth.py (L45-50) | Functions: authenticate, validate_password
  [2] utils.py (L10-15) | Functions: safe_null_check
  [3] models.py (L78-85) | Functions: User.set_password
```

### Example 2: Apply LLM Suggestion with Chunk Reference

After LLM suggests a fix:

```python
from backend.store.file_editor import FileEditor

editor = FileEditor("/path/to/project")

# LLM suggests: Fix in auth.py, lines 45-50
result = editor.edit_chunk(
    file_path="src/auth.py",
    start_line=45,
    end_line=50,
    new_content="""def authenticate(user, pwd):
    if not user or not pwd:
        return None
    if not validate_password(pwd):
        return None
    return create_token(user)""",
    description="Fixed null password crash",
    chunk_ref="chunk_123"  # Reference from retrieval
)

print(result)
# {
#     'status': 'success',
#     'file': '/path/to/project/src/auth.py',
#     'lines_changed': 6,
#     'backup': './store/file_backups/auth.py.20260418_143022.bak',
#     'chunk_ref': 'chunk_123'
# }

# Verify syntax
validation = editor.validate_syntax("src/auth.py")
print(validation)  # {'status': 'valid', 'file': '...'}

# View history
history = editor.get_edit_history("src/auth.py")
for h in history:
    print(f"{h['timestamp']}: {h['description']} (from chunk {h['chunk_ref']})")

# Rollback if needed
editor.rollback_to_backup("./store/file_backups/auth.py.20260418_143022.bak")
```

### Example 3: Monitor with LangSmith

After setting `LANGSMITH_API_KEY`:

1. **Run a query**:
   ```
   DevMind > implement the payment processing function
   ```

2. **Go to dashboard**: https://smith.langchain.com/
   - See your project "DevMind"
   - Click on the trace
   - View:
     - Query that was executed
     - Chunks retrieved (with scores)
     - LLM response
     - Latency breakdown
     - Token usage

3. **Provide feedback** (optional):
   - 👍 = Good suggestion
   - 👎 = Bad suggestion
   - This helps improve the system

## Understanding Scores

Each chunk has multiple scores:

```python
chunk = {
    "content": "def authenticate()...",
    "semantic_score": 0.82,      # How similar to query semantically
    "keyword_score": 0.45,       # BM25 keyword relevance
    "hybrid_score": 0.70,        # Combined (60% sem + 40% kw)
    "rerank_score": 0.87,        # Cross-encoder final ranking
    "final_score": 0.78          # Ultimate score (50% rerank + 50% hybrid)
}
```

**Higher is better**. Final score used for ranking.

## Configuration Cheat Sheet

### Adjust Retrieval Quality

**In `backend/store/hybrid_rag.py`**:

```python
# Get more/fewer results
results = hybrid_semantic_keyword_search(
    query=query,
    top_k=10  # Change: 5 (fast), 10 (balanced), 15 (thorough)
)

# Adjust semantic vs keyword balance
weights={
    "semantic": 0.6,  # Change: 0.5 (balanced), 0.7 (favor semantic)
    "keyword": 0.4    # Change: 0.5 (balanced), 0.3 (favor semantic)
}
```

### Adjust Chunk Size

**In `backend/store/indexer.py`**:

```python
def chunk_file(filepath: str, content: str, chunk_size: int = 60):
    # Change chunk_size:
    # 40 = More granular, finds specific functions
    # 60 = Balanced (recommended)
    # 100 = More context, may include unrelated code
```

Then re-index:
```
devmind interact
/index
```

## Common Workflows

### Workflow 1: Find and Fix a Bug

```
1. Ask DevMind
   DevMind > why does the login crash with null password?

2. LLM analyzes chunks from:
   - authenticate() function (semantic match)
   - null_check() function (keyword match)
   - password validation (both)

3. LLM suggests fix with chunk references

4. Apply edit with chunk_ref
   editor.edit_chunk(..., chunk_ref=chunks[0]["id"])

5. Verify syntax
   editor.validate_syntax()

6. Monitor in LangSmith
   - See what was searched
   - See what was edited
   - See LLM reasoning
```

### Workflow 2: Implement New Feature

```
1. Ask DevMind
   DevMind > add email notification to payment processing

2. Receives chunks for:
   - existing payment functions
   - existing notification code
   - email service integrations

3. LLM suggests implementation

4. Apply multiple edits
   - Add email function
   - Update payment callback
   - Add queue handling

5. Track all edits with chunk_refs

6. Roll back if needed
   editor.rollback_to_backup(backup_path)
```

### Workflow 3: Debug Production Issue

```
1. Ask DevMind
   DevMind > what could cause race condition in database.py?

2. Gets both:
   - Semantically similar concurrency issues
   - Keywords: "race", "condition", "database", "lock"

3. LLM analyzes:
   - Where locks are missing
   - Where timing issues can occur
   - What database operations race

4. Apply suggested locks and synchronization

5. LangSmith trace shows:
   - What code was analyzed
   - LLM reasoning
   - Changes made
   - Can replay to debug
```

## Troubleshooting

### Problem: Slow Retrieval (~2 seconds)

**Solution**: First run is slow (model download). Subsequent runs ~500ms.

### Problem: Poor Relevance

**Solutions**:
1. Re-index: `devmind interact` → `/index`
2. Increase top_k: `top_k=15` instead of 10
3. Adjust weights: `semantic=0.7, keyword=0.3` for semantic-focused
4. Reduce chunk_size: 40 instead of 60 for finer granularity

### Problem: File Edit Failed

**Solutions**:
1. Check file exists in workspace
2. Verify line numbers: `editor.read_file("src/file.py")`
3. Use replace_text instead: easier to find exact text
4. Check for encoding issues: ensure UTF-8

### Problem: No LangSmith Traces

**Solutions**:
1. Set LANGSMITH_API_KEY: `export LANGSMITH_API_KEY=...`
2. Verify key is valid at smith.langchain.com
3. Restart DevMind after setting key
4. Check network connectivity

## Performance Tips

### Fast Retrieval (for production)
```python
top_k=5           # Fewer results
n_semantic=10     # Fewer candidates
n_keyword=10      # Fewer candidates
```
**Speed**: ~300ms | **Quality**: Good

### Balanced (recommended)
```python
top_k=10          # Standard
n_semantic=15     # Default
n_keyword=15      # Default
```
**Speed**: ~500ms | **Quality**: Excellent

### Thorough Search (for complex bugs)
```python
top_k=15          # More results
n_semantic=20     # More candidates
n_keyword=20      # More candidates
```
**Speed**: ~700ms | **Quality**: Excellent+

## Next Steps

1. **Try it**: `devmind interact` → Ask a question
2. **Monitor**: Check LangSmith dashboard
3. **Experiment**: Try different top_k and weights
4. **Automate**: Build CLI commands around the APIs
5. **Customize**: Fork for your specific use case

## Documentation

- **[ADVANCED_RAG_GUIDE.md](ADVANCED_RAG_GUIDE.md)** - Complete guide with architecture
- **[RAG_ARCHITECTURE.md](RAG_ARCHITECTURE.md)** - Technical details
- **[RAG_API_REFERENCE.md](RAG_API_REFERENCE.md)** - Full API docs

## Getting Help

- Check docs above for detailed explanations
- LangSmith traces show exactly what happened
- Edit history shows all changes made
- Can always rollback to backups
- Run with `LANGSMITH_API_KEY` for full debugging visibility
