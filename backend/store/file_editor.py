"""
Safe File Editor with LLM Suggestions
Allows reading and editing files with validation and chunk tracking.
Maintains history and enables rollback.
"""

import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional


class FileEditor:
    """Safe file editing with validation and history."""
    
    def __init__(self, workspace_root: str, backup_dir: str = "./store/file_backups"):
        """
        Initialize file editor.
        
        Args:
            workspace_root: Root directory for file operations
            backup_dir: Directory to store file backups
        """
        self.workspace_root = workspace_root
        self.backup_dir = backup_dir
        self.history = []
        
        os.makedirs(backup_dir, exist_ok=True)
    
    def _resolve_path(self, file_path: str) -> str:
        """
        Resolve relative path to absolute, with safety checks.
        
        Args:
            file_path: File path (relative or absolute)
            
        Returns:
            str: Absolute path
            
        Raises:
            ValueError: If path is outside workspace
        """
        # Handle relative paths
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.workspace_root, file_path)
        
        # Resolve symlinks and normalize
        file_path = os.path.abspath(file_path)
        workspace_abs = os.path.abspath(self.workspace_root)
        
        # Security check: ensure file is within workspace
        if not file_path.startswith(workspace_abs):
            raise ValueError(f"Path {file_path} is outside workspace")
        
        return file_path
    
    def read_file(self, file_path: str, start_line: int = None, end_line: int = None) -> str:
        """
        Read file or specific lines.
        
        Args:
            file_path: Path to file
            start_line: Optional start line (1-indexed)
            end_line: Optional end line (1-indexed, inclusive)
            
        Returns:
            str: File content
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        file_path = self._resolve_path(file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        if start_line is not None:
            start_line = max(1, start_line) - 1  # Convert to 0-indexed
            end_line = min(len(lines), end_line or len(lines))
            return "".join(lines[start_line:end_line])
        
        return "".join(lines)
    
    def _create_backup(self, file_path: str) -> str:
        """
        Create backup of file before editing.
        
        Args:
            file_path: Path to file
            
        Returns:
            str: Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        backup_path = os.path.join(
            self.backup_dir,
            f"{filename}.{timestamp}.bak"
        )
        
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copy2(file_path, backup_path)
        
        return backup_path
    
    def edit_chunk(
        self,
        file_path: str,
        start_line: int,
        end_line: int,
        new_content: str,
        description: str = "",
        chunk_ref: str = None
    ) -> dict:
        """
        Edit specific chunk (lines) in file.
        
        Args:
            file_path: Path to file
            start_line: Start line number (1-indexed)
            end_line: End line number (1-indexed, inclusive)
            new_content: New content for the chunk
            description: What was changed (for history)
            chunk_ref: Reference chunk ID for traceability
            
        Returns:
            dict: Edit result with backup path and changes
            
        Example:
            >>> result = editor.edit_chunk(
            ...     "src/utils.py",
            ...     start_line=10,
            ...     end_line=15,
            ...     new_content="def fixed_function():\n    pass",
            ...     description="Fixed null pointer exception",
            ...     chunk_ref="abc123"
            ... )
        """
        file_path = self._resolve_path(file_path)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # Create backup
        backup_path = self._create_backup(file_path)
        
        # Read file
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Validate line numbers
        start_line = max(1, start_line)
        end_line = min(len(lines), end_line)
        
        if start_line > end_line or start_line > len(lines):
            raise ValueError(f"Invalid line numbers: {start_line}-{end_line}")
        
        # Get old content
        old_content = "".join(lines[start_line - 1:end_line])
        
        # Replace lines (convert to 0-indexed)
        new_lines = new_content.rstrip().split('\n')
        new_lines = [line + '\n' for line in new_lines]
        
        lines[start_line - 1:end_line] = new_lines
        
        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        
        # Track edit
        edit_record = {
            "timestamp": datetime.now().isoformat(),
            "file": file_path,
            "start_line": start_line,
            "end_line": end_line,
            "old_content": old_content,
            "new_content": new_content,
            "backup_path": backup_path,
            "description": description,
            "chunk_ref": chunk_ref
        }
        
        self.history.append(edit_record)
        
        return {
            "status": "success",
            "file": file_path,
            "lines_changed": end_line - start_line + 1,
            "backup": backup_path,
            "description": description,
            "chunk_ref": chunk_ref
        }
    
    def replace_text(
        self,
        file_path: str,
        old_text: str,
        new_text: str,
        description: str = "",
        chunk_ref: str = None
    ) -> dict:
        """
        Find and replace text in file.
        
        Args:
            file_path: Path to file
            old_text: Text to find
            new_text: Replacement text
            description: What was changed
            chunk_ref: Reference chunk ID
            
        Returns:
            dict: Edit result with count of replacements
        """
        file_path = self._resolve_path(file_path)
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Check if text exists
        if old_text not in content:
            raise ValueError(f"Text not found in file:\n{old_text}")
        
        # Create backup
        backup_path = self._create_backup(file_path)
        
        # Replace
        new_content = content.replace(old_text, new_text)
        replacement_count = content.count(old_text)
        
        # Write back
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        
        # Track
        edit_record = {
            "timestamp": datetime.now().isoformat(),
            "file": file_path,
            "operation": "replace_text",
            "old_text": old_text,
            "new_text": new_text,
            "replacements": replacement_count,
            "backup_path": backup_path,
            "description": description,
            "chunk_ref": chunk_ref
        }
        
        self.history.append(edit_record)
        
        return {
            "status": "success",
            "file": file_path,
            "replacements": replacement_count,
            "backup": backup_path,
            "description": description,
            "chunk_ref": chunk_ref
        }
    
    def validate_syntax(self, file_path: str) -> dict:
        """
        Validate Python file syntax.
        
        Args:
            file_path: Path to Python file
            
        Returns:
            dict: Validation result with errors if any
        """
        file_path = self._resolve_path(file_path)
        
        if not file_path.endswith(".py"):
            return {"status": "skipped", "reason": "Not a Python file"}
        
        try:
            import ast
            with open(file_path, "r", encoding="utf-8") as f:
                ast.parse(f.read())
            return {"status": "valid", "file": file_path}
        except SyntaxError as e:
            return {
                "status": "invalid",
                "error": str(e),
                "line": e.lineno,
                "file": file_path
            }
    
    def rollback_to_backup(self, backup_path: str) -> dict:
        """
        Restore file from backup.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            dict: Rollback result
        """
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup not found: {backup_path}")
        
        # Extract original file path from history
        original_file = None
        for record in reversed(self.history):
            if record.get("backup_path") == backup_path:
                original_file = record["file"]
                break
        
        if not original_file:
            raise ValueError(f"Cannot determine original file for {backup_path}")
        
        # Restore
        shutil.copy2(backup_path, original_file)
        
        return {
            "status": "success",
            "file": original_file,
            "restored_from": backup_path
        }
    
    def get_edit_history(self, file_path: str = None, limit: int = 10) -> list[dict]:
        """
        Get edit history for a file or all files.
        
        Args:
            file_path: Optional specific file
            limit: Max results to return
            
        Returns:
            list[dict]: History records
        """
        history = self.history
        
        if file_path:
            file_path = self._resolve_path(file_path)
            history = [h for h in history if h.get("file") == file_path]
        
        return history[-limit:]
    
    def get_pending_edits_summary(self) -> dict:
        """
        Get summary of edits since last baseline.
        
        Returns:
            dict: Summary of changes
        """
        summary = {
            "total_edits": len(self.history),
            "files_modified": set(),
            "descriptions": []
        }
        
        for record in self.history:
            summary["files_modified"].add(record.get("file"))
            if record.get("description"):
                summary["descriptions"].append(record["description"])
        
        summary["files_modified"] = list(summary["files_modified"])
        
        return summary
