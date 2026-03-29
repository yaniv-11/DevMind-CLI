from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from backend.graph.state import DevMindState
from backend.config import settings

REASONING_PROMPT = """You are a senior engineer diagnosing a bug.

Given the error and relevant code context, identify:
1. The ROOT CAUSE (not just the symptom)
2. Which exact lines are affected
3. A hypothesis for the fix

Be specific. Reference actual variable names, function names, and line numbers from the code.
Do not write the fix yet. Only diagnose."""

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name=settings.groq_model,
    temperature=0.1
)

def reasoning_agent_node(state: DevMindState) -> DevMindState:
    if not state.context_chunks:
        return state.model_copy(update={"root_cause": "No context available to reason about."})

    context_text = "\n\n".join([
        f"# {c['file']} (lines {c['lines']})\n{c['content']}"
        for c in state.context_chunks
    ])

    messages = [
        SystemMessage(content=REASONING_PROMPT),
        HumanMessage(content=f"Error:\n{state.raw_message}\n\nCode context:\n{context_text}")
    ]

    response = llm.invoke(messages)

    return state.model_copy(update={
        "root_cause": response.content,
        "fix_hypothesis": response.content
    })