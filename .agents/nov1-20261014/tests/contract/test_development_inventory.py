import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("development_inventory", ROOT / "tools/development_inventory.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DevelopmentInventoryTests(unittest.TestCase):
    def test_exact_content_hashes_and_distinct_watch_selection(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for path in ("src/a.py", "contracts/state_catalog.json", "requirements-contract-tests.lock",
                         "instruction-source.txt", ".gitignore", "unknown.txt"):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"fixture")
            result = module.inventory(root)
            self.assertEqual(result["inventory_file_count"], 6)
            self.assertEqual(result["source_test_watched_count"], 3)
            self.assertEqual(result["files"]["unknown.txt"]["sha256"], hashlib.sha256(b"fixture").hexdigest())
            self.assertFalse(result["files"]["instruction-source.txt"]["source_test_watched"])

    def test_explicit_cache_and_private_exclusions(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for path in (".venv/x.py", ".local-profiles/data", ".private/data", "src/__pycache__/a.pyc",
                         "native/canonical_reference/target/a.exe", "test.KEY", "secret.pem", "x.p12", "x.pfx"):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"excluded fixture")
            self.assertEqual(module.inventory(root)["files"], {})

    def test_ambient_gitignore_does_not_hide_an_unknown_source(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            (root / ".gitignore").write_text("*.py\n", encoding="utf-8")
            (root / "a.py").write_bytes(b"fixture")
            self.assertEqual(set(module.inventory(root)["files"]), {".gitignore", "a.py"})

    def test_windows_case_variants_of_excluded_paths_are_not_read(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            for path in (".PRIVATE/data", ".Local-Profiles/data", ".VENV/code.py",
                         "Native/Canonical_Reference/Target/a.exe"):
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b"excluded fixture")
            self.assertEqual(module.inventory(root)["files"], {})

    def test_scan_permission_failure_rejects_incomplete_inventory(self):
        def fail_walk(*args, **kwargs):
            kwargs["onerror"](PermissionError("synthetic inaccessible source directory"))
            yield None
        with tempfile.TemporaryDirectory() as name:
            with patch.object(module.os, "walk", side_effect=fail_walk):
                with self.assertRaisesRegex(ValueError, "INVENTORY_SCAN_FAILED"):
                    module.inventory(Path(name))

    def test_input_drift_rejects_the_observation(self):
        with tempfile.TemporaryDirectory() as name:
            with patch.object(module, "_read", side_effect=[{"a": {}}, {"b": {}}]):
                with self.assertRaisesRegex(ValueError, "SOURCE_CHANGED_DURING_INVENTORY"):
                    module.inventory(Path(name))


if __name__ == "__main__":
    unittest.main()
