import warnings
warnings.filterwarnings("ignore")

import typer
import os
import json
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

try:
    from rich_pixels import Pixels
except ImportError:
    Pixels = None

app = typer.Typer(help="DevMind CLI", invoke_without_command=True)
console = Console()

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    query: str = typer.Argument(None, help="Query or command")
):
    """
    DevMind - AI Code Copilot with parallel agent execution.
    
    Usage:
        devmind "fix the null pointer bug"     # Process query
        devmind "/index"                        # Index workspace
        devmind                                 # Interactive mode with logo
    """
    from backend.config import settings
    from main import devmind_graph, DevMindState
    from backend.logo.logo import display_logo_in_terminal
    from backend.store.vector_store import get_collection
    from backend.store.indexer import index_workspace
    
    if not settings.groq_api_key and "GROQ_API_KEY" not in os.environ:
        console.print("[bold red]Error: API Key missing![/bold red]")
        console.print("Please set GROQ_API_KEY environment variable or run `devmind config` to save it locally.")
        raise typer.Exit(1)
        
    if "GROQ_API_KEY" in os.environ and not settings.groq_api_key:
        settings.groq_api_key = os.environ["GROQ_API_KEY"]

    # Initialize models
    with console.status("[bold green]Initializing models (first time only)...[/bold green]"):
        collection = get_collection()
        
        # Auto-index if database is completely empty
        if collection.count() == 0:
            console.print("[bold blue]Workspace not yet indexed. Indexing now...[/bold blue]")
            result = index_workspace(os.getcwd())
            console.print(f"[bold green]Workspace indexed![/bold green] ({result['indexed_files']} files, {result['total_chunks']} chunks)")
    
    # Handle /index command
    if query and query.strip().lower() == '/index':
        with console.status("[bold blue]Indexing workspace (this might take a moment)...[/bold blue]"):
            result = index_workspace(os.getcwd())
            console.print(f"[bold green]Workspace indexed![/bold green] ({result['indexed_files']} files, {result['total_chunks']} chunks)")
        return
    
    # Handle single query or interactive mode
    if query:
        # Single query mode (no logo)
        _process_query(query, devmind_graph, os.getcwd())
    else:
        # Interactive mode - show logo
        display_logo_in_terminal()
        console.print(Panel.fit("[bold magenta]Welcome to DevMind CLI![/bold magenta]\n ", border_style="magenta"))
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
                with console.status("[bold blue]Indexing workspace...[/bold blue]"):
                    result = index_workspace(os.getcwd())
                    console.print(f"[bold green]Workspace indexed![/bold green] ({result['indexed_files']} files, {result['total_chunks']} chunks)")
                continue
                
            _process_query(message, devmind_graph, os.getcwd())


def _process_query(message: str, devmind_graph, workspace_root: str):
    """Process a single query with parallel agent execution and file approval."""
    from backend.graph.state import DevMindState
    
    with console.status(f"[bold green]Agents working in parallel...[/bold green]"):
        initial_state = DevMindState(
            raw_message=message,
            workspace_root=workspace_root
        )
        
        try:
            final_state = devmind_graph.invoke(initial_state)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            return

    # Display response
    chat_msg = final_state.get("chat_response")
    if chat_msg:
        console.print(Markdown(chat_msg))
        console.print("")
    
    # Display root cause diagnosis
    root_cause = final_state.get("root_cause")
    if root_cause and not chat_msg:
        console.print(Panel(Markdown(root_cause), title="Root Cause Diagnosis", border_style="yellow"))
    
    # Handle file edits with approval
    pending_edits = final_state.get("pending_edits", [])
    if pending_edits:
        _handle_file_edits(pending_edits)
    else:
        # Display patch if no pending edits
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


def _handle_file_edits(edits: list):
    """Handle file edit approval (like GitHub Copilot)."""
    from backend.store.file_editor import FileEditor
    import os
    
    if not edits:
        return
    
    console.print("\n[bold yellow]Suggested file edits:[/bold yellow]\n")
    
    for i, edit in enumerate(edits, 1):
        file_path = edit.get("file")
        old_code = edit.get("old_code", "")
        new_code = edit.get("new_code", "")
        reason = edit.get("reason", "No description")
        chunk_ref = edit.get("chunk_ref")
        
        console.print(Panel(
            f"[bold blue]File:[/bold blue] {file_path}\n"
            f"[bold blue]Reason:[/bold blue] {reason}\n"
            f"[bold blue]Chunk Ref:[/bold blue] {chunk_ref}\n\n"
            f"[bold red]- Old:[/bold red]\n{old_code}\n\n"
            f"[bold green]+ New:[/bold green]\n{new_code}",
            title=f"Edit {i}/{len(edits)}",
            border_style="cyan"
        ))
        
        # Ask user to approve
        approval = typer.confirm(f"Apply this edit to {file_path}?", default=False)
        
        if approval:
            editor = FileEditor(os.getcwd())
            try:
                result = editor.edit_chunk(
                    file_path,
                    start_line=edit.get("line_start", 1),
                    end_line=edit.get("line_end", 1),
                    new_content=new_code,
                    description=reason,
                    chunk_ref=chunk_ref
                )
                console.print(f"[bold green]Applied![/bold green] Backup: {result['backup']}\n")
            except Exception as e:
                console.print(f"[bold red]Failed:[/bold red] {e}\n")
        else:
            console.print("[yellow]Skipped[/yellow]\n")

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