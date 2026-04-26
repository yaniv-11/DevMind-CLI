# backend/models/schemas.py
from typing import Optional, List
from pydantic import BaseModel

class TriggerRequest(BaseModel):
    message: str
    

class DevMindResponse(BaseModel):
    intent: Optional[str] = None
    summary: Optional[str] = None
    root_cause: Optional[str] = None
    patch: Optional[dict] = None
    confidence_score: Optional[float] = None
    validation_issues: Optional[List[str]] = None
    context_files: List[str] = []

class IndexRequest(BaseModel):
    workspace_root: str
'''

**Final folder structure — everything that exists now:**

devmind/
└── backend/
    ├── main.py
    ├── config.py
    ├── requirements.txt
    ├── agents/
    │   ├── __init__.py
    │   ├── orchestrator.py
    │   ├── context_harvester.py
    │   ├── reasoning_agent.py
    │   ├── code_writer.py
    │   ├── validator.py
    │   └── memory_agent.py
    ├── graph/
    │   ├── state.py
    │   └── edges.py
    ├── models/
    │   └── schemas.py
    └── store/
        ├── vector_store.py
        └── indexer.py   '''