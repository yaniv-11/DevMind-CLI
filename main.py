# backend/main.py
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from langgraph.graph import StateGraph, END

from backend.graph.state import DevMindState
from backend.graph.edges import (
    route_after_orchestrator,
    route_after_harvester,
    route_after_reasoning,
    route_after_code_writer,
    route_after_validator
)
from backend.agents.orchestrator      import orchestrator_node
from backend.agents.context_harvester import context_harvester_node
from backend.agents.reasoning_agent   import reasoning_agent_node
from backend.agents.code_writer       import code_writer_node
from backend.agents.validator         import validator_node
from backend.agents.memory_agent      import memory_agent_node
from backend.agents.chat_agent        import chat_agent_node
from backend.models.schemas           import TriggerRequest, DevMindResponse, IndexRequest
from backend.store.indexer            import index_workspace

app = FastAPI(title="DevMind", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ── Respond node ────────────────────────────────────────────────
def respond_node(state: DevMindState) -> DevMindState:
    response = {
        "intent":           state.intent,
        "confidence":       state.confidence,
        "summary":          state.task_summary,
        "root_cause":       state.root_cause,
        "patch":            state.patch,
        "validation_passed":state.validation_passed,
        "validation_issues":state.validation_issues,
        "confidence_score": state.confidence_score,
        "context_files":    list({c["file"] for c in (state.context_chunks or [])})
    }
    return state.model_copy(update={"response": response})

# ── Build LangGraph ─────────────────────────────────────────────
def build_graph():
    graph = StateGraph(DevMindState)

    graph.add_node("orchestrator",       orchestrator_node)
    graph.add_node("context_harvester",  context_harvester_node)
    graph.add_node("reasoning_agent",    reasoning_agent_node)
    graph.add_node("code_writer",        code_writer_node)
    graph.add_node("validator",          validator_node)
    graph.add_node("memory_agent",       memory_agent_node)
    graph.add_node("chat_agent",         chat_agent_node)
    graph.add_node("respond",            respond_node)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges("orchestrator",
        route_after_orchestrator,
        {"context_harvester": "context_harvester"}
    )
    graph.add_conditional_edges("context_harvester",
        route_after_harvester,
        {
            "reasoning_agent": "reasoning_agent",
            "code_writer":     "code_writer",
            "chat_agent":      "chat_agent",
            "respond":         "respond"
        }
    )
    graph.add_conditional_edges("reasoning_agent",
        route_after_reasoning,
        {
            "code_writer": "code_writer",
            "chat_agent":  "chat_agent",
            "respond":     "respond"
        }
    )
    graph.add_conditional_edges("code_writer",
        route_after_code_writer,
        {
            "validator": "validator",
            "respond":   "respond"
        }
    )
    graph.add_conditional_edges("validator",
        route_after_validator,
        {"respond": "respond"}
    )
    graph.add_edge("chat_agent", "respond")
    graph.add_edge("respond", "memory_agent")
    graph.add_edge("memory_agent", END)

    return graph.compile()

devmind_graph = build_graph()

# ── Endpoints ───────────────────────────────────────────────────
@app.post("/analyze", response_model=DevMindResponse)
async def analyze(request: TriggerRequest):
    initial_state = DevMindState(
        source=request.source,
        raw_message=request.message,
        file_path=request.file_path,
        line_number=request.line_number,
        surrounding_code=request.surrounding_code,
        terminal_output=request.terminal_output,
        workspace_root=request.workspace_root
    )
    final_state = devmind_graph.invoke(initial_state)
    return DevMindResponse(**final_state.response)

@app.post("/index")
async def index(request: IndexRequest, background_tasks: BackgroundTasks):
    """Index a workspace into ChromaDB. Runs in background."""
    background_tasks.add_task(index_workspace, request.workspace_root)
    return {"status": "indexing started", "workspace": request.workspace_root}

@app.get("/health")
def health():
    return {"status": "ok", "model": "llama3.2:1b"}