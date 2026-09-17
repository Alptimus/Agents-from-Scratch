# Legacy SQL Agents

This directory archives the original standalone, hardcoded SQL agent scripts:
- `agent.py`: Initial prototype querying `us_salaries.sqlite` using raw Gemini chat sessions.
- `agent_v2.py`: Second prototype querying `chinook.db` with dual prompt cycles.

## Deprecation Notice

> [!WARNING]
> These standalone scripts are **deprecated** and kept strictly for reference and backward compatibility.

They have been superseded by the unified, backend-agnostic agent framework in the root directory:
1. **Tool-based Execution**: `execute_sql_query` registered in [tools.py](../../tools.py).
2. **Autonomous Multi-Step Orchestration**: [orchestrator.py](../../orchestrator.py) supporting both Ollama and Gemini.
3. **Skill Guidance**: [sql_agent/SKILL.md](../SKILL.md) provides system instructions and best practices for query formulation.

## Modern Usage

Instead of running these scripts directly, execute SQL tasks through the main CLI:

```bash
# Query salaries using Gemini
python3 main.py "Find all employees with salary over 500k in databases/us_salaries.sqlite" --skill sql_agent/SKILL.md --provider gemini

# Query Chinook music database using Ollama
python3 main.py "List albums and their artists from databases/chinook.db" --skill sql_agent/SKILL.md --provider ollama
```

