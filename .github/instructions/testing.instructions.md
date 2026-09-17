---
name: testing
description: "Guide to testing agents and tools. Use when: writing unit tests, mocking LLMs, testing tool behavior, or validating CLI and import behavior."
applyTo: "**/test_*.py,**/tests/**"
---

# Testing Guide

The repository uses a small standard-library `unittest` smoke suite under `tests/`. Tests must be deterministic, fast, and runnable without an Ollama server, Gemini credentials, network access, or live model calls.

## Run Tests

```bash
python3 -m unittest discover -s tests -v
```

For active-module syntax validation:

```bash
find . -path './venv' -prune -o -path './.git' -prune -o -name '*.py' -print0 \
  | xargs -0 python3 -m py_compile
```

## Current Coverage

- `test_orchestrator_import.py`: imports the orchestrator while simulating a missing Google SDK.
- `test_gemini_import.py`: imports `gemini_utils.py` without `google-genai` and checks its actionable runtime error.
- `test_tools_optional_docx.py`: imports the registry without `python-docx` and checks the DOCX failure path.
- `test_main_cli.py`: loads the CLI module and rejects blank Gemini credentials.
- `test_agent_loop.py`: uses a fake `BaseAgent` subclass to verify tool-result continuation and max-iteration failure.

## Test Patterns

### Import Isolation

Patch `builtins.__import__` for the exact optional top-level package, remove the target module from `sys.modules`, import it, and restore the original module in `finally`. Do not uninstall packages or mutate the developer environment.

### Fake Backends

Subclass `BaseAgent` and implement its backend hooks. Return scripted responses from `_call_llm()`, set `verbose=False`, and use a temporary directory for logs. This tests prompt continuation, tool extraction, tool execution, and termination without external services.

### Tool Tests

Call handlers directly with temporary files and directories. Check both successful results and actionable failures. Also verify registry entries have unique names, descriptions, parameter schemas, and callable functions.

### CLI Tests

Load `main.py` as a module and test pure validation helpers directly. Mock configuration and network calls instead of invoking a live provider. Subprocess tests are appropriate for exit-code behavior when argument parsing itself must be exercised.

## Scope Boundaries

Live Ollama and Gemini checks are environment-dependent integration checks, not part of the default smoke suite. Do not add tests that require API keys, running daemons, model downloads, or network access to the default test discovery path.
