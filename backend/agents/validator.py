# backend/agents/validator.py
import ast
from backend.graph.state import DevMindState

def validator_node(state: DevMindState) -> DevMindState:
    patch = state.patch

    # No patch to validate
    if not patch or "error" in patch:
        return state.model_copy(update={
            "validation_passed": False,
            "confidence_score": 0.0,
            "validation_issues": ["No valid patch to validate"]
        })

    issues = []
    confidence = 1.0

    new_code = patch.get("new_code", "")

    # Check 1: is the new code valid Python syntax?
    if new_code:
        try:
            ast.parse(new_code)
        except SyntaxError as e:
            issues.append(f"Syntax error in patch: {str(e)}")
            confidence -= 0.5

    # Check 2: did model hallucinate an unknown file?
    if patch.get("file") and state.file_path:
        import os
        patch_file = os.path.basename(patch["file"])
        state_file = os.path.basename(state.file_path)
        if patch_file != state_file:
            issues.append(f"Patch targets {patch_file} but active file is {state_file}")
            confidence -= 0.2

    # Check 3: does old_code actually exist in context?
    old_code = patch.get("old_code", "")
    if old_code and state.context_chunks:
        found = any(
            old_code.strip() in chunk["content"]
            for chunk in state.context_chunks
        )
        if not found:
            issues.append("old_code not found in context — model may have hallucinated it")
            confidence -= 0.3

    confidence = max(0.0, round(confidence, 2))
    passed = len(issues) == 0 and confidence >= 0.6

    return state.model_copy(update={
        "validation_passed": passed,
        "confidence_score": confidence,
        "validation_issues": issues
    })