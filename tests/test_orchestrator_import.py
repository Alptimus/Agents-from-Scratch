import builtins
import importlib
import sys
import unittest
from unittest.mock import patch


class TestOrchestratorImport(unittest.TestCase):
    def test_orchestrator_imports_without_google_genai(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "google" or name.startswith("google."):
                raise ImportError("No module named 'google'")
            return original_import(name, *args, **kwargs)

        sys.modules.pop("orchestrator", None)

        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module("orchestrator")

        self.assertTrue(hasattr(module, "OllamaAgent"))
        self.assertTrue(hasattr(module, "GeminiAgent"))


if __name__ == "__main__":
    unittest.main()
