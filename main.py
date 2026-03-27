#!/usr/bin/env python3
"""
Minimal CLI entry point for autonomous agent task execution.

Provides a command-line interface to execute tasks using Ollama or Gemini backends.
Supports two input modes: direct task prompt or SKILL.md file input.

Usage:
    # Mode 1: Direct prompt
    python main.py "Your task description" --provider ollama --model mistral
    python main.py "Your task" --provider gemini --model gemini-2.5-flash
    
    # Mode 2: Skill file input
    python main.py --skill path/to/SKILL.md --provider gemini
    
    # Mode 3: Skill + additional prompt (merged, skill is primary)
    python main.py "Also check performance" --skill path/to/SKILL.md
"""

import argparse
import sys
import requests
from decouple import config

from orchestrator import OllamaAgent, GeminiAgent
from skill_loader import load_skill_file


def validate_ollama_connection(base_url: str = "http://localhost:11434") -> bool:
    """
    Check if Ollama service is reachable.

    Args:
        base_url: Ollama base URL

    Returns:
        True if Ollama is reachable, False otherwise
    """
    try:
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        return response.status_code == 200
    except (requests.ConnectionError, requests.Timeout, requests.RequestException):
        return False


def validate_gemini_api_key(api_key_name: str = "GOOGLE_API_KEY") -> bool:
    """
    Check if Gemini API key is set in environment.

    Args:
        api_key_name: Environment variable name for API key

    Returns:
        True if API key is set, False otherwise
    """
    api_key = config(api_key_name, default=None)
    return api_key is not None


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Execute autonomous agent tasks with Ollama or Gemini backends",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "List all Python files" --provider ollama --model mistral
  %(prog)s "Analyze code quality" --provider gemini
  %(prog)s --skill .github/skills/code-analysis/SKILL.md
  %(prog)s "Focus on performance" --skill path/to/SKILL.md -q
        """,
    )

    # Positional argument: task description (optional if --skill provided)
    parser.add_argument(
        "task",
        nargs="?",
        default=None,
        help="Task description for the agent to execute (required if --skill not provided)",
    )

    # Skill file input
    parser.add_argument(
        "--skill",
        type=str,
        default=None,
        help="Path to SKILL.md file to use as task input (takes priority over task prompt)",
    )

    # Optional arguments
    parser.add_argument(
        "--provider",
        choices=["ollama", "gemini"],
        default="gemini",
        help="LLM provider backend (default: gemini)",
    )

    parser.add_argument(
        "--model",
        default=None,
        help="Model to use. Defaults: ollama='mistral', gemini='gemini-2.5-flash'",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="Show agent iteration details (default: True for verbose output)",
    )

    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output (same as not using --verbose)",
    )

    args = parser.parse_args()

    # Set verbose flag based on arguments
    verbose = args.verbose and not args.quiet

    # Load skill file if provided, and merge with task prompt if both given
    task_description = None
    skill_info = None

    if args.skill:
        # Load skill file
        try:
            skill_info = load_skill_file(args.skill)
            task_description = skill_info["description"]

            if args.task:
                # Both skill and prompt provided: merge them (skill is primary)
                task_description = f"{task_description}\n\nAdditional user instructions:\n{args.task}"

            if verbose:
                print(f"📚 Skill loaded: {skill_info['name']} from {args.skill}")
        except (FileNotFoundError, ValueError) as e:
            print(
                f"❌ Error loading skill file: {str(e)}",
                file=sys.stderr,
            )
            sys.exit(1)
    elif args.task:
        # Only prompt provided (traditional mode)
        task_description = args.task
    else:
        # Neither skill nor prompt provided
        parser.print_help()
        print(
            "\n❌ Error: You must provide either a task prompt or a --skill file path.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Determine model based on provider if not specified
    if args.model is None:
        model = "mistral" if args.provider == "ollama" else "gemini-2.5-flash"
    else:
        model = args.model

    # Validate backend availability
    if args.provider == "ollama":
        if not validate_ollama_connection():
            print(
                "❌ Error: Ollama service is not running.",
                file=sys.stderr,
            )
            print(
                "   Please start Ollama with: ollama serve",
                file=sys.stderr,
            )
            sys.exit(1)
    elif args.provider == "gemini":
        if not validate_gemini_api_key():
            print(
                "❌ Error: GOOGLE_API_KEY environment variable not set.",
                file=sys.stderr,
            )
            print(
                "   Please set your Gemini API key in .env or environment.",
                file=sys.stderr,
            )
            sys.exit(1)

    # Instantiate the appropriate agent
    try:
        if args.provider == "ollama":
            agent = OllamaAgent(model=model, verbose=verbose)
        else:  # gemini
            agent = GeminiAgent(model=model, verbose=verbose)
    except Exception as e:
        print(f"❌ Error initializing agent: {str(e)}", file=sys.stderr)
        sys.exit(1)

    # Execute the task
    try:
        if verbose:
            print(f"\n🤖 Agent: {args.provider.upper()} ({model})")
            print(f"📋 Task: {task_description[:100]}{'...' if len(task_description) > 100 else ''}\n")
            print("=" * 70)

        result = agent.execute_task(task_description)

        if verbose:
            print("=" * 70)

        # Display result
        if result.get("success", False):
            print(f"\n✅ Task completed successfully!")
            print("\n" + "=" * 70)
            print("RESULT")
            print("=" * 70)
            print(result.get("result", "No result returned"))
            print(f"\nIterations: {result.get('iterations', '?')}")
            sys.exit(0)
        else:
            print(f"\n❌ Task failed!")
            print("\n" + "=" * 70)
            print("ERROR")
            print("=" * 70)
            print(result.get("result", "No error message"))
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⏹️  Task interrupted by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
