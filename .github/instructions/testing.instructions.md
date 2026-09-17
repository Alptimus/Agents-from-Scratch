---
name: testing
description: "Guide to testing agents and tools. Use when: writing unit tests, integration tests, mocking LLMs, testing tool behavior, or setting up CI/CD pipelines."
applyTo: "**/test_*.py,**/tests/**"
---

# Testing Strategy Guide

The project has a lightweight `unittest` smoke suite under `tests/`. This guide establishes testing patterns for tools, agents, and the orchestration system.

## Test Structure

Keep focused tests under `tests/`:
```
Agents-from-Scratch/
├── tools.py
├── orchestrator.py
└── tests/
    ├── test_agent_loop.py
    ├── test_gemini_import.py
    ├── test_main_cli.py
    ├── test_orchestrator_import.py
    └── test_tools_optional_docx.py
```

## Tool Testing

### Unit Tests for Tools

Test tools in isolation, without LLM involvement.

**File: `test_tools.py`**

```python
import json
import tempfile
from pathlib import Path
import pytest

from tools import (
    read_file, write_file, list_directory, run_shell, 
    read_docx_file, get_tool_by_name, TOOLS
)


class TestReadFile:
    """Test file reading tool."""

    def test_read_file_success(self, tmp_path):
        """Test reading an existing file."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")
        
        result = read_file(str(test_file))
        
        assert result["success"] is True
        assert result["content"] == "Hello, World!"
        assert result["file_path"] == str(test_file)

    def test_read_file_not_found(self):
        """Test reading a non-existent file."""
        result = read_file("/path/that/does/not/exist.txt")
        
        assert result["success"] is False
        assert "File not found" in result["error"]

    def test_read_file_permission_denied(self):
        """Test reading a file without permissions (Unix only)."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            f.flush()
            
            import os
            os.chmod(f.name, 0o000)  # No permissions
            
            try:
                result = read_file(f.name)
                assert result["success"] is False
                assert "Error reading file" in result["error"]
            finally:
                os.chmod(f.name, 0o644)  # Restore for cleanup
                os.unlink(f.name)

    @pytest.mark.parametrize("content", [
        "Simple ASCII text",
        "UTF-8: café, 日本語, 🚀",
        "Multi\nline\ntext",
        "",  # Empty file
    ])
    def test_read_file_various_encodings(self, tmp_path, content):
        """Test reading files with various encodings."""
        test_file = tmp_path / "encoded.txt"
        test_file.write_text(content, encoding="utf-8")
        
        result = read_file(str(test_file))
        
        assert result["success"] is True
        assert result["content"] == content


class TestWriteFile:
    """Test file writing tool."""

    def test_write_file_creates_new_file(self, tmp_path):
        """Test creating a new file."""
        new_file = tmp_path / "new.txt"
        
        result = write_file(str(new_file), "New content")
        
        assert result["success"] is True
        assert new_file.read_text() == "New content"

    def test_write_file_creates_directories(self, tmp_path):
        """Test that write_file creates parent directories."""
        nested_file = tmp_path / "a" / "b" / "c" / "file.txt"
        
        result = write_file(str(nested_file), "Nested content")
        
        assert result["success"] is True
        assert nested_file.read_text() == "Nested content"

    def test_write_file_overwrites_existing(self, tmp_path):
        """Test that write_file overwrites existing file."""
        existing_file = tmp_path / "existing.txt"
        existing_file.write_text("Old content")
        
        result = write_file(str(existing_file), "New content")
        
        assert result["success"] is True
        assert existing_file.read_text() == "New content"


class TestListDirectory:
    """Test directory listing tool."""

    def test_list_directory_success(self, tmp_path):
        """Test listing a directory with files."""
        (tmp_path / "file1.txt").write_text("test1")
        (tmp_path / "file2.txt").write_text("test2")
        (tmp_path / "subdir").mkdir()
        
        result = list_directory(str(tmp_path))
        
        assert result["success"] is True
        assert set(result["items"]) == {"file1.txt", "file2.txt", "subdir"}
        assert result["count"] == 3

    def test_list_directory_not_found(self):
        """Test listing a non-existent directory."""
        result = list_directory("/path/that/does/not/exist")
        
        assert result["success"] is False
        assert "Directory not found" in result["error"]

    def test_list_directory_empty(self, tmp_path):
        """Test listing an empty directory."""
        result = list_directory(str(tmp_path))
        
        assert result["success"] is True
        assert result["items"] == []
        assert result["count"] == 0


class TestRunShell:
    """Test shell command execution tool."""

    def test_run_shell_success(self):
        """Test successful command execution."""
        result = run_shell("echo 'Hello'")
        
        assert result["success"] is True
        assert "Hello" in result["stdout"]
        assert result["return_code"] == 0

    def test_run_shell_with_stderr(self):
        """Test command that produces stderr."""
        result = run_shell("python -c \"import sys; sys.stderr.write('error')\"")
        
        assert "error" in result["stderr"]
        # Note: success based on return_code, not stderr presence

    def test_run_shell_failure(self):
        """Test command that returns non-zero exit code."""
        result = run_shell("exit 42")
        
        assert result["success"] is True  # Tool execution succeeded
        assert result["return_code"] == 42  # But command failed

    def test_run_shell_timeout(self):
        """Test command that exceeds timeout."""
        result = run_shell("sleep 60")  # Default timeout is 30s
        
        assert result["success"] is False
        assert "timed out" in result["error"].lower()


class TestToolRegistry:
    """Test tool discovery and registration."""

    def test_all_tools_have_required_fields(self):
        """Ensure all registered tools have required fields."""
        required_fields = {"name", "description", "parameters", "fn"}
        
        for tool in TOOLS:
            assert required_fields.issubset(tool.keys()), \
                f"Tool {tool.get('name')} missing required fields"
            assert callable(tool["fn"]), \
                f"Tool {tool['name']}: fn is not callable"

    def test_tool_names_are_unique(self):
        """Ensure no duplicate tool names."""
        names = [tool["name"] for tool in TOOLS]
        assert len(names) == len(set(names)), \
            f"Duplicate tool names: {[n for n in names if names.count(n) > 1]}"

    def test_get_tool_by_name(self):
        """Test tool lookup function."""
        tool = get_tool_by_name("read_file")
        
        assert tool is not None
        assert tool["name"] == "read_file"
        assert callable(tool["fn"])

    def test_get_tool_by_name_not_found(self):
        """Test tool lookup for non-existent tool."""
        tool = get_tool_by_name("nonexistent_tool")
        
        assert tool is None
```

