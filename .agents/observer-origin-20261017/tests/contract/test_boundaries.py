import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
import ceta.contracts.wire as wire


class BoundaryTests(unittest.TestCase):
    def test_actual_import_is_mapped_namespace_not_retained_ceta(self):
        self.assertTrue(Path(wire.__file__).resolve().is_relative_to(ROOT / "src/ceta"))

    def test_contract_leaf_imports_only_declared_pure_dependencies(self):
        allowed = {"__future__", "dataclasses", "datetime", "enum", "hashlib", "json", "re", "unicodedata", "typing"}
        for path in (ROOT / "src/ceta/contracts").glob("*.py"):
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split(".")[0], allowed, str(path))
                elif isinstance(node, ast.ImportFrom) and not node.level:
                    self.assertIn(node.module.split(".")[0], allowed, str(path))
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    self.assertNotIn(node.func.id, {"eval", "exec", "__import__", "open"}, str(path))


if __name__ == "__main__":
    unittest.main()
