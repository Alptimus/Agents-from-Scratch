---
name: orchestrator
description: |
  Guidance for working with orchestrator.py: autonomous agent implementation.
  Use when: modifying agent behavior, adding backends, debugging tool iteration loops, or extending orchestrator features.
applyTo: "**/higher_end/orchestrator.py"
---

# Orchestrator Implementation Guide

`orchestrator.py` contains the shared `BaseAgent` loop and the two active provider implementations: `OllamaAgent` and `GeminiAgent`.

## Shared Loop

`BaseAgent.execute_task()` owns all provider-independent behavior:

1. Set up plaintext and JSON Lines logging.
2. Check the backend through `_check_connection()`.
3. Build prompts using `prompts.py` and the current `TOOLS` registry.
4. Call `_call_llm()`.
5. Extract JSON tool calls with `_extract_tool_calls()`.
6. Execute calls through `_execute_tool()`.
7. Build a continuation prompt with tool results.
8. Stop on a no-tool response, an LLM failure, or `max_iterations`.

Do not duplicate this loop in a provider subclass. Provider classes should only implement connection details, model calls, and provider metadata.

## Backend Hooks

Every `BaseAgent` subclass must implement:

- `_get_backend_name()`
- `_check_connection()`
- `_get_connection_error_msg()`
- `_call_llm(prompt)`
- `_get_backend_connection_info()`

Keep the public constructor shape of existing agents compatible:

```python
OllamaAgent(
    ollama_base_url="http://localhost:11434",
    model="mistral",
    max_iterations=10,
    verbose=True,
    log_dir="logs",
    think=False,
)

GeminiAgent(
    api_key_name="GOOGLE_API_KEY",
    model="gemini-2.5-flash",
    max_iterations=10,
    verbose=True,
    log_dir="logs",
)
```

## Tool Contract

`_extract_tool_calls()` expects JSON objects containing `tool` and `params`. `_execute_tool()` looks up the name through `get_tool_by_name()` and returns a standard `success` plus result-or-error dictionary. Keep the prompt format and parser synchronized when changing tool-call syntax.

All tools adhere to a backend-agnostic return structure: `{"success": bool, "result": ..., "error": ...}`.
Active domain tools include:
- `execute_sql_query(database, query, params)`: Introspects and queries SQLite databases (`databases/us_salaries.sqlite`, `databases/chinook.db`).
- `take_screenshot(url, output_dir, timeout)`: Captures web page state via Playwright headless browser automation.

## Skills Integration

Skills (such as `sql_agent/SKILL.md` and `browser_automation/SKILL.md`) provide domain-specific instructions, workflows, and tool parameters. `skill_loader.py` parses their YAML frontmatter and Markdown body to instruct agents on optimal usage patterns without altering core orchestrator logic.

## Error Behavior

Connection checks fail before the first model call. Provider call failures return `None` and become `LLM call failed` task results. Tool lookup, parameter, and execution errors are returned to the model as tool results. The default maximum is 10 iterations.

Gemini support is optional at import time. `orchestrator.py` must remain importable when `google-genai` is unavailable; `GeminiAgent` should fail clearly when Gemini support is actually requested. Ollama requires `requests` and a reachable compatible endpoint.

## Testing Changes

Use a fake `BaseAgent` subclass for shared-loop tests. Avoid external services. Before claiming a change works, run:

```bash
python3 -m unittest discover -s tests -v
```

When changing provider behavior, test both the success path and its connection or dependency failure path. Preserve conversation history, logging events, and result keys unless the API change is intentional and documented.
