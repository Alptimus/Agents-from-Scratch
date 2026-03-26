---
name: tools
description: "Guide for extending agent capabilities. Use when: adding new tools to the registry, implementing tool handlers, integrating APIs, or designing tool parameters for agents."
applyTo: "**/tools.py"
---

# Tool Development Guide

This file explains how to create, register, and test tools that agents can execute autonomously.

## Tool Architecture

A **tool** is a callable function that agents can invoke to perform work. Each tool must:

1. **Follow the Standard Response Format**
   ```python
   {
       "success": bool,           # True if execution succeeded
       "result": <any>,           # Result data (on success)
       # OR
       "error": str,              # Error message (on failure)
   }
   ```

2. **Be Registered in the TOOLS List**
   ```python
   {
       "name": "tool_identifier",
       "description": "What it does (one line)",
       "parameters": {
           "param_name": {
               "type": "string|number|boolean|array",
               "description": "Parameter description",
               "optional": True  # Optional fields have this set
           }
       },
       "fn": callable  # Function to execute
   }
   ```

## Adding a New Tool: Step-by-Step

### 1. Implement the Handler Function

Create a function that:
- Takes typed parameters (avoid `**kwargs` for clarity)
- Returns the standard response format
- Handles all edge cases (missing files, permissions, timeouts, etc.)

**Example: CSV File Tool**
```python
def read_csv_file(file_path: str) -> Dict[str, Any]:
    """Read CSV file and return rows as list of dicts."""
    try:
        import csv
        path = Path(file_path)
        
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
        if not file_path.lower().endswith(".csv"):
            return {"success": False, "error": f"Not a CSV file: {file_path}"}
        
        rows = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        
        return {"success": True, "rows": rows, "count": len(rows)}
    
    except Exception as e:
        return {"success": False, "error": f"Error reading CSV: {str(e)}"}
```

### 2. Add Tool to Registry

Append to the `TOOLS` list in [tools.py](tools.py):

```python
TOOLS = [
    # ... existing tools ...
    {
        "name": "read_csv_file",
        "description": "Read a CSV file and return its rows as a list of dictionaries, with headers from first row.",
        "parameters": {
            "file_path": {
                "type": "string",
                "description": "Absolute or relative path to the CSV file"
            }
        },
        "fn": read_csv_file
    }
]
```

### 3. Test Tool in Isolation

Before using with agents, verify the tool works:

```python
# Direct function call
result = read_csv_file("data.csv")
assert result["success"] is True
assert len(result["rows"]) > 0

# Via agent
from orchestrator import OllamaAgent
agent = OllamaAgent()
result = agent.execute_task(
    "Read contacts.csv and tell me how many rows there are"
)
```

## Tool Design Patterns

### Error Handling

Always validate inputs before processing:
```python
def example_tool(param1: str, param2: int) -> Dict[str, Any]:
    # Check types
    if not isinstance(param1, str):
        return {"success": False, "error": f"param1 must be string, got {type(param1).__name__}"}
    
    # Check constraints
    if param2 < 0:
        return {"success": False, "error": "param2 must be non-negative"}
    
    # Check preconditions
    if not Path(param1).exists():
        return {"success": False, "error": f"File not found: {param1}"}
    
    # Proceed with safe assumptions
    return {"success": True, "result": ...}
```

### Large Results

If a tool returns large data (100MB+ files, thousands of rows):
- **For files**: Return file path instead of content
- **For lists**: Return summary (count, first N items, truncation indicator)
- **For text**: Return preview (first 5000 chars) + metadata

```python
def read_large_file(file_path: str) -> Dict[str, Any]:
    path = Path(file_path)
    size_mb = path.stat().st_size / (1024*1024)
    
    if size_mb > 10:
        # Don't return full content
        return {
            "success": True,
            "file_path": str(path.resolve()),
            "size_mb": size_mb,
            "preview": path.read_text()[:5000],
            "message": "File too large to load; returning preview"
        }
    else:
        # Safe to return full content
        return {"success": True, "content": path.read_text()}
```

### Timeout & Resource Limits

Use `timeout` parameter on long-running operations:
```python
def run_analysis(data_path: str) -> Dict[str, Any]:
    try:
        # Set timeout to prevent agent hangs
        result = subprocess.run(
            ["python", "analysis.py", data_path],
            timeout=30,  # 30 seconds max
            capture_output=True,
            text=True
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Analysis timed out after 30 seconds"}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

## Tool Registry Discovery

Agents automatically discover tools via the `TOOLS` list. At startup, agents:

1. Load all tool definitions from `tools.TOOLS`
2. Extract names, descriptions, and parameters
3. Generate a system prompt listing all available tools
4. When LLM outputs JSON `{"tool": "name", "params": {...}}`, lookup is automatic

**To verify tools are discoverable:**
```python
from tools import TOOLS, get_tool_by_name, format_tool_descriptions

# See all registered tools
for tool in TOOLS:
    print(f"- {tool['name']}: {tool['description']}")

# Generate system prompt content (used by agents)
print(format_tool_descriptions())

# Lookup a specific tool
csv_tool = get_tool_by_name("read_csv_file")
assert csv_tool is not None
```

## Common Tool Patterns

### File Operations
- **read_file**: Read text content (handles encoding)
- **write_file**: Write/append text (creates directories)
- **read_csv_file**: CSV → list of dicts
- **read_docx_file**: .docx → plain text (already implemented)

### System Operations
- **run_shell**: Execute commands, capture stdout/stderr
- **list_directory**: Walk directory tree, filter by pattern

### Integration Points
- **HTTP requests**: Fetch APIs (not yet implemented)
- **Database query**: Execute SQL (not yet implemented)
- **Screenshot**: Capture web pages via Playwright (partially implemented)

## When NOT to Create a Tool

Some operations don't belong in tools:

| What | Why | Alternative |
|------|-----|-------------|
| Core orchestration logic | Agent framework | Modify `orchestrator.py` |
| Formatting output for user | UI concern | Handle in `main.py` or display layer |
| Caching/persistence | Infrastructure | Add to agent or storage module |
| Auth/security checks | Middleware | Handle in `_call_ollama()` or agent init |

## Implementation Checklist

- [ ] Handler function has type hints on all parameters
- [ ] Function returns standard `{"success": bool, "result"/"error": value}` format
- [ ] All error cases are caught and returned as `{"success": False, "error": "..."}`
- [ ] Tool description is clear (one sentence, describes output)
- [ ] Parameters are minimal (3 or fewer preferred)
- [ ] Tool is tested in isolation before agent integration
- [ ] Tool name follows `snake_case` convention
- [ ] Added to `TOOLS` list in [tools.py](tools.py)
- [ ] Docstring includes usage example
- [ ] No external API keys required (use agent config for sensitive data)
