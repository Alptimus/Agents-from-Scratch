"""
Core agent orchestrator for autonomous tool coordination.

Handles:
- Communication with Ollama LLM
- Tool call extraction and validation
- Tool execution with result feedback
- Multi-step task execution with iteration limits
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

# Add parent directory to path to import tools
# sys.path.insert(0, str(Path(__file__).parent.parent))

from tools import TOOLS, get_tool_by_name, format_tool_descriptions

# Import gemini_utils - handle both module and direct execution
try:
    try:
        from .gemini_utils import get_gemini_client, call_gemini
    except (ImportError, ValueError):
        from gemini_utils import get_gemini_client, call_gemini
except ImportError as e:
    print(f"Warning: Could not import gemini_utils: {e}")


class OllamaAgent:
    """Agent that orchestrates tasks using Ollama LLM and tool calls."""

    def __init__(
        self,
        ollama_base_url: str = "http://localhost:11434",
        model: str = "mistral",
        max_iterations: int = 10,
        verbose: bool = True
    ):
        """
        Initialize the agent.

        Args:
            ollama_base_url: Base URL for Ollama API
            model: Model name to use (e.g., 'mistral', 'neural-chat')
            max_iterations: Maximum number of agent iterations to prevent infinite loops
            verbose: Whether to print reasoning and progress
        """
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.api_url = f"{ollama_base_url}/api/generate"

    def _check_ollama_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            response = requests.get(
                f"{self.ollama_base_url}/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """
        Call Ollama with a prompt and return the full response text.

        Args:
            prompt: The prompt to send to Ollama

        Returns:
            Full response text, or None if request failed
        """
        try:
            response = requests.post(
                self.api_url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            else:
                if self.verbose:
                    print(f"[ERROR] Ollama returned status {response.status_code}")
                return None
        except requests.exceptions.Timeout:
            if self.verbose:
                print("[ERROR] Ollama request timed out")
            return None
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] Failed to call Ollama: {str(e)}")
            return None

    def _extract_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from LLM response.

        The LLM is instructed to output JSON tool calls on separate lines.
        Format expected: {"tool": "tool_name", "params": {"param1": "value1"}}

        Args:
            response_text: Raw response from Ollama

        Returns:
            List of extracted tool calls
        """
        tool_calls = []
        
        # Look for JSON blocks that start with { and contain "tool" key
        # Use a more robust approach: find potential JSON blocks and try to parse them
        in_json = False
        json_depth = 0
        json_start = -1
        
        for i, char in enumerate(response_text):
            if char == '{':
                if json_depth == 0:
                    json_start = i
                json_depth += 1
            elif char == '}':
                json_depth -= 1
                if json_depth == 0 and json_start >= 0:
                    # Potential complete JSON block
                    json_str = response_text[json_start:i+1]
                    try:
                        tool_call = json.loads(json_str)
                        if "tool" in tool_call and "params" in tool_call:
                            tool_calls.append(tool_call)
                    except (json.JSONDecodeError, ValueError):
                        pass
                    json_start = -1
        
        return tool_calls

    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and return its result.

        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool

        Returns:
            Tool execution result
        """
        tool = get_tool_by_name(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool not found: {tool_name}"}
        
        try:
            fn = tool["fn"]
            # Handle optional parameters
            params_to_pass = {}
            for param_name, param_value in params.items():
                params_to_pass[param_name] = param_value
            
            result = fn(**params_to_pass)
            return result
        except TypeError as e:
            return {"success": False, "error": f"Invalid parameters for {tool_name}: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}

    def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a task autonomously using the agent loop.

        Args:
            task_description: Natural language description of the task

        Returns:
            Final result with task outcome and conversation history
        """
        # Check Ollama connection
        if not self._check_ollama_connection():
            return {
                "success": False,
                "error": f"Ollama not running on {self.ollama_base_url}. Start it with: ollama serve"
            }

        conversation_history = []
        tool_descriptions = format_tool_descriptions()

        system_prompt = f"""You are a helpful assistant that accomplishes tasks by using tools.

AVAILABLE TOOLS:
{tool_descriptions}

When you need to use a tool, output a JSON object on a single line with this format:
{{"tool": "tool_name", "params": {{"param1": "value1", "param2": "value2"}}}}

You may call multiple tools in one response by outputting multiple JSON objects.

After all tool calls are complete, summarize what you did and the results.
Always be clear about what you're doing and why.
"""

        initial_prompt = f"""{system_prompt}

TASK: {task_description}

Think through this step by step. What tools do you need to use? How will you accomplish this?"""

        if self.verbose:
            print(f"\n[TASK] {task_description}\n")
            print("[AGENT] Starting execution...\n")

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            if self.verbose:
                print(f"--- Iteration {iteration} ---")

            # Get LLM response
            llm_response = self._call_ollama(initial_prompt)
            if not llm_response:
                return {
                    "success": False,
                    "error": "LLM call failed",
                    "conversation": conversation_history
                }

            conversation_history.append({
                "iteration": iteration,
                "agent_response": llm_response
            })

            if self.verbose:
                print(f"[LLM] {llm_response[:200]}..." if len(llm_response) > 200 else f"[LLM] {llm_response}")

            # Extract and execute tools
            tool_calls = self._extract_tool_calls(llm_response)

            if not tool_calls:
                # No tools called; task is complete
                if self.verbose:
                    print("\n[SUCCESS] Task completed.\n")
                return {
                    "success": True,
                    "result": llm_response,
                    "iterations": iteration,
                    "conversation": conversation_history
                }

            # Execute all tools and collect results
            all_results = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})

                if self.verbose:
                    print(f"  → Calling {tool_name} with params: {params}")

                result = self._execute_tool(tool_name, params)
                all_results.append({
                    "tool": tool_name,
                    "params": params,
                    "result": result
                })

                if self.verbose:
                    status = "✓" if result.get("success") else "✗"
                    print(f"    {status} {result}")

            conversation_history[-1]["tool_calls"] = all_results

            # Prepare next prompt with tool results
            results_summary = json.dumps(all_results, indent=2)
            initial_prompt = f"""{system_prompt}

TASK: {task_description}

Previous response:
{llm_response}

Tool execution results:
{results_summary}

Based on these results, what's the next step? If the task is complete, say so explicitly and summarize what was accomplished."""

        # Max iterations reached
        return {
            "success": False,
            "error": f"Max iterations ({self.max_iterations}) reached without task completion",
            "last_response": llm_response,
            "conversation": conversation_history
        }


