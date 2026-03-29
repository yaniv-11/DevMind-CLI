from typing import Optional, List, Literal
from pydantic import BaseModel

class TriggerSource(str):
    DIAGNOSTIC  = "diagnostic"
    USER_MESSAGE = "user_message"
    TERMINAL    = "terminal"
    TEST_RUNNER = "test_runner"
    HOTKEY      = "hotkey"

class DevMindState(BaseModel):
    # --- Input (set by FastAPI before graph starts) ---
    source: str                          # where trigger came from
    raw_message: str                     # the user's text or error message
    file_path: Optional[str] = None      # active file in editor
    line_number: Optional[int] = None    # error line
    surrounding_code: Optional[str] = None
    terminal_output: Optional[str] = None
    workspace_root: Optional[str] = None # user's project folder

    # --- Orchestrator output ---
    intent: Optional[Literal[
        "fix_error",
        "explain_code",
        "write_feature",
        "answer_question",
        "find_usages"
    ]] = None
    confidence: Optional[float] = None
    agent_plan: Optional[List[str]] = None   # ordered list of agents to run
    task_summary: Optional[str] = None
    needs_reasoning: bool = False
    needs_validation: bool = False

    # --- Context harvester output ---
    context_chunks: Optional[List[dict]] = None   # relevant file slices
    import_graph: Optional[dict] = None

    # --- Reasoning agent output ---
    root_cause: Optional[str] = None
    affected_lines: Optional[List[int]] = None
    fix_hypothesis: Optional[str] = None

    # --- Code writer output ---
    patch: Optional[dict] = None   # {file, line, old_code, new_code}

    # --- Validator output ---
    validation_passed: Optional[bool] = None
    confidence_score: Optional[float] = None
    validation_issues: Optional[List[str]] = None

    # --- Final response ---
    response: Optional[dict] = None
    chat_response: Optional[str] = None
    error: Optional[str] = None