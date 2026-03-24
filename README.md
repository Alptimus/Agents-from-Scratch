# Agents-from-Scratch

A Python-based **autonomous AI agent framework** that orchestrates task execution by combining cloud-based (Google Gemini) and local LLM (Ollama/Llamafile) capabilities.

## Quick Start

### 1. Installation

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

```bash
cp .env.example .env
# Add your GOOGLE_API_KEY for Gemini backend
```

### 3. Run a Task

**Using Ollama (Local):**
```bash
python main.py "List all Python files and count their lines of code" --provider ollama --model mistral
```

**Using Gemini (Cloud):**
```bash
python main.py "Your task" --provider gemini --model gemini-2.5-flash
```

---

## Project Structure

| File | Purpose |
|------|---------|
| [orchestrator.py](orchestrator.py) | Core agent classes (`OllamaAgent`, `GeminiAgent`) — task execution loop, LLM integration |
| [tools.py](tools.py) | Tool registry and implementations — file ops, shell commands, directory listing |
| [main.py](main.py) | CLI entry point — backend provider selection, argument validation |
| [gemini_utils.py](gemini_utils.py) | Gemini API client initialization and utilities |
| [chat_gemini_latest.py](chat_gemini_latest.py) | Standalone Gemini wrapper (embeddings, generation) |
| [Dockerfile](Dockerfile) | Llamafile container for local LLM deployment |
| [.github/copilot-instructions.md](.github/copilot-instructions.md) | **Full architecture guide** — complete reference for development |

---

## How It Works

Both backends follow the same **agent loop**:

```
1. User provides task
   ↓
2. Agent calls LLM with task + conversation history
   ↓
3. LLM extracts JSON tool calls (or completes task)
   ↓
4. Execute tools, collect results
   ↓
5. Feed results back to LLM
   ↓
6. Iterate (max 10 cycles) until complete
```

---

## Common Tasks

### Execute a Task (Python)
```python
from orchestrator import OllamaAgent
# or: from orchestrator import GeminiAgent

agent = OllamaAgent(model="mistral")
result = agent.execute_task("Your task here")
print(result)
```

### Add a New Tool
1. Define function in [tools.py](tools.py) returning `{"success": bool, "result"/"error": <value>}`
2. Add tool dict to `TOOLS` list with: `name`, `description`, `parameters` (JSON schema), `fn`
3. Agent automatically discovers and calls it

### Switch Between Backends
```python
# Local: Ollama
agent = OllamaAgent(model="neural-chat", max_iterations=15)

# Cloud: Gemini
agent = GeminiAgent(model="gemini-1.5-pro", max_iterations=15)
```

### Enable Debug Output
```python
agent = GeminiAgent(verbose=True)
result = agent.execute_task("Your task")
# Prints: tool name, params, result, iteration count
```

---

## Troubleshooting

### Ollama Backend
| Issue | Solution |
|-------|----------|
| **LLM not responding** | Verify: `curl http://localhost:11434/api/tags` |
| **Connection refused** | Start Ollama: `ollama serve` |
| **Model not found** | Pull it: `ollama pull mistral` |

### Gemini Backend
| Issue | Solution |
|-------|----------|
| **API key error** | Verify `GOOGLE_API_KEY` is set in `.env` |
| **Quota exceeded** | Check Google Cloud billing and rate limits |
| **Model not available** | Ensure model name is valid (e.g., `gemini-2.5-flash`) |

### General
| Issue | Solution |
|-------|----------|
| **Agent not finding tools** | Check `TOOLS` list in [tools.py](tools.py) is populated |
| **Tool execution fails** | Review verbose output: `agent = Agent(verbose=True)` |
| **Docker build issues** | Verify Llamafile download URL in [Dockerfile](Dockerfile) |

---

## Full Documentation

For complete architecture, conventions, dependencies, and advanced usage, see:
→ **[.github/copilot-instructions.md](.github/copilot-instructions.md)**

This includes:
- Detailed backend setup (Ollama, Llamafile, Gemini)
- Tool system design patterns
- LLM communication protocols
- How to add new backends
- Environment configuration