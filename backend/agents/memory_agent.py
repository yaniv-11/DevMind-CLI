# backend/agents/memory_agent.py
import json
import os
from datetime import datetime
from backend.graph.state import DevMindState

MEMORY_FILE = "./store/project_memory.json"

def _load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {
        "project_conventions": [],
        "past_fixes": [],
        "known_files": [],
        "language": None,
        "frameworks": []
    }

def _save_memory(memory: dict):
    os.makedirs("./store", exist_ok=True)
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)

def memory_agent_node(state: DevMindState) -> DevMindState:
    memory = _load_memory()

    # Record this interaction
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "intent": state.intent,
        "file": state.file_path,
        "summary": state.task_summary,
        "root_cause": state.root_cause,
        "fix_applied": state.patch is not None and "error" not in (state.patch or {}),
        "validation_passed": state.validation_passed
    }

    memory["past_fixes"].append(entry)

    # Keep only last 50 interactions
    memory["past_fixes"] = memory["past_fixes"][-50:]

    # Track files seen
    if state.file_path and state.file_path not in memory["known_files"]:
        memory["known_files"].append(state.file_path)

    # Infer language from file extension
    if state.file_path and memory["language"] is None:
        ext = os.path.splitext(state.file_path)[-1]
        lang_map = {".py": "Python", ".ts": "TypeScript", ".js": "JavaScript",
                    ".go": "Go", ".rs": "Rust", ".java": "Java"}
        memory["language"] = lang_map.get(ext, "unknown")

    _save_memory(memory)

    return state.model_copy(update={})  # Return updated copy, not same object