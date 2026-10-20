from pathlib import Path
import importlib.util
import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import zipfile

PROJECT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("preservation", PROJECT / "tools/preserve_ceta_baseline.py")
preservation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preservation)


class PreservationTests(unittest.TestCase):
    def setUp(self):
        cache = PROJECT / ".local-test-output"
        cache.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=cache)
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        self.repo.mkdir()
        self.command("init")
        (self.repo / "one.txt").write_bytes(b"original\r\n")
        (self.repo / ".gitignore").write_text("private/\n", encoding="utf-8")
        self.command("add", ".")
        self.command("-c", "user.name=Fixture", "-c", "user.email=fixture@invalid",
                     "commit", "-m", "fixture")

    def command(self, *args):
        subprocess.run(["git", "-C", str(self.repo), *args], check=True, capture_output=True)

    def test_dirty_staged_untracked_and_ignored_survive_exactly(self):
        (self.repo / "one.txt").write_bytes(b"staged\r\n")
        self.command("add", "one.txt")
        (self.repo / "one.txt").write_bytes(b"working\x00\xff")
        (self.repo / "unknown.txt").write_bytes(b"unknown")
        (self.repo / "private").mkdir()
        secret = self.repo / "private" / "key.key"
        secret.write_bytes(b"secret must stay in place")
        before = preservation.inventory(self.repo)
        result = preservation.checkpoint(self.repo, self.base / "backup")
        self.assertEqual(result["result"], "PASS")
        self.assertEqual(before, preservation.inventory(self.repo))
        self.assertEqual(secret.read_bytes(), b"secret must stay in place")
        self.assertEqual((self.base / "backup/restoration-proof/one.txt").read_bytes(), b"working\x00\xff")
        self.assertTrue((self.base / "backup/working.patch").stat().st_size)
        self.assertTrue((self.base / "backup/staged.patch").stat().st_size)
        with zipfile.ZipFile(self.base / "backup/working-source.zip") as source:
            self.assertNotIn("private/key.key", source.namelist())

    def test_checkpoint_never_overwrites_existing_directory(self):
        target = self.base / "existing"
        target.mkdir()
        with self.assertRaisesRegex(ValueError, "already exists"):
            preservation.checkpoint(self.repo, target)

    def test_nested_directory_is_not_accepted_as_repository_root(self):
        target = self.repo / "nested"
        target.mkdir()
        with self.assertRaisesRegex(ValueError, "exact Git root"):
            preservation.inventory(target)

    def test_untracked_sensitive_file_blocks_plaintext_backup(self):
        (self.repo / "unknown.key").write_bytes(b"secret")
        with self.assertRaisesRegex(ValueError, "sensitive paths"):
            preservation.checkpoint(self.repo, self.base / "backup")
        self.assertFalse((self.base / "backup").exists())

    def test_restore_rejects_escape_without_creating_output(self):
        archive = self.base / "bad.zip"
        data = b"escape"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("../escape.txt", data)
        expected = {"files": [{"path": "../escape.txt", "bytes": len(data),
                               "sha256": preservation.digest(data)}]}
        with self.assertRaisesRegex(ValueError, "unsafe archive"):
            preservation.verify_restore(archive, expected, self.base / "restore")
        self.assertFalse((self.base / "restore").exists())

    def test_changed_archive_is_rejected_before_restore(self):
        archive = self.base / "bad.zip"
        with zipfile.ZipFile(archive, "w") as output:
            output.writestr("one.txt", b"tampered")
        expected = {"files": [{"path": "one.txt", "bytes": 8,
                               "sha256": preservation.digest(b"original")}]}
        with self.assertRaisesRegex(ValueError, "hash changed"):
            preservation.verify_restore(archive, expected, self.base / "restore")
        self.assertFalse((self.base / "restore").exists())

    def test_restore_never_overwrites_existing_directory(self):
        target = self.base / "existing"
        target.mkdir()
        with self.assertRaisesRegex(ValueError, "already exists"):
            preservation.verify_restore(self.base / "unused.zip", {"files": []}, target)

    def test_deleted_source_is_preserved_as_absence_and_diff(self):
        (self.repo / "one.txt").unlink()
        result = preservation.checkpoint(self.repo, self.base / "backup")
        inv = json.loads((self.base / "backup/inventory.json").read_text())
        self.assertEqual(inv["absent_tracked_paths"], ["one.txt"])
        self.assertEqual(result["result"], "PASS")
        self.assertFalse((self.base / "backup/restoration-proof/one.txt").exists())

    def test_concurrent_source_change_invalidates_checkpoint_and_preserves_new_work(self):
        original_git = preservation.git
        def changed_git(root, *args):
            output = original_git(root, *args)
            if args[:2] == ("bundle", "verify"):
                (self.repo / "one.txt").write_bytes(b"newer concurrent work")
            return output
        with patch.object(preservation, "git", changed_git):
            with self.assertRaisesRegex(RuntimeError, "state changed during checkpoint"):
                preservation.checkpoint(self.repo, self.base / "backup")
        self.assertEqual((self.repo / "one.txt").read_bytes(), b"newer concurrent work")
        self.assertFalse((self.base / "backup/checkpoint.json").exists())


if __name__ == "__main__":
    unittest.main()
