"""
Integration tests for SQL tool and Playwright browser automation workflows.
Verifies autonomous multi-step agent behaviors, tool execution chaining,
and resilience to operational error scenarios.
"""

import sqlite3
import tempfile
import unittest
from itertools import cycle
from pathlib import Path
from unittest.mock import MagicMock, patch

import browser_automation
from orchestrator import BaseAgent


class WorkflowAgent(BaseAgent):
    """Deterministic agent for multi-step workflow integration tests."""

    def __init__(self, responses, **kwargs):
        super().__init__(model="workflow-test", verbose=False, **kwargs)
        self.responses = iter(responses)

    def _get_backend_name(self) -> str:
        return "WorkflowMock"

    def _get_backend_connection_info(self) -> str:
        return "offline-integration"

    def _check_connection(self) -> bool:
        return True

    def _get_connection_error_msg(self) -> str:
        return "mock backend unavailable"

    def _call_llm(self, prompt: str) -> str:
        return next(self.responses)


class TestSqlAgentWorkflow(unittest.TestCase):
    """Test suite for autonomous agent workflows using SQL and browser tools."""

    @staticmethod
    def _close_logging(agent: BaseAgent) -> None:
        """Close log handlers to avoid resource leaks during tests."""
        if agent.logger:
            for handler in agent.logger.handlers:
                handler.close()
            agent.logger.handlers.clear()

    def setUp(self):
        """Create a temporary directory and test database."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "workflow_test.sqlite"

        with sqlite3.connect(str(self.db_path)) as conn:
            conn.execute("""
                CREATE TABLE employees (
                    id INTEGER PRIMARY KEY,
                    name TEXT,
                    department TEXT,
                    salary REAL
                )
            """)
            conn.execute("INSERT INTO employees VALUES (1, 'Alice', 'Engineering', 125000)")
            conn.execute("INSERT INTO employees VALUES (2, 'Bob', 'Marketing', 95000)")
            conn.execute("INSERT INTO employees VALUES (3, 'Charlie', 'Engineering', 140000)")
            conn.commit()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_autonomous_sql_query_workflow(self):
        """Test agent autonomously executes SQL query and synthesizes results."""
        query_call = (
            f'{{"tool": "execute_sql_query", "params": '
            f'{{"database": "{self.db_path}", "query": '
            f'"SELECT name, salary FROM employees WHERE department = \'Engineering\' ORDER BY salary DESC"}}}}'
        )
        final_summary = "Engineering employees are Charlie ($140,000) and Alice ($125,000)."

        agent = WorkflowAgent(
            responses=[query_call, final_summary],
            log_dir=self.temp_dir.name
        )

        result = agent.execute_task("List all engineering employees and their salaries")
        self._close_logging(agent)

        self.assertTrue(result["success"])
        self.assertEqual(result["iterations"], 2)
        self.assertEqual(len(result["conversation"]), 2)
        # Check first step called execute_sql_query
        step_1_tools = result["conversation"][0]["tool_calls"]
        self.assertEqual(len(step_1_tools), 1)
        self.assertEqual(step_1_tools[0]["tool"], "execute_sql_query")
        self.assertIn("Charlie", result["result"])

    def test_autonomous_browser_screenshot_workflow(self):
        """Test agent autonomously captures a screenshot and reports status."""
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        screenshot_dir = Path(self.temp_dir.name) / "screenshots"
        screenshot_call = (
            f'{{"tool": "take_screenshot", "params": '
            f'{{"url": "https://example.com/status", "output_dir": "{screenshot_dir}"}}}}'
        )
        final_summary = "The webpage screenshot was successfully captured and saved."

        with patch.object(browser_automation, "sync_playwright", mock_sync_playwright):
            agent = WorkflowAgent(
                responses=[screenshot_call, final_summary],
                log_dir=self.temp_dir.name
            )

            result = agent.execute_task("Capture a screenshot of example.com/status")
            self._close_logging(agent)

        self.assertTrue(result["success"])
        self.assertEqual(result["iterations"], 2)
        step_1_tools = result["conversation"][0]["tool_calls"]
        self.assertEqual(step_1_tools[0]["tool"], "take_screenshot")
        self.assertIn("successfully captured", result["result"])

    def test_multi_step_hybrid_workflow(self):
        """Test chaining browser automation and SQL query in a single autonomous task."""
        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        screenshot_call = (
            f'{{"tool": "take_screenshot", "params": '
            f'{{"url": "https://portal.internal", "output_dir": "{self.temp_dir.name}"}}}}'
        )
        sql_call = (
            f'{{"tool": "execute_sql_query", "params": '
            f'{{"database": "{self.db_path}", "query": "SELECT count(*) FROM employees"}}}}'
        )
        final_summary = "Audit complete: portal captured and 3 active employees verified."

        with patch.object(browser_automation, "sync_playwright", mock_sync_playwright):
            agent = WorkflowAgent(
                responses=[screenshot_call, sql_call, final_summary],
                log_dir=self.temp_dir.name
            )

            result = agent.execute_task("Verify system status via screenshot and employee headcount")
            self._close_logging(agent)

        self.assertTrue(result["success"])
        self.assertEqual(result["iterations"], 3)
        self.assertEqual(result["conversation"][0]["tool_calls"][0]["tool"], "take_screenshot")
        self.assertEqual(result["conversation"][1]["tool_calls"][0]["tool"], "execute_sql_query")
        self.assertIn("Audit complete", result["result"])

    def test_error_handling_invalid_database(self):
        """Test agent handles database not found error without crashing."""
        query_call = '{"tool": "execute_sql_query", "params": {"database": "/invalid/nonexistent.db", "query": "SELECT 1"}}'
        error_handling_response = "The requested database does not exist on disk."

        agent = WorkflowAgent(
            responses=[query_call, error_handling_response],
            log_dir=self.temp_dir.name
        )

        result = agent.execute_task("Query the missing database")
        self._close_logging(agent)

        self.assertTrue(result["success"])
        self.assertIn("does not exist", result["result"])

    def test_error_handling_malformed_sql(self):
        """Test agent handles malformed SQL query and recovers."""
        malformed_call = (
            f'{{"tool": "execute_sql_query", "params": '
            f'{{"database": "{self.db_path}", "query": "SELECT FROM employees WHERE"}}}}'
        )
        recovery_call = (
            f'{{"tool": "execute_sql_query", "params": '
            f'{{"database": "{self.db_path}", "query": "SELECT count(*) FROM employees"}}}}'
        )
        final_response = "Corrected query executed; 3 employees found."

        agent = WorkflowAgent(
            responses=[malformed_call, recovery_call, final_response],
            log_dir=self.temp_dir.name
        )

        result = agent.execute_task("Count employees with error recovery")
        self._close_logging(agent)

        self.assertTrue(result["success"])
        self.assertEqual(result["iterations"], 3)
        self.assertIn("3 employees found", result["result"])

    def test_error_handling_browser_timeout(self):
        """Test agent handles browser navigation failure gracefully."""
        mock_page = MagicMock()
        mock_page.goto.side_effect = Exception("Page load timed out after 30000ms")
        mock_context = MagicMock()
        mock_context.new_page.return_value = mock_page
        mock_browser = MagicMock()
        mock_browser.new_context.return_value = mock_context

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch.return_value = mock_browser

        mock_sync_playwright = MagicMock()
        mock_sync_playwright.return_value.__enter__.return_value = mock_playwright

        screenshot_call = '{"tool": "take_screenshot", "params": {"url": "https://slow.example.com"}}'
        final_response = "Browser capture timed out; website could not be reached."

        with patch.object(browser_automation, "sync_playwright", mock_sync_playwright):
            agent = WorkflowAgent(
                responses=[screenshot_call, final_response],
                log_dir=self.temp_dir.name
            )

            result = agent.execute_task("Screenshot slow site")
            self._close_logging(agent)

        self.assertTrue(result["success"])
        self.assertIn("timed out", result["result"])


if __name__ == "__main__":
    unittest.main()

