# backend/agents/code_writer.py
import json
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from backend.graph.state import DevMindState
from backend.config import settings

CODE_WRITER_PROMPT = """You are an expert code writer. You write minimal, precise fixes.

Rules:
- Write ONLY the fix. No explanation outside the JSON.
- Match the existing code style exactly — same indentation, same naming.
- Output ONLY this JSON, nothing else:

{
  "file": "<filename>",
  "line_start": <integer>,
  "line_end": <integer>,
  "old_code": "<exact lines being replaced>",
  "new_code": "<replacement lines>",
  "explanation": "<one sentence why>"
}

If you cannot produce a fix, output:
{"error": "cannot fix", "reason": "<why>"}"""

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name=settings.groq_model,
    temperature=0.1,
    model_kwargs={"response_format": {"type": "json_object"}}
)

def code_writer_node(state: DevMindState) -> DevMindState:
    if not state.context_chunks:
        return state.model_copy(update={
            "patch": {"error": "no context", "reason": "Context harvester returned nothing"}
        })

    context_text = "\n\n".join([
        f"# {c['file']} (lines {c['lines']})\n{c['content']}"
        for c in state.context_chunks
    ])

    task = f"""Task: {state.task_summary}

Error: {state.raw_message or 'N/A'}

Root cause diagnosis:
{state.root_cause or 'Not analyzed yet'}

Code context:
{context_text}

File to fix: {state.file_path or 'unknown'}
Error line: {state.line_number or 'unknown'}"""

    messages = [
        SystemMessage(content=CODE_WRITER_PROMPT),
        HumanMessage(content=task)
    ]

    response = llm.invoke(messages)

    try:
        patch = json.loads(response.content)
    except json.JSONDecodeError:
        patch = {
            "error": "parse_failed",
            "reason": "Model returned non-JSON",
            "raw": response.content[:500]
        }

    return state.model_copy(update={"patch": patch})