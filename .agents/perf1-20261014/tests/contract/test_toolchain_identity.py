import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("native_build", ROOT / "tools/build_native_reference.py")
native_build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(native_build)


class ToolchainIdentityTests(unittest.TestCase):
    def test_exact_compiler_is_admitted_for_reference_build(self):
        version = "\n".join(f"{key}: {value}" for key, value in native_build.EXPECTED.items())
        native_build.require_compiler_identity(version)

    def test_release_host_or_compiler_commit_drift_prevents_build(self):
        for changed in native_build.EXPECTED:
            fields = dict(native_build.EXPECTED)
            fields[changed] = "other"
            version = "\n".join(f"{key}: {value}" for key, value in fields.items())
            with self.subTest(field=changed), self.assertRaises(ValueError):
                native_build.require_compiler_identity(version)
