import warnings
warnings.filterwarnings("ignore")

import typer
import os
import json
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

try:
    from rich_pixels import Pixels
except ImportError:
    Pixels = None

app = typer.Typer(help="DevMind CLI")
console = Console()

@app.command()
def interact():
    """
    Start an interactive chat with DevMind.
    """
    from backend.config import settings
    from main import devmind_graph, DevMindState
    from backend.logo.logo import display_logo_in_terminal
    
    if not settings.groq_api_key and "GROQ_API_KEY" not in os.environ:
        console.print("[bold red]Error: API Key missing![/bold red]")
        console.print("Please set GROQ_API_KEY environment variable or run `devmind config` to save it locally.")
        raise typer.Exit(1)
        
    if "GROQ_API_KEY" in os.environ and not settings.groq_api_key:
        settings.groq_api_key = os.environ["GROQ_API_KEY"]

    # Display DevMind logo
    display_logo_in_terminal()
    
    console.print(Panel.fit("[bold magenta]Welcome to DevMind CLI![/bold magenta]\n ", border_style="magenta"))

    with console.status("[bold green]Initializing local embedding models (first time only)...[/bold green]"):
        from backend.store.vector_store import query_chunks, get_collection
        collection = get_collection()
        
        # Auto-index if database is completely empty
        if collection.count() == 0:
            console.print("[bold blue]Workspace not yet indexed. Indexing now...[/bold blue]")
            from backend.store.indexer import index_workspace
            result = index_workspace(os.getcwd())
            console.print(f"[bold green]Workspace indexed successfully![/bold green] ({result['indexed_files']} files, {result['total_chunks']} chunks)")
            
        # Warmup query forces chromadb to download the ONNX model before user interacts
        query_chunks("warmup", n_results=1)

    console.print("Type your request, '/index' to re-index, or 'exit' to quit.\n")
    
    while True:
        try:
            message = typer.prompt("DevMind > ")
        except typer.Abort:
            break
            
        if message.lower() in ['exit', 'quit']:
            break
            
        if not message.strip():
            continue
            
        if message.strip().lower() == '/index':
            with console.status("[bold blue]Indexing workspace (this might take a moment)...[/bold blue]"):
                from backend.store.indexer import index_workspace
                result = index_workspace(os.getcwd())
                console.print(f"[bold green]Workspace indexed successfully![/bold green] ({result['indexed_files']} files, {result['total_chunks']} chunks)")
            continue
            
        with console.status(f"[bold green]DevMind is analyzing...[/bold green]"):
            initial_state = DevMindState(
                source="cli",
                raw_message=message,
                workspace_root=os.getcwd()
            )
            
            try:
                final_state = devmind_graph.invoke(initial_state)
            except Exception as e:
                console.print(f"[bold red]Execution failed:[/bold red] {e}")
                continue

        response = final_state.get("response", {})
        
        chat_msg = final_state.get("chat_response")
        if chat_msg:
            console.print(Markdown(chat_msg))
            console.print("")
        
        root_cause = final_state.get("root_cause")
        if root_cause and not chat_msg:
            console.print(Panel(Markdown(root_cause), title="Root Cause Diagnosis", border_style="yellow"))
            
        patch = final_state.get("patch")
        if patch and "error" not in patch:
            console.print(Panel(
                f"[bold red]Old Code (L{patch.get('line_start')}-L{patch.get('line_end')}):[/bold red]\n{patch.get('old_code')}\n\n"
                f"[bold green]New Code:[/bold green]\n{patch.get('new_code')}\n\n"
                f"[bold blue]Reason:[/bold blue] {patch.get('explanation')}",
                title=f"Proposed Patch for {patch.get('file')}",
                border_style="green"
            ))
        elif patch and "error" in patch:
            console.print(f"[bold red]Did not write patch:[/bold red] {patch.get('reason')}")

@app.command()
def config():
    """
    Set up your Groq API key locally.
    """
    api_key = typer.prompt("Enter your Groq API Key", hide_input=True)
    with open(".env", "a") as f:
        f.write(f"\nGROQ_API_KEY={api_key}\n")
    console.print("[bold green]API key saved automatically to .env[/bold green]")

if __name__ == "__main__":
    app()