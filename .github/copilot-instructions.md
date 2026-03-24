# Workspace Instructions: Multi-Model AI Agent Orchestration System

This is a Python-based **autonomous AI agent framework** that orchestrates task execution by combining cloud-based (Google Gemini) and local LLM (Ollama/Llamafile) capabilities.

## Project Architecture

```
chat_gemini_latest.py  → Google Gemini API wrapper (embeddings, generation)
tools.py               → Tool registry (file ops, shell commands, directory listing)
orchestrator.py        → OllamaAgent & GeminiAgent classes (autonomous task execution)
gemini_utils.py        → Gemini client initialization and API utilities
main.py                → CLI entry point for task execution
Dockerfile             → Llamafile container (Qwen 3.5 9B quantized model)
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
python chat_gemini_latest.py  # Demonstrates embeddings & generation
```

## Code Conventions

### Tool System
- **Definition**: Tools are dictionaries with `name`, `description`, `parameters` (JSON schema), and `fn` (callable)
- **Registration**: All tools added to `TOOLS` list in [tools.py](tools.py)
- **Response Format**: Tool functions return `{"success": bool, "result": <data> or "error": str}`
- **Location**: Common tools: `execute_shell()`, `read_file()`, `write_file()`, `list_directory()` in [tools.py](tools.py)

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
| [chat_gemini_latest.py](chat_gemini_latest.py) | Gemini API wrapper (legacy) | Integrating embeddings, token counting, or generation features |
| [main.py](main.py) | CLI entry point | Execute tasks with command-line arguments |
| [requirements.txt](requirements.txt) | Python dependencies | Adding packages or version pinning |
| [Dockerfile](Dockerfile) | Container runtime | Updating LLM model, layer dependencies, or ports |

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

## Dependencies & Versions

| Package | Purpose | Note |
|---------|---------|------|
| `google-genai` | Gemini API client | Used in [chat_gemini_latest.py](chat_gemini_latest.py) |
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
