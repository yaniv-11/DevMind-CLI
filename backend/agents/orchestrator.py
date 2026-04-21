import json
import asyncio
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from backend.graph.state import DevMindState
from backend.config import settings
from backend.integrations.langsmith_tracker import get_tracker

ORCHESTRATOR_PROMPT = """You are DevMind orchestrator - coordinate parallel agent execution.

Analyze the trigger and output a PARALLEL execution plan as JSON.
Agents run together, not sequentially. Each agent adds to the result.

Intent options:
- fix_error       → traceback, exception, or diagnostic error present
- explain_code    → user asks what/how/why about existing code  
- write_feature   → user asks to add/build/create/implement
- answer_question → general question, no code change needed
- find_usages     → user asks where something is called/imported

Agent groups (executed in parallel within groups, sequentially between):
Group 1 (always):
  - context_harvester  → retrieve relevant code chunks

Group 2 (optional, parallel):
  - reasoning_agent    → diagnose/understand the issue
  - memory_agent       → access project knowledge

Group 3 (optional, parallel):
  - code_writer        → suggest code changes
  - validator          → check for issues

Agents communicate continuously, not blocked by each other.

Return ONLY this JSON, no explanation:
{
  "intent": "<intent>",
  "confidence": <0.0-1.0>,
  "agent_groups": [
    ["context_harvester"],
    ["reasoning_agent", "memory_agent"],
    ["code_writer", "validator"]
  ],
  "task_summary": "<one sentence>",
  "parallel_execution": true
}"""

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name=settings.groq_model,
    temperature=0.0,    
    model_kwargs={"response_format": {"type": "json_object"}}
)

def orchestrator_node(state: DevMindState) -> DevMindState:
    """Orchestrate parallel agent execution."""
    tracker = get_tracker()
    
    trigger_text = f"""
Source: {state.source}
Message: {state.raw_message}
File: {state.file_path or 'unknown'}
Line: {state.line_number or 'unknown'}

Surrounding code:
{state.surrounding_code or 'not provided'}

Terminal output:
{state.terminal_output or 'not provided'}
""".strip()

    messages = [
        SystemMessage(content=ORCHESTRATOR_PROMPT),
        HumanMessage(content=trigger_text)
    ]

    response = llm.invoke(messages)

    try:
        plan = json.loads(response.content)
    except json.JSONDecodeError:
        # fallback
        plan = {
            "intent": "answer_question",
            "confidence": 0.5,
            "agent_groups": [["context_harvester"]],
            "task_summary": state.raw_message,
            "parallel_execution": True
        }

    # Log orchestration
    tracker.trace_rag_retrieval(f"orchestration", {"plan": plan})
    
    return state.model_copy(update={
        "intent": plan["intent"],
        "confidence": plan["confidence"],
        "agent_plan": plan.get("agent_groups", [["context_harvester"]]),
        "task_summary": plan["task_summary"],
        "parallel_execution": plan.get("parallel_execution", True)
    })
