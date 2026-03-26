---
name: logging
description: "Guide to the logging system. Use when: understanding agent execution traces, debugging iteration loops, analyzing performance metrics, or interpreting log output formats."
applyTo: "**/logging.instructions.md,**/logger_config.py,**/orchestrator.py"
---

# Logging System Guide

The agents implement **dual-output structured logging**: human-readable plaintext + machine-parseable JSON Lines format. This enables both interactive debugging and programmatic analysis.

## Logging Architecture

### Dual Output

When agents execute tasks, two log files are created:

| File Name | Format | Purpose | Example |
|-----------|--------|---------|---------|
| `logs/task_YYYYMMDD_HHMMSS.txt` | Plaintext | Human-readable execution trace | View directly in editor |
| `logs/task_YYYYMMDD_HHMMSS.jsonl` | JSON Lines | Programmatic analysis, dashboards | Parse with `jq`, import to Analytics |

Both files log the **same events** to the same output directory.

### Log Initialization

Logging is set up when an agent starts executing a task:

```python
from orchestrator import OllamaAgent

agent = OllamaAgent(log_dir="logs")  # Logs will be in ./logs/
result = agent.execute_task("Your task here")

# Two files created:
# - logs/task_20260326_142315.txt
# - logs/task_20260326_142315.jsonl
```

### Log Directory

- **Default location**: `./logs/` (relative to script execution directory)
- **Format**: All logs for a run use same timestamp: `task_YYYYMMDD_HHMMSS.{txt,jsonl}`
- **Auto-created**: Directory is created automatically if it doesn't exist
- **Not version-controlled**: Logs are typically in `.gitignore`

## Event Types

Agents log structured events throughout execution. Each event type includes specific metadata:

### [TASK_INIT]

Task execution begins. Logs backend type, model, and settings.

```
[TASK_INIT] Backend: Ollama | Model: mistral | Max Iterations: 10 | Connection: OK
[TASK_INIT] Backend: Gemini | Model: gemini-2.5-flash | Max Iterations: 10 | Connection: OK
```

**JSON representation:**
```json
{
  "timestamp": "2026-03-26T14:23:15.789Z",
  "level": "INFO",
  "event_type": "TASK_INIT",
  "message": "Backend: Ollama | Model: mistral | Max Iterations: 10 | Connection: OK"
}
```

### [ITERATION_START]

Beginning of agent iteration loop. Includes prompt preview.

```
[ITERATION_START] Iteration: 0 | Prompt: Your task: Read config.json and extract the API key...
[ITERATION_START] Iteration: 1 | Prompt: You found the file. Now check if valid JSON...
```

**Key fields:**
- `Iteration`: Zero-indexed iteration number (0-9 max)
- `Prompt`: First 150 characters of full prompt sent to LLM

### [LLM_CALL]

LLM responded with output. Logs token-level performance.

```
[LLM_CALL] Response: {"tool": "read_file", "params": {"file_path": "config.json"}} | Latency: 1250ms
[LLM_CALL] Response: I found the key! The API key is abc123... | Latency: 875ms
```

**Key fields:**
- `Response`: First 100 characters of response text
- `Latency`: Milliseconds taken for LLM to respond

### [TOOL_EXTRACTION]

JSON tool calls were parsed from LLM response.

```
[TOOL_EXTRACTION] Tools: read_file, validate_json | Count: 2
[TOOL_EXTRACTION] No tools extracted  # Task may be complete
```

### [TOOL_EXECUTION]

Individual tool invocation result. Status emoji indicates success/failure.

```
[TOOL_EXECUTION] ✓ Tool: read_file | Params: {"file_path": "config.json"} | Result: Valid JSON, 47 lines | Latency: 12ms
[TOOL_EXECUTION] ✗ Tool: read_file | Params: {"file_path": "missing.json"} | Result: File not found: missing.json | Latency: 2ms
```

**Key fields:**
- `✓` / `✗`: Success/failure indicator
- `Tool`: Tool name invoked
- `Params`: Parameter dict sent to tool
- `Result`: First 50 characters of result
- `Latency`: Milliseconds for tool execution

### [TASK_COMPLETE]

Task execution finished. Summary of final result.

```
[TASK_COMPLETE] Status: SUCCESS | Iterations: 3 | Duration: 4.2s | Result: The API key is xyz789
[TASK_COMPLETE] Status: FAILED | Iterations: 10 | Duration: 8.5s | Result: Max iterations exceeded
```

**Key fields:**
- `Status`: SUCCESS or FAILED
- `Iterations`: How many iteration cycles ran
- `Duration`: Total wall-clock time in seconds
- `Result`: First 80 characters of final result

### [ERROR]

Logged when exceptions occur during execution.

```
[ERROR] Connection refused | Context: Ollama service not running at localhost:11434
[ERROR] Timeout waiting for tool | Context: run_shell command exceeded 30 seconds
```

## JSON Lines Format

The `.jsonl` file contains one JSON object per line for easy programmatic parsing.

