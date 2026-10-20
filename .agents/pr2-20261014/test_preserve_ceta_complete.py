"""Actual disposable Windows filesystem and Git acceptance/recovery tests.

Fixtures are retained under this explicitly assigned cut. No test discovers,
modifies, resets, cleans, or restores an actual CETA source repository.
"""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import sqlite3
import ssl
import subprocess
import sys
import unittest
import uuid
from unittest.mock import patch
import zipfile

import preserve_ceta_complete as tool


CUT = Path(__file__).parent.absolute()
DEFAULT_FIXTURES = CUT / "disposable-windows-fixtures"
REVIEW_FIXTURES = CUT.parent / "runtime" / CUT.name / "native-review-fixtures"
FIXTURES = Path(os.environ.get("CETA_PRESERVATION_TEST_FIXTURE_ROOT", str(DEFAULT_FIXTURES))).absolute()


class PreservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.name != "nt":
            raise RuntimeError("This native acceptance suite requires actual Windows")
        if FIXTURES not in {DEFAULT_FIXTURES, REVIEW_FIXTURES}:
            raise RuntimeError("Test fixture root is outside the two exact assigned locations")
        tool.safe_components(FIXTURES, allow_missing=True)
        FIXTURES.mkdir(exist_ok=True)

    def setUp(self):
        self.area = FIXTURES / ("t-" + tool.sha(self._testMethodName.encode())[:8] + "-" + uuid.uuid4().hex[:8])
        self.area.mkdir()
        self.source = self.area / "source"
        self.source.mkdir()
        self.capture_path = self.area / "checkpoint"
        self.restore_path = self.area / "recovered"
        self.fixture_git = False

    def write(self, name, data=b"fixture bytes\n"):
        path = self.source.joinpath(*name.split("/"))
        os.makedirs(tool.io_path(path.parent), exist_ok=True)
        tool.write_new(path, data)
        return path

    def policy_data(self):
        return {"schema_version": 1, "source_roots": [str(self.source)],
                "git_roots": [str(self.source / ".git")] if self.fixture_git else [],
                "capture_targets": [str(self.capture_path)], "restore_targets": [str(self.restore_path)],
                "classifications": [], "declared_inputs": []}

    def policy(self, **changes):
        data = self.policy_data()
        data.update(changes)
        return tool.Policy(data)

    def fixture_command(self, *args, root=None, data=None):
        root = root or self.source
        self.assertTrue(tool.inside(root.absolute(), self.area.absolute()))
        self.assertTrue(tool.inside(self.area.absolute(), FIXTURES.absolute()))
        return tool.git(root, *args, data=data)

    def initialize_git(self):
        self.fixture_command("init", "--initial-branch=main")
        self.fixture_git = True
        self.fixture_command("config", "user.name", "CETA disposable acceptance fixture")
        self.fixture_command("config", "user.email", "fixture@example.invalid")
        self.fixture_command("config", "core.autocrlf", "false")
        self.write("tracked.txt", b"base\n")
        self.write(".gitignore", b"ignored/\n*.ignored\n")
        self.fixture_command("add", "tracked.txt", ".gitignore")
        self.fixture_command("commit", "-m", "disposable fixture base")
        return self.fixture_command("rev-parse", "HEAD").decode().strip()

    def dirty_git(self):
        base = self.initialize_git()
        self.write("reflog-only.txt", b"retained only through reflog\n")
        self.fixture_command("add", "reflog-only.txt")
        self.fixture_command("commit", "-m", "disposable reflog-only commit")
        hidden = self.fixture_command("rev-parse", "HEAD").decode().strip()
        # Fixture-only ref movement creates the recovery obligation without a
        # source reset, clean, checkout or deletion.
        self.fixture_command("update-ref", "-m", "fixture: retain old head in reflog", "refs/heads/main", base, hidden)
        self.fixture_command("branch", "fixture-feature", base)
        self.fixture_command("tag", "-a", "fixture-tag", "-m", "annotated fixture tag", base)
        (self.source / "tracked.txt").write_bytes(b"staged\n")
        self.fixture_command("add", "tracked.txt")
        (self.source / "tracked.txt").write_bytes(b"unstaged final bytes\n")
        self.write("ignored/generated.ignored", b"ignored artifact must survive\x00\xff")
        self.write("unknown-owner-note.txt", b"unknown untracked user work\n")
        self.assertNotIn(hidden, self.fixture_command("rev-list", "--all").decode().splitlines())
        self.assertIn(hidden, self.fixture_command("rev-list", "--all", "--reflog").decode().splitlines())
        return base, hidden

    def full_hashes(self):
        return {p.relative_to(self.source).as_posix(): tool.hash_file(p)[:2]
                for p in self.source.rglob("*") if p.is_file() and not p.is_symlink()}

    def native_source_snapshot(self):
        values, stack = {}, [(self.source, "")]
        while stack:
            directory, prefix = stack.pop()
            with os.scandir(tool.io_path(directory)) as listing:
                entries = list(listing)
            for entry in entries:
                path, name = directory / entry.name, prefix + entry.name
                info = entry.stat(follow_symlinks=False)
                self.assertFalse(tool.reparse(info))
                if entry.is_dir(follow_symlinks=False):
                    stack.append((path, name + "/"))
                else:
                    values[name] = {**tool.file_identity(info), "sha256": tool.hash_file(path)[1]}
        return values

    def reseal(self):
        manifest = tool.load_json(self.capture_path / "checkpoint.json")
        for artifact in manifest["artifacts"]:
            artifact["bytes"], artifact["sha256"], _ = tool.hash_file(self.capture_path / artifact["path"])
        payload = (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode()
        (self.capture_path / "checkpoint.json").write_bytes(payload)
        (self.capture_path / "COMMITTED").write_text(tool.sha(payload) + "\n")

    def test_ignored_unknown_empty_and_long_paths_restore_exactly(self):
        base, hidden = self.dirty_git()
        long_name = "/".join(["long-segment-" + "x" * 48] * 5) + "/native-long-name.bin"
        long_file = self.write(long_name, b"native Windows long-path bytes\x00\xfe")
        self.assertGreater(len(str(long_file)), 260)
        (self.source / "empty-directory").mkdir()
        readonly = self.write("readonly.bin", b"retain read-only bytes")
        os.chmod(readonly, 0o444)
        before = self.full_hashes()
        policy = self.policy()
        source_before = self.native_source_snapshot()
        captured = tool.capture(self.source, self.capture_path, policy)
        self.assertTrue(captured["complete"])
        self.assertTrue(captured["source_unchanged"])
        result = tool.restore(self.capture_path, self.restore_path, policy)
        recovered = self.restore_path / "working-tree"
        self.assertEqual(tool.read_bytes(recovered / long_name), b"native Windows long-path bytes\x00\xfe")
        self.assertEqual((recovered / "ignored/generated.ignored").read_bytes(), b"ignored artifact must survive\x00\xff")
        self.assertEqual((recovered / "unknown-owner-note.txt").read_bytes(), b"unknown untracked user work\n")
        self.assertTrue((recovered / "empty-directory").is_dir())
        self.assertEqual((recovered / "readonly.bin").read_bytes(), b"retain read-only bytes")
        self.assertEqual(self.fixture_command("rev-parse", "HEAD", root=recovered).decode().strip(), base)
        self.assertEqual(self.fixture_command("show", hidden + ":reflog-only.txt", root=recovered), b"retained only through reflog\n")
        self.assertEqual(self.fixture_command("rev-parse", "refs/heads/fixture-feature", root=recovered).decode().strip(), base)
        self.assertEqual(self.fixture_command("cat-file", "-t", "refs/tags/fixture-tag", root=recovered), b"tag\n")
        self.assertIn(hidden, self.fixture_command("rev-list", "--all", root=recovered).decode().splitlines())
        self.assertFalse(tool.exists(recovered / ".git/objects/info/alternates"))
        self.assertEqual(before, self.full_hashes())
        self.assertEqual(source_before, self.native_source_snapshot())
        self.assertGreater(result["git_objects"], 0)

    def test_binary_staged_and_working_patches_and_index_are_preserved(self):
        self.initialize_git()
        self.write("binary.bin", bytes(range(256)))
        self.fixture_command("add", "binary.bin")
        (self.source / "binary.bin").write_bytes(b"\x00\xffunstaged\x00")
        index_before = (self.source / ".git/index").read_bytes()
        staged = self.fixture_command("diff", "--cached", "--binary", "--full-index", "--no-ext-diff", "--no-textconv")
        working = self.fixture_command("diff", "--binary", "--full-index", "--no-ext-diff", "--no-textconv")
        policy = self.policy()
        tool.capture(self.source, self.capture_path, policy)
        self.assertEqual((self.capture_path / "staged.patch").read_bytes(), staged)
        self.assertEqual((self.capture_path / "working.patch").read_bytes(), working)
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "working-tree/.git/index").read_bytes(), index_before)
        self.assertEqual((self.restore_path / "working-tree/binary.bin").read_bytes(), b"\x00\xffunstaged\x00")
        self.assertEqual((self.source / ".git/index").read_bytes(), index_before)

    def test_exact_inside_source_exclusion_preserves_previous_outputs(self):
        self.initialize_git()
        self.write("past-checkpoints/prior-evidence.txt", b"historical evidence preserved")
        self.capture_path = self.source / "new-exact-checkpoint"
        policy = self.policy()
        with self.assertRaisesRegex(tool.PreservationError, "exact active-output"):
            tool.capture(self.source, self.capture_path, policy)
        with self.assertRaisesRegex(tool.PreservationError, "exact active-output"):
            tool.capture(self.source, self.capture_path, policy, active_output_exclusion=self.source)
        captured = tool.capture(self.source, self.capture_path, policy, active_output_exclusion=self.capture_path)
        self.assertTrue(captured["complete"])
        manifest, inventory = tool.verify_checkpoint(self.capture_path, policy)
        names = [e["path"] for e in inventory["entries"]]
        self.assertIn("past-checkpoints/prior-evidence.txt", names)
        self.assertFalse(any(n.startswith("new-exact-checkpoint") for n in names))
        self.assertEqual(manifest["active_output_exclusion"], str(self.capture_path))

    def test_deleted_historical_path_cannot_be_excluded(self):
        self.initialize_git()
        old = self.write("reserved-output/old-user-work.txt", b"preserve historical work")
        self.fixture_command("add", "reserved-output/old-user-work.txt")
        self.fixture_command("commit", "-m", "historical destination fixture")
        # Only this disposable known file is removed to simulate the history gap.
        self.assertTrue(tool.inside(old.absolute(), self.area.absolute()))
        old.unlink()
        old.parent.rmdir()
        self.fixture_command("add", "-u")
        self.fixture_command("commit", "-m", "fixture records removal")
        self.capture_path = self.source / "reserved-output"
        with self.assertRaisesRegex(tool.PreservationError, "historical work"):
            tool.capture(self.source, self.capture_path, self.policy(), active_output_exclusion=self.capture_path)
        self.assertFalse(self.capture_path.exists())

    def test_unclassified_sqlite_is_pending_not_asserted_live(self):
        database = self.source / "disposable-fixture.sqlite"
        with sqlite3.connect(database) as connection:
            connection.execute("create table fixture (id integer)")
        captured = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(captured["complete"])
        self.assertEqual(captured["pending"][0]["classification"], "PROVENANCE_REQUIRED")
        self.assertEqual(captured["pending"][0]["contents"], "NOT_READ_OR_COPIED")
        with self.assertRaisesRegex(tool.PreservationError, "partial checkpoint"):
            tool.restore(self.capture_path, self.restore_path, self.policy())
        self.assertFalse(self.restore_path.exists())

    def test_exact_provenance_classified_sqlite_fixture_is_copied(self):
        database = self.source / "disposable-fixture.sqlite"
        with sqlite3.connect(database) as connection:
            connection.execute("create table fixture (id integer)")
            connection.execute("insert into fixture values (17)")
        classification = {"source_root": str(self.source), "path": database.name,
                          "kind": "fixture_database", "sha256": tool.sha(database.read_bytes()),
                          "evidence": "Created by this native test; isolated single-row disposable SQLite fixture."}
        policy = self.policy(classifications=[classification])
        self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])
        tool.restore(self.capture_path, self.restore_path, policy)
        recovered = self.restore_path / "working-tree" / database.name
        self.assertEqual(recovered.read_bytes(), database.read_bytes())
        with sqlite3.connect(recovered) as connection:
            self.assertEqual(connection.execute("select id from fixture").fetchall(), [(17,)])

    def test_windows_public_certificate_is_distinguished_from_private_key(self):
        certs = ssl.enum_certificates("ROOT")
        self.assertTrue(certs)
        der = next(data for data, encoding, _ in certs if encoding == "x509_asn")
        data = ssl.DER_cert_to_PEM_cert(der).encode("ascii")
        self.write("public-root.pem", data)
        classification = {"source_root": str(self.source), "path": "public-root.pem", "kind": "public_certificate",
                          "sha256": tool.sha(data), "evidence": "Public certificate exported from Windows ROOT by ssl.enum_certificates; no private-key API."}
        policy = self.policy(classifications=[classification])
        self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "working-tree/public-root.pem").read_bytes(), data)

    def test_certificate_bundle_standard_comments_preserve_original_bytes(self):
        certs = [data for data, encoding, _ in ssl.enum_certificates("ROOT") if encoding == "x509_asn"]
        self.assertTrue(certs)
        pem = ssl.DER_cert_to_PEM_cert(certs[0]).encode("ascii")
        data = b"# Public root bundle metadata\n\n" + pem + b"\n  # Standard inter-certificate comment\n\n" + pem + b"\n# End of public bundle\n"
        self.write("commented-bundle.pem", data)
        classification = {"source_root": str(self.source), "path": "commented-bundle.pem", "kind": "public_certificate",
                          "sha256": tool.sha(data), "evidence": "Public Windows ROOT bytes with standard bundle comments; original bytes retained."}
        policy = self.policy(classifications=[classification])
        tool.validate_public_certificate(data)
        self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "working-tree/commented-bundle.pem").read_bytes(), data)

    def test_certificate_comments_do_not_admit_private_markers_or_extraneous_text(self):
        der = next(data for data, encoding, _ in ssl.enum_certificates("ROOT") if encoding == "x509_asn")
        pem = ssl.DER_cert_to_PEM_cert(der).encode("ascii")
        for data in (b"# -----BEGIN PRIVATE KEY-----\n" + pem, pem + b"\nexecute-unreviewed-program\n",
                     b"-----BEGIN CERTIFICATE-----\nINVALID\n-----END CERTIFICATE-----\n"):
            with self.subTest(data=data[:40]), self.assertRaises(tool.PreservationError):
                tool.validate_public_certificate(data)

    def test_two_historical_sqlite_versions_use_exact_independent_classifications(self):
        self.initialize_git()
        database = self.source / "history-fixture.sqlite"
        versions, commits, classes = [], [], []
        for value in (11, 29):
            with sqlite3.connect(database) as connection:
                connection.execute("create table if not exists fixture (id integer)")
                connection.execute("delete from fixture")
                connection.execute("insert into fixture values (?)", (value,))
            data = database.read_bytes()
            versions.append(data)
            classes.append({"source_root": str(self.source), "path": database.name, "kind": "fixture_database",
                            "sha256": tool.sha(data), "evidence": f"Native disposable SQLite producer version with fixture id {value}."})
            self.fixture_command("add", database.name)
            self.fixture_command("commit", "-m", f"fixture DB version {value}")
            commits.append(self.fixture_command("rev-parse", "HEAD").decode().strip())
        self.assertNotEqual(versions[0], versions[1])
        policy = self.policy(classifications=classes)
        self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])
        tool.restore(self.capture_path, self.restore_path, policy)
        recovered = self.restore_path / "working-tree"
        for commit, data in zip(commits, versions):
            self.assertEqual(self.fixture_command("show", commit + ":" + database.name, root=recovered), data)
        self.assertEqual((recovered / database.name).read_bytes(), versions[-1])

    def test_historical_classification_cannot_authorize_changed_current_sqlite(self):
        database = self.source / "same-path.sqlite"
        with sqlite3.connect(database) as connection:
            connection.execute("create table fixture (id integer)")
        old_digest = tool.sha(database.read_bytes())
        with sqlite3.connect(database) as connection:
            connection.execute("insert into fixture values (41)")
        classification = {"source_root": str(self.source), "path": database.name, "kind": "fixture_database",
                          "sha256": old_digest, "evidence": "Old exact producer fixture; current changed bytes remain unclassified."}
        result = tool.capture(self.source, self.capture_path, self.policy(classifications=[classification]))
        self.assertFalse(result["complete"])
        self.assertEqual(result["pending"][0]["classification"], "EXACT_CURRENT_BYTES_PROVENANCE_REQUIRED")
        with zipfile.ZipFile(self.capture_path / "working-tree.zip") as archive:
            self.assertNotIn(database.name, archive.namelist())

    def test_git_process_environment_cannot_redirect_source_authority(self):
        self.initialize_git()
        foreign = self.area / "not-authorized-git-directory"
        foreign.mkdir()
        keeper = foreign / "owner-evidence.txt"
        keeper.write_text("separate fixture owner remains untouched")
        before = keeper.read_bytes()
        with patch.dict(os.environ, {"GIT_COMMON_DIR": str(foreign), "GIT_OBJECT_DIRECTORY": str(foreign),
                                    "GIT_NAMESPACE": "unrelated", "GIT_CONFIG": str(foreign / "not-authorized-config")}):
            policy = self.policy()
            self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual(keeper.read_bytes(), before)

    def test_private_key_marker_cannot_be_authorized_as_public_certificate(self):
        data = b"-----BEGIN PRIVATE KEY-----\nDISPOSABLE INVALID TEST MARKER\n-----END PRIVATE KEY-----\n"
        self.write("false-public.pem", data)
        classification = {"source_root": str(self.source), "path": "false-public.pem", "kind": "public_certificate",
                          "sha256": tool.sha(data), "evidence": "Deliberately false test classification; must reject transfer."}
        captured = tool.capture(self.source, self.capture_path, self.policy(classifications=[classification]))
        self.assertFalse(captured["complete"])
        self.assertEqual(captured["pending"][0]["classification"], "PRIVATE_KEY_MARKER_OBSERVED")
        with zipfile.ZipFile(self.capture_path / "working-tree.zip") as archive:
            self.assertNotIn("false-public.pem", archive.namelist())

    def test_unclassified_private_suffix_is_not_read_or_copied(self):
        key = self.write("fixture-secret.key", b"DISPOSABLE LOCATION: content must not be read")
        original = tool.hash_file
        def forbidden(path):
            self.assertNotEqual(path, key)
            return original(path)
        with patch.object(tool, "hash_file", side_effect=forbidden):
            captured = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(captured["complete"])
        self.assertEqual(captured["pending"][0]["contents"], "NOT_READ_OR_COPIED")

    def test_committed_private_key_marker_blocks_git_object_transfer(self):
        self.initialize_git()
        self.write("retained-unknown.txt", b"-----BEGIN PRIVATE KEY-----\nINVALID DISPOSABLE FIXTURE\n-----END PRIVATE KEY-----\n")
        self.fixture_command("add", "retained-unknown.txt")
        self.fixture_command("commit", "-m", "fixture secret marker")
        captured = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(captured["complete"])
        self.assertTrue(any(p.get("git_object") and p["kind"] == "private_key_candidate" for p in captured["pending"]))
        self.assertFalse((self.capture_path / "git-objects.pack").exists())

    def test_pending_staged_secret_cannot_escape_through_patch_artifacts(self):
        self.initialize_git()
        self.write("protected-candidate.key", b"-----BEGIN PRIVATE KEY-----\nINVALID DISPOSABLE STAGED MARKER\n-----END PRIVATE KEY-----\n")
        self.fixture_command("add", "protected-candidate.key")
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertFalse((self.capture_path / "working.patch").exists())
        self.assertFalse((self.capture_path / "staged.patch").exists())
        self.assertFalse((self.capture_path / "git-objects.pack").exists())
        inventory = tool.load_json(self.capture_path / "inventory.json")
        self.assertIsNone(inventory["git"]["working_patch_b64"])
        self.assertIsNone(inventory["git"]["staged_patch_b64"])
        self.assertEqual(inventory["git"]["diff_contents"], "WITHHELD_PENDING_SENSITIVE")
        self.assertIn("protected-candidate.key", inventory["git"]["protected_working_paths"])

    def test_missing_or_changed_declared_inputs_refuse_before_capture(self):
        path = self.write("must-have.txt", b"original declaration")
        with self.assertRaisesRegex(tool.PreservationError, "declared path is missing"):
            self.policy(declared_inputs=[{"path": str(self.source / "missing.txt"), "sha256": "0" * 64}])
        with self.assertRaisesRegex(tool.PreservationError, "hash differs"):
            self.policy(declared_inputs=[{"path": str(path), "sha256": "0" * 64}])
        self.assertFalse(self.capture_path.exists())

    def test_producer_pinned_invalid_marker_is_preserved_without_claiming_a_live_key(self):
        self.initialize_git()
        data = b"-----BEGIN PRIVATE KEY-----\nINVALID DISPOSABLE FIXTURE MARKER\n-----END PRIVATE KEY-----\n"
        path = self.write("invalid-fixture.key", data)
        self.fixture_command("add", "invalid-fixture.key")
        self.fixture_command("commit", "-m", "producer-owned invalid marker fixture")
        classification = {"source_root": str(self.source), "path": path.name, "kind": "fixture_secret_marker",
                          "sha256": tool.sha(data), "evidence": "This test's exact invalid text; contains no encoded key material."}
        policy = self.policy(classifications=[classification])
        captured = tool.capture(self.source, self.capture_path, policy)
        self.assertTrue(captured["complete"])
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "working-tree" / path.name).read_bytes(), data)

    def test_fixture_marker_cannot_authorize_encoded_private_material(self):
        data = b"-----BEGIN PRIVATE KEY-----\n" + base64.b64encode(b"\x30\x82" + bytes(range(128))) + b"\n-----END PRIVATE KEY-----\n"
        path = self.write("encoded-material.key", data)
        classification = {"source_root": str(self.source), "path": path.name, "kind": "fixture_secret_marker",
                          "sha256": tool.sha(data), "evidence": "False assertion of invalid marker; encoded material must refuse."}
        with self.assertRaisesRegex(tool.PreservationError, "potential private-key material"):
            tool.capture(self.source, self.capture_path, self.policy(classifications=[classification]))
        self.assertFalse((self.capture_path / "COMMITTED").exists())
        legacy = b"-----BEGIN RSA PRIVATE KEY-----\nProc-Type: 4,ENCRYPTED\nDEK-Info: AES-256-CBC,INVALID\n\n" + base64.b64encode(bytes(range(128))) + b"\n-----END RSA PRIVATE KEY-----\n"
        with self.assertRaisesRegex(tool.PreservationError, "potential private-key material"):
            tool.validate_fixture_marker(legacy)

    def test_existing_capture_and_restore_targets_are_never_overwritten(self):
        self.write("ordinary.txt")
        policy = self.policy()
        tool.capture(self.source, self.capture_path, policy)
        with self.assertRaisesRegex(tool.PreservationError, "already exists"):
            tool.capture(self.source, self.capture_path, policy)
        self.restore_path.mkdir()
        keeper = self.restore_path / "owner-note.txt"
        keeper.write_text("keep this")
        with self.assertRaisesRegex(tool.PreservationError, "already exists"):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual(keeper.read_text(), "keep this")

    def test_undeclared_source_destination_and_lexical_traversal_are_refused(self):
        self.write("ordinary.txt")
        policy = self.policy()
        with self.assertRaisesRegex(tool.PreservationError, "not explicitly authorized"):
            tool.capture(self.area, self.capture_path, policy)
        with self.assertRaisesRegex(tool.PreservationError, "not explicitly authorized"):
            tool.capture(self.source, self.area / "unapproved", policy)
        with self.assertRaisesRegex(tool.PreservationError, "parent traversal"):
            tool.capture(self.source / ".." / "source", self.capture_path, policy)
        self.assertFalse(self.capture_path.exists())

    def test_source_change_during_actual_copy_rejects_checkpoint(self):
        original = self.write("ordinary.txt", b"original source")
        operation = tool.add_file
        def mutate_after_copy(*args, **kwargs):
            operation(*args, **kwargs)
            original.write_bytes(b"changed source during native copy")
        with patch.object(tool, "add_file", side_effect=mutate_after_copy):
            with self.assertRaisesRegex(tool.PreservationError, "changed during capture"):
                tool.capture(self.source, self.capture_path, self.policy())
        self.assertTrue((self.capture_path / "FAILED.json").exists())
        self.assertFalse((self.capture_path / "COMMITTED").exists())

    def test_git_ref_change_during_capture_rejects_checkpoint(self):
        base = self.initialize_git()
        operation = tool.export_objects
        def mutate_after_export(*args):
            operation(*args)
            self.fixture_command("update-ref", "refs/heads/concurrent-fixture-change", base)
        with patch.object(tool, "export_objects", side_effect=mutate_after_export):
            with self.assertRaisesRegex(tool.PreservationError, "Git metadata changed"):
                tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse((self.capture_path / "COMMITTED").exists())

    def test_corrupt_archive_fails_before_restore_creates_output(self):
        self.write("ordinary.txt")
        policy = self.policy()
        tool.capture(self.source, self.capture_path, policy)
        with open(self.capture_path / "working-tree.zip", "ab") as stream:
            stream.write(b"unexpected append")
        with self.assertRaisesRegex(tool.PreservationError, "artifact differs"):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())
        self.assertFalse(list(self.area.glob("recovered.incomplete-*")))

    def test_unsafe_zip_member_rejects_even_if_seal_is_recomputed(self):
        self.write("ordinary.txt")
        policy = self.policy()
        tool.capture(self.source, self.capture_path, policy)
        with zipfile.ZipFile(self.capture_path / "working-tree.zip", "w") as archive:
            archive.writestr("../escape.txt", b"unsafe fixture")
        self.reseal()
        with self.assertRaisesRegex(tool.PreservationError, "membership differs"):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())
        self.assertFalse((self.area / "escape.txt").exists())

    def test_restore_failure_keeps_stage_and_retry_can_recover(self):
        self.write("ordinary.txt")
        policy = self.policy()
        tool.capture(self.source, self.capture_path, policy)
        with patch.object(tool, "extract_tree", side_effect=OSError("controlled disposable extraction failure")):
            with self.assertRaisesRegex(OSError, "extraction failure"):
                tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())
        stages = list(self.area.glob("recovered.incomplete-*"))
        self.assertEqual(len(stages), 1)
        self.assertTrue((stages[0] / "FAILED.json").exists())
        self.assertEqual(tool.restore(self.capture_path, self.restore_path, policy)["ordinary_files"], 1)

    def test_racing_restore_target_is_preserved_and_not_replaced(self):
        self.write("ordinary.txt")
        policy = self.policy()
        tool.capture(self.source, self.capture_path, policy)
        operation = tool.publish_new
        def create_racing_owner_target(stage, destination):
            destination.mkdir()
            (destination / "racing-owner-note.txt").write_text("preserve racing work")
            operation(stage, destination)
        with patch.object(tool, "publish_new", side_effect=create_racing_owner_target):
            with self.assertRaisesRegex(tool.PreservationError, "appeared during recovery"):
                tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "racing-owner-note.txt").read_text(), "preserve racing work")

    def test_native_junction_is_inert_and_never_traversed_or_recreated(self):
        external = self.area / "separate-owner-target"
        external.mkdir()
        (external / "must-not-copy.txt").write_text("separate owner contents")
        junction = self.source / "junction"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(external)], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr.decode(errors="replace"))
        self.write("ordinary.txt")
        policy = self.policy()
        captured = tool.capture(self.source, self.capture_path, policy)
        self.assertEqual(captured["reparse_entries"], 1)
        _, inventory = tool.verify_checkpoint(self.capture_path, policy)
        descriptor = next(e for e in inventory["entries"] if e["kind"] == "reparse")
        self.assertTrue(descriptor["descriptor"]["raw_descriptor_b64"])
        self.assertNotIn("junction/must-not-copy.txt", [e["path"] for e in inventory["entries"]])
        with self.assertRaisesRegex(tool.PreservationError, "inert-descriptor"):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())
        recovered = tool.restore(self.capture_path, self.restore_path, policy, allow_inert_reparse=True)
        self.assertFalse(tool.exists(self.restore_path / "working-tree/junction"))
        self.assertFalse(recovered["usable_links_restored"])
        self.assertEqual((external / "must-not-copy.txt").read_text(), "separate owner contents")

    def test_reparse_source_and_target_ancestors_are_refused(self):
        external = self.area / "external"
        external.mkdir()
        junction = self.area / "unsafe-parent"
        result = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(external)], capture_output=True)
        self.assertEqual(result.returncode, 0)
        with self.assertRaisesRegex(tool.PreservationError, "reparse path component"):
            self.policy(capture_targets=[str(junction / "capture")])
        with self.assertRaisesRegex(tool.PreservationError, "reparse path component"):
            self.policy(source_roots=[str(junction)])

    def test_shared_git_worktree_restores_without_source_pointer_dependency(self):
        base = self.initialize_git()
        other = self.area / "linked-worktree"
        self.fixture_command("worktree", "add", "-b", "linked-fixture", str(other), base)
        (other / "tracked.txt").write_bytes(b"linked dirty bytes\n")
        self.fixture_command("add", "tracked.txt", root=other)
        original = self.full_hashes()
        data = self.policy_data()
        data["source_roots"].append(str(other))
        policy = tool.Policy(data)
        tool.capture(other, self.capture_path, policy)
        restored = tool.restore(self.capture_path, self.restore_path, policy)
        recovered = self.restore_path / "working-tree"
        self.assertTrue((recovered / ".git").is_dir())
        self.assertEqual((recovered / "tracked.txt").read_bytes(), b"linked dirty bytes\n")
        self.assertFalse(tool.exists(recovered / ".git/commondir"))
        self.assertEqual(original, self.full_hashes())
        self.assertGreater(restored["original_refs"], 1)

    def test_custom_git_filters_fail_closed_before_execution(self):
        self.initialize_git()
        self.fixture_command("config", "filter.unreviewed.clean", "fixture-program-that-must-not-execute")
        with self.assertRaisesRegex(tool.PreservationError, "executable filters"):
            tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(self.capture_path.exists())

    def test_external_git_include_is_refused_before_reading_external_file(self):
        self.initialize_git()
        external = self.area / "external-config-must-not-be-read"
        self.fixture_command("config", "include.path", str(external))
        with self.assertRaisesRegex(tool.PreservationError, "Git includes"):
            tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(self.capture_path.exists())

    def test_alternate_object_directory_is_refused(self):
        self.initialize_git()
        alternatives = self.source / ".git/objects/info/alternates"
        tool.write_new(alternatives, (str(self.area / "outside-objects") + "\n").encode())
        with self.assertRaisesRegex(tool.PreservationError, "external object storage"):
            tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(self.capture_path.exists())

    def test_split_index_is_restored_with_required_shared_index(self):
        self.initialize_git()
        self.fixture_command("update-index", "--split-index")
        (self.source / "tracked.txt").write_bytes(b"split staged\n")
        self.fixture_command("add", "tracked.txt")
        (self.source / "tracked.txt").write_bytes(b"split final work\n")
        policy = self.policy()
        source_before = self.native_source_snapshot()
        tool.capture(self.source, self.capture_path, policy)
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual(source_before, self.native_source_snapshot())
        recovered = self.restore_path / "working-tree"
        self.assertTrue(list((recovered / ".git").glob("sharedindex.*")))
        self.assertEqual((recovered / "tracked.txt").read_bytes(), b"split final work\n")

    def test_corrupt_git_pack_cannot_publish_partial_restore(self):
        self.initialize_git()
        policy = self.policy()
        tool.capture(self.source, self.capture_path, policy)
        (self.capture_path / "git-objects.pack").write_bytes(b"corrupt native Git pack fixture")
        self.reseal()
        with self.assertRaisesRegex(tool.PreservationError, "independently restored"):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())
        stages = list(self.area.glob("recovered.incomplete-*"))
        self.assertEqual(len(stages), 1)
        self.assertTrue((stages[0] / "FAILED.json").exists())

    def test_sha256_git_object_format_is_recoverable(self):
        self.fixture_command("init", "--object-format=sha256", "--initial-branch=sha256-fixture")
        self.fixture_git = True
        self.fixture_command("config", "user.name", "CETA disposable sha256 fixture")
        self.fixture_command("config", "user.email", "fixture@example.invalid")
        self.write("tracked.txt", b"sha256 native Git fixture")
        self.fixture_command("add", "tracked.txt")
        self.fixture_command("commit", "-m", "sha256 fixture commit")
        head = self.fixture_command("rev-parse", "HEAD").decode().strip()
        self.assertEqual(len(head), 64)
        policy = self.policy()
        tool.capture(self.source, self.capture_path, policy)
        tool.restore(self.capture_path, self.restore_path, policy)
        recovered = self.restore_path / "working-tree"
        self.assertEqual(self.fixture_command("rev-parse", "HEAD", root=recovered).decode().strip(), head)
        self.assertEqual(self.fixture_command("rev-parse", "--show-object-format", root=recovered), b"sha256\n")

    def test_duplicate_json_keys_and_windows_unsafe_names_are_refused(self):
        duplicate = self.area / "duplicate.json"
        duplicate.write_text('{"schema_version": 1, "schema_version": 1}')
        with self.assertRaisesRegex(tool.PreservationError, "duplicate JSON key"):
            tool.load_json(duplicate)
        for name in ("../escape", "C:/escape", "file:alternate", "NUL", "COM1.txt", "trailing.", "trailing ", "a\\b"):
            with self.subTest(name=name), self.assertRaises(tool.PreservationError):
                tool.relative_name(name)

    def test_git_metadata_credential_url_is_pending_and_not_copied(self):
        self.initialize_git()
        self.fixture_command("config", "remote.fixture.url", "https://fixture-user:INVALID-DISPOSABLE-PASSWORD@example.invalid/repo.git")
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertTrue(any(e.get("classification") == "CREDENTIAL_URL_OBSERVED" for e in result["pending"]))
        with zipfile.ZipFile(self.capture_path / "git-common-metadata.zip") as archive:
            self.assertNotIn("config", archive.namelist())

    def test_unborn_git_worktree_is_preserved(self):
        self.fixture_command("init", "--initial-branch=unborn-fixture")
        self.fixture_git = True
        self.write("untracked.txt")
        policy = self.policy()
        tool.capture(self.source, self.capture_path, policy)
        result = tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual(result["git_objects"], 0)
        self.assertEqual((self.restore_path / "working-tree/untracked.txt").read_bytes(), b"fixture bytes\n")

    def test_cli_capture_verify_and_restore_use_explicit_policy(self):
        self.write("ordinary.txt")
        policy_path = self.area / "policy.json"
        policy_path.write_text(json.dumps(self.policy_data()))
        base = [sys.executable, "-B", str(CUT / "preserve_ceta_complete.py"), "--policy", str(policy_path)]
        for args, label in ((["capture", "--source", str(self.source), "--output", str(self.capture_path)], "CAPTURED_COMPLETE"),
                            (["verify", "--checkpoint", str(self.capture_path)], "VERIFIED_CAPTURE_ARTIFACTS"),
                            (["restore", "--checkpoint", str(self.capture_path), "--destination", str(self.restore_path)], "RESTORED_ORDINARY_BYTES_AND_INDEPENDENT_GIT")):
            completed = subprocess.run(base + args, capture_output=True)
            self.assertEqual(completed.returncode, 0, completed.stdout.decode() + completed.stderr.decode())
            self.assertEqual(json.loads(completed.stdout)["result"], label)


if __name__ == "__main__":
    unittest.main(verbosity=2)
