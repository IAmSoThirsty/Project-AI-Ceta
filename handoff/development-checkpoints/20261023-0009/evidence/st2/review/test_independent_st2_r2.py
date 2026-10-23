"""Independent frozen-record and additive-closure controls; review scope only."""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
from unittest.mock import patch
import ast,copy,difflib,hashlib,json,sys,unittest

F=Path('T:/00-Active/Project-AI-CETA');S=F/'.agents/runtime/oq23/st2';W=S/'work';R=S/'review';C=S/'control';D=S/'delivery';RUN='ceta-st23-r2'
MF='5729a01e71127efd8d9970e8b5d1405f9b297eb12e421e94946983f125c6ff32'
AMEND='cc7de6e2547f9b566d4dc6c3880c6a0ce3b4cbf13f5a82ebee7f7d42921efbff'
SUCCESSOR='9543dcaca98f74ec2836401cbbfc263a6521771f981b664b921caa4b261e2484'
OLD='8174315abc34152ce883f9fd380735bd0688b45f2e9810895aa5ff5107a6778a'
sys.path.insert(0,str(W));import status_core as s
OUT=R/'independent-controls-r2'
def load(path):return json.loads(path.read_bytes())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def typed_equal(a,b):
    if type(a) is not type(b):return False
    if type(a) is dict:return a.keys()==b.keys() and all(typed_equal(a[k],b[k]) for k in a)
    if type(a) is list:return len(a)==len(b) and all(typed_equal(x,y) for x,y in zip(a,b))
    return a==b
def metadata_call(tree):
    return next(n for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='dict' and (any(k.arg is None and isinstance(k.value,ast.Name) and k.value.id=='post' for k in n.keywords) or any(isinstance(a,ast.Name) and a.id=='post' for a in n.args)))
OLD_TREE=ast.parse((C/'ROOT-CLOSE.py').read_bytes());NEW_TREE=ast.parse((C/'ROOT-CLOSE-R2.py').read_bytes())

