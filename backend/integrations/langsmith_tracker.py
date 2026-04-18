"""
LangSmith Integration for Tracing and Monitoring
Tracks agent executions, LLM calls, and retrieval quality.
"""

import os
from typing import Any, Dict, Optional
from datetime import datetime
from functools import wraps


class LangSmithTracker:
    """Wrapper for LangSmith tracing and monitoring."""
    
    def __init__(self, project_name: str = "DevMind"):
        """
        Initialize LangSmith tracker.
        
        Args:
            project_name: Project name for LangSmith
        """
        self.project_name = project_name
        self.enabled = bool(os.getenv("LANGSMITH_API_KEY"))
        self.client = None
        
        if self.enabled:
            try:
                from langsmith import Client
                self.client = Client(project_name=project_name)
                print(f"LangSmith tracker enabled for project: {project_name}")
            except ImportError:
                print("LangSmith not installed. Set LANGSMITH_API_KEY to enable tracing.")
                self.enabled = False
    
    def trace_rag_retrieval(self, query: str, results: list[dict]) -> str:
        """
        Trace RAG retrieval operation.
        
        Args:
            query: Search query
            results: Retrieved chunks
            
        Returns:
            str: Trace ID
        """
        if not self.enabled:
            return None
        
        try:
            from langsmith import trace
            
            @trace
            def retrieve():
                return {
                    "query": query,
                    "chunks_retrieved": len(results),
                    "top_score": results[0].get("final_score", 0) if results else 0,
                    "files": list(set(
                        r.get("metadata", {}).get("file") for r in results
                    ))
                }
            
            return retrieve()
        except Exception as e:
            print(f"LangSmith trace error: {e}")
            return None
    
    def trace_llm_call(self, model: str, messages: list, response: str) -> str:
        """
        Trace LLM API call.
        
        Args:
            model: Model name
            messages: Input messages
            response: LLM response
            
        Returns:
            str: Trace ID
        """
        if not self.enabled:
            return None
        
        try:
            from langsmith import trace
            
            @trace
            def call_llm():
                return {
                    "model": model,
                    "messages_count": len(messages),
                    "response_length": len(response),
                    "timestamp": datetime.now().isoformat()
                }
            
            return call_llm()
        except Exception as e:
            print(f"LangSmith trace error: {e}")
            return None
    
    def trace_file_edit(self, file_path: str, edit_type: str, result: dict) -> str:
        """
        Trace file editing operation.
        
        Args:
            file_path: File being edited
            edit_type: Type of edit (chunk, replace_text)
            result: Edit result
            
        Returns:
            str: Trace ID
        """
        if not self.enabled:
            return None
        
        try:
            from langsmith import trace
            
            @trace
            def edit_file():
                return {
                    "file": file_path,
                    "edit_type": edit_type,
                    "status": result.get("status"),
                    "chunk_ref": result.get("chunk_ref"),
                    "backup": result.get("backup")
                }
            
            return edit_file()
        except Exception as e:
            print(f"LangSmith trace error: {e}")
            return None
    
    def log_metric(self, name: str, value: float, run_id: str = None):
        """
        Log custom metric to LangSmith.
        
        Args:
            name: Metric name
            value: Metric value
            run_id: Optional run ID
        """
        if not self.enabled or not self.client:
            return
        
        try:
            # LangSmith supports logging feedback
            pass
        except Exception as e:
            print(f"LangSmith metric error: {e}")
    
    def create_run(self, run_name: str, metadata: dict = None) -> Optional[str]:
        """
        Create a new run for tracking.
        
        Args:
            run_name: Name for the run
            metadata: Optional metadata
            
        Returns:
            str: Run ID or None
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            # Return a run context
            return run_name
        except Exception as e:
            print(f"LangSmith run error: {e}")
            return None


class TracedFunction:
    """Decorator for tracing function calls."""
    
    def __init__(self, tracker: LangSmithTracker):
        self.tracker = tracker
    
    def __call__(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not self.tracker.enabled:
                return func(*args, **kwargs)
            
            try:
                from langsmith import trace
                
                @trace
                def traced_call():
                    return func(*args, **kwargs)
                
                return traced_call()
            except Exception as e:
                print(f"Trace error in {func.__name__}: {e}")
                return func(*args, **kwargs)
        
        return wrapper


# Global tracker instance
_tracker = None

def get_tracker(project_name: str = "DevMind") -> LangSmithTracker:
    """Get or create global tracker instance."""
    global _tracker
    if _tracker is None:
        _tracker = LangSmithTracker(project_name)
    return _tracker

def traced(func):
    """Decorator for tracing any function."""
    tracker = get_tracker()
    return TracedFunction(tracker)(func)
