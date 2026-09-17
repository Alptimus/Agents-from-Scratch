# Agents-from-Scratch

**Autonomous AI agent framework** that orchestrates task execution by combining cloud-based (Google Gemini) and local LLM (Ollama/Llamafile) capabilities.

→ **[Start here: Full Documentation (.github/copilot-instructions.md)](.github/copilot-instructions.md)**

## Quick Start

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure API Keys
Set `GOOGLE_API_KEY` in your environment or in a local `.env` file for the optional Gemini backend.

### 3. Run a Task

**Using Ollama (Local):**
```bash
python main.py "List all Python files and count lines of code" --provider ollama --model mistral
```
*Requires: `ollama serve` running in another terminal*

**Using Gemini (Cloud):**
```bash
python main.py "Your task" --provider gemini --model gemini-2.5-flash
```

Or run from Python:
```python
from orchestrator import OllamaAgent  # or GeminiAgent
agent = OllamaAgent(model="mistral")
print(agent.execute_task("Your task here"))
```

## Smoke Tests

Run the offline smoke suite without starting Ollama or configuring Gemini:

```bash
python3 -m unittest discover -s tests -v
```

Live Ollama execution requires `ollama serve`; live Gemini execution requires `GOOGLE_API_KEY` and the installed dependencies in `requirements.txt`.

## Full Documentation

**→ See [.github/copilot-instructions.md](.github/copilot-instructions.md) for:**
- Complete architecture and control flow
- Backend setup (Ollama, Llamafile, Gemini)
- Tool system design patterns
- Add new tools & extend capabilities
- Task execution logging (plaintext + JSON)
- Troubleshooting and common issues
- Code conventions and patterns
- Advanced configurations