"""Finite changed-caller controls with fake release/owners; no CETA/native work."""
from foundation_support import *
import copy
import contextlib
import io
import types
import unittest
from unittest.mock import patch
import js8_support as j
import run_full as runner

D=R/'caller-controls-r1';D.mkdir(exist_ok=False)
events=[]


class Gate:
    def __init__(self,passed=True,close_error=None):
        self.reader=types.SimpleNamespace(closed=False);self.passed=passed;self.close_error=close_error
    def start(self):events.append('gate-start')
    def finish(self):events.append('gate-finish');return dict(passed=self.passed,original_case_id='case')
    def close(self,primary=None):
        events.append('gate-close');self.reader.closed=True
        if self.close_error is not None:raise self.close_error


class CallerControls(unittest.TestCase):
    def setUp(self):events.clear()
    def main(self,name,gate,error=None):
        root=D/name;root.mkdir();(root/'candidate-full').mkdir()
        def execute(*args):
            events.append('execute')
            if error is not None:raise error
            return dict(tests_run=2334,exit_status=0)
        with patch.object(runner,'R',root),patch.object(runner,'execute',execute), \
             patch.object(j,'require_release',return_value={}),patch.object(j,'verify',return_value={}), \
             patch.object(j,'capture_native_case_gate',return_value=gate), \
             patch.object(j,'manifest',return_value={'native_gate':{'original_case_id':'case'}}), \
             patch.object(sys,'argv',['run_full.py','candidate-full','--release-path',str(root/'release.json'),
                 '--release-sha256','a'*64]),contextlib.redirect_stdout(io.StringIO()):
            return runner.main()
    def test_original_case_gate_starts_before_execution_and_closes_before_result(self):
        self.assertEqual(self.main('positive',Gate()),0)
        self.assertEqual(events,['gate-start','execute','gate-finish','gate-close'])
        record=read(D/'positive/candidate-full/RESULT.json')
        proof=read(safe_proof(record['native_case_proof']))
        self.assertIs(proof['release_reader_closed'],True)
    def test_failed_gate_cannot_turn_passing_suite_into_acceptance(self):
        self.assertEqual(self.main('denied-gate',Gate(False)),1)
        self.assertEqual(read(D/'denied-gate/candidate-full/RESULT.json')['exit_status'],1)
    def test_primary_and_exact_secondary_survive_caller_cleanup_failure(self):
        primary=KeyboardInterrupt('execution primary');secondary=SystemExit('reader close refusal')
        try:self.main('primary',Gate(close_error=secondary),primary)
        except BaseException as caught:self.assertIs(caught,primary)
        else:self.fail('Exact primary required')
        fields=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertTrue(any(stage=='native-case-release-close' and error is secondary
            for stage,error,_ in dict.get(fields,'publication_evidence_failures',())))
        self.assertEqual(events,['gate-start','execute','gate-finish','gate-close'])
    def test_full_proof_requires_native_gate_physical_closure_and_exact_obligations(self):
        case=['case'];payload={'src/ceta/example.py':'1'*64};subject={'mode':'candidate-full','source_root':str(Q)}
        m={'expected_payload_hashes':payload,'native_gate':{'original_case_id':'case'}}
        native_ref={'repository_relative_path':'native','sha256':'a'*64}
        refs={
            'gate':dict(passed=True,release_reader_closed=True,original_case_id='case',subject=subject,
                release=native_ref,run_nonce='b'*32),
            'release':dict(native_case_release=native_ref),
            'physical':dict(owned_resources_closed=True,remaining_resources=[]),
            'owners':dict(owned_resources_closed=True,obligations={name:True for name in (
                'exact_process_job_handles_closed','clocks_retired','bindings_closed','pending_API_custody_accounted',
                'controlled_allocations_released','approval_lifetimes_closed','observer_lifetimes_closed',
                'observer_source_handles_closed','session_lifetimes_closed','CPU_binding_lifetimes_closed',
                'throttling_lifetimes_closed','admission_lifetimes_closed')})}
        full=dict(phase='candidate-full',manifest_sha256='manifest',Source_publication=False,Source_accepted=False,
            expected_ids=case,tests_run=1,failures=0,errors=0,skips=0,exit_status=0,executed_ids=case,stopped_ids=case,
            suite_aborted=False,gc_observation_failed=False,remaining_threads=[],captured_journal_fixtures_closed=True,
            before_hashes=payload,after_hashes=payload,expected_payload_hashes=payload,
            uniform_pre_test_collection=[dict(test_id='case',gc_enabled=True)],source_unchanged=True,
            native_case_proof='gate',physical_custody='physical',native_owners_proof='owners',release='release',
            mandatory_full_gate_complete=True,deferred_ids=[])
        launch=dict(exit_status=0,primary_error=None,phase='candidate-full',own_job_only=True,
            record=dict(child_exit=0,primary_error=None,retirement_error=None,child_result='full',
                native_owner_after={name:True for name in ('closed','process_closed','thread_closed','job_closed','startup_handles_closed')}))
        def check():j.require_full(full,launch,'candidate-full','full')
        with patch.object(j,'manifest',return_value=m),patch.object(j,'require_case_ids',return_value=case), \
             patch.object(j.s,'sha',return_value='manifest'),patch.object(j,'proof',side_effect=lambda key:(Path('model'),refs[key])), \
             patch.object(j,'require_interpreter_command'),patch.object(j,'native_case_subject',return_value=subject):
            check()
            mutations=[('gate','passed',False),('gate','release_reader_closed',False),
                ('physical','owned_resources_closed',False),('physical','remaining_resources',[{'kind':'sqlite'}]),
                ('owners','owned_resources_closed',False),('owners','obligations',{})]
            for category,key,value in mutations:
                with self.subTest(category=category,key=key):
                    old=refs[category][key];refs[category][key]=value
                    try:
                        with self.assertRaises(AssertionError):check()
                    finally:refs[category][key]=old
            old=refs['owners']['obligations']['clocks_retired']
            for bad in (False,1):
                refs['owners']['obligations']['clocks_retired']=bad
                with self.assertRaises(AssertionError):check()
            refs['owners']['obligations']['clocks_retired']=old


suite=unittest.defaultTestLoader.loadTestsFromTestCase(CallerControls)
expected=list(j.ids(suite));executed=[];stopped=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
    def stopTest(self,test):stopped.append(test.id());super().stopTest(test)
with (D/'RAW.txt').open('x',encoding='utf8') as stream:
    result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
assert not any(name=='ceta' or name.startswith('ceta.') for name in sys.modules)
write_new(D/'RESULT.json',dict(at=utc(),expected_ids=expected,executed_ids=executed,stopped_ids=stopped,
    tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped),
    scripts=j.scripts(),raw=reference(D/'RAW.txt'),CETA_imports=0,native_calls=0,Source_mutations=0,
    scope='Changed caller/reader predicates only; filesystem/release/outer execution supplied controlled data. No product/full execution.',
    exit_status=0 if result.wasSuccessful() and not result.skipped and expected==executed==stopped else 1))
print(canonical(dict(tests_run=result.testsRun,failures=len(result.failures),errors=len(result.errors),skips=len(result.skipped))))
sys.exit(0 if result.wasSuccessful() else 1)
