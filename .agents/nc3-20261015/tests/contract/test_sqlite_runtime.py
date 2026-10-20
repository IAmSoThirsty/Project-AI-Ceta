"""Verify actual DLL identity and refusal of a preloaded installed engine."""
import importlib.util
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.store.sqlite_runtime import DLL_PATH, DLL_SHA256, runtime_identity


class SqliteRuntimeTests(unittest.TestCase):
    def test_actual_loaded_identity_is_project_dll_and_original_wrapper(self):
        identity = runtime_identity()
        self.assertEqual(Path(identity["dll_path"]), DLL_PATH)
        self.assertEqual(identity["dll_sha256"], DLL_SHA256)
        self.assertEqual(identity["version"], "3.53.4")
        self.assertEqual(identity["wrapper_sha256"], "64b51df2805c58b023a875e8ae3be7ac7f61ef664f32ca6c90f6315da47ef0bc")

    def test_preloaded_other_engine_is_rejected_in_real_fresh_process(self):
        code = "import sys,sqlite3;sys.path.insert(0,sys.argv[1]);from ceta.store.sqlite_runtime import load_sqlite;load_sqlite()"
        result = subprocess.run([sys.executable, "-B", "-X", "utf8", "-c", code, str(ROOT / "src")], capture_output=True, timeout=15)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"SQLITE_PRELOADED_ENGINE_CONFLICT", result.stderr)

    def test_inventory_and_runner_watch_actual_sqlite_binary(self):
        sys.path.insert(0, str(ROOT / "tools"))
        from development_inventory import watched
        self.assertTrue(watched("native/sqlite_runtime/win-x64/sqlite3.dll"))
        self.assertTrue(watched("native/sqlite_runtime/win-x64/sqlite3.def"))
        spec = importlib.util.spec_from_file_location("source_runner_watch_check", ROOT / "tools/run_source_tests.py")
        runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runner)
        self.assertEqual(runner.snapshot()["native/sqlite_runtime/win-x64/sqlite3.dll"], DLL_SHA256)


if __name__ == "__main__":
    unittest.main()
