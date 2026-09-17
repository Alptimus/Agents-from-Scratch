# Orchestrator.py - Complete Step-by-Step Explanation

## Overview

`orchestrator.py` contains two agent classes that autonomously execute tasks by orchestrating tool calls and LLM reasoning:
- **`OllamaAgent`** — Uses a local LLM (Ollama)
- **`GeminiAgent`** — Uses Google's Gemini API (cloud-based)

Both agents follow the **same core loop pattern**: take a task → call LLM → extract tool calls → execute tools → feed results back → repeat until complete.

---

## Architecture Flow

```
User Task
    ↓
Initialize Agent (OllamaAgent or GeminiAgent)
    ↓
execute_task(task_description)
    ├─ Step 1: Check backend connection
    ├─ Step 2: Prepare system prompt + tools list
    ├─ Step 3: Enter iteration loop (max 10 cycles)
    │   ├─ Call LLM with task + history
    │   ├─ Parse JSON tool calls from response
    │   ├─ If no tools → task complete, return result
    │   ├─ If tools found → execute each tool
    │   ├─ Collect results, feed back to LLM
    │   └─ Loop to next iteration
    └─ Return final result + conversation history
```

---

## Detailed Component Breakdown

### 1. Class Initialization

#### OllamaAgent.__init__()
```python
OllamaAgent(
    ollama_base_url="http://localhost:11434",  # Ollama server location
    model="mistral",                           # LLM model name
    max_iterations=10,                         # Safety limit on loops
    verbose=True                               # Print debug output
)
```

**What it does:**
- Stores Ollama endpoint and model name
- Constructs the API URL: `http://localhost:11434/api/generate`
- Sets iteration limit to prevent infinite loops
- Enables/disables debug printing

#### GeminiAgent.__init__()
```python
GeminiAgent(
    api_key_name="GOOGLE_API_KEY",    # Environment variable for API key
    model="gemini-2.5-flash",         # Gemini model version
    max_iterations=10,                # Safety limit on loops
    verbose=True                      # Print debug output
)
```

**What it does:**
- Stores API key environment variable name
- Stores model selection
- Sets iteration limit
- Client is initialized lazily in `_check_gemini_connection()`

---

### 2. Connection Validation (Pre-Execution)

#### OllamaAgent._check_ollama_connection()
```
1. Send GET request to http://localhost:11434/api/tags
2. Check if response status is 200 (HTTP OK)
3. Return True/False (success/failure)
4. If fails → Ollama service isn't running or unreachable
```

**Why it matters:**
- Fails fast before wasting iterations
- Error message tells user to run `ollama serve`

#### GeminiAgent._check_gemini_connection()
```
1. Call get_gemini_client(api_key_name)
   - Loads API key from environment
   - Initializes Google Gemini client
2. Store client reference
3. Return True if successful, False if API key missing or invalid
```

**Why it matters:**
- Validates credentials before making expensive API calls
- Prevents rate-limit waste on bad keys

---

### 3. Main Execution Loop: execute_task()

This is the **core orchestration logic** that runs for both agents (with backend-specific differences).

#### Step 3.1: Pre-Loop Setup

```python
# Check backend is available
if not self._check_*_connection():
    return {"success": False, "error": "..."}

# Initialize empty conversation history (tracks all iterations)
conversation_history = []

# Get formatted list of available tools from tools.py
tool_descriptions = format_tool_descriptions()
```

**Purpose:**
- Ensure backend is ready
- Set up tracking for multi-turn conversation
- Make tools known to the LLM

#### Step 3.2: Craft System Prompt

```
System Prompt = [Preamble] + [Tool Descriptions] + [Instructions]

The prompt tells the LLM:
1. "You're an assistant that uses tools to complete tasks"
2. Here are the available tools: [list]
3. Format tool calls as: {"tool": "name", "params": {...}}
4. You can call multiple tools per response
5. Summarize what you did when complete
```

**Example:**
```
You are a helpful assistant that accomplishes tasks by using tools.

AVAILABLE TOOLS:
- read_file(file_path: str) → reads file contents
- write_file(file_path: str, content: str) → writes file
- run_shell(command: str) → runs shell command
- list_directory(dir_path: str) → lists directory

When you need to use a tool, output JSON:
{"tool": "tool_name", "params": {"param1": "value1"}}
```

