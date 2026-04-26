# DevMind CLI 

A local, AI-powered coding assistant that indexes your workspace and provides intelligent context-aware support from the terminal. 

<img width="762" height="565" alt="Screenshot 2026-03-27 213115" src="https://github.com/user-attachments/assets/27832c87-ebaf-4f8d-8315-a46be2b7d62f" />

Core Architecture
 1. Orchestrator Agent
Classifies user intent:
fix_error
explain_code
write_feature
find_usages
Dynamically builds execution plan
 2. Context Harvester (Hybrid RAG)

Retrieval pipeline:

Semantic Search (Top 15)
Keyword Search (Top 15)
Reranking → Top 10

Vector Store:

ChromaDB

 Ensures relevant code grounding before reasoning

 3. Reasoning Agent

Performs:

Root cause analysis
Dependency understanding
Fix hypothesis generation
 4. Memory Agent
Stores project-level knowledge
Improves consistency across interactions
 5. Code Writer

Generates structured patches:

{
  "file": "path/to/file.py",
  "line_start": 10,
  "line_end": 20,
  "old_code": "...",
  "new_code": "..."
}
 6. Validator

Ensures:

Syntax correctness
Code compatibility
Logical consistency
 7. Chat Agent

Aggregates:

reasoning output
patch
confidence score

Returns final response to user.
<img width="1536" height="1024" alt="ChatGPT Image Apr 26, 2026, 11_59_55 AM" src="https://github.com/user-attachments/assets/2bd453c2-99a0-4d51-9585-2a262cd7114f" />

 Execution Flow
User query received via CLI/API
Intent classified
Relevant code retrieved (Hybrid RAG)
Reasoning agent analyzes issue
Code writer generates patch
Validator checks correctness
Final response returned
 CLI Usage
devmind interact

Example:

> Fix this error in utils.py line 45
 Key Features
 Hybrid RAG (semantic + keyword + rerank)
 Multi-agent architecture
 Structured patch generation
 Parallel agent execution
 Confidence-based responses
#  Installation & Setup
You can set up DevMind globally on your system in a few simple steps. 

### 1. Download the Project
Download the project files (e.g., zip format) and extract them to a directory on your machine.
For example, extract it to `C:\Tools\DevMind`.

### 2. Install the Package
Open your terminal, navigate to the extracted directory, and install the package using `pip` in editable mode:

```bash
cd /path/to/extracted/DevMind
pip install -e .
```

This will automatically install all dependencies and register the `devmind` command globally on your system.

### 3. Setup Your Groq API Key

DevMind requires a Groq API key to function. You only need to provide this key once per project folder. 

Navigate to your target project folder (the project you want to get help with) and run:
```bash
devmind config
```
You will be prompted to paste your Groq API key. DevMind will silently save this key into a hidden `.env` file in that folder so **it remembers your key for every future session in that specific project.**

*(Alternatively, you can set `GROQ_API_KEY` as a global system environment variable, and DevMind will automatically pick it up for all projects without needing a `.env` file!)*

## 🛠️ How to Use

Once installed and configured, you can use DevMind from inside **any** project directory on your computer!

To start the interactive coding assistant, simply open a terminal in any of your project directories and type:
```bash
devmind interact
```

### Features inside the CLI
- **Smart Startup:** If it's your first time running DevMind in a specific project, it will automatically index your codebase and create an isolated memory folder (`./store/`) unique to that project.
- **Context-Aware Assistance:** Ask questions like *"Explain how authentication works in this repository"* or *"Find the bug causing a 404 in the router."*
- **Re-indexing:** Added or removed several huge files? Just type `/index` directly into the chat prompt to refresh your workspace's search vectors!
- **Exit:** Type `exit` or `quit` to leave the chat loop.
