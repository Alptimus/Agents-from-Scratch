import importlib.util
import pathlib
import unittest


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


if __name__ == "__main__":
    unittest.main()
