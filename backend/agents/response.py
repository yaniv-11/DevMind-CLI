from backend.graph.state import DevMindState

# ── Respond node ────────────────────────────────────────────────
def respond_node(state: DevMindState) -> DevMindState:
    response = {
        "intent":           state.intent,
        "summary":          state.task_summary,
        "root_cause":       state.root_cause,
        "patch":            state.patch,
        "validation_issues":state.validation_issues,
        "confidence":       state.confidence,
        "context_files":    list({c["file"] for c in (state.context_chunks or [])})
    }
    return state.model_copy(update={"response": response})