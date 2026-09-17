# Agents-from-Scratch

Agents-from-Scratch is a Python framework for running autonomous, tool-using tasks with either a local Ollama-compatible model or Google Gemini. The two backends share one orchestration loop, tool registry, prompt format, logging system, and result structure.

## What Is Included

| Component | Responsibility |
| --- | --- |
| [main.py](main.py) | Command-line interface, task/skill input, provider validation, and result display |
| [orchestrator.py](orchestrator.py) | `BaseAgent`, `OllamaAgent`, `GeminiAgent`, iteration loop, tool extraction, execution, and logging |
| [tools.py](tools.py) | Built-in tool implementations and the `TOOLS` registry |
| [prompts.py](prompts.py) | Shared system, initial, and continuation prompts |
| [gemini_utils.py](gemini_utils.py) | Optional Gemini client initialization and generation calls |
| [skill_loader.py](skill_loader.py) | Markdown skill-file parsing for CLI task input |
| [logger_config.py](logger_config.py) | Plaintext and JSON Lines execution logs |
| [tests/](tests/) | Fast offline smoke tests |
| [legacy/chat_gemini_latest.py](legacy/chat_gemini_latest.py) | Isolated manual Gemini/embedding demo; not used by the active flow |
| [playwright_mcp.py](playwright_mcp.py) | Separate manual Playwright screenshot utility |
| [Dockerfile](Dockerfile) | Optional Llamafile container configuration |

## Requirements

- Python 3.10 or newer is recommended.
- Install the packages in [requirements.txt](requirements.txt).
- Ollama mode requires an Ollama-compatible HTTP service.
- Gemini mode requires `google-genai` and a `GOOGLE_API_KEY`.
- DOCX reading is optional and requires `python-docx`.
- The Playwright utility requires Playwright and installed browser binaries; it is not part of the agent loop.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
python3 -m pip install -r requirements.txt
```

For Gemini, set the key in the environment or a local, untracked `.env` file:

```bash
export GOOGLE_API_KEY="your-key"
```

The project does not require a `.env.example` file. `python-decouple` is used when installed, and the active code falls back to regular environment variables when it is unavailable.

## Run Tasks

### Ollama

Start Ollama separately, then run a task:

```bash
ollama serve
python3 main.py "List all Python files" --provider ollama --model mistral
```

The CLI checks `http://localhost:11434/api/tags` before starting. Use the Python API to select another endpoint:

```python
from orchestrator import OllamaAgent

agent = OllamaAgent(
    ollama_base_url="http://localhost:11434",
    model="mistral",
    max_iterations=10,
    verbose=True,
    think=False,
)
result = agent.execute_task("Inspect the project and summarize its Python files")
```

### Gemini

```bash
export GOOGLE_API_KEY="your-key"
python3 main.py "Summarize the project architecture" --provider gemini --model gemini-2.5-flash
```

Or use the Python API:

```python
from orchestrator import GeminiAgent

agent = GeminiAgent(
    api_key_name="GOOGLE_API_KEY",
    model="gemini-2.5-flash",
    max_iterations=10,
    verbose=True,
)
result = agent.execute_task("Summarize the project architecture")
```

Gemini support is optional at import time. If `google-genai` is missing, importing the active modules still works; creating or using Gemini functionality raises an actionable installation error.

## CLI Reference

```text
python3 main.py [task] [options]
```

- `--provider {ollama,gemini}` selects the backend. The default is `gemini`.
- `--model MODEL` overrides the backend default (`mistral` for Ollama, `gemini-2.5-flash` for Gemini).
- `--skill PATH` loads a Markdown skill file. The skill description becomes the task input.
- A positional task and `--skill` can be supplied together; the positional task is appended as additional instructions.
- `--quiet` suppresses progress output. Verbose output is enabled unless `--quiet` is supplied.
- `--verbose` is accepted for compatibility but does not override the default quiet behavior when `--quiet` is supplied.
- `--think` enables Ollama extended thinking and has no effect for Gemini.

Examples:

```bash
python3 main.py "Inspect requirements.txt" --provider ollama
python3 main.py --skill path/to/SKILL.md --provider gemini
python3 main.py "Focus on performance" --skill path/to/SKILL.md --quiet
```

