from backend.graph.state import DevMindState

def route_after_orchestrator(state: DevMindState) -> str:
    """Always go to context harvester first."""
    return "context_harvester"

def route_after_harvester(state: DevMindState) -> str:
    """After harvesting context, go to reasoning if needed, else code writer."""
    if state.intent in ["answer_question", "explain_code", "find_usages"]:
        return "chat_agent"
    if state.needs_reasoning:
        return "reasoning_agent"
    if "code_writer" in state.agent_plan:
        return "code_writer"
    return "chat_agent"

def route_after_reasoning(state: DevMindState) -> str:
    """After reasoning, go to code writer if in plan, else respond."""
    if "code_writer" in state.agent_plan:
        return "code_writer"
    return "chat_agent"
def route_after_code_writer(state: DevMindState) -> str:
    """After writing code, validate if needed."""
    if state.needs_validation:
        return "validator"
    return "respond"

def route_after_validator(state: DevMindState) -> str:
    return "respond"