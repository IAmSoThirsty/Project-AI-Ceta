"""HP3 predicates and recovery through actual owned Windows files/Git resources.

Synthetic proof documents receive a test-only patched anchor. They establish
parser behavior, never publication provenance or real CETA source admission.
The production anchor cannot be overridden by policy or command-line input.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import marshal
import os
from pathlib import Path
import struct
import sys
import unittest
from unittest.mock import patch
import zipfile

import preserve_ceta_complete as tool
import test_preserve_ceta_complete as native


URI = b"https" + b"://" + b"fixture-user:fixture-password" + b"@example.invalid/path"
MARKER = b"-----BEGIN " + b"PRIVATE KEY-----"


class ProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native.PreservationTests.setUpClass.__func__(cls)

    def setUp(self):
        native.PreservationTests.setUp(self)
        self.bundle = self.area / "proof"
        self.bundle.mkdir()
        self.snapshot_path = self.area / "frozen-inventory.json"
        self.anchor_patch = None

    write = native.PreservationTests.write
    policy_data = native.PreservationTests.policy_data
    fixture_command = native.PreservationTests.fixture_command
    initialize_git = native.PreservationTests.initialize_git

    def literal_source(self, owner="test_bound_literal", *, suffix=b""):
        return ("def " + owner + "():\n    value = " + repr(URI.decode()) + "\n    return value\n").encode() + suffix

    def pyc(self, source, *, trailing=b"", body=None):
        code = compile(source, "<synthetic-generator>", "exec", dont_inherit=True, optimize=0)
        return importlib.util.MAGIC_NUMBER + struct.pack("<III", 0, 100, len(source)) + (marshal.dumps(code) if body is None else body) + trailing

    def specimen(self, identity, kind, name, payload, *, classification=None, oid=None, aliases=None, generator=None):
        classes = {"public_wheel_member": "PUBLISHED_PYTHON_SYNTAX_OR_DOCUMENTATION_LITERAL",
                   "owned_test_literal": "VERSION_SPECIFIC_TEST_FIXTURE_LITERAL" if oid else "OWNED_TEST_FIXTURE_LITERAL",
                   "generated_cache": "HISTORICAL_SOURCE_EQUIVALENT_GENERATED_CACHE" if generator and generator.get("git_oid") else "CURRENT_SOURCE_EQUIVALENT_GENERATED_CACHE"}
        entry = {"entry_id": identity, "kind": kind, "source_root": str(self.source), "sha256": tool.sha(payload)}
        entry.update({"git_oid": oid, "aliases": aliases} if oid else {"path": name})
        record = {"entry_id": identity, "kind": "historical" if oid else "working", "path": None if oid else name,
                  "git_oid": oid, "whole_file_sha256": tool.sha(payload), "bytes": len(payload),
                  "classification": classification or classes[kind], "source_positions": tool.protected_positions(payload)}
        return {"entry": entry, "record": record, "payload": payload, "generator": generator}

    def proof_policy(self, specimens, *, trust_fixture=True, mutate=None):
        """Only this test patches trust; production receives no such parameter."""
        aliases = {}
        if self.fixture_git:
            base = tool.Policy(self.policy_data())
            view = tool.create_read_view(self.source, base, self.area / "proof-index-view")
            aliases = tool.git_state(self.source, base, view=view)["object_path_provenance"]["blobs"]
        inventory = {"source_root": str(self.source), "git": {"object_path_provenance": {"blobs": aliases}}}
        inventory_bytes = tool.canonical_proof(inventory)
        self.snapshot_path.write_bytes(inventory_bytes)
        records = [copy.deepcopy(s["record"]) for s in specimens]
        fillers = [{"entry_id": "held-" + str(i), "classification": "LEGACY_CACHE_GENERATOR_UNRESOLVED"}
                   for i in range(69 - len(records))]
        evidence = {"upstream-artifact-comparison-r1.json": {"groups": []},
                    "format-context-followup-r2.json": {"pyc": [], "source_support_before_after": {}},
                    "historical-cache-generator-links-r1.json": {"entries": []}}
        for specimen in specimens:
            entry, record, generator = specimen["entry"], specimen["record"], specimen["generator"]
            if entry["kind"] == "public_wheel_member":
                item = {"id": entry["entry_id"], "local_source_path": entry["path"], "whole_file_match": True,
                        "local_whole_file_sha256": entry["sha256"], "wheel_member_sha256": entry["sha256"],
                        "local_bytes": record["bytes"], "wheel_member_bytes": record["bytes"], "wheel_member": entry["path"]}
                evidence["upstream-artifact-comparison-r1.json"]["groups"].append({"artifact_hash_matches_pypi": True,
                    "all_target_members_match": True, "downloaded_bytes": 100,
                    "pypi_json_url": "https://pypi.org/pypi/explicit-test-double/1/json",
                    "artifact": {"filename": "explicit-test-double.whl", "sha256": "a" * 64, "size": 100,
                                 "url": "https://files.pythonhosted.org/packages/explicit-test-double.whl"}, "entries": [item]})
            if generator:
                cache = {"id": entry["entry_id"], "sha256": entry["sha256"], "marshal_all_body_consumed": True,
                         "all_structural_code_fields_and_constants_equal": not generator.get("git_oid"),
                         "associated_source": generator["path"], "associated_source_sha256": tool.sha(generator["payload"]),
                         "interpreter": generator.get("interpreter", sys.version), "magic_hex": importlib.util.MAGIC_NUMBER.hex()}
                evidence["format-context-followup-r2.json"]["pyc"].append(cache)
                if generator.get("git_oid"):
                    evidence["historical-cache-generator-links-r1.json"]["entries"].append({"entry_id": entry["entry_id"],
                        "pyc_sha256": entry["sha256"], "exact_historical_structural_matches": [{"git_oid": generator["git_oid"],
                        "header_source_size_match": True, "source_sha256": tool.sha(generator["payload"]), "source_bytes": len(generator["payload"])}]})
                else:
                    evidence["format-context-followup-r2.json"]["source_support_before_after"][str(self.source / generator["path"])] = {
                        "sha256": tool.sha(generator["payload"]), "bytes": len(generator["payload"])}
        report = {"schema_version": 1, "held_count": 69, "admitted_count": 0, "approved_source_root": str(self.source),
                  "entries": records + fillers, "sealed_HP1_checkpoint_current_hashes": {"inventory_sha256": tool.sha(inventory_bytes)}, "evidence": {}}
        if mutate:
            mutate(report, evidence)
        for name, value in evidence.items():
            raw = tool.canonical_proof(value)
            (self.bundle / name).write_bytes(raw)
            report["evidence"][name] = {"sha256": tool.sha(raw)}
        raw = tool.canonical_proof(report)
        (self.bundle / "HP2-FINAL-REPORT.json").write_bytes(raw)
        digest = tool.sha(raw)
        if trust_fixture:
            self.anchor_patch = patch.object(tool, "TRUSTED_PROVENANCE_REPORT_SHA256", digest)
            self.anchor_patch.start()
            self.addCleanup(self.anchor_patch.stop)
        data = self.policy_data()
        data["content_provenance"] = {"proof_bundle": str(self.bundle), "snapshot_inventory": str(self.snapshot_path),
                                     "report_sha256": digest, "entries": [copy.deepcopy(s["entry"]) for s in specimens]}
        return data

    def complete_capture(self, data):
        policy = tool.Policy(data)
        manifest = tool.capture(self.source, self.capture_path, policy)
        self.assertTrue(manifest["complete"])
        self.assertEqual(manifest["pending"], [])
        return policy

    def reseal_inventory(self, edit):
        inventory = json.loads((self.capture_path / "inventory.json").read_text())
        edit(inventory)
        (self.capture_path / "inventory.json").write_bytes(tool.canonical_proof(inventory))
        manifest = json.loads((self.capture_path / "checkpoint.json").read_text())
        for artifact in manifest["artifacts"]:
            artifact["bytes"], artifact["sha256"], _ = tool.hash_file(self.capture_path / artifact["path"])
        (self.capture_path / "checkpoint.json").write_bytes(tool.canonical_proof(manifest))
        (self.capture_path / "COMMITTED").write_text(tool.sha((self.capture_path / "checkpoint.json").read_bytes()) + "\n")

    def test_exact_owned_test_literal_native_capture_and_restore(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        data = self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)])
        policy = self.complete_capture(data)
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "working-tree/tests/test_example.py").read_bytes(), body)
        self.assertEqual((self.source / "tests/test_example.py").read_bytes(), body)

    def test_unclassified_current_candidate_is_partial_and_cannot_restore(self):
        self.write("unknown.txt", URI)
        policy = tool.Policy(self.policy_data())
        manifest = tool.capture(self.source, self.capture_path, policy)
        self.assertFalse(manifest["complete"])
        with zipfile.ZipFile(self.capture_path / "working-tree.zip") as archive:
            self.assertEqual(archive.namelist(), [])
        with self.assertRaises(tool.PreservationError):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())

    def test_fabricated_reviewed_public_proof_has_no_production_trust(self):
        body = b"# " + URI + b"\n"
        self.write("library.py", body)
        data = self.proof_policy([self.specimen("W014", "public_wheel_member", "library.py", body)], trust_fixture=False)
        data["reviewed"] = True
        with self.assertRaises(tool.PreservationError):
            tool.Policy(data)
        self.assertFalse(self.capture_path.exists())

    def test_exact_published_python_pattern_fixture_roundtrip(self):
        body = b'"""' + URI + b'"""\n'
        self.write("library.py", body)
        policy = self.complete_capture(self.proof_policy([self.specimen("W014", "public_wheel_member", "library.py", body)]))
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "working-tree/library.py").read_bytes(), body)

    def test_public_record_without_independent_wheel_equality_is_refused(self):
        body = b"# " + URI + b"\n"
        self.write("library.py", body)
        def invalidate(report, evidence):
            evidence["upstream-artifact-comparison-r1.json"]["groups"][0]["artifact_hash_matches_pypi"] = False
        data = self.proof_policy([self.specimen("W014", "public_wheel_member", "library.py", body)], mutate=invalidate)
        with self.assertRaises(tool.PreservationError):
            tool.Policy(data)

    def test_stale_public_proof_hash_is_refused_before_capture(self):
        body = b"# " + URI + b"\n"
        self.write("library.py", body)
        data = self.proof_policy([self.specimen("W014", "public_wheel_member", "library.py", body)])
        path = self.bundle / "upstream-artifact-comparison-r1.json"
        path.write_bytes(path.read_bytes() + b" ")
        with self.assertRaises(tool.PreservationError):
            tool.Policy(data)
        self.assertFalse(self.capture_path.exists())

    def test_absent_or_malformed_binding_is_refused(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        original = self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)])
        changes = [{"proof_bundle": str(self.area / "missing-proof")}, {"entries": "untyped"}, {"report_sha256": "0" * 64}]
        for change in changes:
            data = copy.deepcopy(original)
            data["content_provenance"].update(change)
            with self.subTest(field=next(iter(change))), self.assertRaises(tool.PreservationError):
                tool.Policy(data)

    def test_restore_refuses_proof_drift_after_completed_capture(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        policy = self.complete_capture(self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)]))
        target = self.bundle / "HP2-FINAL-REPORT.json"
        target.write_bytes(target.read_bytes() + b" ")
        with self.assertRaises(tool.PreservationError):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())

    def test_bound_byte_drift_is_held(self):
        body = self.literal_source()
        target = self.write("tests/test_example.py", body)
        data = self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)])
        target.write_bytes(body + b"# drift\n")
        manifest = tool.capture(self.source, self.capture_path, tool.Policy(data))
        self.assertFalse(manifest["complete"])
        with zipfile.ZipFile(self.capture_path / "working-tree.zip") as archive:
            self.assertEqual(archive.namelist(), [])

    def test_path_root_whole_hash_and_object_mismatch_are_refused(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        original = self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)])
        mutations = [lambda e: e.update(path="other.py"), lambda e: e.update(source_root=str(self.area)),
                     lambda e: e.update(sha256="0" * 64), lambda e: (e.pop("path"), e.update(git_oid="0" * 40, aliases=["tests/test_example.py"]))]
        for mutate in mutations:
            data = copy.deepcopy(original)
            mutate(data["content_provenance"]["entries"][0])
            with self.subTest(mutation=mutations.index(mutate)), self.assertRaises(tool.PreservationError):
                tool.Policy(data)

    def test_duplicate_entry_and_malformed_position_binding_are_refused(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        data = self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)])
        data["content_provenance"]["entries"].append(copy.deepcopy(data["content_provenance"]["entries"][0]))
        with self.assertRaises(tool.PreservationError):
            tool.Policy(data)
        with self.assertRaises(tool.PreservationError):
            tool.position_binding({"private_markers": [], "userinfo": [{"scheme_separator_offset": True, "at_offset": 10}]})
        for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b'[]']:
            with self.assertRaises(tool.PreservationError):
                tool.strict_proof_json(raw)

    def test_added_uri_position_cannot_be_authorized_by_matching_hash_alone(self):
        body = self.literal_source(suffix=b"# " + URI + b"\n")
        self.write("tests/test_example.py", body)
        specimen = self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)
        specimen["record"]["source_positions"]["userinfo"].pop()
        manifest = tool.capture(self.source, self.capture_path, tool.Policy(self.proof_policy([specimen])))
        self.assertFalse(manifest["complete"])

    def test_owned_literal_outside_test_function_is_held(self):
        body = self.literal_source(owner="ordinary_runtime")
        self.write("tests/test_example.py", body)
        manifest = tool.capture(self.source, self.capture_path,
                                tool.Policy(self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)])))
        self.assertFalse(manifest["complete"])

    def test_encoded_private_payload_is_refused_even_in_published_fixture(self):
        import base64
        encoded = MARKER + b"\n" + base64.b64encode(bytes(range(64))) + b"\n-----END PRIVATE KEY-----"
        body = b"VALUE = " + repr(encoded).encode() + b"\n"
        self.write("library.py", body)
        specimen = self.specimen("W011", "public_wheel_member", "library.py", body,
                                  classification="PUBLISHED_FORMAT_MARKER_P4_VALIDATED")
        manifest = tool.capture(self.source, self.capture_path, tool.Policy(self.proof_policy([specimen])))
        self.assertFalse(manifest["complete"])

    def test_new_private_marker_position_is_held(self):
        body = self.literal_source(suffix=b"VALUE = " + repr(MARKER).encode() + b"\n")
        self.write("tests/test_example.py", body)
        specimen = self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)
        specimen["record"]["source_positions"]["private_markers"] = []
        manifest = tool.capture(self.source, self.capture_path, tool.Policy(self.proof_policy([specimen])))
        self.assertFalse(manifest["complete"])

    def test_proof_drift_before_immutable_copy_refuses_all_members(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        policy = tool.Policy(self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)]))
        original = tool.archive_tree
        def changed(*args, **kwargs):
            if args[0].name == "working-tree.zip":
                target = self.bundle / "HP2-FINAL-REPORT.json"
                target.write_bytes(target.read_bytes() + b" ")
            return original(*args, **kwargs)
        with patch.object(tool, "archive_tree", side_effect=changed), self.assertRaises(tool.PreservationError):
            tool.capture(self.source, self.capture_path, policy)
        with zipfile.ZipFile(self.capture_path / "working-tree.zip") as archive:
            self.assertEqual(archive.namelist(), [])
        self.assertFalse((self.capture_path / "COMMITTED").exists())

    def test_generated_cache_preserves_generator_and_never_executes_it(self):
        marker = self.area / "must-not-be-created"
        source = self.literal_source(suffix=("open(" + repr(str(marker)) + ", 'x').write('unwanted execution')\n").encode())
        cache = self.pyc(source)
        self.write("tests/test_generator.py", source)
        self.write("cache.pyc", cache)
        specimens = [self.specimen("W050", "owned_test_literal", "tests/test_generator.py", source),
                     self.specimen("W047", "generated_cache", "cache.pyc", cache, generator={"path": "tests/test_generator.py", "payload": source})]
        policy = self.complete_capture(self.proof_policy(specimens))
        self.assertTrue((self.capture_path / "provenance-generators.zip").is_file())
        self.assertFalse(marker.exists())
        (self.source / "tests/test_generator.py").write_bytes(b"changed after completed capture\n")
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "working-tree/cache.pyc").read_bytes(), cache)
        self.assertEqual((self.restore_path / "working-tree/tests/test_generator.py").read_bytes(), source)
        self.assertFalse(marker.exists())

    def cache_policy(self, *, cache_change=None, generator_change=None, interpreter=None):
        source = self.literal_source()
        cache = self.pyc(source)
        if cache_change:
            cache = cache_change(cache)
        self.write("tests/test_generator.py", source)
        self.write("cache.pyc", cache)
        generator = {"path": "tests/test_generator.py", "payload": source}
        if interpreter:
            generator["interpreter"] = interpreter
        specimens = [self.specimen("W050", "owned_test_literal", "tests/test_generator.py", source),
                     self.specimen("W047", "generated_cache", "cache.pyc", cache, generator=generator)]
        data = self.proof_policy(specimens)
        if generator_change:
            (self.source / "tests/test_generator.py").write_bytes(generator_change(source))
        return tool.Policy(data)

    def test_cache_extra_marshal_bytes_are_refused(self):
        policy = self.cache_policy(cache_change=lambda c: c + b"trailing marshal content")
        self.assertFalse(tool.capture(self.source, self.capture_path, policy)["complete"])

    def test_cache_protected_filename_is_refused_despite_equal_code_shape(self):
        code = compile(self.literal_source(), URI.decode(), "exec", dont_inherit=True, optimize=0)
        policy = self.cache_policy(cache_change=lambda c: c[:16] + marshal.dumps(code))
        self.assertFalse(tool.capture(self.source, self.capture_path, policy)["complete"])

    def test_cache_encoded_private_constant_is_refused(self):
        source = (b"VALUE = " + repr(MARKER + b" extended material").encode() + b"\n")
        code = compile(source, "unprotected-filename", "exec")
        with self.assertRaises(tool.PreservationError):
            tool.cache_literal_constraints(code)

    def test_hash_based_cache_header_matches_exact_generator(self):
        source = self.literal_source()
        policy = self.cache_policy(cache_change=lambda c: c[:4] + struct.pack("<I", 3) + importlib.util.source_hash(source) + c[16:])
        self.assertTrue(tool.capture(self.source, self.capture_path, policy)["complete"])

    def test_cache_non_code_marshal_body_is_refused(self):
        policy = self.cache_policy(cache_change=lambda c: c[:16] + marshal.dumps((URI,)))
        self.assertFalse(tool.capture(self.source, self.capture_path, policy)["complete"])

    def test_cache_generator_drift_is_refused(self):
        policy = self.cache_policy(generator_change=lambda s: s + b"# generator drift\n")
        self.assertFalse(tool.capture(self.source, self.capture_path, policy)["complete"])

    def test_cache_exact_interpreter_version_is_required(self):
        policy = self.cache_policy(interpreter="unavailable interpreter version")
        self.assertFalse(tool.capture(self.source, self.capture_path, policy)["complete"])

    def test_cache_wrong_magic_is_refused(self):
        policy = self.cache_policy(cache_change=lambda c: b"wrong"[:4] + c[4:])
        self.assertFalse(tool.capture(self.source, self.capture_path, policy)["complete"])

    def test_cache_wrong_generator_size_and_flags_are_refused(self):
        policy = self.cache_policy(cache_change=lambda c: c[:4] + struct.pack("<I", 4) + c[8:])
        self.assertFalse(tool.capture(self.source, self.capture_path, policy)["complete"])
        valid = self.pyc(self.literal_source())
        changed = valid[:12] + struct.pack("<I", 1) + valid[16:]
        binding = policy.provenance.entries["W047"]
        with self.assertRaises(tool.PreservationError):
            policy.provenance.cache_constraints(binding, changed)

    def test_structural_constant_or_bytecode_change_is_refused(self):
        source = self.literal_source()
        changed_code = compile(source + b"another_constant = 99\n", "<synthetic-generator>", "exec")
        policy = self.cache_policy(cache_change=lambda c: c[:16] + marshal.dumps(changed_code))
        self.assertFalse(tool.capture(self.source, self.capture_path, policy)["complete"])

    def test_frozensets_unordered_and_filename_excluded_only(self):
        a = compile("value = 4\nif value in {'first', 'second'}: value = 2\n", "first-name", "exec")
        b = compile("value = 4\nif value in {'first', 'second'}: value = 2\n", "second-name", "exec")
        self.assertEqual(tool.code_shape(a), tool.code_shape(b))
        constants = list(b.co_consts)
        index = next(i for i, v in enumerate(constants) if isinstance(v, frozenset))
        constants[index] = frozenset(reversed(tuple(constants[index])))
        self.assertEqual(tool.code_shape(a), tool.code_shape(b.replace(co_consts=tuple(constants))))
        self.assertNotEqual(tool.code_shape(a), tool.code_shape(b.replace(co_name="different-code-owner")))

    def test_historical_object_native_roundtrip_with_complete_alias_binding(self):
        self.initialize_git()
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        self.fixture_command("add", "tests/test_example.py")
        self.fixture_command("commit", "-m", "owned test literal")
        oid = self.fixture_command("rev-parse", "HEAD:tests/test_example.py").decode().strip()
        specimens = [self.specimen("W050", "owned_test_literal", "tests/test_example.py", body),
                     self.specimen("H001", "owned_test_literal", None, body, oid=oid, aliases=["tests/test_example.py"])]
        policy = self.complete_capture(self.proof_policy(specimens))
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual(self.fixture_command("cat-file", "blob", oid, root=self.restore_path / "working-tree"), body)

    def test_new_staged_alias_of_known_historical_object_is_held(self):
        self.initialize_git()
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        self.fixture_command("add", "tests/test_example.py")
        oid = self.fixture_command("rev-parse", ":tests/test_example.py").decode().strip()
        specimens = [self.specimen("W050", "owned_test_literal", "tests/test_example.py", body),
                     self.specimen("H001", "owned_test_literal", None, body, oid=oid, aliases=["tests/test_example.py"])]
        policy = tool.Policy(self.proof_policy(specimens))
        self.write("extra-alias.py", body)
        self.fixture_command("add", "extra-alias.py")
        view = tool.create_read_view(self.source, tool.Policy(self.policy_data()), self.area / "live-alias-view")
        state = tool.git_state(self.source, tool.Policy(self.policy_data()), view=view)
        pending = tool.git_sensitive(self.source, state, policy)
        self.assertTrue(any(e.get("git_object") == oid for e in pending))

    def test_omitted_or_invented_canonical_alias_is_refused(self):
        self.initialize_git()
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        self.fixture_command("add", "tests/test_example.py")
        oid = self.fixture_command("rev-parse", ":tests/test_example.py").decode().strip()
        data = self.proof_policy([self.specimen("H001", "owned_test_literal", None, body, oid=oid, aliases=["tests/test_example.py"])])
        for aliases in [[], ["invented.py"], ["tests/test_example.py", "tests/test_example.py"]]:
            bad = copy.deepcopy(data)
            bad["content_provenance"]["entries"][0]["aliases"] = aliases
            with self.subTest(aliases=aliases), self.assertRaises(tool.PreservationError):
                tool.Policy(bad)

    def test_historical_cache_uses_exact_old_generator_without_execution(self):
        self.initialize_git()
        source = self.literal_source()
        self.write("tests/test_generator.py", source)
        self.fixture_command("add", "tests/test_generator.py")
        self.fixture_command("commit", "-m", "old exact generator")
        oid = self.fixture_command("rev-parse", "HEAD:tests/test_generator.py").decode().strip()
        (self.source / "tests/test_generator.py").write_bytes(b"current_value = 17\n")
        cache = self.pyc(source)
        self.write("cache.pyc", cache)
        specimens = [self.specimen("H001", "owned_test_literal", None, source, oid=oid, aliases=["tests/test_generator.py"]),
                     self.specimen("W048", "generated_cache", "cache.pyc", cache,
                                   generator={"path": "tests/test_generator.py", "payload": source, "git_oid": oid})]
        policy = self.complete_capture(self.proof_policy(specimens))
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "working-tree/cache.pyc").read_bytes(), cache)

    def test_historical_cache_new_generator_alias_is_not_copied(self):
        self.initialize_git()
        source = self.literal_source()
        self.write("tests/test_generator.py", source)
        self.fixture_command("add", "tests/test_generator.py")
        self.fixture_command("commit", "-m", "old exact generator")
        oid = self.fixture_command("rev-parse", "HEAD:tests/test_generator.py").decode().strip()
        (self.source / "tests/test_generator.py").write_bytes(b"current_value = 17\n")
        cache = self.pyc(source)
        self.write("cache.pyc", cache)
        specimens = [self.specimen("H001", "owned_test_literal", None, source, oid=oid, aliases=["tests/test_generator.py"]),
                     self.specimen("W048", "generated_cache", "cache.pyc", cache,
                                   generator={"path": "tests/test_generator.py", "payload": source, "git_oid": oid})]
        policy = tool.Policy(self.proof_policy(specimens))
        self.write("new-generator-alias.py", source)
        self.fixture_command("add", "new-generator-alias.py")
        manifest = tool.capture(self.source, self.capture_path, policy)
        self.assertFalse(manifest["complete"])
        with zipfile.ZipFile(self.capture_path / "working-tree.zip") as archive:
            self.assertNotIn("cache.pyc", archive.namelist())

    def test_restore_without_proof_policy_is_refused_before_publication(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        self.complete_capture(self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)]))
        with self.assertRaises(tool.PreservationError):
            tool.restore(self.capture_path, self.restore_path, tool.Policy(self.policy_data()))
        self.assertFalse(self.restore_path.exists())

    def test_resealed_erased_admission_receipt_is_refused(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        policy = self.complete_capture(self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)]))
        def erase(inventory):
            inventory["entries"][-1].pop("provenance", None)
            inventory.pop("content_provenance", None)
            inventory.pop("provenance_objects", None)
        self.reseal_inventory(erase)
        with self.assertRaises(tool.PreservationError):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())

    def test_restore_generator_archive_tampering_is_refused(self):
        policy = self.cache_policy()
        tool.capture(self.source, self.capture_path, policy)
        with zipfile.ZipFile(self.capture_path / "provenance-generators.zip", "a") as archive:
            archive.writestr("unclassified-extra.py", b"unknown extra content")
        self.reseal_inventory(lambda inventory: None)
        with self.assertRaises(tool.PreservationError):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())

    def test_resealed_generator_byte_drift_cannot_restore(self):
        policy = self.cache_policy()
        tool.capture(self.source, self.capture_path, policy)
        target = self.capture_path / "provenance-generators.zip"
        original = target.read_bytes()
        (self.area / "generator-archive-before.zip").write_bytes(original)
        with zipfile.ZipFile(target) as archive:
            members = [(item.filename, archive.read(item)) for item in archive.infolist()]
        with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, body in members:
                archive.writestr(name, b"X" + body[1:])
        self.reseal_inventory(lambda inventory: None)
        with self.assertRaises(tool.PreservationError):
            tool.restore(self.capture_path, self.restore_path, policy)
        self.assertFalse(self.restore_path.exists())

    def test_resealed_git_pack_with_unknown_extra_object_cannot_publish(self):
        self.initialize_git()
        policy = tool.Policy(self.policy_data())
        tool.capture(self.source, self.capture_path, policy)
        oid = self.fixture_command("hash-object", "-w", "--stdin", data=URI).decode().strip()
        manifest = json.loads((self.capture_path / "checkpoint.json").read_text())
        inventory = json.loads((self.capture_path / "inventory.json").read_text())
        objects = inventory["git"]["objects"] + [{"oid": oid, "type": "blob", "bytes": len(URI)}]
        import subprocess
        with (self.capture_path / "git-objects.pack").open("wb") as stream:
            result = subprocess.run(["git", "--no-optional-locks", "-C", str(self.source), "pack-objects", "--stdout"],
                                    input="".join(o["oid"] + "\n" for o in objects).encode(), stdout=stream,
                                    stderr=subprocess.PIPE, env=tool.git_environment())
        self.assertEqual(result.returncode, 0)
        for listed in [False, True]:
            self.reseal_inventory(lambda value: value["git"]["objects"].append(objects[-1]) if listed else None)
            with self.subTest(secret_object_listed=listed), self.assertRaises(tool.PreservationError):
                tool.restore(self.capture_path, self.restore_path, policy)
            self.assertFalse(self.restore_path.exists())

    def pe_fixture(self, tail):
        data = bytearray(512)
        data[:2] = b"MZ"
        struct.pack_into("<I", data, 60, 128)
        data[128:132] = b"PE\0\0"
        struct.pack_into("<H", data, 134, 1)
        struct.pack_into("<H", data, 148, 224)
        struct.pack_into("<H", data, 152, 0x10B)
        struct.pack_into("<II", data, 392, len(tail), 512)
        return bytes(data) + tail

    def test_exact_published_pe_binary_format_pattern_roundtrip_without_execution(self):
        tail = b"binary" + b"://" + b"\0\x01" + b"@" + b"\0" + MARKER + b"\0"
        body = self.pe_fixture(tail)
        self.write("library.dll", body)
        specimen = self.specimen("W001", "public_wheel_member", "library.dll", body, classification="PUBLISHED_PE_BINARY_PATTERN")
        policy = self.complete_capture(self.proof_policy([specimen]))
        tool.restore(self.capture_path, self.restore_path, policy)
        self.assertEqual((self.restore_path / "working-tree/library.dll").read_bytes(), body)

    def test_pe_printable_authority_and_extended_private_marker_are_refused(self):
        for tail in [URI, MARKER + b" extended-content\0"]:
            body = self.pe_fixture(tail)
            with self.subTest(predicate="printable_authority" if tail == URI else "private_marker"):
                with self.assertRaises(tool.PreservationError):
                    tool.pe_pattern_constraints(body, tool.protected_positions(body))

    def test_pe_truncated_section_or_wrong_header_is_refused(self):
        good = self.pe_fixture(b"format" + b"://\0@\0")
        for body in [good[:400], b"XX" + good[2:], good[:128] + b"BAD!" + good[132:]]:
            with self.assertRaises(tool.PreservationError):
                tool.pe_pattern_constraints(body, tool.protected_positions(body))

    def test_explicit_blocked_location_overrides_a_bound_literal(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        data = self.proof_policy([self.specimen("W050", "owned_test_literal", "tests/test_example.py", body)])
        data["classifications"] = [{"source_root": str(self.source), "path": "tests/test_example.py", "kind": "unknown", "evidence": "owned negative classification"}]
        manifest = tool.capture(self.source, self.capture_path, tool.Policy(data))
        self.assertFalse(manifest["complete"])
        self.assertEqual(manifest["pending"][0]["contents"], "NOT_READ_OR_COPIED")

    def test_legacy_cache_and_opaque_installer_types_cannot_be_relabelled(self):
        body = self.literal_source()
        self.write("tests/test_example.py", body)
        specimen = self.specimen("W045", "owned_test_literal", "tests/test_example.py", body,
                                  classification="LEGACY_CACHE_GENERATOR_UNRESOLVED")
        data = self.proof_policy([specimen])
        with self.assertRaises(tool.PreservationError):
            tool.Policy(data)
        for kind in tool.PROVENANCE_KINDS.values():
            self.assertNotIn("LEGACY_CACHE_GENERATOR_UNRESOLVED", kind)
            self.assertNotIn("OPAQUE_INSTALLER_OVERLAY_PATTERN", kind)


class RootVettedProofTests(unittest.TestCase):
    def test_actual_frozen_report_and_canonical_alias_inventory_parse_without_source_admission(self):
        f = Path(__file__).parent.parent.parent
        bundle = f / ".agents/runtime/hp2-provenance-20261014"
        report = json.loads((bundle / "HP2-FINAL-REPORT.json").read_text())
        inventory_path = f / ".agents/hp1-20261014/checkpoint/inventory.json"
        inventory = json.loads(inventory_path.read_text())
        entries = []
        for record in report["entries"]:
            kinds = [kind for kind, classes in tool.PROVENANCE_KINDS.items() if record["classification"] in classes]
            if not kinds:
                continue
            entry = {"entry_id": record["entry_id"], "kind": kinds[0], "source_root": report["approved_source_root"], "sha256": record["whole_file_sha256"]}
            entry.update({"path": record["path"]} if record["kind"] == "working" else
                         {"git_oid": record["git_oid"], "aliases": inventory["git"]["object_path_provenance"]["blobs"][record["git_oid"]]})
            entries.append(entry)
        data = {"schema_version": 1, "source_roots": [report["approved_source_root"]], "git_roots": [report["approved_git_common"]],
                "capture_targets": [], "restore_targets": [], "classifications": [],
                "content_provenance": {"proof_bundle": str(bundle), "snapshot_inventory": str(inventory_path),
                                       "report_sha256": tool.TRUSTED_PROVENANCE_REPORT_SHA256, "entries": entries}}
        policy = tool.Policy(data)
        self.assertEqual(len(policy.provenance.entries), 66)
        self.assertTrue({"W043", "W044", "W045"}.isdisjoint(policy.provenance.entries))
        self.assertEqual(policy.paths["capture_targets"], [])
        self.assertEqual(policy.paths["restore_targets"], [])
        policy.provenance.recheck()


if __name__ == "__main__":
    unittest.main()