#### Step 3.3: Initial Prompt Construction

```python
initial_prompt = [system_prompt] + [TASK: user's request]
```

#### Step 3.4: Enter Iteration Loop

```
FOR iteration = 1 TO max_iterations:
    Step A: Call LLM
    Step B: Parse tool calls
    Step C: Decide: tools found or not?
    Step D: If tools → execute and loop back
    Step E: If no tools → task complete
```

---

### 4. LLM Communication (Per Iteration)

#### Step 4.1: Call Backend LLM

**For OllamaAgent (_call_ollama):**
```
POST http://localhost:11434/api/generate
{
    "model": "mistral",
    "prompt": [current_prompt],
    "stream": false
}

←─ Returns:
{
    "response": "Let me start by reading the config file...\n{\"tool\": \"read_file\", \"params\": {\"file_path\": \"config.json\"}}"
}
```

**For GeminiAgent (_call_gemini):**
```
POST https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent
{
    "contents": [{"parts": [{"text": [current_prompt]}]}],
    "generationConfig": {...}
}

←─ Returns:
{
    "candidates": [{
        "content": {
            "parts": [{
                "text": "Let me start by reading the config file...\n{\"tool\": \"read_file\", \"params\": {\"file_path\": \"config.json\"}}"
            }]
        }
    }]
}
```

**Error Handling:**
- Timeout (60 seconds) → return None
- Connection error → return None
- Bad status code → return None

#### Step 4.2: Add Response to History

```python
conversation_history.append({
    "iteration": 1,
    "agent_response": "[LLM's full response text]"
})
```

---

### 5. Tool Call Extraction: _extract_tool_calls()

The LLM response contains natural language **plus** JSON tool calls. This method extracts them.

#### Algorithm: Character-by-Character JSON Parsing

```
Scan through response character by character:

WHEN see '{':
  ├─ If not already in JSON block → mark as start
  └─ Increment nesting depth

WHEN see '}':
  ├─ Decrement nesting depth
  ├─ If nesting reaches 0 → potentially complete JSON block
  └─ Try to parse as JSON
       ├─ If valid JSON with "tool" + "params" keys → ADD TO RESULTS
       └─ If invalid JSON → SKIP

RETURN list of valid tool calls
```

#### Example Input/Output

**Input (LLM response):**
```
I'll start by reading the configuration file to understand the structure.

{"tool": "read_file", "params": {"file_path": "config.json"}}

Once I have that, I'll check the format and make modifications...

{"tool": "write_file", "params": {"file_path": "config.json", "content": "..."}}
```

**Output (extracted tool_calls):**
```python
[
    {"tool": "read_file", "params": {"file_path": "config.json"}},
    {"tool": "write_file", "params": {"file_path": "config.json", "content": "..."}}
]
```

---

### 6. Tool Execution: _execute_tool()

For each tool call, execute it and capture the result.

#### Process

```
1. Look up tool in TOOLS registry (from tools.py)
   └─ If not found → return {"success": false, "error": "..."}

2. Get the function reference: fn = tool["fn"]

3. Build parameters dict from parsed params

4. Call the function: result = fn(**params_to_pass)

5. Return result (must follow {"success": bool, "result"/"error": ...} format)
```

#### Example

**Tool Call:**
```json
{"tool": "read_file", "params": {"file_path": "config.json"}}
```

**Execution:**
```python
tool = get_tool_by_name("read_file")
result = tool["fn"](file_path="config.json")
# → {"success": true, "content": "{ \"timeout\": 30 }"}
```

#### Error Handling

```
Try:
  Execute tool function with params
Catch TypeError:
  → Invalid parameters → return error
Catch Exception:
  → Tool execution failed → return error
```

---

### 7. Decision Point: Complete or Loop?

After executing tools and collecting results:

```
IF no tool_calls extracted from LLM response:
    ├─ LLM did not call any tools
    ├─ This means task is complete
    └─ RETURN success with result

ELSE:
    ├─ Tools were called
    ├─ Add tool results to conversation history
    ├─ Build new prompt with results
    └─ LOOP BACK to next iteration
```

#### History Update

```python
conversation_history[-1]["tool_calls"] = [
    {
        "tool": "read_file",
        "params": {"file_path": "config.json"},
        "result": {"success": true, "content": "..."}
    }
]
```

