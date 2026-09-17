# Workspace Instructions: Multi-Model AI Agent Orchestration System

This is a Python-based **autonomous AI agent framework** that orchestrates task execution by combining cloud-based (Google Gemini) and local LLM (Ollama/Llamafile) capabilities.

## Working Rules for This Repo

These are the guardrails most likely to reduce friction in this codebase:

- Start with a narrow read of the exact files involved; do not rewrite broad sections of the project without confirming the current implementation.
- Treat this repo as a Python tool-automation project: verify imports, tool registration, and task-loop behavior before changing agent behavior.
- Prefer surgical edits to [orchestrator.py](../orchestrator.py), [tools.py](../tools.py), and [main.py](../main.py); avoid broad rewrites unless the task clearly requires them.
- When a request touches execution or validation, run the smallest relevant command before claiming success. If there is no automated test suite for the change, state that limitation and use a targeted syntax or runtime check instead.
- Preserve the existing instruction structure: keep project guidance concise, and prefer links to [README.md](../README.md) and the files in [.github/instructions](./instructions) rather than duplicating long explanations in every task.
- Do not invent missing APIs, environment assumptions, or tool names; confirm actual code paths and config values before generating patches.
- If a task spans multiple steps, keep the agent loop explicit: inspect, patch, validate, summarize.
- Favor direct evidence over assumptions. A claim like “fixed” or “works” must be backed by a fresh verification result from the relevant command or test.

## Project Architecture

```
legacy/chat_gemini_latest.py  → Legacy Gemini demo wrapper (embeddings, generation)
tools.py                     → Tool registry (file ops, shell commands, directory listing)
orchestrator.py              → OllamaAgent & GeminiAgent classes (autonomous task execution)
gemini_utils.py              → Gemini client initialization and API utilities
main.py                      → CLI entry point for task execution
Dockerfile                   → Llamafile container (Qwen 3.5 9B quantized model)
```

**Control Flow (Both Backends):**
1. User provides task → 2. Agent calls LLM (Ollama HTTP or Gemini API) → 3. Extract JSON tool calls → 4. Execute tools → 5. Feed results back to LLM → 6. Iterate (max 10 cycles)

## Build & Run

### Development Setup
```bash
# Clone and install dependencies
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up environment
cp .env.example .env  # Add your GOOGLE_API_KEY
```

### Backend Option 1: Ollama (Local)

**Option 1a: Use existing Ollama service**
```bash
# Terminal 1: Start Ollama (if not running)
ollama serve

# Terminal 2: Run agent-based tasks
python -c "from orchestrator import OllamaAgent; \
agent = OllamaAgent(model='mistral'); \
print(agent.execute_task('Your task here'))"
```

**Option 1b: Use Docker container (Llamafile)**
```bash
docker build -t debian-llamafile .
docker run -d -p 1111:1111 debian-llamafile
# Then update OllamaAgent base_url to http://localhost:1111
```

### Backend Option 2: Gemini (Cloud)

```bash
# Terminal: Run with Gemini backend
python -c "from orchestrator import GeminiAgent; \
agent = GeminiAgent(model='gemini-2.5-flash'); \
print(agent.execute_task('Your task here'))"
```

### Run Gemini Module (Legacy)
```bash
python legacy/chat_gemini_latest.py  # Demonstrates embeddings & generation
```

## Code Conventions

### Tool System
- **Definition**: Tools are dictionaries with `name`, `description`, `parameters` (JSON schema), and `fn` (callable)
- **Registration**: All tools added to `TOOLS` list in [tools.py](tools.py)
- **Response Format**: Tool functions return `{"success": bool, "result": <data> or "error": str}`
- **Location**: Common tools: `run_shell()`, `read_file()`, `write_file()`, `list_directory()` in [tools.py](tools.py)

### LLM Communication Patterns
- **JSON Output**: Both agents parse single-line JSON from LLM: `{"tool": "<name>", "params": {...}}`
- **Error Handling**: Tool execution errors captured and fed back to agent with context
- **Iteration Limit**: Max 10 turns to prevent infinite loops
- **Backend Flexibility**: Switch between Ollama and Gemini by using `OllamaAgent` or `GeminiAgent`

### Agent Configuration

**Using OllamaAgent (Local):**
```python
from orchestrator import OllamaAgent

agent = OllamaAgent(
    ollama_base_url="http://localhost:11434",  # Default Ollama endpoint
    model="mistral",  # Or "neural-chat", etc.
    max_iterations=10
)
result = agent.execute_task("Your task here")
```

**Using GeminiAgent (Cloud):**
```python
from orchestrator import GeminiAgent

agent = GeminiAgent(
    api_key_name="GOOGLE_API_KEY",  # From .env file
    model="gemini-2.5-flash",  # Or "gemini-1.5-pro", etc.
    max_iterations=10
)
result = agent.execute_task("Your task here")
```

