# Architecture Explanation

This document explains the active execution path in Agents-from-Scratch. For installation and command examples, see [README.md](README.md).

## System Overview

The project is a synchronous Python agent framework with two interchangeable model providers:

- `OllamaAgent` sends prompts to an Ollama-compatible HTTP endpoint.
- `GeminiAgent` sends prompts through the optional Google Gemini SDK.

Both providers inherit the same orchestration behavior from `BaseAgent`. Only connection checks and model calls are backend-specific.

```text
CLI or Python caller
        |
        v
  OllamaAgent / GeminiAgent
        |
        v
  BaseAgent.execute_task()
        |
        +--> prompts.py: build prompts
        +--> tools.py: describe, find, and execute tools
        +--> model backend: generate response
        +--> logger_config.py: write execution trace
```

## Active Modules

| Module | Role |
| --- | --- |
| `main.py` | Parses CLI arguments, loads optional skills, validates the selected provider, runs an agent, and maps results to exit codes. |
| `orchestrator.py` | Owns the shared task loop and provider implementations. |
| `prompts.py` | Defines the common system, initial, and continuation prompts. |
| `tools.py` | Defines the callable tools and the registry exposed to the model. |
| `gemini_utils.py` | Lazily depends on `google-genai`; creates clients and sends Gemini requests. |
| `skill_loader.py` | Parses Markdown skill files and returns task metadata. |
| `logger_config.py` | Creates paired plaintext and JSON Lines log handlers. |
| `tests/` | Verifies imports, optional dependency behavior, CLI validation, and backend-independent loop behavior without external services. |

`legacy/chat_gemini_latest.py` and `playwright_mcp.py` are separate manual utilities. Neither is imported by the active agent flow.

## Agent Abstraction

`BaseAgent` defines the shared public and protected behavior:

- `execute_task(task_description)` runs the complete task lifecycle.
- `_extract_tool_calls(response_text)` extracts one or more JSON tool calls.
- `_execute_tool(tool_name, params)` resolves a tool in the registry and invokes it.
- `_setup_logging()` and the `_log_*` methods record execution details.
- `_check_connection()`, `_get_connection_error_msg()`, `_call_llm()`, `_get_backend_name()`, and `_get_backend_connection_info()` are abstract backend hooks.

`OllamaAgent` adds `ollama_base_url`, `api_url`, and `think`. `GeminiAgent` adds `api_key_name` and lazily stores its client after a successful connection check. Their constructors retain the same configuration shape used by the CLI and Python examples.

## Task Lifecycle

`BaseAgent.execute_task()` follows this sequence:

1. Create the configured log files.
2. Check the provider connection.
3. Format the current `TOOLS` registry into the system prompt.
4. Build the initial prompt from the system prompt and task description.
5. Call the provider through `_call_llm()`.
6. Add the model response to conversation history.
7. Extract JSON objects containing `tool` and `params`.
8. If no calls are found, return a successful result.
9. Execute every extracted call and attach results to the current history item.
10. Build a continuation prompt containing the prior response and JSON tool results.
11. Continue until completion, an LLM failure, or `max_iterations` is reached.

The default iteration limit is 10. The limit is a safety boundary, not a guarantee that a task needs 10 model calls.

## Prompt Contract

`prompts.py` gives the model the available tool descriptions and requires calls in this shape:

```json
{"tool": "tool_name", "params": {"parameter": "value"}}
```

Multiple objects may appear in one response. The extractor scans balanced JSON objects and ignores malformed objects or JSON objects without both required keys. After tool execution, the continuation prompt includes:

- the original task,
- the previous model response, and
- a JSON summary containing each tool name, parameters, and result.

The model completes the task by returning a response with no tool-call objects.

## Tool Registry

A registered tool is a dictionary with:

```python
{
    "name": "tool_name",
    "description": "What the tool does",
    "parameters": {...},
    "fn": callable,
}
```

The active registry contains:

- `read_file(file_path)`
- `write_file(file_path, content)`
- `list_directory(dir_path=".")`
- `run_shell(command)` with a 30-second timeout
- `read_docx_file(file_path)`

Tool handlers return dictionaries with `success` and either result data or `error`. Unknown tools, invalid parameters, and raised tool exceptions are converted into failed tool results so the model can see the failure.

`python-docx` is optional. `tools.py` keeps the registry importable when the package is absent, and `read_docx_file()` returns an installation instruction only when that tool is used.

## Provider Behavior

### Ollama

