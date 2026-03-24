"""
Tool definitions and implementations for the agentic orchestrator.

Each tool is a dict with:
  - name: str (tool identifier)
  - description: str (what the tool does)
  - params: dict (parameter schema, e.g., {"file_path": "str"})
  - fn: callable (execution function)
"""

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List
import docx # Added for docx file reading


def read_file(file_path: str) -> Dict[str, Any]:
    """Read the contents of a file."""
    try:
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        if not path.is_file():
            return {"success": False, "error": f"Path is not a file: {file_path}"}
        content = path.read_text(encoding="utf-8")
        return {"success": True, "content": content, "file_path": file_path}
    except Exception as e:
        return {"success": False, "error": f"Error reading file: {str(e)}"}


def write_file(file_path: str, content: str) -> Dict[str, Any]:
    """Write content to a file. Creates the file if it doesn't exist."""
    try:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {"success": True, "message": f"File written: {file_path}"}
    except Exception as e:
        return {"success": False, "error": f"Error writing file: {str(e)}"}


def list_directory(dir_path: str = ".") -> Dict[str, Any]:
    """List files and directories in a given path."""
    try:
        path = Path(dir_path)
        if not path.exists():
            return {"success": False, "error": f"Directory not found: {dir_path}"}
        if not path.is_dir():
            return {"success": False, "error": f"Path is not a directory: {dir_path}"}
        
        items = sorted([item.name for item in path.iterdir()])
        return {
            "success": True,
            "directory": str(path.resolve()),
            "items": items,
            "count": len(items)
        }
    except Exception as e:
        return {"success": False, "error": f"Error listing directory: {str(e)}"}


def run_shell(command: str) -> Dict[str, Any]:
    """Execute a shell command and return stdout/stderr."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30
        )
        return {
            "success": True,
            "command": command,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"Command timed out after 30 seconds: {command}"}
    except Exception as e:
        return {"success": False, "error": f"Error executing command: {str(e)}"}


def read_docx_file(file_path: str) -> Dict[str, Any]:
    """Read the complete text content from a .docx file."""
    try:
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        if not path.is_file():
            return {"success": False, "error": f"Path is not a file: {file_path}"}
        if not file_path.lower().endswith(".docx"):
            return {"success": False, "error": f"File is not a .docx file: {file_path}"}

        document = docx.Document(file_path)
        full_text = []
        for para in document.paragraphs:
            full_text.append(para.text)
        content = "\n".join(full_text)
        return {"success": True, "content": content, "file_path": file_path}
    except Exception as e:
        return {"success": False, "error": f"Error reading docx file: {str(e)}"}


# Tool registry: list of available tools
TOOLS = [
    {
        "name": "read_file",
        "description": "Read the complete contents of a file. Returns the file content as a string.",
        "parameters": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file to read"
            }
        },
        "fn": read_file
    },
    {
        "name": "write_file",
        "description": "Write or create a file with the given content. Creates directories if needed.",
        "parameters": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the file to write"
            },
            "content": {
                "type": "string",
                "description": "The content to write to the file"
            }
        },
        "fn": write_file
    },
    {
        "name": "list_directory",
        "description": "List all files and directories in a given path. Sorts alphabetically.",
        "parameters": {
            "dir_path": {
                "type": "string",
                "description": "Absolute or relative path to the directory (default: current directory)",
                "optional": True
            }
        },
        "fn": list_directory
    },
    {
        "name": "run_shell",
        "description": "Execute a shell command and return stdout/stderr. Useful for quick file checks or system operations.",
        "parameters": {
            "command": {
                "type": "string",
                "description": "The shell command to execute (e.g., 'ls -la', 'pwd', 'grep pattern file.txt')"
            }
        },
        "fn": run_shell
    },
    {
        "name": "read_docx_file",
        "description": "Read the complete text content from a .docx file.",
        "parameters": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the .docx file to read"
            }
        },
        "fn": read_docx_file
    }
]


def get_tool_by_name(name: str) -> Any:
    """Retrieve a tool by name."""
    for tool in TOOLS:
        if tool["name"] == name:
            return tool
    return None


def format_tool_descriptions() -> str:
    """Format all tools as a readable string for the prompt."""
    descriptions = []
    for tool in TOOLS:
        desc = f"- **{tool['name']}**: {tool['description']}\n"
        if tool.get("parameters"):
            for param_name, param_info in tool["parameters"].items():
                optional = " (optional)" if param_info.get("optional") else ""
                desc += f"  - {param_name} ({param_info.get('type', 'unknown')}){optional}: {param_info.get('description', '')}\n"
        descriptions.append(desc)
    return "".join(descriptions)


if __name__ == "__main__":
    # Example usage: print tool descriptions
    print("Available Tools:\n")
    print(format_tool_descriptions())