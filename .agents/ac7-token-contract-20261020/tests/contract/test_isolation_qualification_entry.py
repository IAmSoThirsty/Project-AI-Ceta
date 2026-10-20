"""DATA_ONLY entry-gate checks; host execution and actual approval are excluded."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import ast
from datetime import datetime, timezone
import json
import os
import types
import unittest
import uuid

Q = Path(__file__).resolve().parents[2]
source = Q / 'tools/qualify_isolated_worker.py'
tree = ast.parse(source.read_text(encoding='utf8'))
# The real module's identity reader opens native file handles at import. Extract
# only these exact function bodies; all host/approval dependencies below are
# explicitly DATA_ONLY substitutions. No dormant native import is claimed.
functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
             and node.name in ('require', 'save', 'qualify')]
assert len(functions) == 3
tool = types.ModuleType('ac7_data_only_entry_gate')
tool.__dict__.update(Path=Path, R=Q, Q=Q, PROPOSAL=Q / 'NO_PROPOSAL', json=json, os=os,
                     uuid=uuid, now=lambda: datetime.now(timezone.utc).isoformat(),
                     fs=types.SimpleNamespace(safe_components=lambda path: path))
tool.__file__ = str(source)
def unavailable(*args, **kwargs): raise AssertionError('DATA_ONLY dependency not substituted')
for name in ('validate_operator_record', 'read', 'capture', 'sha', '_QualificationRun'):
    setattr(tool, name, unavailable)
exec(compile(ast.Module(body=functions, type_ignores=[]), str(source), 'exec'), tool.__dict__)
PIN = 'e' * 64


class QualificationEntryGateTests(unittest.TestCase):
    def exercise(self, *, review_changes=None, interrupt=False, absent_marker=False):
        calls = []
        class ControlledRun:
            def __init__(self, directory, approval):
                calls.append(('DATA_ONLY_construct', str(directory)))
            def execute(self):
                calls.append(('DATA_ONLY_execute',))
                if interrupt: raise KeyboardInterrupt('DATA_ONLY interruption')
                return 0
        reviewed = dict(decision='approved', tool_sha256=PIN, wrapper_sha256=PIN,
                        proposal_sha256=PIN, reviewer='/root/independent_control')
        reviewed.update(review_changes or {})
        marker = dict(actual_approval_sha256=PIN, tool_sha256=PIN,
                      review_path=str(Q / 'CONTROLLED_REVIEW_NOT_A_FILE'), review_sha256=PIN)
        def read_marker(path):
            if absent_marker: raise FileNotFoundError('DATA_ONLY missing marker')
            return marker
        def capture_review(path, digest): return json.dumps(reviewed).encode(), {}
        with TemporaryDirectory(prefix='ac7-entry-control-', dir=Q) as temporary:
            root = Path(temporary)
            with patch.object(tool, 'R', root), \
                    patch.object(tool, 'validate_operator_record', return_value=None), \
                    patch.object(tool, 'read', side_effect=read_marker), \
                    patch.object(tool, 'capture', side_effect=capture_review), \
                    patch.object(tool, 'sha', return_value=PIN), \
                    patch.object(tool, '_QualificationRun', ControlledRun):
                if absent_marker:
                    with self.assertRaises(FileNotFoundError): tool.qualify(root / 'NO_APPROVAL', PIN)
                elif review_changes:
                    with self.assertRaises(AssertionError): tool.qualify(root / 'NO_APPROVAL', PIN)
                else:
                    if interrupt:
                        with self.assertRaises(KeyboardInterrupt): tool.qualify(root / 'NO_APPROVAL', PIN)
                    else:
                        self.assertEqual(tool.qualify(root / 'NO_APPROVAL', PIN), 0)
                    claim = json.loads((root / 'EXECUTION-CLAIM.json').read_bytes())
                    self.assertIs(claim['automatic_retry'], False)
                    before = (root / 'EXECUTION-CLAIM.json').read_bytes()
                    with self.assertRaises(FileExistsError): tool.qualify(root / 'NO_APPROVAL', PIN)
                    self.assertEqual((root / 'EXECUTION-CLAIM.json').read_bytes(), before)
                    self.assertEqual([row[0] for row in calls], ['DATA_ONLY_construct', 'DATA_ONLY_execute'])
                if absent_marker or review_changes:
                    self.assertEqual(calls, [])
                    self.assertFalse((root / 'EXECUTION-CLAIM.json').exists())

    def test_single_claim_survives_success_and_blocks_a_second_entry(self):
        self.exercise()

    def test_single_claim_survives_interruption_and_blocks_retry(self):
        self.exercise(interrupt=True)

    def test_direct_entry_without_reviewed_marker_cannot_start(self):
        self.exercise(absent_marker=True)

    def test_review_must_bind_tool_wrapper_proposal_and_distinct_reviewer(self):
        for changes in ({'decision': 'rejected'}, {'tool_sha256': '0' * 64},
                        {'wrapper_sha256': '0' * 64}, {'proposal_sha256': '0' * 64},
                        {'reviewer': '/root'}, {'reviewer': ''}, {'reviewer': None}):
            with self.subTest(changes=changes): self.exercise(review_changes=changes)


class DriverLivenessTransformTests(unittest.TestCase):
    def transformed_driver(self):
        prepare = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                       and node.name == 'prepare_probe')
        selected, started = [], False
        for node in prepare.body:
            names = [target.id for target in node.targets if isinstance(target, ast.Name)] \
                if isinstance(node, ast.Assign) else []
            if 'launch_needle' in names: started = True
            if started: selected.append(node)
            if started and 'driver_payload' in names: break
        self.assertTrue(started)
        # Q's parent is .agents; the original is a same-project pinned input.
        original = Q.parent / 'runtime/ac1-20261014/native_fixture_support.py'
        namespace = dict(body=original.read_text(encoding='utf8'), require=tool.require)
        exec(compile(ast.Module(body=selected, type_ignores=[]), str(source), 'exec'), namespace)
        return ast.parse(namespace['driver_payload'].decode())

    def test_exact_transform_brackets_worker_with_owned_target_observations_and_serializes_them(self):
        driver = self.transformed_driver()
        run = next(node for node in driver.body if isinstance(node, ast.FunctionDef) and node.name == 'run_native_probe')
        before = next(node for node in ast.walk(run) if isinstance(node, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'target_alive_before' for t in node.targets))
        after = next(node for node in ast.walk(run) if isinstance(node, ast.Assign)
                     and any(isinstance(t, ast.Name) and t.id == 'target_alive_after' for t in node.targets))
        worker_launch = next(node.lineno for node in ast.walk(run) if isinstance(node, ast.Call)
                             and isinstance(node.func, ast.Attribute) and node.func.attr == 'launch'
                             and isinstance(node.func.value, ast.Name) and node.func.value.id == 'IsolatedWindowsWorker')
        worker_wait = next(node.lineno for node in ast.walk(run) if isinstance(node, ast.Call)
                           and isinstance(node.func, ast.Attribute) and node.func.attr == 'wait'
                           and isinstance(node.func.value, ast.Name) and node.func.value.id == 'worker')
        self.assertLess(before.lineno, worker_launch)
        self.assertLess(worker_launch, worker_wait)
        self.assertLess(worker_wait, after.lineno)
        serialized = {key.value: value.id for node in ast.walk(run) if isinstance(node, ast.Dict)
                      for key, value in zip(node.keys, node.values)
                      if isinstance(key, ast.Constant) and key.value in ('alive_before_worker', 'alive_after_worker')
                      and isinstance(value, ast.Name)}
        self.assertEqual(serialized, dict(alive_before_worker='target_alive_before', alive_after_worker='target_alive_after'))

    def test_actual_liveness_assignments_and_assertions_reject_either_exited_target(self):
        driver = self.transformed_driver()
        run = next(node for node in driver.body if isinstance(node, ast.FunctionDef) and node.name == 'run_native_probe')
        nodes = [node for node in ast.walk(run) if isinstance(node, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id in ('target_alive_before', 'target_alive_after') for t in node.targets)
                 or isinstance(node, ast.Assert) and isinstance(node.test, ast.Name)
                 and node.test.id in ('target_alive_before', 'target_alive_after')]
        nodes.sort(key=lambda node: node.lineno)
        self.assertEqual(len(nodes), 4)
        compiled = compile(ast.Module(body=nodes, type_ignores=[]), str(source), 'exec')
        for observed in ((None, None), (0, None), (None, 0)):
            iterator = iter(observed)
            trusted = types.SimpleNamespace(poll=lambda: next(iterator))
            with self.subTest(observed=observed):
                if observed == (None, None): exec(compiled, dict(trusted=trusted))
                else:
                    with self.assertRaises(AssertionError): exec(compiled, dict(trusted=trusted))


if __name__ == '__main__':
    unittest.main()