`OllamaAgent._check_connection()` sends a five-second GET request to `<ollama_base_url>/api/tags`. `_call_llm()` sends a non-streaming POST request to `<ollama_base_url>/api/generate` with:

```json
{
  "model": "mistral",
  "prompt": "...",
  "stream": false,
  "think": false
}
```

The default endpoint is `http://localhost:11434`. Missing `requests` is handled as a clear dependency failure rather than an import-time crash.

### Gemini

`gemini_utils.py` treats `google-genai` as an optional import. The active modules can be imported without it, while `get_gemini_client()` and `call_gemini()` raise an actionable installation error when the SDK is unavailable. `get_gemini_client()` reads the configured API-key variable and rejects missing or blank values.

`GeminiAgent._check_connection()` initializes the client lazily. `_call_llm()` delegates generation to `call_gemini()` and returns the response text.

## Result Contract

A successful task returns the final model response and history:

```python
{
    "success": True,
    "result": "final response",
    "iterations": 2,
    "conversation": [
        {
            "iteration": 1,
            "agent_response": "...",
            "tool_calls": [
                {
                    "tool": "read_file",
                    "params": {"file_path": "README.md"},
                    "result": {"success": True, "content": "..."},
                }
            ],
        },
        {"iteration": 2, "agent_response": "Task complete."},
    ],
}
```

Failure results use `success: False` and normally include `error`. Backend connection failures stop before the first model call. Empty model responses return `LLM call failed`. Exhausting the iteration limit includes `last_response` and the accumulated conversation.

## CLI Flow

`main.py` supports either a positional task, a `--skill` Markdown file, or both. When both are supplied, the parsed skill description is primary and the positional task is appended as additional instructions.

Before creating an agent, the CLI:

1. Selects the default model for the provider if none was supplied.
2. Checks Ollama reachability or validates a nonblank Gemini API key.
3. Instantiates the selected agent.
4. Executes the task and prints the result.

The default provider is Gemini. Use `--provider ollama` for local execution. `--quiet` suppresses progress output; otherwise the CLI is verbose by default. `--think` is forwarded only to `OllamaAgent`.

## Logging

Each task creates:

- `logs/agent_YYYYMMDD_HHMMSS.log`
- `logs/agent_YYYYMMDD_HHMMSS.jsonl`

The plaintext file contains readable previews. The JSON Lines file contains one event object per line and may include full prompt, response, tool-result, and conversation text. Events emitted by the orchestrator include:

- `LOG_INIT`
- `TASK_INIT`
- `ITERATION_START`
- `LLM_CALL`
- `TOOL_EXTRACTION`
- `TOOL_EXECUTION`
- `TASK_COMPLETE`
- `CONVERSATION_EXPORT`
- `ERROR`

Use the JSON Lines file for scripts and the plaintext file for quick inspection. Generated logs are runtime artifacts and should not be committed.

## Skill Files

`skill_loader.load_skill_file()` accepts a Markdown path. It supports simple YAML-like frontmatter between `---` markers and extracts:

- `name`, falling back to the filename stem;
- `description`, combined with the first relevant body section; and
- `body`, containing the Markdown after frontmatter.

The loader raises `FileNotFoundError` for missing paths and `ValueError` for non-Markdown files, unreadable files, or files without a usable description.

## Testing Strategy

The smoke tests are intentionally offline and use import guards, mocks, temporary files, and a fake `BaseAgent` subclass. They do not contact Ollama or Gemini.

```bash
python3 -m unittest discover -s tests -v
```

The suite checks:

- import safety without `google-genai`;
- import safety and explicit failure without `python-docx`;
- CLI module loading and blank-key validation;
- tool-result continuation through the shared loop; and
- max-iteration termination.

For syntax validation, compile active files while excluding `.git` and `venv`. Live provider checks require their respective services, credentials, models, and network access.

## Extension Guidance

To add a tool:

1. Implement a typed handler in `tools.py`.
2. Return the standard `success`/result-or-error dictionary.
3. Add its metadata and callable to `TOOLS`.
4. Add a focused offline test.
5. Run the smoke suite.

To add a provider, subclass `BaseAgent` and implement the five backend hooks. Keep prompt construction, extraction, tool execution, logging, conversation tracking, and iteration limits in `BaseAgent` so provider behavior remains consistent.

## Current Limits

The framework is synchronous and single-threaded. It does not currently provide streaming responses, concurrent tool execution, automatic retries, persistent conversation storage, or live integration tests. These are boundaries of the current implementation, not required setup steps.
