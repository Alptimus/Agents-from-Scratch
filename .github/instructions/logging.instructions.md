---
name: logging
description: "Guide to the logging system. Use when: understanding agent execution traces, debugging iteration loops, analyzing performance metrics, or interpreting log output formats."
applyTo: "**/logging.instructions.md,**/logger_config.py,**/orchestrator.py"
---

# Logging System Guide

The agent loop writes the same execution trace to two files: a human-readable plaintext log and a machine-readable JSON Lines log.

## Files

`BaseAgent.execute_task()` calls `setup_logging()` before checking the backend. With the default `log_dir="logs"`, it creates:

```text
logs/agent_YYYYMMDD_HHMMSS.log
logs/agent_YYYYMMDD_HHMMSS.jsonl
```

The directory is created automatically. The logger returns the two paths through `agent.log_files` after task initialization. Runtime logs should not be committed.

## Events

The orchestrator emits these event types:

- `LOG_INIT`: log files were initialized.
- `TASK_INIT`: provider, model, and iteration limit.
- `ITERATION_START`: iteration number and prompt preview.
- `LLM_CALL`: response preview and latency.
- `TOOL_EXTRACTION`: extracted tool names and count, or no tools.
- `TOOL_EXECUTION`: tool name, parameters, result preview, and latency.
- `TASK_COMPLETE`: success/failure, iteration count, duration, and result preview.
- `CONVERSATION_EXPORT`: full conversation history is attached to the JSON event.
- `ERROR`: connection, model, or iteration-limit errors.

Iterations are one-based in the runtime logs: the first model call is `Iteration: 1`.

## Plaintext Logs

The `.log` file is intended for quick inspection. It contains timestamped previews, for example:

```text
[ITERATION_START] Iteration: 1 | Prompt: ...
[LLM_CALL] Response: ... | Latency: 1200ms
[TOOL_EXECUTION] ✓ Tool: read_file | Params: {...} | Result: ... | Latency: 4ms
[TASK_COMPLETE] Status: SUCCESS | Iterations: 2 | Duration: 2.4s | Result: ...
```

## JSON Lines Logs

The `.jsonl` file contains one JSON object per line. Each event includes `timestamp`, `level`, `logger`, `event_type`, and `message`. Some events also include `full_text`; the orchestrator uses that field for complete prompts, responses, tool results, and conversation exports.

Read event types with:

```bash
jq -r '.event_type' logs/agent_*.jsonl
```

Parse a task in Python:

```python
import json
from pathlib import Path

for line in Path("logs/agent_YYYYMMDD_HHMMSS.jsonl").read_text().splitlines():
    event = json.loads(line)
    print(event["event_type"], event["message"])
```

## Debugging Workflow

1. Check `TASK_INIT` to confirm the selected provider and model.
2. Check `ERROR` events for connection or model failures.
3. Compare `ITERATION_START`, `LLM_CALL`, and `TOOL_EXECUTION` counts.
4. Inspect `full_text` when the preview omits relevant prompt or result content.
5. Check `TASK_COMPLETE` or the final error for the termination reason.

The JSON handler intentionally avoids allowing logging failures to crash the task. A deprecation warning may be emitted by the current UTC timestamp implementation in `logger_config.py`; it does not change the log format or agent result.
