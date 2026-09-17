import builtins
import importlib
import sys
import unittest
from unittest.mock import patch


class TestGeminiImport(unittest.TestCase):
    def test_module_imports_without_google_genai(self):
        original_import = builtins.__import__
        original_module = sys.modules.pop("gemini_utils", None)

        def guarded_import(name, *args, **kwargs):
            if name == "google" or name.startswith("google."):
                raise ImportError("No module named 'google'")
            return original_import(name, *args, **kwargs)

        try:
            with patch("builtins.__import__", side_effect=guarded_import):
                module = importlib.import_module("gemini_utils")
        finally:
            sys.modules.pop("gemini_utils", None)
            if original_module is not None:
                sys.modules["gemini_utils"] = original_module

        self.assertIsNone(module.genai)
        with self.assertRaisesRegex(RuntimeError, "google-genai"):
            module.get_gemini_client()


if __name__ == "__main__":
    unittest.main()
