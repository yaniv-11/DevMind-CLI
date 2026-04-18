# backend/store/indexer.py
import os
import hashlib
from backend.store.vector_store import upsert_chunks
from backend.store.chunk_extractor import extract_chunk_metadata

IGNORE_DIRS  = {".git", "__pycache__", "node_modules", ".venv", "venv",
                "dist", "build", ".mypy_cache", ".pytest_cache"}
ALLOWED_EXTS = {".py", ".ts", ".js", ".tsx", ".jsx", ".go",
                ".rs", ".java", ".cpp", ".c", ".md"}

def chunk_file(filepath: str, content: str, chunk_size: int = 60) -> list[dict]:
    """
    Split file into overlapping line chunks with metadata.
    Extracts functions, methods, and classes in each chunk.
    """
    lines = content.splitlines()
    chunks = []
    step = chunk_size // 2   # 50% overlap

    for start in range(0, max(1, len(lines)), step):
        end = min(start + chunk_size, len(lines))
        chunk_lines = lines[start:end]
        chunk_text = "\n".join(chunk_lines)

        chunk_id = hashlib.md5(
            f"{filepath}:{start}:{end}".encode()
        ).hexdigest()
        
        # Extract function/class metadata
        definitions = extract_chunk_metadata(chunk_text, filepath)
        
        # Build definition names list for quick reference
        definition_names = []
        for defn in definitions:
            if defn["type"] == "method" and defn.get("parent"):
                definition_names.append(f"{defn['parent']}.{defn['name']}")
            else:
                definition_names.append(defn["name"])

        chunks.append({
            "id": chunk_id,
            "content": chunk_text,
            "metadata": {
                "file": filepath,
                "line_start": start + 1,
                "line_end": end,
                "language": os.path.splitext(filepath)[-1].lstrip("."),
                "definitions": definition_names,  # Quick lookup
                "has_function": any(d["type"] in ["function", "method"] for d in definitions),
                "has_class": any(d["type"] == "class" for d in definitions)
            }
        })

        if end >= len(lines):
            break

    return chunks

def index_workspace(workspace_root: str) -> dict:
    """Walk workspace and index all code files into ChromaDB."""
    total_files = 0
    total_chunks = 0
    errors = []

    for dirpath, dirnames, filenames in os.walk(workspace_root):
        # Prune ignored dirs in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for filename in filenames:
            ext = os.path.splitext(filename)[-1].lower()
            if ext not in ALLOWED_EXTS:
                continue

            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, workspace_root)

            try:
                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                if not content.strip():
                    continue

                chunks = chunk_file(rel_path, content)
                if chunks:
                    upsert_chunks(chunks)
                    total_chunks += len(chunks)
                    total_files += 1

            except Exception as e:
                errors.append(f"{rel_path}: {str(e)}")

    return {
        "indexed_files": total_files,
        "total_chunks": total_chunks,
        "errors": errors
    }