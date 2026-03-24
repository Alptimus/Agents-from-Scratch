---
name: orchestrator
description: |
  Guidance for working with orchestrator.py: autonomous agent implementation.
  Use when: modifying agent behavior, adding backends, debugging tool iteration loops, or extending orchestrator features.
applyTo: "**/higher_end/orchestrator.py"
---

# Orchestrator Agent Implementation Guide

This file contains the core `OllamaAgent` and `GeminiAgent` classes that implement autonomous task execution with tool calling.

## Architecture Overview

### Agent Loop Flow

Both `OllamaAgent` and `GeminiAgent` follow the same execution pattern:

```
1. Check Backend Connection (Ollama/Gemini)
   ↓
2. Enter Iteration Loop (max 10 iterations)
   ├─ Call LLM with task + conversation history
   ├─ Parse JSON tool calls from response
   ├─ If no tools: task complete → return result
   ├─ If tools found: execute each tool
   ├─ Collect results, feed back to LLM
   └─ Next iteration
   ↓
3. Return final result or "max iterations reached"
```

### Key Methods (Shared Between Both Agents)

| Method | Purpose |
|--------|---------|
| `_extract_tool_calls(response_text)` | Parse JSON `{"tool": "name", "params": {...}}` from LLM response |
| `_execute_tool(tool_name, params)` | Look up tool in `TOOLS` registry, call it, return result |
| `execute_task(task_description)` | Main public entry point; runs iteration loop until complete |

### Backend-Specific Methods

**OllamaAgent:**
- `_check_ollama_connection()` — Ping Ollama at configured base_url
- `_call_ollama(prompt)` — POST to `/api/generate` endpoint; parse JSON response

**GeminiAgent:**
- `_check_gemini_connection()` — Initialize Gemini client; validate API key
- `_call_gemini(prompt)` — Call `gemini_utils.call_gemini()`; return text response

## When to Modify Orchestrator

### Adding a New Backend (e.g., Claude, Local Model)

1. **Create a new Agent class** (e.g., `ClaudeAgent`)
2. **Implement required methods**:
   - `__init__()` — Store backend-specific config
   - `_check_connection()` — Validate backend availability
   - `_call_llm(prompt)` — API call; return text response
   - `_extract_tool_calls()` — **Reuse from OllamaAgent** (identical)
   - `_execute_tool()` — **Reuse from OllamaAgent** (identical)
   - `execute_task()` — **Mostly reuse iteration loop** (only `_call_llm()` call differs)
3. **Add to imports** in `.github/copilot-instructions.md`

### Modifying Tool Extraction Logic

The JSON parsing in `_extract_tool_calls()` handles:
- Multiple tool calls in one response
- JSON blocks nested in text
- Malformed JSON (gracefully skipped)

**Do NOT change** this method unless you change the system prompt or LLM instruction format. Both agents share this logic intentionally for consistency.

### Changing Iteration Behavior

To modify max iterations, timeout, or feedback loops:
1. Edit `__init__()` parameters (e.g., add `timeout`, `retry_policy`)
2. Update iteration loop logic in `execute_task()`
3. **Apply to both agents** to keep parity

### Debugging Tool Calls

**Enable verbose output:**
```python
agent = GeminiAgent(verbose=True)
result = agent.execute_task("Your task")
```

**Read conversation history:**
```python
result = agent.execute_task("task")
if not result["success"]:
    for iteration in result["conversation"]:
        print(f"Iter {iteration['iteration']}: {iteration.get('tool_calls', 'no tools')}")
```

## Code Patterns to Maintain

### Consistent Property Initialization

Both agents follow this pattern in `__init__()`:
```python
self.param_name = param  # Store all config params
self.verbose = verbose
```

### Consistent Tool Execution

Both agents use identical `_execute_tool()`:
```python
fn = tool["fn"]
params_to_pass = {name: value for name, value in params.items()}
result = fn(**params_to_pass)
return result  # Always: {"success": bool, "error": str} or {"success": true, "result": data}
```

### Consistent Error Handling

All LLM calls follow:
```python
try:
    response = _call_llm(prompt)
    if not response:
        return {"success": False, "error": "..."}
except Exception as e:
    if self.verbose:
        print(f"[ERROR] {str(e)}")
    return None
```

## Testing Checklist

Before committing changes:
- [ ] Both agents initialize without errors
- [ ] Tool extraction correctly parses multiple JSON calls
- [ ] Tool execution returns proper `{"success": bool, ...}` format
- [ ] Iteration loop stops at max_iterations
- [ ] Conversation history tracks all iterations
- [ ] Verbose output logs each step clearly
- [ ] Backward compatibility: `OllamaAgent` works unchanged

## Common Mistakes

### ❌ Changing `_extract_tool_calls()` without updating system prompt
The JSON parsing is tightly coupled to LLM instructions. If you change tool format (e.g., "output as XML"), update **both** together.

### ❌ Not initializing `self.client` in `_check_connection()`
GeminiAgent lazily initializes the client on first connection check. Don't initialize in `__init__()` to avoid API calls during setup.

### ❌ Not applying changes to both agents
If you fix a bug in one agent's iteration loop, apply it to the other for consistency.

### ❌ Assuming non-verbose mode is silent
Both agents still run full iterations in non-verbose mode; verbose just suppresses `print()` statements.

## Integration Points

### With `tools.py`
- Calls `format_tool_descriptions()` to build system prompt
- Calls `get_tool_by_name(tool_name)` to look up tools
- Expects `TOOLS` list with `name`, `description`, `parameters`, `fn`

### With `gemini_utils.py` (GeminiAgent only)
- Calls `get_gemini_client(api_key_name)` to initialize
- Calls `call_gemini(client, prompt, model)` to invoke API

### With `.env`
- `OllamaAgent`: Uses `ollama_base_url` parameter (no env lookup)
- `GeminiAgent`: Looks up `api_key_name` env var via `python-decouple`

## Performance & Scaling

### Current Limitations
- **Single-threaded**: Iteration loop is sequential; one LLM call at a time
- **No tool parallelism**: Tools execute one-by-one (even if independent)
- **No streaming**: LLM response must complete before tool extraction

### Future Optimization Options
1. **Parallel tool execution**: `asyncio` for independent tool calls within one iteration
2. **Streaming response handling**: Extract and execute tools as LLM streams response
3. **Auto-retry on tool failure**: Add `retry_on_error=True` parameter
4. **Token usage tracking**: Return token metrics from `execute_task()`

---

**See also:** [copilot-instructions.md](../../.github/copilot-instructions.md) for high-level usage guide.
