import builtins
import importlib
import sys
import unittest
from unittest.mock import patch


class TestOptionalDocxImport(unittest.TestCase):
    def test_tools_module_imports_without_docx_dependency(self):
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == "docx":
                raise ImportError("No module named 'docx'")
            return original_import(name, *args, **kwargs)

        sys.modules.pop("tools", None)

        with patch("builtins.__import__", side_effect=guarded_import):
            module = importlib.import_module("tools")

        self.assertTrue(hasattr(module, "TOOLS"))
        self.assertTrue(module.docx is None)

        result = module.read_docx_file("example.docx")
        self.assertFalse(result["success"])
        self.assertIn("python-docx", result["error"])


if __name__ == "__main__":
    unittest.main()