### Environment Configuration
- **Storage**: `.env` file (not version-controlled)
- **Key Variables**:
  - `GOOGLE_API_KEY` — Google Gemini API authentication
- **Loading**: Use `python-decouple` for safe environment variable access

## Key Files

| File | Purpose | When to Edit |
|------|---------|--------------|
| [orchestrator.py](orchestrator.py) | OllamaAgent & GeminiAgent classes | Adding agentic features, changing iteration logic, or supporting new backends |
| [gemini_utils.py](gemini_utils.py) | Gemini client initialization & API utilities | Integrating new Gemini features or custom client setup |
| [tools.py](tools.py) | Tool definitions & registry | Adding new capabilities (file, shell, API operations) |
| [legacy/chat_gemini_latest.py](legacy/chat_gemini_latest.py) | Legacy Gemini demo wrapper | Integrating embeddings, token counting, or generation features |
| [main.py](main.py) | CLI entry point | Execute tasks with command-line arguments |
| [requirements.txt](requirements.txt) | Python dependencies | Adding packages or version pinning |
| [Dockerfile](Dockerfile) | Container runtime | Updating LLM model, layer dependencies, or ports |

## Specialized Guidance

For specific development tasks, refer to these focused instruction files:

| Task | Instruction File | Coverage |
|------|------------------|----------|
| **Adding new tools** | [.github/instructions/tools.instructions.md](.github/instructions/tools.instructions.md) | Tool design patterns, response format, error handling, tool discovery, adding tools to registry |
| **Understanding logs** | [.github/instructions/logging.instructions.md](.github/instructions/logging.instructions.md) | Dual plaintext + JSON Lines logging, event types, performance analysis, debugging logs |
| **Writing tests** | [.github/instructions/testing.instructions.md](.github/instructions/testing.instructions.md) | Unit tests, mocking, integration tests, pytest setup, CI/CD patterns, coverage targets |
| **Agent implementation** | [.github/instructions/orchestrator.instructions.md](.github/instructions/orchestrator.instructions.md) | Modifying agent behavior, adding backends, debugging iteration loops |

## Common Tasks

### Add a New Tool
1. Define function in [tools.py](tools.py) following `{"success": bool, "result"/"error": <value>}` pattern
2. Add tool dict to `TOOLS` list with: `name`, `description`, `parameters` (JSON schema), `fn`
3. Agent will automatically discover and call it via JSON parsing (works for both backends)

### Switch Between Backends

**Ollama (Local):**
```python
agent = OllamaAgent(model="neural-chat", max_iterations=15)
```

**Gemini (Cloud):**
```python
agent = GeminiAgent(model="gemini-1.5-pro", max_iterations=15)
```

### Modify Agent Behavior
- **Change max iterations**: Set `max_iterations` parameter (e.g., `max_iterations=20`)
- **Change LLM model**: Set `model` parameter for either agent
- **Change Ollama endpoint**: `OllamaAgent(ollama_base_url="http://other-host:11434")`
- **Use custom API key**: `GeminiAgent(api_key_name="CUSTOM_GEMINI_KEY")`

### Add New LLM Model

**For Ollama:**
1. Ensure model is available: `ollama pull <model-name>`
2. Pass to OllamaAgent: `OllamaAgent(model="<model-name>")`

**For Gemini:**
1. Ensure model is available in Gemini API (Gemini 2.5 Flash, 1.5 Pro, etc.)
2. Pass to GeminiAgent: `GeminiAgent(model="<model-name>")`

### Debug Agent Execution

Both agents log each iteration when `verbose=True` (default):
- Tool name and parameters extracted from LLM response
- Execution result (success/error)
- Iteration count (0–10)

```python
agent = GeminiAgent(verbose=True)  # or OllamaAgent(verbose=True)
result = agent.execute_task("Your task")
# Automatic logging to stdout
```

For custom logging, subclass the agent or add debug statements in [orchestrator.py](orchestrator.py).

## Task Execution Logs

Every task generates detailed logs in the `logs/` directory with two formats:
- **`agent_YYYYMMDD_HHMMSS.log`** — Human-readable plaintext
- **`agent_YYYYMMDD_HHMMSS.jsonl`** — Machine-parseable JSON Lines (one object per line)