---

### 8. Next Iteration Prompt Construction

When looping back, the LLM gets enriched context:

```python
next_prompt = [system_prompt] + [
    TASK: [original task]
    Previous response: [LLM's last reasoning]
    Tool execution results: [JSON of all results from this iteration]
    Based on these results, what's the next step?
]
```

**Example:**
```
TASK: Write a summary of config.json

Previous response:
I'll read config.json first.
{"tool": "read_file", "params": {"file_path": "config.json"}}

Tool execution results:
[
  {
    "tool": "read_file",
    "params": {"file_path": "config.json"},
    "result": {
      "success": true,
      "content": "{ \"timeout\": 30, \"max_retries\": 3 }"
    }
  }
]

Based on these results, what's the next step?
```

The LLM then says: "Great! I have the config. Let me write the summary..." and calls `write_file` or simply completes the task.

---

### 9. Loop Termination

The loop exits in **three scenarios:**

#### Scenario A: Task Complete (Success)
```
LLM response contains no tool calls
→ Return {"success": true, "result": last_llm_response}
```

#### Scenario B: Max Iterations Reached (Failure)
```
iteration >= max_iterations (default 10)
→ Return {
    "success": false,
    "error": "Max iterations reached without completion",
    "last_response": last_llm_response
  }
```

#### Scenario C: LLM Call Failed (Error)
```
_call_ollama() or _call_gemini() returns None
→ Return {"success": false, "error": "LLM call failed"}
```

---

## Complete Execution Timeline Example

### Task: "Count Python files in the src directory"

#### Iteration 1
```
Initial Prompt: "TASK: Count Python files in the src directory"

[Agent calls Ollama/Gemini]

LLM Response:
"I'll list the src directory to see what files are there.
{"tool": "list_directory", "params": {"dir_path": "src"}}"

Tool Extraction:
→ Found 1 tool: list_directory(dir_path="src")

Tool Execution:
→ result = {"success": true, "files": ["main.py", "utils.py", "helpers.py", "__init__.py"]}

Decision: Tools were called → LOOP

History Update:
conversation_history[0]["tool_calls"] = [
  {
    "tool": "list_directory",
    "params": {"dir_path": "src"},
    "result": {"success": true, "files": ["main.py", "utils.py", "helpers.py", "__init__.py"]}
  }
]
```

#### Iteration 2
```
Next Prompt: "TASK: ... [Previous response shown] ... Tool results: [listed files] ... What next?"

[Agent calls Ollama/Gemini]

LLM Response:
"Perfect! I found 4 Python files in src: main.py, utils.py, helpers.py, and __init__.py. The count is 4."

Tool Extraction:
→ Found 0 tools → Task is complete!

Decision: No tools called → RETURN SUCCESS

Final Result:
{
  "success": true,
  "result": "Perfect! I found 4 Python files in src: main.py, utils.py, helpers.py, and __init__.py. The count is 4.",
  "iterations": 2,
  "conversation": [
    {
      "iteration": 1,
      "agent_response": "...",
      "tool_calls": [...]
    },
    {
      "iteration": 2,
      "agent_response": "...",
      "tool_calls": []  // Empty means task complete
    }
  ]
}
```

---

## Key Design Principles

### 1. Backend Abstraction
Both `OllamaAgent` and `GeminiAgent` share:
- Same `_extract_tool_calls()` method
- Same `_execute_tool()` method
- Same `execute_task()` loop logic

Only the LLM communication differs (`_call_ollama()` vs `_call_gemini()`).

### 2. Tool Agnosticism
The agent doesn't hard-code tools. It:
1. Reads available tools from `tools.py` via `format_tool_descriptions()`
2. Uses tool registry to look up by name
3. Calls any tool registered in the `TOOLS` list

Adding a new tool requires no changes to `orchestrator.py`.

### 3. Iterative Refinement
The agent:
- Sees task
- Plans steps
- Executes tools
- **Learns from results** (feeds them back)
- Adjusts strategy
- Repeats

This is more robust than single-shot execution.

### 4. Safety Limits
- Max 10 iterations to prevent infinite loops
- Timeout on LLM calls (60 seconds)
- Graceful error handling throughout

### 5. Full Transparency
- Verbose mode logs every step
- Conversation history tracks all iterations
- Easy to replay and debug

