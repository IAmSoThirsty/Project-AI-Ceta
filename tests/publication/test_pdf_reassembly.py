"""Deterministic publication-utility tests; no product runtime is started."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("reassembly", ROOT / "tools/reassemble_codex_pdf.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ReassemblyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = b"%PDF-test\x00\xff\r\ncontent"
        self.manifest = self.root / "parts.json"
        self.output = self.root / "reference.pdf"
        parts = [self.payload[:9], self.payload[9:]]
        self.data = dict(schema="ceta.reference-pdf-parts.v1", file="reference.pdf", bytes=len(self.payload),
                         sha256=hashlib.sha256(self.payload).hexdigest(), parts=[])
        for i, raw in enumerate(parts, 1):
            name = f"reference.pdf.part{i:02}"
            (self.root / name).write_bytes(raw)
            self.data["parts"].append(dict(file=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
        self.save()

    def save(self):
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")

    def assert_failure(self):
        with self.assertRaises((ValueError, OSError)):
            MODULE.assemble(self.manifest, self.output)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".ceta-pdf-*.tmp")), [])

    def test_exact_reassembly(self):
        self.assertEqual(MODULE.assemble(self.manifest, self.output), "REASSEMBLED_AND_VERIFIED")
        self.assertEqual(self.output.read_bytes(), self.payload)

    def test_existing_identical_output_preserved(self):
        self.output.write_bytes(self.payload)
        before = self.output.stat().st_mtime_ns
        self.assertEqual(MODULE.assemble(self.manifest, self.output), "ALREADY_VERIFIED")
        self.assertEqual(self.output.stat().st_mtime_ns, before)

    def test_existing_different_output_preserved(self):
        self.output.write_bytes(b"owner content")
        with self.assertRaises(FileExistsError):
            MODULE.assemble(self.manifest, self.output)
        self.assertEqual(self.output.read_bytes(), b"owner content")

    def test_missing_part(self):
        (self.root / self.data["parts"][0]["file"]).unlink()
        self.assert_failure()

    def test_truncated_part(self):
        (self.root / self.data["parts"][0]["file"]).write_bytes(b"short")
        self.assert_failure()

    def test_corrupt_same_size_part(self):
        entry = self.data["parts"][0]
        (self.root / entry["file"]).write_bytes(b"x" * entry["bytes"])
        self.assert_failure()

    def test_wrong_combined_digest(self):
        self.data["sha256"] = "0" * 64
        self.save()
        self.assert_failure()

    def test_path_traversal(self):
        self.data["parts"][0]["file"] = "../owner-file"
        self.save()
        self.assert_failure()

    def test_duplicate_parts(self):
        self.data["parts"][1]["file"] = self.data["parts"][0]["file"]
        self.save()
        self.assert_failure()

    def test_wrong_total(self):
        self.data["bytes"] += 1
        self.save()
        self.assert_failure()

    def test_part_limit(self):
        self.data["parts"][0]["bytes"] = MODULE.LIMIT
        self.data["bytes"] = sum(p["bytes"] for p in self.data["parts"])
        self.save()
        self.assert_failure()

    def test_boolean_size_rejected(self):
        self.data["parts"][0]["bytes"] = True
        self.save()
        self.assert_failure()


if __name__ == "__main__":
    unittest.main()