**Minimal Example (4 lines for one task):**
```jsonl
{"timestamp":"2026-03-26T14:23:15.789Z","level":"INFO","logger":"orchestrator.OllamaAgent","event_type":"TASK_INIT","message":"Backend: Ollama | Model: mistral | Max Iterations: 10"}
{"timestamp":"2026-03-26T14:23:16.100Z","level":"INFO","logger":"orchestrator.OllamaAgent","event_type":"ITERATION_START","message":"Iteration: 0 | Prompt: Read config.json..."}
{"timestamp":"2026-03-26T14:23:17.350Z","level":"INFO","logger":"orchestrator.OllamaAgent","event_type":"LLM_CALL","message":"Response: {\"tool\": \"read_file\", \"params\": {...}} | Latency: 1250ms"}
{"timestamp":"2026-03-26T14:23:17.362Z","level":"INFO","logger":"orchestrator.OllamaAgent","event_type":"TOOL_EXECUTION","message":"✓ Tool: read_file | Params: ... | Latency: 12ms"}
```

### Parsing JSON Logs

**With Python:**
```python
import json
from pathlib import Path

jsonl_path = Path("logs/task_20260326_142315.jsonl")
events = []
for line in jsonl_path.read_text().strip().split('\n'):
    if line:
        events.append(json.loads(line))

# Filter by event type
llm_calls = [e for e in events if e['event_type'] == 'LLM_CALL']
tool_exec = [e for e in events if e['event_type'] == 'TOOL_EXECUTION']

# Extract latencies
latencies = [
    int(e['message'].split('Latency: ')[1].split('ms')[0])
    for e in llm_calls
]
print(f"Mean LLM latency: {sum(latencies) / len(latencies):.0f}ms")
```

**With `jq` CLI:**
```bash
# Count event types
cat logs/task_*.jsonl | jq -s 'group_by(.event_type) | map({type: .[0].event_type, count: length})'

# Filter tool_execution events
cat logs/task_*.jsonl | jq 'select(.event_type == "TOOL_EXECUTION")'

# Extract all latencies
cat logs/task_*.jsonl | jq -r 'select(.message | contains("Latency")) | .message' | grep -oP 'Latency: \K[0-9]+' | sort -n
```

## Analyzing Logs

### Performance Profiling

**Total execution time:**
```bash
# From plaintext log
grep "TASK_COMPLETE" logs/task_*.txt | grep -oP 'Duration: \K[0-9.]+s'

# From JSON
jq -r 'select(.event_type == "TASK_COMPLETE") | .message' logs/task_*.jsonl | grep -oP 'Duration: \K[0-9.]+'
```

**Per-iteration breakdown:**
```python
import json
from pathlib import Path

log_file = Path("logs/task_20260326_142315.jsonl")
events = [json.loads(line) for line in log_file.read_text().strip().split('\n') if line]

# Group by iteration
iterations = {}
for event in events:
    msg = event['message']
    if 'Iteration' in msg and 'Prompt' in msg:
        iter_num = int(msg.split('Iteration: ')[1].split(' ')[0])
        if iter_num not in iterations:
            iterations[iter_num] = {'start': event['timestamp'], 'events': []}
        iterations[iter_num]['events'].append(event)

# Compute durations
for iter_num, data in iterations.items():
    if len(data['events']) > 1:
        start = data['events'][0]['timestamp']
        end = data['events'][-1]['timestamp']
        print(f"Iteration {iter_num}: {len(data['events'])} events")
```

### Debugging Failed Tasks

When a task fails:
1. **Check TASK_INIT**: Was backend available?
   ```bash
   grep "TASK_INIT" logs/task_*.txt
   ```

2. **Trace iteration sequence**: How many completed?
   ```bash
   grep "ITERATION_START" logs/task_*.txt
   ```

3. **Find error event**: What went wrong?
   ```bash
   grep "\[ERROR\]" logs/task_*.txt
   ```

4. **Review last LLM response**: What was LLM thinking?
   ```bash
   grep "LLM_CALL" logs/task_*.txt | tail -1
   ```

5. **Check tool failures**: Which tools returned errors?
   ```bash
   grep "✗" logs/task_*.txt  # Failed tools
   ```

## Advanced Usage

### Custom Event Logging

Agents expose the logger for custom events. If extending orchestrator:

```python
class CustomAgent(OllamaAgent):
    def execute_task(self, task):
        self._setup_logging(task)
        
        # Custom event
        if self.logger:
            self.logger.info("[CUSTOM_EVENT] Starting analysis of task domain")
        
        # Continue with normal execution
        return super().execute_task(task)
```

### Log Aggregation

For production deployments, aggregate logs from multiple runs:

```bash
# Combine all task logs
cat logs/task_*.jsonl > combined_logs.jsonl

# Analyze across all tasks
cat combined_logs.jsonl | jq -s 'map(select(.event_type == "TASK_COMPLETE"))' | jq -r '.[] | "\(.message)"' | sort
```

### Retention Policy

Logs accumulate over time. Implement cleanup:

```bash
# Keep only logs from last 7 days
find logs/ -name "task_*.txt" -mtime +7 -delete
find logs/ -name "task_*.jsonl" -mtime +7 -delete
```

## Configuration

Logging is automatically initialized when agents run. To customize:

```python
from orchestrator import OllamaAgent

# Custom log directory
agent = OllamaAgent(
    log_dir="custom_logs",  # Logs go to ./custom_logs/
    verbose=False            # Don't print to stdout (still logs to files)
)
```

**Logger implementation**: See [logger_config.py](logger_config.py) for low-level details on JSON handler and plaintext formatting.
