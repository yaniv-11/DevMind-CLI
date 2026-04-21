from backend.graph.state import DevMindState
from langgraph.types import Send

def route_after_orchestrator(state: DevMindState) -> list[Send] | str:
    """Route to all agents in first group (parallel execution)."""
    agent_groups = state.agent_plan
    
    if not agent_groups or len(agent_groups) == 0:
        return "context_harvester"
    
    # LangGraph parallel execution: Send to all agents in first group
    first_group = agent_groups[0]
    return [Send(agent_name, state) for agent_name in first_group]

def route_after_harvester(state: DevMindState) -> list[Send] | str:
    """After context harvester, route to second agent group (parallel)."""
    agent_groups = state.agent_plan
    
    if len(agent_groups) < 2:
        return "chat_agent"
    
    second_group = agent_groups[1]
    return [Send(agent_name, state) for agent_name in second_group]

def route_after_parallel_agents(state: DevMindState) -> list[Send] | str:
    """After second group, route to third group if exists."""
    agent_groups = state.agent_plan
    
    if len(agent_groups) < 3:
        return "chat_agent"
    
    third_group = agent_groups[2]
    return [Send(agent_name, state) for agent_name in third_group]

def route_to_respond(state: DevMindState) -> str:
    """Final route to response generation."""
    return "chat_agent"