class IndependentControls(unittest.TestCase):
    def setUp(self):self.folder=OUT/self._testMethodName;self.folder.mkdir()
    def test_every_original_json_value_or_exact_typed_history_is_preserved(self):
        for rel in ('build/progress.json','handoff/continuity.json','build/gates.json'):
            before=load(W/'before'/rel);after=load(W/'candidate'/rel)
            changed={'current_deliverable','first_next_action','next_action'} if rel=='handoff/continuity.json' else set()
            self.assertTrue(set(before)<=set(after))
            for key,value in before.items():self.assertTrue(typed_equal(value,after['historical_current_fields_before_oq23_st2'][key] if key in changed else after[key]),(rel,key))
            if changed:self.assertTrue(typed_equal(before['next_action'],after['historical_next_action_before_oq23_st2']));self.assertEqual(set(after['historical_current_fields_before_oq23_st2']),changed)
    def test_all_eight_gate_rows_remain_exact_and_not_evaluated(self):
        before=load(W/'before/build/gates.json')['gates'];after=load(W/'candidate/build/gates.json')['gates']
        self.assertTrue(typed_equal(before,after));self.assertEqual(len(after),8);self.assertTrue(all(row['state']=='NOT_EVALUATED' for row in after))
    def test_constructor_changes_only_one_exact_gate_hash_literal(self):
        before=(W/'before/src/ceta/contracts/construction.py').read_bytes();after=(W/'candidate/src/ceta/contracts/construction.py').read_bytes();old=digest(W/'before/build/gates.json').encode();new=digest(W/'candidate/build/gates.json').encode()
        self.assertEqual(before.count(old),1);self.assertEqual(after.count(new),1);self.assertEqual(after.replace(new,old),before)
    def test_source_manifest_changes_only_gate_and_constructor_and_keeps_five_inputs(self):
        packet=load(S/'packet/INPUTS.json');before=load(Path(packet['source_manifest']))['payload_hashes'];after=load(W/'SOURCE-MANIFEST.json')['payload_hashes']
        self.assertEqual(set(before),set(after));self.assertEqual(len(after),560);self.assertEqual({name for name in before if before[name]!=after[name]},{'build/gates.json','src/ceta/contracts/construction.py'})
        fixtures={name for name in after if name.startswith('.local-build-cache/restoration-proof/')};self.assertEqual(len(fixtures),5);self.assertTrue(all(before[name]==after[name] for name in fixtures))
    def test_three_current_status_records_agree_and_do_not_promote_acceptance(self):
        statuses=[load(W/'candidate'/rel)['current_repository_execution_20261023'] for rel in ('build/progress.json','handoff/continuity.json','build/gates.json')]
        self.assertTrue(all(typed_equal(statuses[0],row) for row in statuses[1:]));status=statuses[0]
        self.assertIsNone(status['completion_percentage']);self.assertIs(status['full_product_complete'],False);self.assertIs(status['full_product_acceptance'],False);self.assertIs(status['genuine_native_effect_qualification'],False)
        self.assertEqual(status['broader_state'],'VALID_BROADER_SELECTED_COHORT_PASSED');self.assertIn('NOT_REPRODUCED',status['remaining_milestones'][1]['state']);self.assertIn('NOT_CAPTURED',status['remaining_milestones'][1]['state']);self.assertIn('NOT_ESTABLISHED',status['remaining_milestones'][1]['state'])
    def test_actual_closed_cohorts_are_sealed_same_order_and_successful(self):
        for name,count in (('jr2',33),('tm2',1),('br3',510)):
            root=F/('.agents/runtime/oq23/'+name);closure=load(root/'control/ROOT-EXECUTION-COMPLETION.json');verification=load(root/'control/verify-final-api.json')['response'];start=load(root/'delivery/START.json');result=load(root/'delivery/RESULT.json');process=load(root/'control/EXECUTION-PROCESS.json');seal=load(root/'delivery/REPORT-SEAL.json')
            self.assertIs(closure['terminal_success'],True);self.assertIs(verification['terminal_success'],True);self.assertIs(verification['receipts_valid'],True);self.assertTrue(all(state=='SUCCEEDED' for state in verification['states'].values()));self.assertEqual(process['exit_status'],0)
            ids=start['test_ids'];self.assertEqual(len(ids),count);self.assertEqual(len(set(ids)),count);self.assertEqual(ids,result['selected_test_ids']);self.assertEqual(ids,result['started_test_ids']);self.assertEqual(ids,result['stopped_test_ids']);self.assertIs(result['test_cohort_passed'],True)
            for key in ('failures','errors','skips','expected_failures','unexpected_successes'):self.assertFalse(result[key])
            self.assertIsNone(result['primary']);self.assertIs(result['early_stop'],False)
            if name=='tm2':
                self.assertEqual(set(result['formatted_outcomes']),{'errors','failures'});self.assertEqual(result['formatted_outcomes'],dict(errors=[],failures=[]));self.assertEqual(result['secondary'],[]);self.assertEqual(result['observation']['faults'],[]);self.assertIs(result['observation']['coverage_complete'],True);self.assertIs(result['observation']['functional_success'],True)
            else:self.assertEqual(result['test_error_details'],[]);self.assertEqual(result['cleanup'],[])
            for filename,key in (('RESULT.json','result_sha256'),('START.json','start_sha256'),('events.jsonl','events_sha256'),('TESTS.log','log_sha256')):self.assertEqual(digest(root/'delivery'/filename),seal[key])
        self.assertEqual(load(F/'.agents/runtime/oq23/br/work/COLLECTION.json')['test_ids'],load(F/'.agents/runtime/oq23/br3/delivery/START.json')['test_ids'])
    def test_failed_execution_rejected_preparation_and_admission_remain_distinct(self):
        status=load(W/'candidate/build/progress.json')['current_repository_execution_20261023'];failed=status['failed_broader_predecessor'];rejected=status['rejected_broader_preparation'];admission=status['broader_admission_history']
        self.assertEqual(failed['actual_exit_status'],1);self.assertIs(failed['test_cohort_passed'],False);self.assertIs(failed['success_seal_present'],False);self.assertFalse((F/'.agents/runtime/oq23/br/delivery/REPORT-SEAL.json').exists());self.assertEqual(failed['tests_stopped'],510)
        self.assertEqual(rejected['canonical_test_bodies_executed'],0);self.assertIs(rejected['execution_intent_present'],False);self.assertEqual(rejected['actual_review_state'],'FAILED');self.assertEqual(rejected['actual_validate_state'],'BLOCKED')
        self.assertEqual(admission['original_release_actual_exit_status'],1);self.assertEqual(admission['original_failure_scalars'],'NOT_CAPTURED');self.assertIn('UNKNOWN',admission['original_failure_cause']);self.assertEqual(admission['canonical_bodies_before_continuation'],0);self.assertEqual(admission['continuations'],1)
        qualification=load(W/'ADMISSION-HISTORY-QUALIFICATION.json');self.assertEqual(len(qualification['external_pins']),12)
        for path,pin in qualification['external_pins'].items():self.assertEqual(digest(Path(path)),pin)
    def test_explicit_journal_preserves_hostile_original_traceback_and_close_fault(self):
        class Original(KeyboardInterrupt):
            def __setattr__(self,name,value):raise RuntimeError('hostile assignment '+name)
        primary=Original('original interruption');fault=OSError('review-controlled close failure');path=self.folder/'operations.jsonl';stream=path.open('xb');opening=Path.open;trace=[];caught=None
        class Wrapper:
            def __getattr__(self,name):return getattr(stream,name)
            def close(self):stream.close();raise fault
        def open_file(value,*args,**kwargs):return Wrapper() if value==path else opening(value,*args,**kwargs)
        with patch.object(Path,'open',new=open_file):
            try:
                with s.application_journal(path,lambda error:dict(type='Original')):
                    try:raise primary
                    except BaseException:trace.append(sys.exc_info()[2]);raise
            except BaseException as error:caught=error
        self.assertIs(caught,primary);storage=BaseException.__dict__['__dict__'].__get__(primary);self.assertIs(storage['ceta_status_application_primary_exc_info'][1],primary);self.assertIs(storage['ceta_status_application_primary_exc_info'][2],trace[0]);self.assertEqual(storage['ceta_status_application_secondary_errors'],(fault,));self.assertTrue(stream.closed)
    def test_snapshot_refuses_own_scope_same_api_metadata_drift(self):
        path=self.folder/'controlled.txt';path.write_bytes(b'review control');original=s.native;calls=[]
        def changing(value):
            row=original(value)
            if Path(value)==path:
                calls.append(value)
                if len(calls)==2:row['mode']^=0o100
            return row
        with patch.object(s,'native',new=changing),self.assertRaises(AssertionError):s.stable(path)
    def test_successor_keeps_all_original_proofs_except_the_metadata_expression(self):
        old=[ast.dump(n,include_attributes=False) for n in OLD_TREE.body];new=[ast.dump(n,include_attributes=False) for n in NEW_TREE.body];ops=difflib.SequenceMatcher(a=old,b=new,autojunk=False).get_opcodes();replaced=[op for op in ops if op[0]=='replace'];inserted=[op for op in ops if op[0]=='insert']
        self.assertEqual(len(replaced),1);_,a,b,c,d=replaced[0];self.assertEqual((b-a,d-c),(1,1));self.assertEqual(OLD_TREE.body[a].lineno,21);self.assertEqual(NEW_TREE.body[c].lineno,25);self.assertEqual(len(inserted),1);self.assertFalse(any(op[0]=='delete' for op in ops))
        self.assertEqual(digest(C/'ROOT-CLOSE.py'),OLD);self.assertEqual(digest(C/'ROOT-CLOSE-R2.py'),SUCCESSOR);self.assertEqual(digest(C/'EXECUTION-AMENDMENT.json'),AMEND);self.assertEqual(digest(W/'MANIFEST.json'),MF)
    def metadata_scope(self,post):return dict(datetime=datetime,timezone=timezone,C=C,r=SimpleNamespace(s=SimpleNamespace(sha=lambda path:'c'*64)),post=post)
    def test_successor_metadata_accepts_collisions_without_mutating_original_report(self):
        post=dict(recorded_at='original time',recorded_by='independent recorder',check_path='original',check_sha256='d'*64,reviewer='/root/status_packet_review',decision='PASS_EXACT_RECORD_APPLICATION',nested=dict(value=[False,1]));before=copy.deepcopy(post)
        old=compile(ast.Expression(metadata_call(OLD_TREE)),'old-metadata','eval');new=compile(ast.Expression(metadata_call(NEW_TREE)),'new-metadata','eval')
        with self.assertRaisesRegex(TypeError,'recorded_at'):eval(old,self.metadata_scope(post))
        result=eval(new,self.metadata_scope(post));self.assertTrue(typed_equal(post,before));self.assertEqual(result['reviewer'],post['reviewer']);self.assertEqual(result['nested'],post['nested']);self.assertEqual(result['recorded_by'],'/root');self.assertEqual(result['check_sha256'],'c'*64)
    def successor_guard(self,bad=None,replay=False):
        amendment=load(C/'EXECUTION-AMENDMENT.json');node=dict(state='SUCCEEDED',decision='approved',receipt_ref='receipts/review.json');result=dict(manifest_sha256=MF,execution_amendment_sha256=AMEND,closure_successor_sha256=SUCCESSOR)
        if bad in result:result[bad]='0'*64
        elif bad=='state':node['state']='FAILED'
        elif bad=='decision':node['decision']='rejected'
        documents={C/'EXECUTION-AMENDMENT.json':json.dumps(amendment).encode(),C/RUN/'state.json':json.dumps(dict(nodes=dict(review=node))).encode(),C/RUN/'receipts/review.json':json.dumps(dict(result=result)).encode()}
        hashes={C/'EXECUTION-AMENDMENT.json':AMEND,C/'ROOT-CLOSE-R2.py':SUCCESSOR,C/'ROOT-CLOSE.py':OLD}
        nodes=NEW_TREE.body;end=next(i for i,n in enumerate(nodes) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='process' for t in n.targets));start=next(i for i,n in enumerate(nodes) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='amendment' for t in n.targets));block=ast.Module(body=nodes[start:end],type_ignores=[])
        scope=dict(json=json,C=C,D=D,RUN=RUN,pin=MF,Path=Path,__file__=str(C/'ROOT-CLOSE-R2.py'),r=SimpleNamespace(s=SimpleNamespace(sha=lambda path:hashes[Path(path)])))
        with patch.object(Path,'read_bytes',new=lambda path:documents[path]),patch.object(Path,'exists',new=lambda path:replay and path==D/'COMPLETION.json'):exec(compile(block,'successor-prewrite-guards','exec'),scope)
    def test_successor_requires_all_three_actual_review_pins_and_approval(self):
        for bad in ('manifest_sha256','execution_amendment_sha256','closure_successor_sha256','state','decision'):
            with self.subTest(bad=bad),self.assertRaises(AssertionError):self.successor_guard(bad=bad)
    def test_successor_rejects_completion_replay_and_accepts_exact_review_binding(self):
        self.successor_guard()
        with self.assertRaisesRegex(AssertionError,'no closure replay'):self.successor_guard(replay=True)

if __name__=='__main__':
    OUT.mkdir(exist_ok=False);suite=unittest.defaultTestLoader.loadTestsFromTestCase(IndependentControls)
    with (OUT/'TESTS.log').open('x',encoding='utf8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
    report=dict(tests_run=result.testsRun,failures=[(case.id(),text) for case,text in result.failures],errors=[(case.id(),text) for case,text in result.errors],skips=[(case.id(),reason) for case,reason in result.skipped],successful=result.wasSuccessful(),manifest_sha256=MF,execution_amendment_sha256=AMEND,closure_successor_sha256=SUCCESSOR,old_closer_finding_retained='ST2-CLOSE-METADATA-01; superseded/unexecuted, never approved',canonical_test_bodies_executed=0,canonical_or_fixture_or_Git_writes=False,full_product_acceptance=False)
    with (OUT/'RESULT.json').open('x',encoding='utf8') as stream:json.dump(report,stream,indent=2)
    print(json.dumps(report));raise SystemExit(0 if result.wasSuccessful() else 1)