### Running Tool Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tool tests
pytest test_tools.py -v

# Run with coverage
pytest test_tools.py --cov=tools --cov-report=html

# Run specific test
pytest test_tools.py::TestReadFile::test_read_file_success -v
```

## Agent Testing

### Unit Tests with Mocking

Test agent behavior without relying on real LLMs.

**File: `test_orchestrator.py`**

```python
import json
from unittest.mock import Mock, patch, MagicMock
import pytest

from orchestrator import OllamaAgent, GeminiAgent
from tools import TOOLS


class TestOllamaAgentToolExtraction:
    """Test tool call extraction logic."""

    def test_extract_tool_calls_single_tool(self):
        """Test extracting a single tool call from response."""
        agent = OllamaAgent()
        response = '{"tool": "read_file", "params": {"file_path": "config.json"}}'
        
        calls = agent._extract_tool_calls(response)
        
        assert len(calls) == 1
        assert calls[0]["tool"] == "read_file"
        assert calls[0]["params"]["file_path"] == "config.json"

    def test_extract_tool_calls_multiple(self):
        """Test extracting multiple tool calls."""
        agent = OllamaAgent()
        response = '''
        {"tool": "read_file", "params": {"file_path": "a.txt"}}
        {"tool": "read_file", "params": {"file_path": "b.txt"}}
        '''
        
        calls = agent._extract_tool_calls(response)
        
        assert len(calls) == 2
        assert calls[0]["params"]["file_path"] == "a.txt"
        assert calls[1]["params"]["file_path"] == "b.txt"

    def test_extract_tool_calls_with_surrounding_text(self):
        """Test extraction when JSON is embedded in text."""
        agent = OllamaAgent()
        response = '''
        I'll read the file for you.
        {"tool": "read_file", "params": {"file_path": "config.json"}}
        Let me process that.
        '''
        
        calls = agent._extract_tool_calls(response)
        
        assert len(calls) == 1
        assert calls[0]["tool"] == "read_file"

    def test_extract_tool_calls_malformed_json_skipped(self):
        """Test that malformed JSON is gracefully skipped."""
        agent = OllamaAgent()
        response = '''
        {"tool": "read_file", "params": {"file_path": "good.json"}}
        {broken json here}
        {"tool": "write_file", "params": {"file_path": "also_good.json"}}
        '''
        
        calls = agent._extract_tool_calls(response)
        
        assert len(calls) == 2  # Only valid JSONs parsed
        assert calls[0]["tool"] == "read_file"
        assert calls[1]["tool"] == "write_file"

    def test_extract_tool_calls_no_tools(self):
        """Test response with no tool calls."""
        agent = OllamaAgent()
        response = "I've completed the task. The answer is 42."
        
        calls = agent._extract_tool_calls(response)
        
        assert len(calls) == 0


