# DevMind CLI 

A local, AI-powered coding assistant that indexes your workspace and provides intelligent context-aware support from the terminal, powered by the Groq API. 

##  Installation & Setup

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