## Execution Model

`BaseAgent.execute_task()` is shared by both providers:

1. Initialize task logging.
2. Check backend availability.
3. Build the system prompt from the registered tools.
4. Send the task to the selected model.
5. Extract JSON tool calls from the response.
6. Execute each registered tool and record its result.
7. Feed the tool results into a continuation prompt.
8. Repeat until the model returns no tool calls or `max_iterations` is reached.

Tool calls use this format:

```json
{"tool": "read_file", "params": {"file_path": "README.md"}}
```

The loop has a default maximum of 10 iterations. A response without tool calls is treated as the completed task. Tool failures are returned to the model as results so it can recover or report the problem.

## Built-in Tools

The registry in [tools.py](tools.py) currently provides:

- `read_file`: read a UTF-8 text file.
- `write_file`: create parent directories and write UTF-8 text.
- `list_directory`: list sorted entries in a directory.
- `run_shell`: run a shell command with a 30-second timeout.
- `read_docx_file`: extract paragraph text from a `.docx` file.

Every tool returns a dictionary with `success` and either result data or an `error`. The registry remains importable when `python-docx` is unavailable; using `read_docx_file` in that state returns an installation message.

## Results and Errors

Successful completion returns:

```python
{
    "success": True,
    "result": "final model response",
    "iterations": 2,
    "conversation": [...],
}
```

Connection failures, LLM failures, and iteration exhaustion return `success: False` with an `error` field. The CLI maps successful tasks to exit code 0 and failures to exit code 1. Missing task input, invalid skill files, and keyboard interruption are also reported with nonzero exit codes.

## Logging

Each call to `execute_task()` creates two files in `logs/` by default:

- `agent_YYYYMMDD_HHMMSS.log` for human-readable output.
- `agent_YYYYMMDD_HHMMSS.jsonl` for one JSON object per event.

Events include `LOG_INIT`, `TASK_INIT`, `ITERATION_START`, `LLM_CALL`, `TOOL_EXTRACTION`, `TOOL_EXECUTION`, `TASK_COMPLETE`, `CONVERSATION_EXPORT`, and `ERROR`. The JSON handler stores full prompts, responses, tool results, and conversation exports where the orchestrator supplies them. Generated logs are ignored by Git.

## Skills

`--skill` accepts a Markdown file with optional frontmatter. `skill_loader.py` extracts `name`, `description`, and the body. A missing file, non-Markdown path, unreadable file, or file without usable description raises a clear CLI error.

## Tests and Validation

Run the deterministic smoke suite without Ollama, Gemini credentials, or network access:

```bash
python3 -m unittest discover -s tests -v
```

The tests cover:

- Importing `orchestrator.py` without `google-genai`.
- Importing `gemini_utils.py` without `google-genai` and checking its runtime error.
- Importing `tools.py` without `python-docx` and checking the DOCX failure path.
- CLI module loading and blank API-key rejection.
- Shared-loop tool continuation and maximum-iteration failure.

Additional syntax validation:

```bash
find . -path './venv' -prune -o -path './.git' -prune -o -name '*.py' -print0 \
  | xargs -0 python3 -m py_compile
git diff --check
```

Live backend checks are intentionally environment-dependent: Ollama must be running with a selected model available, and Gemini must have a valid key, installed SDK, network access, and an available model.

## Optional Llamafile Container

The Dockerfile downloads a Qwen Llamafile and exposes port `1111`:

```bash
docker build -t debian-llamafile .
docker run -d -p 1111:1111 debian-llamafile
```

The container is a separate Ollama-compatible service experiment. The default `OllamaAgent` endpoint remains `http://localhost:11434`; pass a compatible endpoint explicitly when using another service.

## Project Boundaries

- [legacy/chat_gemini_latest.py](legacy/chat_gemini_latest.py) is a manual legacy demo and is not imported by the active CLI or orchestrator.
- [playwright_mcp.py](playwright_mcp.py) is a standalone screenshot script, not an agent tool registered in `tools.py`.
- Files under `test_docs/`, `docx_reader/`, and `playwright images/` are examples or supporting artifacts, not required for the core agent flow.
- No concurrency, streaming responses, automatic retries, or live integration tests are currently implemented.
