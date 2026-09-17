import importlib.util
import pathlib
import unittest
from unittest.mock import patch


class TestMainCli(unittest.TestCase):
    def test_main_module_compiles(self):
        repo_root = pathlib.Path(__file__).resolve().parents[1]
        main_path = repo_root / "main.py"

        spec = importlib.util.spec_from_file_location("main_cli_module", main_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        self.assertTrue(hasattr(module, "main"))

    def test_blank_gemini_api_key_is_invalid(self):
        repo_root = pathlib.Path(__file__).resolve().parents[1]
        main_path = repo_root / "main.py"
        spec = importlib.util.spec_from_file_location("main_cli_validation", main_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with patch.object(module, "config", return_value="  "):
            self.assertFalse(module.validate_gemini_api_key())


if __name__ == "__main__":
    unittest.main()