---

## Code Structure

### Class Methods Summary

| Method | Purpose | Used By |
|--------|---------|---------|
| `__init__()` | Store config, setup agent | User |
| `_check_*_connection()` | Validate backend available | `execute_task()` start |
| `_call_*()` | Make API call to LLM | Iteration loop |
| `_extract_tool_calls()` | Parse JSON from response | After LLM call |
| `_execute_tool()` | Run a single tool | For each tool call |
| `execute_task()` | Main public entry point | User |

### Shared Components

**Between Both Agents:**
- System prompt format
- Tool call JSON format
- Iteration loop logic
- Tool execution logic
- Result format

**Different:**
- LLM backend (Ollama HTTP vs Gemini gRPC)
- Connection validation
- Configuration (base URL vs API key)

---

## Return Value Structure

All methods return dictionaries following this pattern:

### Success (Task Complete)
```python
{
    "success": True,
    "result": "...",  # LLM's final output
    "iterations": 2,
    "conversation": [
        {
            "iteration": 1,
            "agent_response": "...",
            "tool_calls": [
                {
                    "tool": "name",
                    "params": {...},
                    "result": {"success": true, "...": "..."}
                }
            ]
        },
        {
            "iteration": 2,
            "agent_response": "...",
            "tool_calls": []  # Empty = task complete
        }
    ]
}
```

### Failure (Backend Error)
```python
{
    "success": False,
    "error": "Ollama not running on http://localhost:11434. Start it with: ollama serve"
}
```

### Failure (Max Iterations)
```python
{
    "success": False,
    "error": "Max iterations (10) reached without task completion",
    "last_response": "...",
    "conversation": [...]
}
```

---

## Execution Flow Diagram (Simplified)

```
    ┌─────────────────────────────────┐
    │  OllamaAgent / GeminiAgent      │
    │  execute_task(task)             │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌─────────────────────────────────┐
    │  Check backend connection       │
    │  (Ollama or Gemini)             │
    └──────────┬──────────────────────┘
               │
        ┌──────▼─────┐
        │  Connected?│
        └──┬──────┬──┘
         NO│      │YES
           │      │
           │      ▼
           │  ┌─────────────────────────┐
           │  │ Prepare System Prompt  │
           │  │ + Tool Descriptions    │
           │  └────────┬────────────────┘
           │           │
           │           ▼
           │  ┌─────────────────────────┐
           │  │ Call LLM with Prompt    │ ◄──┐
           │  │ (Ollama or Gemini)      │    │
           │  └────────┬────────────────┘    │
           │           │                     │
           │           ▼                     │
           │  ┌─────────────────────────┐    │
           │  │ Extract JSON Tool Calls │    │
           │  └────────┬────────────────┘    │
           │           │                     │
           │      ┌────▼────┐                │
           │      │ Any     │                │
           │      │ Tools?  │                │
           │      └───┬──┬──┘                │
           │        NO│ │YES                │
           │          │ │                   │
           │    ┌─────▼─▼──────────┐        │
           │    │ Execute Tools    │        │
           │    │ Collect Results  │        │
           │    └────────┬─────────┘        │
           │             │                  │
           │      ┌──────▼────────┐         │
           │      │ Max Iters     │         │
           │      │ Reached?      │         │
           │      └──┬────────┬───┘         │
           │        NO│      │YES           │
           │          │      │              │
           │          │      ▼              │
           │          │  Return Failure    │
           │          │                    │
           │          ▼                    │
           │      Build Next Prompt        │
           │      (with results) ────────┐ │
           │                             │ │
           └─────────────────────────────┘ │
                                            │
             ┌──────────────────────────────┘
             │
             ▼
       Return Success

```

---

## Summary

The orchestrator implements a **reasoning loop**:

1. **Setup**: Initialize, validate backend, prepare tools list
2. **Loop** (up to 10 iterations):
   - Ask LLM what to do next
   - LLM responds with optional tool calls
   - Execute all tool calls
   - If no tools → **task complete**
   - If tools were called → feed results back and loop
3. **Done**: Return result + history

This design allows a single LLM to autonomously:
- Break down complex tasks
- Use tools as needed
- Learn from results
- Adapt strategy
- Reach conclusions

Both Ollama and Gemini backends work the same way—only the LLM communication layer differs.