class GeminiAgent:
    """Agent that orchestrates tasks using Google Gemini LLM and tool calls."""

    def __init__(
        self,
        api_key_name: str = "GOOGLE_API_KEY",
        model: str = "gemini-2.5-flash",
        max_iterations: int = 10,
        verbose: bool = True
    ):
        """
        Initialize the Gemini agent.

        Args:
            api_key_name: Environment variable name containing Gemini API key
            model: Model name to use (e.g., 'gemini-2.5-flash', 'gemini-1.5-pro')
            max_iterations: Maximum number of agent iterations to prevent infinite loops
            verbose: Whether to print reasoning and progress
        """
        self.api_key_name = api_key_name
        self.model = model
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.client = None

    def _check_gemini_connection(self) -> bool:
        """Check if Gemini API is accessible with valid credentials."""
        try:
            self.client = get_gemini_client(self.api_key_name)
            return True
        except ValueError as e:
            if self.verbose:
                print(f"[ERROR] {str(e)}")
            return False
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] Failed to initialize Gemini client: {str(e)}")
            return False

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """
        Call Gemini with a prompt and return the full response text.

        Args:
            prompt: The prompt to send to Gemini

        Returns:
            Full response text, or None if request failed
        """
        try:
            response = call_gemini(self.client, prompt, self.model)
            return response
        except Exception as e:
            if self.verbose:
                print(f"[ERROR] Failed to call Gemini: {str(e)}")
            return None

    def _extract_tool_calls(self, response_text: str) -> List[Dict[str, Any]]:
        """
        Extract tool calls from LLM response.

        The LLM is instructed to output JSON tool calls on separate lines.
        Format expected: {"tool": "tool_name", "params": {"param1": "value1"}}

        Args:
            response_text: Raw response from Gemini

        Returns:
            List of extracted tool calls
        """
        tool_calls = []

        # Look for JSON blocks that start with { and contain "tool" key
        json_depth = 0
        json_start = -1

        for i, char in enumerate(response_text):
            if char == '{':
                if json_depth == 0:
                    json_start = i
                json_depth += 1
            elif char == '}':
                json_depth -= 1
                if json_depth == 0 and json_start >= 0:
                    # Potential complete JSON block
                    json_str = response_text[json_start:i+1]
                    try:
                        tool_call = json.loads(json_str)
                        if "tool" in tool_call and "params" in tool_call:
                            tool_calls.append(tool_call)
                    except (json.JSONDecodeError, ValueError):
                        pass
                    json_start = -1

        return tool_calls

    def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool and return its result.

        Args:
            tool_name: Name of the tool to execute
            params: Parameters for the tool

        Returns:
            Tool execution result
        """
        tool = get_tool_by_name(tool_name)
        if not tool:
            return {"success": False, "error": f"Tool not found: {tool_name}"}

        try:
            fn = tool["fn"]
            # Handle optional parameters
            params_to_pass = {}
            for param_name, param_value in params.items():
                params_to_pass[param_name] = param_value

            result = fn(**params_to_pass)
            return result
        except TypeError as e:
            return {"success": False, "error": f"Invalid parameters for {tool_name}: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"Tool execution failed: {str(e)}"}

    def execute_task(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a task autonomously using the agent loop.

        Args:
            task_description: Natural language description of the task

        Returns:
            Final result with task outcome and conversation history
        """
        # Check Gemini connection
        if not self._check_gemini_connection():
            return {
                "success": False,
                "error": f"Gemini API not accessible. Ensure GOOGLE_API_KEY is set in .env"
            }

        conversation_history = []
        tool_descriptions = format_tool_descriptions()

        system_prompt = f"""You are a helpful assistant that accomplishes tasks by using tools.

AVAILABLE TOOLS:
{tool_descriptions}

When you need to use a tool, output a JSON object on a single line with this format:
{{"tool": "tool_name", "params": {{"param1": "value1", "param2": "value2"}}}}

You may call multiple tools in one response by outputting multiple JSON objects.

After all tool calls are complete, summarize what you did and the results.
Always be clear about what you're doing and why.
"""

        initial_prompt = f"""{system_prompt}

TASK: {task_description}

Think through this step by step. What tools do you need to use? How will you accomplish this?"""

        if self.verbose:
            print(f"\n[TASK] {task_description}\n")
            print("[AGENT] Starting execution with Gemini...\n")

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            if self.verbose:
                print(f"--- Iteration {iteration} ---")

            # Get LLM response
            llm_response = self._call_gemini(initial_prompt)
            if not llm_response:
                return {
                    "success": False,
                    "error": "LLM call failed",
                    "conversation": conversation_history
                }

            conversation_history.append({
                "iteration": iteration,
                "agent_response": llm_response
            })

            if self.verbose:
                print(f"[LLM] {llm_response[:200]}..." if len(llm_response) > 200 else f"[LLM] {llm_response}")

            # Extract and execute tools
            tool_calls = self._extract_tool_calls(llm_response)

            if not tool_calls:
                # No tools called; task is complete
                if self.verbose:
                    print("\n[SUCCESS] Task completed.\n")
                return {
                    "success": True,
                    "result": llm_response,
                    "iterations": iteration,
                    "conversation": conversation_history
                }

            # Execute all tools and collect results
            all_results = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})

                if self.verbose:
                    print(f"  → Calling {tool_name} with params: {params}")

                result = self._execute_tool(tool_name, params)
                all_results.append({
                    "tool": tool_name,
                    "params": params,
                    "result": result
                })

                if self.verbose:
                    status = "✓" if result.get("success") else "✗"
                    print(f"    {status} {result}")

            conversation_history[-1]["tool_calls"] = all_results

            # Prepare next prompt with tool results
            results_summary = json.dumps(all_results, indent=2)
            initial_prompt = f"""{system_prompt}

TASK: {task_description}

Previous response:
{llm_response}

Tool execution results:
{results_summary}

Based on these results, what's the next step? If the task is complete, say so explicitly and summarize what was accomplished."""

        # Max iterations reached
        return {
            "success": False,
            "error": f"Max iterations ({self.max_iterations}) reached without task completion",
            "last_response": llm_response,
            "conversation": conversation_history
        }


if __name__ == "__main__":
    pass