"""SYNTHETIC authorization/launch fixtures: no CETA test/native execution."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, redirect_stdout
import ast
import copy
import io
import json
import os
from pathlib import Path
import re
import threading
import unittest
import uuid
from unittest.mock import patch

import full_gate as g
import run_authorized as runner
import complete_authorized as completion

R = Path(__file__).resolve().parents[1]
PARENT = runner.PARENT
NOW = 1_800_000_000_000_000_000
FULL_IDS = json.loads((PARENT/'REQUIRED-SOURCE-TESTS.json').read_text())['required_ids']
COHORT = json.loads((PARENT/'COHORT-INPUTS.json').read_text())


class ControlCase(unittest.TestCase):
    def __init__(self, label):
        super().__init__('runTest')
        self.label = label
    def id(self):
        return self.label
    def runTest(self):
        raise AssertionError('Selection fixtures are never executed')


class GateTests(unittest.TestCase):
    def setUp(self):
        self.root = R/'controlled-fixtures'/uuid.uuid4().hex
        self.root.mkdir(parents=True,exist_ok=False)
        self.clock = {'wall':NOW,'mono':1000}
        self.view = {'original_case_id':g.CASE,'run_nonce':'a'*32,
            'source':'SYNTHETIC_SOURCE_BINDING','environment':'SYNTHETIC_ENVIRONMENT_BINDING','tools':'SYNTHETIC_TOOL_BINDING'}
        self.document = {'schema_version':1,'kind':'F4_ENGINEERING_ORIGINAL_NO_PROFILE_CASE_V1',
            'source':'actual_current_human_reply','human_reply':'SYNTHETIC test text, never an actual operator response.',
            'run_nonce':'a'*32,'issued_at_ns':NOW-100,'expires_at_ns':NOW+1000000,'subject':copy.deepcopy(self.view),
            'execute_exact_original_case':True,'create_profiles':False,'expected_denial_winerror':267}
        self.effects = []
    def capture(self, document=None):
        raw = g.canonical(self.document if document is None else document)
        return g.ApprovalCapture(raw,g.digest(raw),{'fixture':'SYNTHETIC_ONLY'},str(self.root/'SYNTHETIC.json'))
    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as stream:
            stream.write(g.canonical(value));stream.flush();os.fsync(stream.fileno())
    def owner(self, document=None, writer=None):
        return g.ExecutionGate(self.capture(document),self.view,snapshot=lambda:copy.deepcopy(self.view),
            write_new=writer or self.write,root=self.root,now=lambda:self.clock['wall'],monotonic=lambda:self.clock['mono'])
    def validate(self,document):
        capture=self.capture(document)
        return g.validate_record(capture.raw,capture.sha256,self.view,self.clock['wall'])
    def native(self,owner,*,error=267,response=0):
        errors={'value':error}
        def operation():
            self.effects.append('CONTROLLED_FUNCTION_ONLY');return response
        return owner.wrap_native_create(operation,lambda:errors['value'],lambda value:errors.update(value=value))
    def full_result(self):
        provenance={'authorization_sha256':'f'*64,'run_nonce':'a'*32}
        value={'exit_status':0,'failures':0,'errors':0,'skips':0,'mandatory_full_gate_complete':True,'deferred_ids':[],
            'full_expected_ids':FULL_IDS.copy(),'expected_ids':FULL_IDS.copy(),'executed_ids':FULL_IDS.copy(),
            'stopped_ids':FULL_IDS.copy(),'tests_run':2053,'engineering_gate_status':'COMPLETE_TEST_RUN',
            'operator_gate_provenance':provenance,'precise_original_denial':{'precise_denial_matched':True,
            'original_case_id':g.CASE,'authorization_sha256':'f'*64,'run_nonce':'a'*32},
            'F4_metadata109_unwaived':True,'Source_acceptance':False}
        return value,provenance

    def test_literal_original_conflict_remains_preserved(self):
        original=(PARENT/'run_joined.py').read_bytes()
        self.assertEqual(g.digest(original),g.PARENT_RUNNER)
        self.assertIn("native_authorization=None",original.decode())
        self.assertIn("assert not authorization_path.exists()",original.decode())
        self.assertIn("full['mandatory_full_gate_complete'] is True",(PARENT/'complete_source.py').read_text())

    def test_exact_runner_delta_preserves_all_other_function_ASTs(self):
        original=(PARENT/'run_joined.py').read_bytes();changed=g.amend_runner(original)
        methods=lambda text:{(node.name,node.lineno):ast.dump(node,include_attributes=False) for node in ast.walk(ast.parse(text))
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))}
        # Line numbers necessarily shift; names are unique in this exact input.
        old={name:value for (name,_),value in methods(original.decode()).items()}
        new={name:value for (name,_),value in methods(changed).items()}
        self.assertEqual(set(old),set(new))
        self.assertEqual({name for name in old if old[name]!=new[name]},{'startTest','guarded_api'})
        self.assertIn("proof['engineering_gate_status']",changed)
        self.assertIn('NO_PROFILE_MUTATION_IN_JOINED_RUNNER',changed)

    def test_completion_keeps_every_old_assertion_except_exact_self_path(self):
        original=(PARENT/'complete_source.py').read_bytes();changed=g.amend_completion(original)
        assertions=lambda text:[ast.dump(n,include_attributes=False) for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Assert)]
        old=assertions(original.decode());new=assertions(changed)
        removed=[item for item in old if item not in new]
        self.assertEqual(len(removed),1)
        self.assertIn('reviewed_scripts',removed[0]);self.assertIn('Path',removed[0])
        self.assertIn('__successor_actual_command',changed)
        self.assertIn('__completion_runtime',changed)

    def test_wrong_frozen_runner_or_completion_rejected_before_compile(self):
        for fn,path in ((g.amend_runner,PARENT/'run_joined.py'),(g.amend_completion,PARENT/'complete_source.py')):
            with self.subTest(path=path.name),self.assertRaises(g.GateError):fn(path.read_bytes()+b'\n')

    def test_authorized_selection_contains_all_actual_2053_ids(self):
        selected,deferred=g.select_ids(FULL_IDS,authorized=True,partial=False)
        self.assertEqual(selected,FULL_IDS);self.assertEqual(deferred,[]);self.assertEqual(len(selected),2053)

    def test_partial_is_exact2052_with_original_not_accepted(self):
        selected,deferred=g.select_ids(FULL_IDS,authorized=False,partial=True)
        self.assertEqual(len(selected),2052);self.assertEqual(deferred,[g.CASE])
        self.assertEqual(set(selected)|set(deferred),set(FULL_IDS))

    def test_no_authorization_never_silently_selects_original(self):
        with self.assertRaisesRegex(g.GateError,'EXPLICIT_OPERATOR'):g.select_ids(FULL_IDS,authorized=False,partial=False)
        with self.assertRaises(g.GateError):g.select_ids(FULL_IDS,authorized=True,partial=True)

    def test_missing_duplicate_or_boolean_selection_denied(self):
        for values in (FULL_IDS+[FULL_IDS[0]],[n for n in FULL_IDS if n!=g.CASE],FULL_IDS+[True]):
            with self.subTest(length=len(values)),self.assertRaises(g.GateError):g.select_ids(values,authorized=True,partial=False)
        with self.assertRaises(g.GateError):g.select_ids(FULL_IDS,authorized=1,partial=False)

    def test_modified_real_selection_segment_executes_full_and_partial(self):
        changed=g.amend_runner((PARENT/'run_joined.py').read_bytes())
        segment=changed[changed.index('authorization_path='):changed.index("\n\nif mode=='destination':")]
        for authorized in (False,True):
            ns={'__gate_authorization_path':self.root/'SYNTHETIC.json','__gate_authorization':self.document if authorized else None,
                '__gate_select':g.select_ids,'__gate_partial':not authorized,'full_expected_ids':FULL_IDS,
                'deferred_case':g.CASE,'all_cases':[ControlCase(name) for name in FULL_IDS],
                'unittest':unittest,'ids':lambda suite:[t.id() for t in suite],'mode':'destination'}
            exec(compile(segment,'<exact-amended-selection>','exec'),ns)
            self.assertEqual(ns['expected_ids'],FULL_IDS if authorized else [n for n in FULL_IDS if n!=g.CASE])

    def test_modified_targeted_segment_preserves1294_and_adds_original1295(self):
        changed=g.amend_runner((PARENT/'run_joined.py').read_bytes())
        segment=changed[changed.index('authorization_path='):changed.index("\n\nif mode=='destination':")]
        full=COHORT['required_parent_ids']+[g.CASE]
        ns={'__gate_authorization_path':self.root/'SYNTHETIC.json','__gate_authorization':self.document,
            '__gate_select':g.select_ids,'__gate_partial':False,'full_expected_ids':full,'deferred_case':g.CASE,
            'all_cases':[ControlCase(name) for name in full],'unittest':unittest,'ids':lambda suite:[t.id() for t in suite],
            'mode':'targeted','cohort_inputs':COHORT}
        exec(compile(segment,'<exact-amended-targeted-selection>','exec'),ns)
        self.assertEqual(len(ns['expected_ids']),1295);self.assertEqual(ns['deferred_ids'],[])

    def test_valid_synthetic_record_exact_roundtrip(self):
        self.assertEqual(self.validate(self.document),self.document)

    def test_record_hash_unknown_duplicate_and_oversize_denied(self):
        capture=self.capture()
        with self.assertRaises(g.GateError):g.validate_record(capture.raw,'0'*64,self.view,NOW)
        value=dict(self.document,extra=True)
        with self.assertRaises(g.GateError):self.validate(value)
        with self.assertRaises(g.GateError):g.decode_record(b'{"x":1,"x":2}')
        with self.assertRaises(g.GateError):g.decode_record(b' '*(g.MAX_RECORD_BYTES+1))

    def test_boolean_integer_float_and_nonfinite_domains_rejected(self):
        for name in ('schema_version','issued_at_ns','expires_at_ns','expected_denial_winerror'):
            value=copy.deepcopy(self.document);value[name]=True
            with self.subTest(name=name),self.assertRaises(g.GateError):self.validate(value)
        for raw in (b'{"x":1.0}',b'{"x":NaN}',b'[]',b'{}\xff'):
            with self.subTest(raw=raw),self.assertRaises(g.GateError):g.decode_record(raw)

    def test_stale_future_expiry_and_overlong_record_window_denied(self):
        for issued,expires in ((NOW-10,NOW),(NOW+1,NOW+10),(NOW-1,NOW+g.MAX_WINDOW_NS+1),(0,NOW+1)):
            value=copy.deepcopy(self.document);value.update(issued_at_ns=issued,expires_at_ns=expires)
            with self.subTest(issued=issued,expires=expires),self.assertRaises(g.GateError):self.validate(value)
        value=copy.deepcopy(self.document);value['issued_at_ns']=NOW
        self.assertEqual(self.validate(value),value)

    def test_source_environment_tools_scope_and_nonce_copy_rejected(self):
        for name in self.view:
            value=copy.deepcopy(self.document);value['subject'][name]='wrong'
            with self.subTest(name=name),self.assertRaises(g.GateError):self.validate(value)
        value=copy.deepcopy(self.document);value['run_nonce']='b'*32
        with self.assertRaises(g.GateError):self.validate(value)

    def test_human_origin_reply_kind_and_profile_scope_are_not_guessed(self):
        for name,value in (('source','model_generated'),('human_reply',' '),('kind','CETA_AUTHORITY'),
                           ('create_profiles',True),('execute_exact_original_case',1),('run_nonce','A'*32)):
            record=copy.deepcopy(self.document);record[name]=value
            with self.subTest(name=name),self.assertRaises(g.GateError):self.validate(record)

    def test_winerror_is_strict_positive_bounded_integer(self):
        for error in (False,0,-1,65536,'267'):
            record=copy.deepcopy(self.document);record['expected_denial_winerror']=error
            with self.subTest(error=error),self.assertRaises(g.GateError):self.validate(record)

    def test_marker_consumption_refuses_same_object_or_second_owner(self):
        first=self.owner();first.start()
        self.assertEqual(len(list((self.root/'consumed-authorizations').glob('*.json'))),1)
        with self.assertRaises(g.GateError):first.start()
        with self.assertRaises(FileExistsError):self.owner().start()
        self.assertEqual(self.effects,[])

    def test_concurrent_start_allows_exactly_one_caller(self):
        owner=self.owner()
        def attempt(_):
            try:owner.start();return 'consumed'
            except g.GateError:return 'denied'
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(attempt,range(24)))
        self.assertEqual(results.count('consumed'),1);self.assertEqual(results.count('denied'),23)

    def test_second_marker_failure_keeps_first_consumed_and_never_calls_launcher(self):
        count=[]
        def writer(path,value):
            count.append(path)
            if len(count)==2:raise OSError('controlled second marker refusal')
            self.write(path,value)
        owner=self.owner(writer=writer)
        with self.assertRaises(OSError):owner.start()
        with self.assertRaises(FileExistsError):owner.start()
        self.assertEqual(self.effects,[])

    def test_response_loss_after_first_marker_cannot_be_retried(self):
        primary=KeyboardInterrupt('controlled marker response loss')
        def writer(path,value):self.write(path,value);raise primary
        owner=self.owner(writer=writer)
        with self.assertRaises(KeyboardInterrupt) as caught:owner.start()
        self.assertIs(caught.exception,primary)
        with self.assertRaises(FileExistsError):owner.start()
        self.assertEqual(self.effects,[])

    def test_drift_before_start_makes_no_marker(self):
        owner=self.owner();self.view['source']='changed'
        with self.assertRaises(g.GateError):owner.start()
        self.assertFalse((self.root/'consumed-authorizations').exists())

    def test_drift_after_consumption_denies_case_and_preserves_marker(self):
        owner=self.owner();owner.start();self.view['environment']='changed'
        with self.assertRaises(g.GateError):owner.enter(g.CASE)
        self.assertTrue((self.root/'consumed-authorizations').exists());self.assertEqual(self.effects,[])

    def test_expiry_after_case_admission_denies_native_call(self):
        owner=self.owner();owner.start();owner.enter(g.CASE)
        call=self.native(owner);self.clock['wall']=self.document['expires_at_ns']
        with self.assertRaises(g.GateError):call()
        self.assertEqual(self.effects,[])

    def test_wall_or_monotonic_rollback_denies_before_native(self):
        for key in ('wall','mono'):
            with self.subTest(clock=key):
                self.root=self.root/uuid.uuid4().hex;self.root.mkdir()
                owner=self.owner();owner.start();owner.enter(g.CASE);self.clock[key]-=1
                with self.assertRaises(g.GateError):self.native(owner)()
                self.clock[key]+=1
        self.assertEqual(self.effects,[])

    def test_elapsed_deadline_charges_only_remaining_authorization_time(self):
        owner=self.owner();self.clock['wall']=self.document['expires_at_ns']-10
        owner.start();self.clock['mono']+=10
        with self.assertRaisesRegex(g.GateError,'ELAPSED_AUTHORIZATION'):owner.enter(g.CASE)

    def test_wrong_test_second_test_and_second_native_attempt_denied(self):
        owner=self.owner();owner.start()
        with self.assertRaises(g.GateError):owner.enter('other')
        owner.enter(g.CASE)
        with self.assertRaises(g.GateError):owner.enter(g.CASE)
        call=self.native(owner);self.assertEqual(call(),0)
        with self.assertRaises(g.GateError):call()
        self.assertEqual(len(self.effects),1)

    def test_precise267_denial_is_separate_from_legacy_suffix_regex(self):
        self.assertRegex('ISOLATION_RESTRICTED_CREATE_FAILED:267','ISOLATION_RESTRICTED_CREATE_FAILED:2')
        owner=self.owner();owner.start();owner.enter(g.CASE);self.native(owner,error=267)()
        receipt=owner.finish()
        self.assertEqual(receipt['actual_native_call']['winerror'],267)
        self.assertTrue(receipt['precise_denial_matched']);self.assertIn('267',receipt['legacy_regex_limitation'])

    def test_legacy_pass_with_wrong_exact_error_does_not_qualify(self):
        document=copy.deepcopy(self.document);document['expected_denial_winerror']=2
        owner=self.owner(document);owner.start();owner.enter(g.CASE);self.native(owner,error=267)()
        with self.assertRaisesRegex(g.GateError,'EXACT_NATIVE_DENIAL'):owner.finish()

    def test_native_success_returns_to_custody_caller_but_denial_gate_fails(self):
        owner=self.owner();owner.start();owner.enter(g.CASE)
        response=object();returned=self.native(owner,error=0,response=response)()
        self.assertIs(returned,response)
        with self.assertRaises(g.GateError):owner.finish()

    def test_control_exception_from_native_call_is_exact_and_never_replayed(self):
        owner=self.owner();owner.start();owner.enter(g.CASE);primary=KeyboardInterrupt('CONTROLLED no native resource')
        def operation():self.effects.append('CONTROLLED_THROW');raise primary
        call=owner.wrap_native_create(operation,lambda:0,lambda _:None)
        with self.assertRaises(KeyboardInterrupt) as caught:call()
        self.assertIs(caught.exception,primary)
        with self.assertRaises(g.GateError):call()
        self.assertEqual(self.effects,['CONTROLLED_THROW'])

    def test_thread_last_error_restored_after_observer_write(self):
        owner=self.owner();owner.start();owner.enter(g.CASE);values=[]
        call=owner.wrap_native_create(lambda:0,lambda:267,values.append)
        self.assertEqual(call(),0);self.assertEqual(values,[267]);owner.finish()

    def test_finish_without_original_attempt_cannot_certify_full_gate(self):
        owner=self.owner();owner.start()
        with self.assertRaises(g.GateError):owner.finish()

    def test_full_result_requires_exact2053_and_no_deferral_skip_or_bool_counts(self):
        original,provenance=self.full_result();self.assertIs(g.require_full_result(original,FULL_IDS,provenance),original)
        for name,value in (('tests_run',2052),('tests_run',True),('skips',1),('failures',False),
                           ('deferred_ids',[g.CASE]),('mandatory_full_gate_complete',False),('engineering_gate_status','PARTIAL_NOT_ACCEPTED')):
            data=copy.deepcopy(original);data[name]=value
            with self.subTest(name=name,value=value),self.assertRaises(g.GateError):g.require_full_result(data,FULL_IDS,provenance)
        changed=copy.deepcopy(original);changed['executed_ids'].reverse()
        with self.assertRaises(g.GateError):g.require_full_result(changed,FULL_IDS,provenance)

    def test_full_result_wrong_approval_or_false_metadata_boundary_rejected(self):
        original,provenance=self.full_result()
        for name,value in (('authorization_sha256','e'*64),('run_nonce','b'*32),('precise_denial_matched',False)):
            data=copy.deepcopy(original);data['precise_original_denial'][name]=value
            with self.subTest(name=name),self.assertRaises(g.GateError):g.require_full_result(data,FULL_IDS,provenance)
        for name,value in (('F4_metadata109_unwaived',False),('Source_acceptance',True)):
            data=copy.deepcopy(original);data[name]=value
            with self.subTest(name=name),self.assertRaises(g.GateError):g.require_full_result(data,FULL_IDS,provenance)

    def test_metadata_scope_decision_never_implies_whole_fixture_preservation(self):
        value={'schema_version':1,'issue_sha256':completion.ISSUE_SHA,'F4_manifest_sha256':g.PARENT_MANIFEST,
            'source':'actual_current_human_reply','human_reply':'SYNTHETIC test text, not actual permission.',
            'decision':'allow_library_source_completion_with_unresolved_fixture_metadata',
            'whole_fixture_preservation_accepted':False,'metadata_issue_waived':False}
        raw=g.canonical(value);self.assertEqual(completion.metadata_disposition(raw,g.digest(raw),manifest_sha=g.PARENT_MANIFEST),value)
        for name,new in (('whole_fixture_preservation_accepted',True),('metadata_issue_waived',True),('source','model_generated'),('human_reply','')):
            document=dict(value);document[name]=new;raw=g.canonical(document)
            with self.subTest(name=name),self.assertRaises(g.GateError):completion.metadata_disposition(raw,g.digest(raw),manifest_sha=g.PARENT_MANIFEST)

    def test_native_ordinary_approval_capture_is_byte_exact_and_retained_readonly(self):
        s=runner.support();path=self.root/'SYNTHETIC-only.json';raw=self.capture().raw;path.write_bytes(raw)
        with ExitStack() as stack:
            capture=runner.capture_approval(s,stack,path,g.digest(raw))
            self.assertEqual(capture.raw,raw);self.assertEqual(capture.native_identity,s.ordinary(path)['native_identity'])
            with self.assertRaises(OSError):path.write_bytes(raw+b' ')
        path.write_bytes(raw+b' ')
        self.assertEqual(path.read_bytes(),raw+b' ')

    def test_native_capture_wrong_digest_or_outside_runtime_denied(self):
        s=runner.support();path=self.root/'SYNTHETIC-only.json';path.write_bytes(self.capture().raw)
        with ExitStack() as stack,self.assertRaises(g.GateError):runner.capture_approval(s,stack,path,'0'*64)
        with ExitStack() as stack,self.assertRaises(g.GateError):runner.capture_approval(s,stack,runner.F/'README.md','0'*64)

    def test_real_inspect_is_readonly_no_approval_and_no_ceta_imports(self):
        stream=io.StringIO()
        with redirect_stdout(stream):result=runner.main(['--mode','targeted','--run-nonce','b'*32,'--inspect'])
        self.assertEqual(result,0);value=json.loads(stream.getvalue())
        self.assertFalse(value['approval_created']);self.assertFalse(value['executed'])
        self.assertEqual(value['subject']['original_case_id'],g.CASE)
        self.assertLess(len(g.canonical(dict(self.document,subject=value['subject']))),g.MAX_RECORD_BYTES)

    def test_current_Source290_cannot_pass_destination_preflight(self):
        with self.assertRaisesRegex(g.GateError,'EXACT_F4_336_RUNTIME_REQUIRED'):
            runner.main(['--mode','destination','--run-nonce','c'*32,'--inspect'])

    def test_no_authorization_entrypoint_fails_before_execution(self):
        with patch.object(runner,'context',return_value=copy.deepcopy(self.view)),patch.object(runner,'launch_compiled',side_effect=AssertionError('MUST_NOT_EXECUTE')) as execute:
            with self.assertRaisesRegex(g.GateError,'EXPLICIT_FULL_AUTHORIZATION'):
                runner.main(['--mode','targeted','--run-nonce','d'*32])
            self.assertEqual(execute.call_count,0)

    def test_completion_entrypoint_requires_actual_successor_review(self):
        with self.assertRaises(FileNotFoundError):
            completion.main(['--run-nonce','a'*32,'--delivery-path',str(self.root/'nonexistent-delivery.json'),
                '--delivery-sha256','0'*64,'--metadata-disposition-path',str(self.root/'nonexistent-metadata.json'),
                '--metadata-disposition-sha256','0'*64])


if __name__ == '__main__':
    unittest.main(verbosity=2)