class TestOllamaAgentWithMocking:
    """Test agent iteration with mocked LLM."""

    @patch('orchestrator.OllamaAgent._call_ollama')
    @patch('orchestrator.OllamaAgent._check_ollama_connection')
    def test_execute_task_single_iteration(self, mock_check, mock_call):
        """Test task completion in one iteration (no tools needed)."""
        mock_check.return_value = True
        mock_call.return_value = "The task is complete."
        
        agent = OllamaAgent(verbose=False)
        result = agent.execute_task("Simple task")
        
        assert result["success"] is True
        assert "complete" in result["result"].lower()
        mock_call.assert_called_once()

    @patch('orchestrator.OllamaAgent._call_ollama')
    @patch('orchestrator.OllamaAgent._check_ollama_connection')
    def test_execute_task_with_tool_calls(self, mock_check, mock_call):
        """Test task requiring tool execution."""
        mock_check.return_value = True
        
        # Simulate: first response calls tool, second returns result
        mock_call.side_effect = [
            '{"tool": "read_file", "params": {"file_path": "test.txt"}}',
            "I read the file successfully."
        ]
        
        agent = OllamaAgent(verbose=False)
        result = agent.execute_task("Read a file")
        
        assert result["success"] is True
        assert mock_call.call_count == 2

    @patch('orchestrator.OllamaAgent._check_ollama_connection')
    def test_execute_task_connection_failed(self, mock_check):
        """Test graceful failure when LLM unavailable."""
        mock_check.return_value = False
        
        agent = OllamaAgent(verbose=False)
        result = agent.execute_task("Any task")
        
        assert result["success"] is False
        assert "connection" in result["error"].lower()

    @patch('orchestrator.OllamaAgent._call_ollama')
    @patch('orchestrator.OllamaAgent._check_ollama_connection')
    def test_execute_task_max_iterations(self, mock_check, mock_call):
        """Test max iteration limit to prevent infinite loops."""
        mock_check.return_value = True
        
        # Always return a tool call (never complete)
        mock_call.return_value = '{"tool": "read_file", "params": {"file_path": "f.txt"}}'
        
        agent = OllamaAgent(max_iterations=3, verbose=False)
        result = agent.execute_task("Infinite loop task")
        
        assert result["success"] is False
        assert "max iterations" in result["error"].lower()
        # Should have called LLM max_iterations times
        assert mock_call.call_count == 3
```

## Integration Tests

Test agents with real LLMs (slower, but more realistic).

**File: `test_integration.py`**

```python
import pytest
import tempfile
from pathlib import Path

