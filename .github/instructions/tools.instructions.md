---
name: tools
description: "Guide for extending agent capabilities. Use when: adding new tools to the registry, implementing tool handlers, integrating APIs, or designing tool parameters for agents."
applyTo: "**/tools.py"
---

# Tool Development Guide

Tools are synchronous Python callables registered in `tools.py`. The agent discovers them through the `TOOLS` list, formats their metadata into the system prompt, and invokes them when the model emits a JSON tool call.

## Registry Contract

Each entry contains:

```python
{
    "name": "tool_name",
    "description": "Short description shown to the model",
    "parameters": {
        "parameter": {
            "type": "string|number|boolean|array",
            "description": "Parameter purpose",
            "optional": True,
        }
    },
    "fn": callable,
}
```

The model calls a tool with:

```json
{"tool": "tool_name", "params": {"parameter": "value"}}
```

## Handler Contract

Handlers should use typed parameters and return a dictionary with `success`. Successful results may expose domain-specific fields such as `content`, `items`, `stdout`, or `message`; failures must include an actionable `error` string.

```python
def example_tool(file_path: str) -> dict:
    try:
        # Validate inputs and perform the operation.
        return {"success": True, "content": "..."}
    except Exception as exc:
        return {"success": False, "error": f"Example failed: {exc}"}
```

The orchestrator converts unknown tool names, invalid parameters, and raised exceptions into failed tool results. Prefer returning expected operational errors from the handler itself so the model receives useful context.

## Current Registry

The active tools are:

- `read_file(file_path)`: reads a UTF-8 text file.
- `write_file(file_path, content)`: creates parent directories and writes UTF-8 text.
- `list_directory(dir_path=".")`: returns sorted directory entries.
- `run_shell(command)`: runs a shell command with a 30-second timeout.
- `read_docx_file(file_path)`: reads paragraph text from a DOCX file.

`python-docx` is optional. Keep optional imports inside a guarded module-level import, leave the tool registered, and return an installation message when the dependent tool is called without the package. Optional packages must not prevent `tools.py` or the rest of the registry from importing.

## Adding a Tool

1. Add a typed handler in `tools.py`.
2. Validate paths, extensions, parameters, and resource limits.
3. Return the standard `success` plus result-or-error structure.
4. Add the tool metadata to `TOOLS`.
5. Confirm `get_tool_by_name("tool_name")` finds it and `format_tool_descriptions()` includes it.
6. Add a deterministic test under `tests/`.
7. Run `python3 -m unittest discover -s tests -v`.

Keep tools focused. Core orchestration belongs in `orchestrator.py`; CLI presentation belongs in `main.py`; credentials should be handled by provider configuration rather than embedded in tool functions.
