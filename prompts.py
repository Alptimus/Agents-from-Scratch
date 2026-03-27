"""
Reusable prompt templates for agent orchestration.

Provides parameterized prompt functions used by both OllamaAgent and GeminiAgent
to ensure consistency and enable easy prompt modifications.
"""


def get_system_prompt(tool_descriptions: str) -> str:
    """
    Get the system prompt that instructs the agent how to use tools.

    Args:
        tool_descriptions: Formatted string of available tools and their parameters

    Returns:
        System prompt with tool descriptions injected
    """
    return f"""You are a helpful assistant that accomplishes tasks by using tools.

AVAILABLE TOOLS:
{tool_descriptions}

When you need to use a tool, output a JSON object on a single line with this format:
{{"tool": "tool_name", "params": {{"param1": "value1", "param2": "value2"}}}}

You may call multiple tools in one response by outputting multiple JSON objects.

After all tool calls are complete, summarize what you did and the results.
Always be clear about what you're doing and why.
"""


def get_initial_prompt(system_prompt: str, task_description: str) -> str:
    """
    Get the initial prompt for the first iteration of task execution.

    Args:
        system_prompt: The system prompt with tool instructions
        task_description: Natural language description of the task

    Returns:
        Complete initial prompt combining system instructions and task
    """
    return f"""{system_prompt}

TASK: {task_description}

Think through this step by step. What tools do you need to use? How will you accomplish this?"""


def get_continuation_prompt(
    system_prompt: str,
    task_description: str,
    llm_response: str,
    results_summary: str
) -> str:
    """
    Get the continuation prompt for subsequent iterations with tool results.

    Args:
        system_prompt: The system prompt with tool instructions
        task_description: Natural language description of the task
        llm_response: The previous LLM response
        results_summary: JSON summary of tool execution results

    Returns:
        Complete prompt for next iteration with tool results injected
    """
    return f"""{system_prompt}

TASK: {task_description}

Previous response:
{llm_response}

Tool execution results:
{results_summary}

Based on these results, what's the next step? If the task is complete, say so explicitly and summarize what was accomplished."""