from orchestrator import OllamaAgent, GeminiAgent
from tools import read_file, write_file


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestOllamaAgentIntegration:
    """Integration tests with real Ollama (requires ollama serve running)."""

    @pytest.mark.skipif(
        not pytest.config.getoption("--with-ollama"),
        reason="Requires --with-ollama and running Ollama service"
    )
    def test_read_and_summarize_file(self, temp_dir):
        """Test real task: read file and summarize."""
        # Create test file
        test_file = temp_dir / "story.txt"
        test_file.write_text("Once upon a time, there was a kingdom. It was peaceful.")
        
        # Execute task
        agent = OllamaAgent(verbose=False, log_dir=str(temp_dir / "logs"))
        result = agent.execute_task(
            f"Read {test_file} and provide a one-sentence summary"
        )
        
        assert result["success"] is True
        # Summary should mention kingdom or story
        assert any(word in result["result"].lower() 
                  for word in ["kingdom", "story", "peaceful"])


class TestGeminiAgentIntegration:
    """Integration tests with Gemini API (requires GOOGLE_API_KEY)."""

    @pytest.mark.skipif(
        not pytest.config.getoption("--with-gemini"),
        reason="Requires --with-gemini and GOOGLE_API_KEY"
    )
    def test_gemini_task_execution(self, temp_dir):
        """Test Gemini agent with real API call."""
        agent = GeminiAgent(verbose=False, log_dir=str(temp_dir / "logs"))
        result = agent.execute_task("What is 2 + 2? Respond with just the number.")
        
        assert result["success"] is True
        assert "4" in result["result"]
```

### Running Integration Tests

```bash
# Run with Ollama (requires ollama serve running)
pytest test_integration.py --with-ollama -v

# Run with Gemini (requires GOOGLE_API_KEY)
pytest test_integration.py --with-gemini -v

# Run all tests including integration
pytest -v
```

## Test Configuration

**File: `tests/conftest.py`**

```python
import os
import pytest


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--with-ollama",
        action="store_true",
        default=False,
        help="Run Ollama integration tests (requires running Ollama service)"
    )
    parser.addoption(
        "--with-gemini",
        action="store_true",
        default=False,
        help="Run Gemini integration tests (requires GOOGLE_API_KEY)"
    )


@pytest.fixture(scope="session")
def google_api_key():
    """Get Gemini API key from environment."""
    key = os.getenv("GOOGLE_API_KEY")
    if not key and pytest.config.getoption("--with-gemini"):
        pytest.skip("GOOGLE_API_KEY not set")
    return key
```

## CI/CD Integration

### GitHub Actions Workflow

**File: `.github/workflows/tests.yml`**

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.9'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install pytest pytest-cov
    
    - name: Run unit tests
      run: pytest test_tools.py test_orchestrator.py -v --cov --cov-report=xml
    
    - name: Upload coverage
      uses: codecov/codecov-action@v3
```

## Testing Checklist

Before merging:

- [ ] All unit tests pass (`pytest test_tools.py test_orchestrator.py -v`)
- [ ] New tools have corresponding unit tests
- [ ] Code coverage > 80% (`pytest --cov`)
- [ ] Integration tests pass with real backends (if modifying orchestrator)
- [ ] No hardcoded paths or API keys in tests
- [ ] Test names are descriptive (`test_feature_scenario`)
- [ ] Edge cases covered (empty input, very large input, permission errors)
- [ ] Mocking used appropriately (agent tests mock LLM, don't mock tools unnecessarily)

## Common Testing Patterns

### Fixture: Minimal Agent for Testing

```python
@pytest.fixture
def mock_agent():
    """Create agent with mocked LLM connection."""
    with patch('orchestrator.OllamaAgent._check_ollama_connection') as mock_check:
        mock_check.return_value = True
        agent = OllamaAgent(verbose=False)
    return agent
```

### Parameterized Tests for Many Cases

```python
@pytest.mark.parametrize("input,expected", [
    ("valid_file.txt", True),
    ("missing_file.txt", False),
    ("/path/to/file.txt", True),
])
def test_read_file(input, expected):
    result = read_file(input)
    assert result["success"] == expected
```

### Isolating Tool Tests from Agent Tests

- **Tool tests**: Direct function calls, no orchestrator involved
- **Agent tests**: Mock the LLM, test tool calling and iteration logic
- **Integration tests**: Real LLM & real tools (slow, use sparingly)
