import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from backend.graph.state import DevMindState
from backend.config import settings

ORCHESTRATOR_PROMPT = """You are the orchestrator for DevMind, a codebase-aware coding assistant.

Your ONLY job: classify the trigger and output an execution plan as JSON.
You never write code. You never diagnose. You only plan.

Intent options:
- fix_error       → traceback, exception, or diagnostic error present
- explain_code    → user asks what/how/why about existing code  
- write_feature   → user asks to add/build/create/implement
- answer_question → general question, no code change needed
- find_usages     → user asks where something is called/imported

Agent options (always start with context_harvester):
- context_harvester  → always first
- reasoning_agent    → only for fix_error, explain_code
- code_writer        → for fix_error, write_feature
- validator          → for fix_error, write_feature
- memory_agent       → always last

Return ONLY this JSON, no explanation, no markdown:
{
  "intent": "<intent>",
  "confidence": <0.0-1.0>,
  "agent_plan": ["context_harvester", ...],
  "task_summary": "<one sentence>",
  "needs_reasoning": <true|false>,
  "needs_validation": <true|false>
}"""

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name=settings.groq_model,
    temperature=0.0,    
    model_kwargs={"response_format": {"type": "json_object"}}
)

def orchestrator_node(state: DevMindState) -> DevMindState:
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
        # fallback — if JSON parsing fails, default to safe plan
        plan = {
            "intent": "answer_question",
            "confidence": 0.5,
            "agent_plan": ["context_harvester"],
            "task_summary": state.raw_message,
            "needs_reasoning": False,
            "needs_validation": False
        }

    return state.model_copy(update={
        "intent": plan["intent"],
        "confidence": plan["confidence"],
        "agent_plan": plan["agent_plan"],
        "task_summary": plan["task_summary"],
        "needs_reasoning": plan["needs_reasoning"],
        "needs_validation": plan["needs_validation"]
    })
