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
        connection.close()
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
            connection.close()
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
        source_before = self.native_source_snapshot()
        with self.assertRaisesRegex(tool.PreservationError, "pending sensitive.*before observation"):
            tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(self.capture_path.exists())
        self.assertEqual(source_before, self.native_source_snapshot())

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


    def assert_no_protected_outputs(self, protected, *, no_pack=True):
        """Inspect every generated output, including ZIP and encoded inventories."""
        needles = [protected] if isinstance(protected, bytes) else protected
        records, stack = [], [self.area]
        def inspect_bytes(payload, location):
            for needle in needles:
                self.assertNotIn(needle, payload, location)
        def inspect_json(value, location):
            if isinstance(value, dict):
                for key, item in value.items():
                    if key.endswith("_b64") and isinstance(item, str):
                        inspect_bytes(base64.b64decode(item, validate=True), location + ":" + key)
                    inspect_json(item, location)
            elif isinstance(value, list):
                for item in value:
                    inspect_json(item, location)
        while stack:
            directory = stack.pop()
            with os.scandir(tool.io_path(directory)) as listing:
                for entry in listing:
                    path = directory / entry.name
                    if tool.same_path(path, self.source):
                        continue
                    self.assertFalse(tool.reparse(entry.stat(follow_symlinks=False)))
                    if entry.is_dir(follow_symlinks=False):
                        stack.append(path)
                        continue
                    if no_pack:
                        self.assertFalse(path.suffix in {".pack", ".idx"}, str(path))
                    payload = tool.read_bytes(path)
                    inspect_bytes(payload, str(path))
                    if path.suffix == ".zip":
                        with zipfile.ZipFile(tool.io_path(path)) as archive:
                            for item in archive.infolist():
                                inspect_bytes(archive.read(item), str(path) + ":" + item.filename)
                    elif path.suffix == ".json":
                        inspect_json(json.loads(payload), str(path))
                    records.append({"path": str(path), "bytes": len(payload), "sha256": tool.sha(payload)})
        tool.write_json(self.area / ("protection-assertion-" + uuid.uuid4().hex[:8] + ".json"),
                        {"test": self._testMethodName, "source_root": str(self.source),
                         "source_snapshot_sha256": tool.sha(json.dumps(self.native_source_snapshot(), sort_keys=True).encode()),
                         "protected_sha256": [tool.sha(needle) for needle in needles],
                         "all_generated_locations_inspected": records,
                         "protected_bytes_absent": True, "independent_pack_absent": no_pack})

    def orphan_blob_tree(self, name, payload, *, commit=False):
        oid = self.fixture_command("hash-object", "-w", "--stdin", data=payload).decode().strip()
        tree = self.fixture_command("mktree", data=("100644 blob " + oid + "\t" + name + "\n").encode()).decode().strip()
        revision = None
        if commit:
            revision = self.fixture_command("commit-tree", tree, "-m", "unreferenced disposable preservation fixture").decode().strip()
        return oid, tree, revision

    def test_pr01_unreachable_commit_sensitive_path_never_enters_any_output(self):
        self.initialize_git()
        protected = b'{"fixture_token":"INVALID-DISPOSABLE-PR01-SECRET"}\n'
        oid, tree, commit = self.orphan_blob_tree("auth.json", protected, commit=True)
        self.assertNotIn(commit, self.fixture_command("rev-list", "--all", "--reflog").decode().splitlines())
        before = self.native_source_snapshot()
        policy = self.policy()
        result = tool.capture(self.source, self.capture_path, policy)
        self.assertFalse(result["complete"])
        self.assertTrue(any(e.get("git_object") == oid and e.get("path") == "auth.json" for e in result["pending"]))
        inventory = tool.load_json(self.capture_path / "inventory.json")
        self.assertTrue({oid, tree, commit}.issubset({e["oid"] for e in inventory["git"]["objects"]}))
        self.assertIn("auth.json", inventory["git"]["object_path_provenance"]["blobs"][oid])
        with self.assertRaisesRegex(tool.PreservationError, "partial checkpoint"):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr01_orphan_tree_without_commit_has_sensitive_path_provenance(self):
        self.initialize_git()
        protected = b'{"fixture":"INVALID-DISPOSABLE-ORPHAN-TREE-AUTH"}\n'
        oid, tree, _ = self.orphan_blob_tree("credentials.json", protected)
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertTrue(any(e.get("git_object") == oid and e.get("path") == "credentials.json" for e in result["pending"]))
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr01_index_only_sensitive_blob_has_exact_staged_path(self):
        self.initialize_git()
        protected = b'{"fixture":"INVALID-DISPOSABLE-INDEX-ONLY-AUTH"}\n'
        oid = self.fixture_command("hash-object", "-w", "--stdin", data=protected).decode().strip()
        self.fixture_command("update-index", "--add", "--cacheinfo", "100644," + oid + ",auth.json")
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertTrue(any(e.get("git_object") == oid and e.get("path") == "auth.json" for e in result["pending"]))
        inventory = tool.load_json(self.capture_path / "inventory.json")
        self.assertIsNone(inventory["git"]["staged_patch_b64"])
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr01_pathless_blob_is_retained_in_inventory_and_refused(self):
        self.initialize_git()
        protected = b"INVALID-DISPOSABLE-UNKNOWN-PATH-BLOB\n"
        oid = self.fixture_command("hash-object", "-w", "--stdin", data=protected).decode().strip()
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertTrue(any(e.get("git_object") == oid and e["kind"] == "unknown_path_provenance" for e in result["pending"]))
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr01_normal_orphan_tree_and_index_only_blob_restore_exactly(self):
        self.initialize_git()
        payload = b"ordinary unreferenced source revision\n"
        oid, tree, commit = self.orphan_blob_tree("ordinary.txt", payload, commit=True)
        staged = b"ordinary stage-only bytes\n"
        stage_oid = self.fixture_command("hash-object", "-w", "--stdin", data=staged).decode().strip()
        self.fixture_command("update-index", "--add", "--cacheinfo", "100644," + stage_oid + ",stage-only.txt")
        before = self.native_source_snapshot()
        policy = self.policy()
        self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])
        tool.restore(self.capture_path, self.restore_path, policy)
        recovered = self.restore_path / "working-tree"
        self.assertEqual(self.fixture_command("cat-file", "blob", oid, root=recovered), payload)
        self.assertEqual(self.fixture_command("cat-file", "blob", stage_oid, root=recovered), staged)
        self.assertEqual(self.fixture_command("cat-file", "-t", commit, root=recovered), b"commit\n")
        self.assertEqual(before, self.native_source_snapshot())

    def test_pr01_unreachable_historical_output_path_cannot_be_excluded(self):
        self.initialize_git()
        oid, tree, _ = self.orphan_blob_tree("reserved-orphan-output", b"ordinary historical preservation bytes")
        self.capture_path = self.source / "reserved-orphan-output"
        before = self.native_source_snapshot()
        with self.assertRaisesRegex(tool.PreservationError, "historical work"):
            tool.capture(self.source, self.capture_path, self.policy(), active_output_exclusion=self.capture_path)
        self.assertFalse(self.capture_path.exists())
        self.assertEqual(before, self.native_source_snapshot())

    def test_pr02_attributes_marker_is_refused_before_any_observation_copy(self):
        self.initialize_git()
        protected = b"# -----BEGIN PRIVATE KEY-----\n# INVALID-DISPOSABLE-ATTRIBUTES-SECRET\n"
        tool.write_new(self.source / ".git/info/attributes", protected)
        before = self.native_source_snapshot()
        with patch.object(tool, "create_read_view", wraps=tool.create_read_view) as observe:
            with self.assertRaisesRegex(tool.PreservationError, "pending sensitive.*before observation"):
                tool.capture(self.source, self.capture_path, self.policy())
            observe.assert_not_called()
        self.assertFalse(self.capture_path.exists())
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr02_exclude_and_unused_hook_are_classified_before_scratch(self):
        self.initialize_git()
        protected = b"# -----BEGIN PRIVATE KEY-----\n# INVALID-DISPOSABLE-UNCONSULTED-METADATA\n"
        tool.write_new(self.source / ".git/info/exclude.private-fixture", protected)
        tool.write_new(self.source / ".git/hooks/unused-private-fixture", protected)
        before = self.native_source_snapshot()
        target = self.area / "direct-index-observation"
        with self.assertRaisesRegex(tool.PreservationError, "pending sensitive.*before observation"):
            tool.create_read_view(self.source, self.policy(), target)
        self.assertFalse(target.exists())
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr02_metadata_mutation_is_rejected_before_protected_archive_write(self):
        self.initialize_git()
        path = self.source / ".git/info/attributes"
        safe = b"# safe fixture attributes\n"
        protected = b"# -----BEGIN PRIVATE KEY-----\n# INVALID-DISPOSABLE-MUTATION-SECRET\n"
        tool.write_new(path, safe)
        original = tool.snapshot
        def mutate_after_snapshot(*args, **kwargs):
            value = original(*args, **kwargs)
            path.write_bytes(protected)
            return value
        with patch.object(tool, "snapshot", side_effect=mutate_after_snapshot):
            with self.assertRaisesRegex(tool.PreservationError, "metadata identity changed|metadata bytes changed"):
                tool.capture(self.source, self.capture_path, self.policy())
        self.assertTrue((self.capture_path / "FAILED.json").exists())
        self.assertEqual(path.read_bytes(), protected)
        self.assert_no_protected_outputs(protected)

    def protected_tag(self, reachable):
        base = self.initialize_git()
        protected = b"-----BEGIN PRIVATE KEY-----\nINVALID-DISPOSABLE-TAG-MESSAGE\n-----END PRIVATE KEY-----\n"
        data = ("object " + base + "\ntype commit\ntag private-fixture\ntagger Disposable Fixture <fixture@example.invalid> 1700000000 +0000\n\n").encode() + protected
        oid = self.fixture_command("mktag", data=data).decode().strip()
        if reachable:
            self.fixture_command("update-ref", "refs/tags/private-fixture", oid)
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertTrue(any(e.get("git_object") == oid and e.get("object_type") == "tag" for e in result["pending"]))
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr03_reachable_annotated_tag_marker_never_enters_any_output(self):
        self.protected_tag(True)

    def test_pr03_unreachable_annotated_tag_marker_never_enters_any_output(self):
        self.protected_tag(False)

    def protected_commit(self, reachable):
        base = self.initialize_git()
        tree = self.fixture_command("rev-parse", base + "^{tree}").decode().strip()
        protected = b"-----BEGIN PRIVATE KEY-----\nINVALID-DISPOSABLE-COMMIT-MESSAGE\n-----END PRIVATE KEY-----\n"
        oid = self.fixture_command("commit-tree", tree, "-p", base, data=protected).decode().strip()
        if reachable:
            self.fixture_command("update-ref", "refs/heads/private-message-fixture", oid)
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertTrue(any(e.get("git_object") == oid and e.get("object_type") == "commit" for e in result["pending"]))
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr03_reachable_commit_marker_never_enters_any_output(self):
        self.protected_commit(True)

    def test_pr03_unreachable_commit_marker_never_enters_any_output(self):
        self.protected_commit(False)

    def test_pr03_tree_path_marker_is_refused_without_diagnostic_disclosure(self):
        self.initialize_git()
        protected = b"-----BEGIN PRIVATE KEY-----"
        self.orphan_blob_tree(protected.decode(), b"ordinary bytes behind protected path")
        before = self.native_source_snapshot()
        with self.assertRaisesRegex(tool.PreservationError, "tree path requires protected provenance"):
            tool.capture(self.source, self.capture_path, self.policy())
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr03_tag_credential_url_is_scanned_beyond_first_sample(self):
        base = self.initialize_git()
        protected = b"https://fixture:INVALID-DISPOSABLE-TAG-URL@example.invalid/repo"
        data = ("object " + base + "\ntype commit\ntag url-fixture\ntagger Disposable Fixture <fixture@example.invalid> 1700000000 +0000\n\n").encode()
        data += b"ordinary tag message\n" * 300 + protected + b"\n"
        oid = self.fixture_command("mktag", data=data).decode().strip()
        self.fixture_command("update-ref", "refs/tags/url-fixture", oid)
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertTrue(any(e.get("git_object") == oid and e["kind"] == "credential_url_candidate" for e in result["pending"]))
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr04_config_credential_after_four_mib_is_refused_before_any_copy(self):
        self.initialize_git()
        config = self.source / ".git/config"
        protected = b"https://fixture-user:INVALID-DISPOSABLE-UNCHECKED-TAIL@example.invalid/repo.git"
        data = config.read_bytes() + b"\n# harmless disposable comment\n" * 150000
        data += b'\n[remote "fixture-tail"]\n\turl = ' + protected + b"\n"
        self.assertGreater(data.index(protected), 4 * tool.BLOCK)
        config.write_bytes(data)
        before = self.native_source_snapshot()
        with self.assertRaisesRegex(tool.PreservationError, "pending sensitive.*before observation"):
            tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(self.capture_path.exists())
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr04_netrc_credential_after_four_mib_never_enters_output(self):
        protected = b"https://fixture-user:INVALID-DISPOSABLE-NETRC-TAIL@example.invalid/repo"
        self.write(".netrc", b"# harmless disposable line\n" * 175000 + protected + b"\n")
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertEqual(result["pending"][0]["classification"], "CREDENTIAL_URL_OBSERVED")
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr04_native_credentials_cross_chunks_and_unbounded_authority(self):
        credentials = [b"https://fixture-user:INVALID-DISPOSABLE-BOUNDARY@example.invalid/repo",
                       b"https://fixture-user:" + b"INVALID-DISPOSABLE-" * 70000 + b"@example.invalid/repo"]
        for index, (protected, offset) in enumerate(((credentials[0], tool.BLOCK - 6),
                                                    (credentials[0], tool.BLOCK - 20),
                                                    (credentials[1], tool.BLOCK - 12))):
            self.write("credential-boundary-" + str(index) + ".txt", b" " * offset + protected + b"\n")
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["pending"]), 3)
        self.assertTrue(all(e["classification"] == "CREDENTIAL_URL_OBSERVED" for e in result["pending"]))
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(credentials)

    def test_pr04_large_public_config_and_port_url_remain_exactly_recoverable(self):
        self.initialize_git()
        config = self.source / ".git/config"
        data = config.read_bytes() + b"\n# harmless public fixture comment\n" * 140000
        data += b'\n[remote "public-fixture"]\n\turl = https://example.invalid:8443/repository.git\n'
        self.assertGreater(len(data), 4 * tool.BLOCK)
        config.write_bytes(data)
        before = self.native_source_snapshot()
        policy = self.policy()
        self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])
        tool.restore(self.capture_path, self.restore_path, policy)
        recovered = self.restore_path / "preservation-metadata/original-git-common/config"
        self.assertEqual(recovered.read_bytes(), data)
        self.assertEqual(before, self.native_source_snapshot())


    def test_pr05_changed_same_identity_bytes_are_rejected_before_any_archive_member(self):
        payload = b"-----BEGIN PRIVATE KEY-----\nINVALID-DISPOSABLE-PRE-COPY\n-----END PRIVATE KEY-----\n"
        path = self.write("ordinary.txt", b"x" * len(payload))
        original_open = tool.open_source
        mutated = []

        @tool.contextmanager
        def mutate_before_lease(candidate, *, exclusive=False):
            if candidate == path and exclusive and not mutated:
                prior = tool.lstat(path)
                with open(tool.io_path(path), "wb") as changed:
                    changed.write(payload)
                os.utime(tool.io_path(path), ns=(prior.st_atime_ns, prior.st_mtime_ns))
                mutated.append(True)
            with original_open(candidate, exclusive=exclusive) as stream:
                yield stream

        with patch.object(tool, "open_source", mutate_before_lease):
            with self.assertRaisesRegex(tool.PreservationError, "before immutable copy admission"):
                tool.capture(self.source, self.capture_path, self.policy())
        self.assertEqual(mutated, [True])
        self.assertTrue((self.capture_path / "FAILED.json").exists())
        self.assertFalse((self.capture_path / "COMMITTED").exists())
        with zipfile.ZipFile(self.capture_path / "working-tree.zip") as archive:
            self.assertNotIn("ordinary.txt", archive.namelist())
        self.assert_no_protected_outputs(payload)

    def test_pr05_native_writer_and_delete_are_denied_through_copy_and_handle_is_released(self):
        payload = b"ordinary approved bytes\n" * 100000
        path = self.write("ordinary.txt", payload)
        protected = b"-----BEGIN PRIVATE KEY-----\nINVALID-DISPOSABLE-MID-COPY\n"
        before = self.native_source_snapshot()
        original_archive_open = zipfile.ZipFile.open
        rejected = []

        def attempt_native_mutations(archive, name, mode="r", *args, **kwargs):
            if name == "ordinary.txt" and mode == "w":
                with self.assertRaises(OSError):
                    with open(tool.io_path(path), "wb") as writer:
                        writer.write(protected)
                with self.assertRaises(OSError):
                    os.unlink(tool.io_path(path))
                rejected.extend(("write", "delete"))
            return original_archive_open(archive, name, mode, *args, **kwargs)

        policy = self.policy()
        with patch.object(zipfile.ZipFile, "open", attempt_native_mutations):
            result = tool.capture(self.source, self.capture_path, policy)
        self.assertTrue(result["complete"])
        self.assertEqual(rejected, ["write", "delete"])
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual(tool.read_bytes(self.restore_path / "working-tree/ordinary.txt"), payload)
        with open(tool.io_path(path), "r+b") as released:
            released.write(b"released")
        self.assertTrue(tool.read_bytes(path).startswith(b"released"))

    def test_pr05_existing_native_writer_refuses_before_copy_and_fresh_recovery_succeeds(self):
        payload = b"ordinary approved writer-sharing fixture\n"
        path = self.write("ordinary.txt", payload)
        with open(tool.io_path(path), "r+b"):
            with self.assertRaisesRegex(tool.PreservationError, "cannot open ordinary source"):
                tool.capture(self.source, self.capture_path, self.policy())
        self.assertTrue((self.capture_path / "FAILED.json").exists())
        self.assertFalse((self.capture_path / "COMMITTED").exists())
        with zipfile.ZipFile(self.capture_path / "working-tree.zip") as archive:
            self.assertNotIn("ordinary.txt", archive.namelist())
        self.capture_path = self.area / "fresh-after-writer-release"
        policy = self.policy()
        self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual(tool.read_bytes(self.restore_path / "working-tree/ordinary.txt"), payload)

    def test_pr06_token_only_config_userinfo_refuses_before_observation_copy(self):
        self.initialize_git()
        protected = b"https://INVALID-DISPOSABLE-TOKEN@example.invalid/repo.git"
        config = self.source / ".git/config"
        config.write_bytes(config.read_bytes() + b'\n[remote "fixture-token"]\n\turl = ' + protected + b"\n")
        before = self.native_source_snapshot()
        with self.assertRaisesRegex(tool.PreservationError, "pending sensitive.*before observation"):
            tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(self.capture_path.exists())
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr06_token_only_userinfo_crosses_chunks_and_unbounded_authority(self):
        protected_values = [b"https://INVALID-DISPOSABLE-TOKEN@example.invalid/repo",
                            b"https://" + b"INVALID-DISPOSABLE-" * 70000 + b"@example.invalid/repo"]
        for index, (payload, offset) in enumerate(((protected_values[0], tool.BLOCK - 6),
                                                 (protected_values[0], 4 * tool.BLOCK + 100),
                                                 (protected_values[1], tool.BLOCK - 10))):
            self.write("token-" + str(index) + ".txt", b" " * offset + payload + b"\n")
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["pending"]), 3)
        self.assertTrue(all(entry["classification"] == "CREDENTIAL_URL_OBSERVED" for entry in result["pending"]))
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected_values)

    def test_pr06_token_only_annotated_tag_is_withheld_from_pack(self):
        base = self.initialize_git()
        protected = b"https://INVALID-DISPOSABLE-TAG-TOKEN@example.invalid/repo"
        data = ("object " + base + "\ntype commit\ntag token-fixture\ntagger Disposable Fixture <fixture@example.invalid> 1700000000 +0000\n\n").encode()
        oid = self.fixture_command("mktag", data=data + protected + b"\n").decode().strip()
        self.fixture_command("update-ref", "refs/tags/token-fixture", oid)
        before = self.native_source_snapshot()
        result = tool.capture(self.source, self.capture_path, self.policy())
        self.assertFalse(result["complete"])
        self.assertTrue(any(entry.get("git_object") == oid and entry["kind"] == "credential_url_candidate" for entry in result["pending"]))
        self.assertFalse((self.capture_path / "git-objects.pack").exists())
        self.assertEqual(before, self.native_source_snapshot())
        self.assert_no_protected_outputs(protected)

    def test_pr06_public_ports_path_query_and_fragment_at_signs_restore_exactly(self):
        payload = (b"https://example.invalid:8443/repository\n"
                   b"https://example.invalid/path/user@example.invalid\n"
                   b"https://example.invalid?mail=user@example.invalid\n"
                   b"https://example.invalid#user@example.invalid\n")
        self.write("public.txt", payload)
        before = self.native_source_snapshot()
        policy = self.policy()
        self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual(tool.read_bytes(self.restore_path / "working-tree/public.txt"), payload)
        self.assertEqual(before, self.native_source_snapshot())


if __name__ == "__main__":
    unittest.main(verbosity=2)
