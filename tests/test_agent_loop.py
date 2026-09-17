import tempfile
import unittest
from itertools import cycle
from pathlib import Path

from orchestrator import BaseAgent


class FakeAgent(BaseAgent):
    def __init__(self, responses, **kwargs):
        super().__init__(model="fake", verbose=False, **kwargs)
        self.responses = cycle(responses)

    def _get_backend_name(self):
        return "Fake"

    def _get_backend_connection_info(self):
        return "offline"

    def _check_connection(self):
        return True

    def _get_connection_error_msg(self):
        return "fake backend unavailable"

    def _call_llm(self, prompt):
        return next(self.responses)


class TestAgentLoop(unittest.TestCase):
    @staticmethod
    def close_logging(agent):
        for handler in agent.logger.handlers:
            handler.close()
        agent.logger.handlers.clear()

    def test_tool_result_is_continued_to_completion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = Path(temp_dir) / "input.txt"
            file_path.write_text("smoke test", encoding="utf-8")
            agent = FakeAgent([
                '{"tool": "read_file", "params": {"file_path": "' + str(file_path) + '"}}',
                "The file was read successfully.",
            ], log_dir=temp_dir)

            result = agent.execute_task("Read the input file")
            self.close_logging(agent)

        self.assertTrue(result["success"])
        self.assertEqual(result["iterations"], 2)
        self.assertEqual(result["conversation"][0]["tool_calls"][0]["tool"], "read_file")
        self.assertIn("successfully", result["result"])

    def test_max_iterations_returns_failure(self):
        agent = FakeAgent(
            ['{"tool": "list_directory", "params": {"dir_path": "."}}'],
            max_iterations=2,
            log_dir=tempfile.mkdtemp(),
        )

        result = agent.execute_task("Keep checking the directory")
        self.close_logging(agent)

        self.assertFalse(result["success"])
        self.assertIn("Max iterations (2)", result["error"])
        self.assertEqual(len(result["conversation"]), 2)


if __name__ == "__main__":
    unittest.main()
