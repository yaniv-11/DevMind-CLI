"""
Chunk Extractor - Extract Functions, Methods, Classes with Metadata
Uses AST parsing for Python and regex for other languages.
Provides granular chunk metadata for code-aware retrieval.
"""

import ast
import re
from typing import Optional


class PythonCodeExtractor:
    """Extract functions, classes, and methods from Python code."""
    
    @staticmethod
    def extract_definitions(content: str, filepath: str) -> list[dict]:
        """
        Extract all function/class definitions with line numbers.
        
        Args:
            content: Python file content
            filepath: Relative file path
            
        Returns:
            list[dict]: Definitions with structure:
                {
                    "type": "class|function|method",
                    "name": "ClassName" or "function_name",
                    "line_start": 10,
                    "line_end": 45,
                    "parent": "ClassName" for methods,
                    "docstring": "...",
                    "decorators": ["@property"],
                    "signature": "def func(a, b) -> str:"
                }
        """
        definitions = []
        
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return definitions
        
        lines = content.split('\n')
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                docstring = ast.get_docstring(node)
                definitions.append({
                    "type": "class",
                    "name": node.name,
                    "line_start": node.lineno,
                    "line_end": node.end_lineno or node.lineno,
                    "parent": None,
                    "docstring": docstring,
                    "decorators": [ast.unparse(d) for d in node.decorator_list],
                    "file": filepath,
                    "signature": f"class {node.name}:"
                })
                
                # Extract methods
                for item in node.body:
                    if isinstance(item, ast.FunctionDef):
                        method_doc = ast.get_docstring(item)
                        definitions.append({
                            "type": "method",
                            "name": item.name,
                            "line_start": item.lineno,
                            "line_end": item.end_lineno or item.lineno,
                            "parent": node.name,
                            "docstring": method_doc,
                            "decorators": [ast.unparse(d) for d in item.decorator_list],
                            "file": filepath,
                            "signature": f"def {item.name}({', '.join(arg.arg for arg in item.args.args)}):"
                        })
            
            elif isinstance(node, ast.FunctionDef) and not isinstance(node, ast.AsyncFunctionDef):
                # Top-level functions only
                if all(not isinstance(p, ast.ClassDef) for p in ast.walk(tree)):
                    docstring = ast.get_docstring(node)
                    definitions.append({
                        "type": "function",
                        "name": node.name,
                        "line_start": node.lineno,
                        "line_end": node.end_lineno or node.lineno,
                        "parent": None,
                        "docstring": docstring,
                        "decorators": [ast.unparse(d) for d in node.decorator_list],
                        "file": filepath,
                        "signature": f"def {node.name}({', '.join(arg.arg for arg in node.args.args)}):"
                    })
        
        return definitions


class JavaScriptCodeExtractor:
    """Extract functions and classes from JavaScript/TypeScript code."""
    
    @staticmethod
    def extract_definitions(content: str, filepath: str) -> list[dict]:
        """
        Extract function/class definitions using regex.
        Works for JS, TS, JSX, TSX.
        """
        definitions = []
        lines = content.split('\n')
        
        # Class pattern: class ClassName { ... }
        class_pattern = r'^(?:export\s+)?(?:default\s+)?(?:abstract\s+)?class\s+(\w+)'
        # Function pattern: function name(...) or const name = (...)
        func_pattern = r'^(?:export\s+)?(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=)'
        
        current_class = None
        brace_stack = []
        
        for i, line in enumerate(lines, 1):
            # Track braces
            brace_stack.extend(['{'] * line.count('{'))
            brace_stack.extend(['}'] * line.count('}'))
            
            # Class detection
            class_match = re.search(class_pattern, line)
            if class_match:
                current_class = class_match.group(1)
                definitions.append({
                    "type": "class",
                    "name": current_class,
                    "line_start": i,
                    "line_end": i,
                    "parent": None,
                    "file": filepath,
                    "signature": line.strip()
                })
            
            # Function/Method detection
            func_match = re.search(func_pattern, line)
            if func_match:
                func_name = func_match.group(1) or func_match.group(2)
                definitions.append({
                    "type": "method" if current_class else "function",
                    "name": func_name,
                    "line_start": i,
                    "line_end": i,
                    "parent": current_class,
                    "file": filepath,
                    "signature": line.strip()
                })
        
        return definitions


def extract_chunk_metadata(content: str, filepath: str) -> dict:
    """
    Extract metadata from code chunk.
    
    Args:
        content: Code snippet
        filepath: File path
        
    Returns:
        dict with functions, classes, methods found in chunk
    """
    ext = filepath.split('.')[-1].lower()
    
    if ext == "py":
        return PythonCodeExtractor.extract_definitions(content, filepath)
    elif ext in ["js", "ts", "jsx", "tsx"]:
        return JavaScriptCodeExtractor.extract_definitions(content, filepath)
    else:
        return []


def create_enhanced_chunk(
    chunk: dict,
    filepath: str,
    content: str
) -> dict:
    """
    Add metadata to chunk: functions, methods, classes.
    
    Args:
        chunk: Original chunk dict
        filepath: File path
        content: Code content of chunk
        
    Returns:
        Enhanced chunk dict with 'definitions' key
    """
    definitions = extract_chunk_metadata(content, filepath)
    
    return {
        **chunk,
        "definitions": definitions,
        "has_function": any(d["type"] in ["function", "method"] for d in definitions),
        "has_class": any(d["type"] == "class" for d in definitions),
        "definition_names": [d["name"] for d in definitions]
    }


def format_chunk_with_definitions(chunk: dict) -> str:
    """
    Format chunk with definition metadata for display.
    
    Returns:
        String showing chunk with function/class context
    """
    metadata = chunk.get("metadata", {})
    file_path = metadata.get("file", "unknown")
    line_start = metadata.get("line_start", 1)
    line_end = metadata.get("line_end", 1)
    
    definitions = chunk.get("definitions", [])
    def_str = ""
    
    if definitions:
        def_str = " | Contains: "
        def_names = ", ".join([
            f"{d['parent']}.{d['name']}" if d['parent'] else d['name']
            for d in definitions
            if d["type"] in ["function", "method", "class"]
        ])
        def_str += def_names
    
    return f"File: {file_path} (L{line_start}-{line_end}){def_str}"
