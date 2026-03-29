# backend/agents/chat_agent.py
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from backend.graph.state import DevMindState
from backend.config import settings

CHAT_PROMPT = """You are DevMind, an expert AI coding assistant.
You are helping the user understand their codebase or complex questions.

Use the provided context to accurately answer the user's question.
If the context isn't relevant, you can answer from your general knowledge, but prioritize the codebase context when applicable.

Format your response in beautiful Markdown. Be professional, concise, and helpful."""

llm = ChatGroq(
    api_key=settings.groq_api_key,
    model_name=settings.groq_model,
    temperature=0.3
)

def chat_agent_node(state: DevMindState) -> DevMindState:
    context_text = "No context available."
    if state.context_chunks:
        context_text = "\n\n".join([
            f"# {c['file']} (lines {c['lines']})\n{c['content']}"
            for c in state.context_chunks
        ])

    task = f"""User Question/Task: {state.raw_message}

Retrieved Code Context:
{context_text}
"""

    messages = [
        SystemMessage(content=CHAT_PROMPT),
        HumanMessage(content=task)
    ]

    response = llm.invoke(messages)

    return state.model_copy(update={"chat_response": response.content})