**Plaintext Log Example:**
```
2026-03-24 14:23:15,789 [INFO] orchestrator.20260324_142315 — [LOG_INIT] Logging initialized
2026-03-24 14:23:15,825 [INFO] orchestrator.20260324_142315 — [TASK_INIT] Backend: Ollama | Model: mistral | ...
2026-03-24 14:23:15,950 [INFO] orchestrator.20260324_142315 — [ITERATION_START] Iteration: 1 | Prompt: ...
2026-03-24 14:23:17,145 [INFO] orchestrator.20260324_142315 — [LLM_CALL] Response: I'll read the file... | Latency: 1195ms
2026-03-24 14:23:17,156 [INFO] orchestrator.20260324_142315 — [TOOL_EXTRACTION] Tools: read_file | Count: 1
2026-03-24 14:23:17,287 [INFO] orchestrator.20260324_142315 — [TOOL_EXECUTION] ✓ Tool: read_file | Params: {...} | Latency: 131ms
2026-03-24 14:23:18,456 [INFO] orchestrator.20260324_142315 — [TASK_COMPLETE] Status: SUCCESS | Iterations: 2 | Duration: 2.8s
```

**JSON Lines Log Example** (each line is valid JSON):
```bash
tail logs/agent_20260324_142315.jsonl | jq .event_type
# Outputs: TASK_INIT, ITERATION_START, LLM_CALL, TOOL_EXTRACTION, TOOL_EXECUTION, TASK_COMPLETE
```

Parse logs programmatically:
```python
import json

with open("logs/agent_YYYYMMDD_HHMMSS.jsonl") as f:
    for line in f:
        event = json.loads(line)
        print(f"{event['event_type']:20} {event['message']}")
```

**Logged Events:**
- **TASK_INIT**: Backend, model, configuration
- **ITERATION_START**: Iteration number, prompt sent to LLM
- **LLM_CALL**: LLM response text, latency (ms)
- **TOOL_EXTRACTION**: Tool names extracted from LLM response
- **TOOL_EXECUTION**: Tool name, parameters, result, latency (ms)
- **TASK_COMPLETE**: Success status, iteration count, total duration
- **ERROR**: Error messages with context information

See [.github/instructions/logging.instructions.md](.github/instructions/logging.instructions.md) for detailed log analysis.

## Dependencies & Versions

| Package | Purpose | Note |
|---------|---------|------|
| `google-genai` | Gemini API client | Used in [gemini_utils.py](gemini_utils.py) and the legacy demo in [legacy/chat_gemini_latest.py](legacy/chat_gemini_latest.py) |
| `requests` | HTTP client for Ollama | Required for agent LLM communication |
| `python-decouple` | Environment variable management | Loads `GOOGLE_API_KEY` safely |
| `numpy` | Numerical operations | Used for embeddings |

See [requirements.txt](requirements.txt) for exact versions.

## Known Limitations & Next Steps

- ✅ [main.py](main.py) implemented with CLI support
- ⚠️ No test suite — consider adding pytest fixtures for tool execution
- ⚠️ Single-threaded agent loop — concurrent task execution not yet supported
- ✅ **Ready for**: Task automation, autonomous workflows, multi-model orchestration

## Helpful Patterns

### Task with File Operations (Any Backend)
```python
from orchestrator import OllamaAgent  # or GeminiAgent

agent = OllamaAgent()  # or GeminiAgent()
task = "Read config.json, modify the 'timeout' field to 60, and save it back"
result = agent.execute_task(task)
```

### Task with Shell Execution (Any Backend)
```python
task = "List all Python files in the current directory and count the total lines of code"
result = agent.execute_task(task)
```

### Multi-Step Reasoning (Any Backend)
```python
task = """
1. Check if requirements.txt exists
2. If yes, read it and extract all package names
3. Create a summary report: total packages, top 3 by name
"""
result = agent.execute_task(task)  # Agent autonomously iterates until complete
```

### Switch Backends Mid-Development
```python
# Start with fast local model
agent = OllamaAgent(model="mistral")
result = agent.execute_task("My task")

# If needed, switch to powerful cloud model (just change the import and class)
from orchestrator import GeminiAgent
agent = GeminiAgent(model="gemini-2.5-flash")
result = agent.execute_task("My task")
```

## Getting Help

**OllamaAgent Issues:**
- **LLM not responding?** Verify Ollama is running: `curl http://localhost:11434/api/tags`
- **Connection refused?** Ensure Ollama service started: `ollama serve`
- **Model not found?** Pull the model: `ollama pull mistral`

**GeminiAgent Issues:**
- **API key error?** Verify `GOOGLE_API_KEY` is set in `.env` (see Development Setup)
- **Quota exceeded?** Check Google Cloud billing and rate limits
- **Model not available?** Ensure model name is valid (e.g., `gemini-2.5-flash`)

**General Issues:**
- **Agent not finding tools?** Check [tools.py](tools.py) `TOOLS` list is populated
- **Tool execution fails?** Review tool parameters in conversation history (verbose output)
- **Docker build issues?** Check Llamafile download URL and Dockerfile base image compatibility
