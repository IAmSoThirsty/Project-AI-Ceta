"""Disposable checkpoint controls; no canonical Git or publication operations."""
import sys
if sys.flags.optimize != 0:
    raise RuntimeError('CP9_OPTIMIZATION_FORBIDDEN: optimize=0 is required before imports or effects')
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import ast,copy,hashlib,json,os,stat,subprocess,sys,unittest,uuid
import checkpoint_core as c
import exact_git_scope as e
from assemble_checkpoint import blob_oid,evidence_locations
from verify_prepared import files
from publish_checkpoint import describe,valid_readback

FIX=c.W/'control-fixtures'
def directory():
    path=FIX/uuid.uuid4().hex;path.mkdir(parents=True);return path

def final_value():
    return dict(schema_version=1,project=str(c.F),run_id=c.RUN,parent=c.PARENT,status_pins={'build/progress.json':'a'*64,'handoff/continuity.json':'b'*64},source_payload_count=560,current_status_key='current_repository_execution_20261023',closed_prerequisites=[dict(run_id='ceta-st23-r2')],current_broader=dict(root=str(c.F/'.agents/runtime/oq23/br3'),control=str(c.F/'.agents/runtime/oq23/br3/control'),run_id='ceta-br23-r3',closure=dict(path=str(c.F/'.agents/runtime/oq23/br3/control/ROOT-EXECUTION-COMPLETION.json'),sha256='c'*64),verification=dict(path=str(c.F/'.agents/runtime/oq23/br3/control/verify-final-api.json'),sha256='d'*64)),preserved_broader_attempts=[dict(run_id='ceta-br23-r1',stage='EXECUTION_FAILED_POSTCHECK',canonical_test_bodies=510,actual_exit_status=1,success_seal_present=False),dict(run_id='ceta-br23-r2',stage='PREPARATION_REJECTED_BEFORE_CANONICAL_EXECUTION',canonical_test_bodies=0,execution_intent_present=False)],message='Development only.',full_product_acceptance=False)
def export_value():return dict(source=str(c.F/'.agents/runtime/example/work/accepted.py'),destination=c.PREFIX+'engineering/accepted.py',sha256='a'*64,kind='accepted_engineering',review_reference=dict(path=str(c.F/'.agents/runtime/example/review/REVIEW.json'),sha256='b'*64))

class InputControls(unittest.TestCase):
    def test_final_input_absent_blocks_without_creating_it(self):
        path=c.C/'FINAL-CANONICAL-INPUTS-R2.json'
        with patch.object(Path,'is_file',return_value=False):
            with self.assertRaises(c.PendingFinalInput):c.load_final('0'*64)
    def test_final_shape_accepts_exact_pending_contract(self):self.assertIs(c.validate_final_shape(final_value())['full_product_acceptance'],False)
    def test_final_shape_refuses_other_project_run_parent_and_acceptance(self):
        for key,bad in [('project','T:/other'),('run_id','old-run'),('parent','a'*40),('source_payload_count',559),('current_status_key','historical'),('full_product_acceptance',True)]:
            row=final_value();row[key]=bad
            with self.subTest(key=key),self.assertRaises(AssertionError):c.validate_final_shape(row)
    def test_closed_prerequisites_cannot_drop_status_or_duplicate_broader(self):
        for values in ([],[dict(run_id='ceta-br23-r3')],[dict(run_id='ceta-st23-r2'),dict(run_id='ceta-st23-r2')]):
            value=final_value();value['closed_prerequisites']=values
            with self.assertRaises(AssertionError):c.validate_final_shape(value)
    def test_reference_one_byte_mutation_detected(self):
        path=directory()/'source.txt';path.write_bytes(b'AAAA');expected=dict(path=str(path),sha256=c.sha(b'AAAA'));pins={};self.assertEqual(c.reference(expected,pins),b'AAAA');path.write_bytes(b'AAAB')
        with self.assertRaises(AssertionError):c.reference(expected,{})
    def test_stable_receipt_has_size_hash_and_path_binding(self):
        path=directory()/'proof.txt';path.write_bytes(b'proof');raw,pin=c.stable(path)
        self.assertEqual((raw,pin['bytes'],pin['sha256']),(b'proof',5,hashlib.sha256(b'proof').hexdigest()));self.assertTrue(path.is_absolute())
    def test_outside_traversal_and_git_references_refused(self):
        for path in (Path('C:/elsewhere/source.py'),c.F/'../other/source.py',c.F/'.git/config'):
            with self.subTest(path=str(path)),self.assertRaises(AssertionError):c.local(path)
    def test_invalid_relative_windows_aliases_refused(self):
        for name in ('../x','/x','x:y','x\\y','x.','x ','x/../y','.git/config','X/.GIT/config','x\ny'):
            with self.subTest(name=name),self.assertRaises(AssertionError):c.relative(name)
    def test_ignored_accepted_tool_is_not_excluded_by_location(self):self.assertEqual(c.validate_exports([export_value()],{}),[export_value()])
    def test_case_colliding_export_refused(self):
        row=export_value();other=dict(row,destination=row['destination'].upper())
        with self.assertRaises(AssertionError):c.validate_exports([row,other],{})
    def test_extra_exports_cannot_replace_canonical_or_escape_namespace(self):
        row=export_value();row['destination']='src/ceta/example.py'
        with self.assertRaises(AssertionError):c.validate_exports([row],{'src/ceta/example.py'})
    def test_env_state_cache_native_and_original_pdf_exports_refused(self):
        for suffix in ('.git/config','.venv/pyvenv.cfg','.agents/runtime/example/control/state.json','.agents/runtime/example/control/claims.json','.local-build-cache/other.json','settings/.env','native/worker.exe','assets/original.pdf'):
            row=export_value();row['source']=str(c.F/suffix)
            with self.subTest(suffix=suffix),self.assertRaises(AssertionError):c.validate_exports([row],{})
    def test_rejected_executable_cannot_be_called_failure_evidence(self):
        row=export_value();row['kind']='historical_failure_evidence'
        with self.assertRaises(AssertionError):c.validate_exports([row],{})
    def test_json_failed_receipt_can_be_retained_as_evidence(self):
        row=export_value();row.update(source=str(c.F/'.agents/runtime/failed/delivery/RESULT.json'),kind='historical_failure_evidence');self.assertEqual(c.validate_exports([row],{}),[row])

class ConservationControls(unittest.TestCase):
    def setUp(self):
        self.parent={name:['100644','blob','a'*40] for name in c.IMMUTABLE_FIXTURES|c.PDF_PATHS};self.parent['src/ceta/kept.py']=['100755','blob','b'*40]
    def test_parent_paths_and_modes_and_special_exports_preserved(self):
        child=copy.deepcopy(self.parent);child['fresh.py']=['100644','blob','c'*40];self.assertEqual(c.conservation(self.parent,child,{'fresh.py'}),['fresh.py'])
    def test_parent_path_deletion_refused(self):
        child=copy.deepcopy(self.parent);child.pop('src/ceta/kept.py');child['new']=['100644','blob','c'*40]
        with self.assertRaises(AssertionError):c.conservation(self.parent,child,{'new'})
    def test_mode_loss_refused(self):
        child=copy.deepcopy(self.parent);child['src/ceta/kept.py'][0]='100644'
        with self.assertRaises(AssertionError):c.conservation(self.parent,child,{'src/ceta/kept.py'})
    def test_five_registry_fixtures_and_pdf_exports_are_immutable_parent_inputs(self):
        for name in c.IMMUTABLE_FIXTURES|c.PDF_PATHS:
            child=copy.deepcopy(self.parent);child[name][2]='c'*40
            with self.subTest(name=name),self.assertRaises(AssertionError):c.conservation(self.parent,child,{name})
    def test_empty_or_unexported_tree_change_refused(self):
        with self.assertRaises(AssertionError):c.conservation(self.parent,copy.deepcopy(self.parent),set())
        child=copy.deepcopy(self.parent);child['other']=['100644','blob','c'*40]
        with self.assertRaises(AssertionError):c.conservation(self.parent,child,set())
    def test_only_five_cache_source_inputs_can_enter_tree(self):
        child=copy.deepcopy(self.parent);child['.local-build-cache/generated.json']=['100644','blob','c'*40]
        with self.assertRaises(AssertionError):c.conservation(self.parent,child,{'.local-build-cache/generated.json'})
    def test_full_scan_detects_addition_and_byte_change(self):
        root=directory();(root/'one').write_bytes(b'A');first=files(root);(root/'two').write_bytes(b'B');second=files(root);self.assertNotEqual(first,second);(root/'one').write_bytes(b'C');third=files(root);self.assertNotEqual(second['one'],third['one'])
    def test_full_scan_refuses_enumeration_error(self):
        with patch('verify_prepared.os.scandir',side_effect=OSError('controlled enumeration failure')):
            with self.assertRaises(OSError):files(directory())
    def test_blob_oid_matches_standard_known_empty_object(self):self.assertEqual(blob_oid(b''),'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')

class EvidenceLocationControls(unittest.TestCase):
    def value(self):
        first=export_value();second=dict(first,destination=c.PREFIX+'engineering/second-copy.py')
        third=dict(export_value(),source=str(c.F/'.agents/runtime/failed/delivery/RESULT.json'),destination=c.PREFIX+'history/FAILED-RESULT.json',kind='historical_failure_evidence')
        return dict(source_manifest=dict(path=str(c.F/'.agents/runtime/status/work/SOURCE-MANIFEST.json'),sha256='c'*64),exports=[first,second,third])
    def test_every_explicit_export_and_review_ref_is_located_exactly(self):
        value=self.value();actual=evidence_locations(value,'d'*64)
        self.assertEqual(actual['final_input_sha256'],'d'*64);self.assertEqual(actual['source_manifest_sha256'],'c'*64);self.assertIs(actual['full_product_acceptance'],False);self.assertEqual(actual['classification'],'EVIDENCE_LOCATOR_DATA_ONLY')
        self.assertEqual(actual['exports'],[dict(original_repository_relative_path=Path(row['source']).relative_to(c.F).as_posix(),published_destination=row['destination'],sha256=row['sha256'],kind=row['kind'],review_reference=dict(original_repository_relative_path=Path(row['review_reference']['path']).relative_to(c.F).as_posix(),sha256=row['review_reference']['sha256'])) for row in value['exports']])
        self.assertEqual(len(actual['exports']),3);self.assertEqual(actual['exports'][0]['original_repository_relative_path'],actual['exports'][1]['original_repository_relative_path']);self.assertNotEqual(actual['exports'][0]['published_destination'],actual['exports'][1]['published_destination'])
    def test_locator_preserves_input_and_does_not_discover_or_read_paths(self):
        value=self.value();before=copy.deepcopy(value)
        with patch.object(Path,'iterdir',side_effect=AssertionError('path discovery forbidden')),patch.object(Path,'read_bytes',side_effect=AssertionError('source reread forbidden')):actual=evidence_locations(value,'d'*64)
        self.assertEqual(value,before);self.assertEqual(len(actual['exports']),len(value['exports']))
    def test_locator_refuses_outside_source_review_or_destination(self):
        for field in ('source','review_reference','destination'):
            value=self.value();row=value['exports'][0]
            if field=='review_reference':row[field]=dict(path='C:/elsewhere/review.json',sha256='b'*64)
            else:row[field]='C:/elsewhere/source.py' if field=='source' else 'handoff/other-checkpoint/accepted.py'
            with self.subTest(field=field),self.assertRaises(AssertionError):evidence_locations(value,'d'*64)

class FinalConsumerGuardControls(unittest.TestCase):
    def load_current(self,closure_success=True,verification_success=True,stage='SUCCEEDED'):
        value=final_value();digest=c.sha(b'controlled canonical bytes');value['status_pins']={name:digest for name in value['status_pins']};value['exports']=[];documents={}
        def reference(name,body):
            path=str(c.F/('.agents/runtime/controlled-final-input/'+name+'.json'));documents[path]=json.dumps(body).encode();return dict(path=path,sha256=c.sha(documents[path]))
        value['source_manifest']=reference('source-manifest',dict(payload_hashes={name:digest for name in [*c.IMMUTABLE_FIXTURES,*('src/controlled-%03d.py'%n for n in range(555))]}))
        status=value['closed_prerequisites'][0];status['closure']=reference('status-closure',dict(actual_run=status['run_id'],terminal_success=True));status['verification']=reference('status-verify',dict(response=dict(run_id=status['run_id'],receipts_valid=True,terminal_success=True,states=dict(integrate='SUCCEEDED'))))
        broader=value['current_broader'];documents[broader['closure']['path']]=json.dumps(dict(actual_run=broader['run_id'],terminal_success=closure_success)).encode();documents[broader['verification']['path']]=json.dumps(dict(response=dict(run_id=broader['run_id'],receipts_valid=True,terminal_success=verification_success,states=dict(discover='SUCCEEDED',review='SUCCEEDED',integrate=stage)))).encode()
        for item in value['preserved_broader_attempts']:
            if item['run_id']=='ceta-br23-r1':
                closure=dict(run_id=item['run_id'],terminal_success=False,actual_exit_status=1,execution_success=False);states=dict(integrate='FAILED')
            else:
                closure=dict(run_id=item['run_id'],terminal_success=False,classification='REJECTED_PREPARATION_BEFORE_CANONICAL_EXECUTION',canonical_test_bodies_executed=0,execution_intent_present=False,all_actual_claims_closed=True);states=dict(review='FAILED',validate='BLOCKED',integrate='PENDING');item['review_reference']=reference('rejected-review',dict(decision='rejected'))
            item['closure']=reference(item['run_id']+'-closure',closure);item['verification']=reference(item['run_id']+'-verify',dict(response=dict(run_id=item['run_id'],receipts_valid=True,terminal_success=False,states=states)))
        expected='f'*64;raw=json.dumps(value).encode()
        def stable(path):return (raw,dict(sha256=expected)) if Path(path)==c.C/'FINAL-CANONICAL-INPUTS-R2.json' else (b'controlled canonical bytes',dict(sha256=digest))
        with patch.object(Path,'is_file',return_value=True),patch.object(Path,'exists',return_value=False),patch.object(c,'stable',side_effect=stable),patch.object(c,'reference',side_effect=lambda item,pins:documents[item['path']]):return c.load_final(expected)
    def test_current_broader_requires_both_terminal_success_flags(self):
        for closure,verification in ((False,True),(True,False),(False,False)):
            with self.subTest(closure=closure,verification=verification),self.assertRaisesRegex(AssertionError,'current broader execution is not closed successfully'):self.load_current(closure,verification)
    def test_failed_or_cancelled_current_broader_stage_is_refused(self):
        for state in ('FAILED','CANCELLED'):
            with self.subTest(state=state),self.assertRaisesRegex(AssertionError,'current broader execution contains a non-successful stage'):self.load_current(stage=state)
    def test_successful_current_broader_preserves_distinct_failed_histories(self):
        value,manifest,pins,canonical=self.load_current();self.assertEqual(len(manifest['payload_hashes']),560);self.assertEqual(len(canonical),562);self.assertEqual([(row['run_id'],row['canonical_test_bodies']) for row in value['preserved_broader_attempts']],[('ceta-br23-r1',510),('ceta-br23-r2',0)])
    def publication_mismatch(self,gate):
        import verify_publication as validation
        import publish_checkpoint as publisher
        prepared=json.dumps(dict(commit='a'*40)).encode();frozen=b'controlled frozen work';spec=dict(commit='b'*40,prepared_sha256=c.sha(prepared),work_freeze_sha256=c.sha(frozen),final_input_sha256='f'*64)
        def read(path):
            if path==c.W/'WORK-FREEZE.json':return frozen
            if path==c.W/'prepared-0002/PREPARED.json':return prepared
            raise AssertionError(('unexpected controlled file read',str(path)))
        with patch.object(e,'packet',return_value=spec),patch.object(c,'stable',return_value=(b'controlled packet',dict(sha256='e'*64))),patch.object(Path,'read_bytes',new=read),patch.object(c,'engine',side_effect=AssertionError('Git engine must not be reached')) as engine,patch.object(c,'save',side_effect=AssertionError('publication marker must not be created')) as save:
            if gate:
                with patch.object(validation,'OrchestrationRuntime',return_value=SimpleNamespace(verify=lambda run:dict(allowed=True,receipts_valid=True,terminal_success=True,states=dict(implement='SUCCEEDED')))),patch.object(validation,'audit',side_effect=AssertionError('must refuse commit before further audit')):
                    with self.assertRaisesRegex(AssertionError,'reviewed publication packet commit differs from prepared commit'):validation.audit_publication()
            else:
                with patch.object(publisher,'audit',return_value={}):
                    with self.assertRaisesRegex(AssertionError,'reviewed publication packet commit differs from prepared commit'):publisher.publish('e'*64)
            engine.assert_not_called();save.assert_not_called()
    def test_publication_gate_refuses_mismatched_packet_commit(self):self.publication_mismatch(True)
    def test_publisher_refuses_mismatched_packet_commit_before_marker(self):self.publication_mismatch(False)

class ScopeControls(unittest.TestCase):
    def setUp(self):
        self.pack='a'*40;self.scope=e.scope_paths(self.pack);self.spec=dict(pack_id=self.pack,git_scope=self.scope,graph_fingerprint='f'*64)
        self.runtime=e.ExactCheckpointRuntime(e.CONTROL,'f'*64);self.node=dict(kind='integration',role='integrator',access='write_scoped',write_scope=self.scope)
        self.graph=SimpleNamespace(root=Path('T:/'),scope=e.CONTROL,graph_id='t_drive_repository_change',fingerprint='f'*64,nodes={'integrate':self.node})
    def test_exact17_paths_include_git_itself_refs_reflogs_lfs_and_temp_locks(self):
        self.assertEqual(len(self.scope),17);self.assertIn(e.PREFIX,self.scope);self.assertIn(e.PREFIX+'/'+e.CACHE+'.lock',self.scope);self.assertEqual(e.validate_declarations(self.scope,self.pack),self.scope)
    def test_stock_workspace_expansion_is_narrowed_only_after_stock_admission(self):
        original=e.OrchestrationRuntime._effective_workspace_scope(self.runtime,self.graph,self.node,c.F/'.git');self.assertEqual(original[1],[e.PREFIX+'/**'])
        with patch.object(e,'packet',return_value=self.spec):self.assertEqual(self.runtime._effective_workspace_scope(self.graph,self.node,c.F/'.git')[1],self.scope)
    def test_stock_outside_root_and_outside_scope_denials_run_first(self):
        with patch.object(e,'packet',side_effect=AssertionError('packet must not be read')):
            with self.assertRaises(e.TransitionDenied) as caught:self.runtime._effective_workspace_scope(self.graph,self.node,Path('C:/other'))
            self.assertEqual(caught.exception.code,'WORKSPACE_OUTSIDE_ROOT')
            self.node['write_scope']=self.scope[1:]
            with self.assertRaises(e.TransitionDenied) as caught:self.runtime._effective_workspace_scope(self.graph,self.node,c.F/'.git')
            self.assertEqual(caught.exception.code,'WORKSPACE_OUTSIDE_SCOPE')
    def test_no_scope_broadening_or_unrelated_git_metadata_allowed(self):
        for extra in (e.PREFIX+'/**',e.PREFIX+'/config',e.PREFIX+'/objects/**',e.PREFIX+'/lfs/**',e.PREFIX+'/refs/heads/other'):
            with self.subTest(extra=extra),self.assertRaises(e.TransitionDenied):e.validate_declarations(self.scope+[extra],self.pack)
    def test_missing_duplicate_and_second_pack_identity_refused(self):
        for values in (self.scope[1:],self.scope+[e.PREFIX],self.scope+[e.PREFIX+'/objects/pack/pack-'+'b'*40+'.pack']):
            with self.assertRaises(e.TransitionDenied):e.validate_declarations(values,self.pack)
    def test_wrong_run_node_executor_or_implicit_workspace_rejected_before_store(self):
        for run,node,executor,workspace in (('old','integrate','/root',c.F/'.git'),(c.PUBLICATION_RUN,'implement','/root',c.F/'.git'),(c.PUBLICATION_RUN,'integrate','/other',c.F/'.git'),(c.PUBLICATION_RUN,'integrate','/root',None),(c.PUBLICATION_RUN,'integrate','/root',c.F)):
            with patch.object(e.OrchestrationRuntime,'claim',side_effect=AssertionError('store must not be accessed')):
                with self.assertRaises(e.TransitionDenied):self.runtime.claim(run,node,executor,workspace=workspace)
    def test_correct_claim_keeps_installed_transition(self):
        with patch.object(e,'packet',return_value=self.spec),patch.object(e.OrchestrationRuntime,'claim',return_value={'allowed':True}) as original:
            self.assertTrue(self.runtime.claim(c.PUBLICATION_RUN,'integrate','/root',workspace=c.F/'.git')['allowed']);original.assert_called_once()
    def test_other_workspace_retains_stock_behavior(self):
        path=c.W;self.node['write_scope']=['00-Active/Project-AI-CETA/.agents/runtime/oq23/cp9/work/**']
        with patch.object(e,'packet',side_effect=AssertionError('not a Git claim')):self.assertEqual(self.runtime._effective_workspace_scope(self.graph,self.node,path)[1],self.node['write_scope'])
    def test_wrong_graph_fingerprint_root_scope_or_node_role_refused(self):
        with patch.object(e,'packet',return_value=self.spec):
            for field,value in (('fingerprint','0'*64),('scope',e.CONTROL/'other')):
                original=getattr(self.graph,field);setattr(self.graph,field,value)
                with self.assertRaises(e.TransitionDenied):self.runtime._effective_workspace_scope(self.graph,self.node,c.F/'.git')
                setattr(self.graph,field,original)
            self.node['role']='worker'
            with self.assertRaises(e.TransitionDenied):self.runtime._effective_workspace_scope(self.graph,self.node,c.F/'.git')
    def test_readback_one_byte_mutation_refused(self):
        valid_readback(b'ABC',c.sha(b'ABC'))
        with self.assertRaises(AssertionError):valid_readback(b'ABD',c.sha(b'ABC'))
    def test_error_formatter_cannot_replace_caught_exception(self):
        class Bad(Exception):
            def __str__(self):raise RuntimeError('untrusted formatter')
        self.assertEqual(describe(Bad('original'))['message'],'original')


class SuccessorControls(unittest.TestCase):
    def test_root_current_broader_root_control_run_and_refs_are_exact(self):
        self.assertEqual(c.validate_final_shape(final_value())['current_broader']['run_id'],'ceta-br23-r3')
        for field,bad in [('run_id','ceta-br23-r2'),('root',str(c.F/'.agents/runtime/oq23/br2')),('control',str(c.F/'.agents/runtime/oq23/br3/control-r2'))]:
            value=final_value();value['current_broader'][field]=bad
            with self.subTest(field=field),self.assertRaises(AssertionError):c.validate_final_shape(value)
        value=final_value();value['current_broader']['closure']['path']=str(c.F/'.agents/runtime/oq23/br2/control-r2/ROOT-EXECUTION-COMPLETION.json')
        with self.assertRaises(AssertionError):c.validate_final_shape(value)
    def test_rejected_preparation_cannot_become_executed_bodies_or_intent(self):
        for changes in (dict(canonical_test_bodies=510),dict(execution_intent_present=True),dict(stage='EXECUTION_PASSED')):
            value=final_value();value['preserved_broader_attempts'][1].update(changes)
            with self.subTest(changes=changes),self.assertRaises(AssertionError):c.validate_final_shape(value)
        value=final_value();value['preserved_broader_attempts']=value['preserved_broader_attempts'][:1]
        with self.assertRaises(AssertionError):c.validate_final_shape(value)

    def test_canonical_status_keeps_rejected_preparation_separate_from_current(self):
        status=dict(completion_percentage=None,full_product_acceptance=False,full_product_complete=False,failed_broader_predecessor=dict(run_id='ceta-br23-r1',test_cohort_passed=False,actual_exit_status=1),journal_runtime=dict(tests_run=33),broader_regression=dict(run_id='ceta-br23-r3'),rejected_broader_preparation=dict(run_id='ceta-br23-r2',canonical_test_bodies_executed=0,execution_intent_present=False))
        self.assertIs(c.check_canonical_status(final_value(),status),status)
        for field,bad in [('run_id','ceta-br23-r3'),('canonical_test_bodies_executed',510),('canonical_test_bodies_executed',False),('execution_intent_present',True)]:
            changed=copy.deepcopy(status);changed['rejected_broader_preparation'][field]=bad
            with self.subTest(field=field,bad=bad),self.assertRaises(AssertionError):c.check_canonical_status(final_value(),changed)
        changed=copy.deepcopy(status);changed['broader_regression']['run_id']='ceta-br23-r2'
        with self.assertRaises(AssertionError):c.check_canonical_status(final_value(),changed)
    def test_actual_rejected_closure_cannot_claim_execution_or_success(self):
        item=dict(run_id='ceta-br23-r2');closure=dict(run_id='ceta-br23-r2',classification='REJECTED_PREPARATION_BEFORE_CANONICAL_EXECUTION',canonical_test_bodies_executed=0,execution_intent_present=False,all_actual_claims_closed=True);verification=dict(run_id='ceta-br23-r2',receipts_valid=True,terminal_success=False,states=dict(review='FAILED',validate='BLOCKED',integrate='PENDING'))
        c.check_historical_closure(item,closure,verification)
        for field,bad in [('canonical_test_bodies_executed',510),('execution_intent_present',True),('all_actual_claims_closed',False)]:
            changed=dict(closure);changed[field]=bad
            with self.subTest(field=field),self.assertRaises(AssertionError):c.check_historical_closure(item,changed,verification)
        changed=copy.deepcopy(verification);changed['states']['review']='RUNNING'
        with self.assertRaises(AssertionError):c.check_historical_closure(item,closure,changed)

class InterpreterSafetyControls(unittest.TestCase):
    ENTRYPOINTS=('checkpoint_core.py','assemble_checkpoint.py','run_prepare.py','verify_prepared.py','verify_publication.py','freeze_preparation.py','exact_git_scope.py','publish_checkpoint.py','test_checkpoint_controls.py','run_controls.py','prepare_checkpoint_successor.py')
    def optimized_refusals(self,option):
        harness='''import builtins,json,sys
path=sys.argv[1]
with open(path,'rb') as stream:code=compile(stream.read(),path,'exec')
original_import=builtins.__import__
calls=[]
def guarded_import(name,*args,**kwargs):
    calls.append(name)
    if name!='sys':raise AssertionError('authority or other import reached before optimization refusal: '+name)
    return original_import(name,*args,**kwargs)
def forbidden_open(*args,**kwargs):raise AssertionError('effect reached before optimization refusal')
builtins.__import__=guarded_import
builtins.open=forbidden_open
try:
    exec(code,{'__name__':'__main__','__file__':path})
except RuntimeError as error:
    if not str(error).startswith('CP9_OPTIMIZATION_FORBIDDEN:'):raise
    if calls!=['sys']:raise AssertionError(('unexpected imports',calls))
    print(json.dumps(dict(optimization=sys.flags.optimize,entrypoint_refused=True,imports=calls,effects=False)))
else:raise AssertionError('optimized entrypoint did not refuse')
'''
        environment={key:value for key,value in os.environ.items() if key.casefold()!='pythonoptimize'}
        output=directory()
        for name in self.ENTRYPOINTS:
            with self.subTest(option=option,entrypoint=name):
                argv=[sys.executable,'-E','-B',option,'-X','utf8','-c',harness,str(c.W/name)]
                process=subprocess.run(argv,env=environment,cwd=output,stdin=subprocess.DEVNULL,capture_output=True,timeout=20)
                (output/(name+'.stdout')).write_bytes(process.stdout);(output/(name+'.stderr')).write_bytes(process.stderr)
                c.save(output/(name+'.json'),dict(argv=argv,actual_process_exit_status=process.returncode,stdout_sha256=c.sha(process.stdout),stderr_sha256=c.sha(process.stderr),inherited_PYTHONOPTIMIZE=False,controlled_execution_only=True))
                self.assertEqual(process.returncode,0,process.stderr.decode('utf8',errors='replace'))
                outcome=json.loads(process.stdout);self.assertEqual(outcome,dict(optimization=1 if option=='-O' else 2,entrypoint_refused=True,imports=['sys'],effects=False))
    def test_all_entrypoints_refuse_O_before_authority_or_effects(self):self.optimized_refusals('-O')
    def test_all_entrypoints_refuse_OO_before_authority_or_effects(self):self.optimized_refusals('-OO')
    def test_create_only_save_writes_exact_bytes_and_refuses_overwrite(self):
        path=directory()/'exact.json';value=dict(exact='checkpoint bytes',count=3);c.save(path,value)
        self.assertEqual(path.read_bytes(),(json.dumps(value,indent=2,allow_nan=False)+'\n').encode())
        with self.assertRaises(FileExistsError):c.save(path,dict(replacement=True))
        self.assertEqual(json.loads(path.read_bytes()),value)
    def test_save_short_write_is_explicit_and_not_flushed_as_success(self):
        calls=[]
        class ShortStream:
            def __enter__(self):return self
            def __exit__(self,*args):return False
            def write(self,raw):calls.append(('write',raw));return len(raw)-1
            def flush(self):raise AssertionError('short write must refuse before flush')
        with patch.object(Path,'open',return_value=ShortStream()),patch.object(c.os,'fsync') as sync:
            with self.assertRaisesRegex(OSError,'short checkpoint JSON write'):c.save(Path('controlled.json'),dict(exact=True))
        self.assertEqual(len(calls),1);sync.assert_not_called()
    def test_preparation_command_journal_write_is_retained(self):
        import run_prepare
        root=directory();c.save(root/'CANONICAL-BEFORE-0002.json',dict(final_input_sha256='f'*64))
        class Engine:
            COMMAND_AUDITOR=None
            def prepare(self,path):
                self.COMMAND_AUDITOR(['status'],SimpleNamespace(args=['git','status'],returncode=0,stdout=b'exact output',stderr=b''))
                return dict(controlled=True)
        with patch.object(c,'W',root),patch.object(c,'preparation_claim',return_value={}),patch.object(c,'load_final',return_value=None),patch.object(c,'engine',return_value=Engine()):run_prepare.prepare('f'*64)
        rows=(root/'PREPARATION-COMMANDS-0002.jsonl').read_bytes().splitlines();self.assertEqual(len(rows),1)
        row=json.loads(rows[0]);self.assertEqual(row['argv'],['git','status']);self.assertEqual(row['stdout_sha256'],c.sha(b'exact output'));self.assertEqual(row['stdout'],'exact output')
        self.assertEqual(json.loads((root/'PRIVATE-PREPARATION-RESULT-0002.json').read_bytes())['commands'],1)
    def test_control_child_uses_E_B_and_scrubs_inherited_optimization(self):
        inherited=dict(os.environ,PYTHONOPTIMIZE='2');environment={key:value for key,value in inherited.items() if key.casefold()!='pythonoptimize'}
        argv=[sys.executable,'-E','-B','-X','utf8','-c',"import json,os,sys;print(json.dumps(dict(optimize=sys.flags.optimize,no_bytecode=sys.dont_write_bytecode,ignore_environment=sys.flags.ignore_environment,optimization_environment_absent=not any(k.casefold()=='pythonoptimize' for k in os.environ))))"]
        process=subprocess.run(argv,env=environment,cwd=directory(),stdin=subprocess.DEVNULL,capture_output=True,timeout=20)
        self.assertEqual(process.returncode,0,process.stderr.decode('utf8',errors='replace'))
        self.assertEqual(json.loads(process.stdout),dict(optimize=0,no_bytecode=True,ignore_environment=1,optimization_environment_absent=True))
    def test_engine_refuses_residual_optimization_before_utility_import_or_child(self):
        for spelling in ('PYTHONOPTIMIZE','PythonOptimize'):
            with self.subTest(spelling=spelling),patch.dict(os.environ,{spelling:'2'}),patch.object(Path,'read_bytes',side_effect=AssertionError('utility import must not be reached')):
                with self.assertRaisesRegex(RuntimeError,'CP9_INHERITED_OPTIMIZATION_FORBIDDEN'):c.engine()

class PackConsumptionControls(unittest.TestCase):
    def test_pack_substitution_is_refused_before_importing_Git_call(self):
        import publish_checkpoint as publisher
        root=directory();pack=root/'controlled.pack';pack.write_bytes(b'substituted bytes')
        engine=SimpleNamespace(git=Mock(side_effect=AssertionError('Git import forbidden on substituted pack')))
        with self.assertRaisesRegex(RuntimeError,'reviewed pack bytes changed before canonical import'):publisher.import_reviewed_pack(engine,pack,c.sha(b'reviewed pack bytes'))
        engine.git.assert_not_called()
    def test_pack_hash_is_computed_from_consumed_bytes_not_metadata_claim(self):
        import publish_checkpoint as publisher
        engine=SimpleNamespace(git=Mock(side_effect=AssertionError('Git import forbidden on forged metadata')))
        with patch.object(c,'stable',return_value=(b'wrong bytes',dict(sha256=c.sha(b'reviewed bytes')))):
            with self.assertRaisesRegex(RuntimeError,'reviewed pack bytes changed before canonical import'):publisher.import_reviewed_pack(engine,Path('controlled.pack'),c.sha(b'reviewed bytes'))
        engine.git.assert_not_called()
    def test_same_checked_pack_bytes_are_imported_without_a_second_read(self):
        import publish_checkpoint as publisher
        pack=directory()/'controlled.pack';reviewed=b'exact reviewed pack bytes';pack.write_bytes(reviewed);calls=[];reads=[];stable=c.stable
        def observe(path):
            value=stable(path);reads.append(value[0]);return value
        def importing(root,args,**kwargs):
            calls.append((root,args,kwargs['data']));pack.write_bytes(b'later substitution that must never be consumed');return b'controlled-index-result\n'
        with patch.object(c,'stable',new=observe):result=publisher.import_reviewed_pack(SimpleNamespace(git=importing),pack,c.sha(reviewed))
        self.assertEqual(result,'controlled-index-result\n');self.assertEqual(len(reads),1);self.assertEqual(calls[0][:2],(c.F,['index-pack','--stdin']));self.assertIs(calls[0][2],reads[0]);self.assertEqual(calls[0][2],reviewed);self.assertNotEqual(pack.read_bytes(),reviewed)

class ArchivalWhitespaceControls(unittest.TestCase):
    def setUp(self):
        self.engine=c.engine();self.policy=self.engine.archival_policy();self.prepared=json.loads((c.W/'prepared-0001/PREPARED.json').read_bytes())
        self.prepared['commit']='b'*40;self.prepared['archival_whitespace_policy_sha256']=self.engine.ARCHIVAL_POLICY_SHA
        self.expected=self.policy['expected_full_stdout_utf8'].encode('utf8');self.calls=[]
        self.blobs={row['destination']:Path(row['input_path']).read_bytes() for row in self.policy['exceptions']}
    def check(self,prepared=None,full=None,strict=None,bad_blob=None):
        full=full if full is not None else SimpleNamespace(returncode=2,stdout=self.expected,stderr=b'')
        strict=strict if strict is not None else SimpleNamespace(returncode=0,stdout=b'',stderr=b'')
        def git(root,args,*,env=None,data=None,allowed=(0,),return_completed=False):
            self.calls.append((list(args),allowed,return_completed))
            if args[:2]==['cat-file','blob']:
                self.assertFalse(return_completed);name=args[2].split(':',1)[1];return b'controlled blob drift' if name==bad_blob else self.blobs[name]
            self.assertTrue(return_completed);self.assertEqual(args[:4],['-c','core.whitespace='+self.engine.WHITESPACE_RULES,'diff-tree','--check'])
            if '--' not in args:self.assertEqual(allowed,(0,2));return full
            self.assertEqual(allowed,(0,));return strict
        with patch.object(self.engine,'git',new=git):return self.engine.archival_whitespace(prepared or self.prepared)
    def test_exact_seven_archival_pairs_and40_rows_qualify_with_other_paths_strict(self):
        result=self.check();self.assertEqual(len(result['exact_archival_pairs']),7);self.assertEqual(result['full_check_actual_exit_status'],2);self.assertEqual(result['expected_archival_diagnostic_rows'],40);self.assertEqual(result['strict_other_paths_actual_exit_status'],0);self.assertFalse(result['canonical_or_new_source_exception'])
    def test_missing_expected_archival_entry_refused_before_Git(self):
        value=copy.deepcopy(self.prepared);value['exports'].pop(self.policy['exceptions'][0]['destination'])
        with self.assertRaisesRegex(ValueError,'expected archival export missing'):self.check(value)
        self.assertEqual(self.calls,[])
    def test_archival_input_hash_drift_refused_before_Git(self):
        original=self.engine.stable_read;first=Path(self.policy['exceptions'][0]['input_path'])
        def stable(path):
            raw,pin=original(path)
            return (raw+b'controlled drift',pin) if Path(path)==first else (raw,pin)
        with patch.object(self.engine,'stable_read',new=stable):
            with self.assertRaisesRegex(ValueError,'archival input bytes drift'):self.check()
        self.assertEqual(self.calls,[])
    def test_archival_input_path_or_export_hash_substitution_refused(self):
        name=self.policy['exceptions'][0]['destination']
        for field,value in (('input_path',str(c.W/'unapproved-source.json')),('sha256','0'*64),('source_kind','frozen_candidate')):
            changed=copy.deepcopy(self.prepared);changed['exports'][name][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'archival export pair differs'):self.check(changed)
        self.assertEqual(self.calls,[])
    def test_archival_commit_blob_hash_drift_refused_before_style_qualification(self):
        with self.assertRaisesRegex(ValueError,'archival blob bytes drift'):self.check(bad_blob=self.policy['exceptions'][0]['destination'])
        self.assertEqual(len(self.calls),1)
    def test_canonical_or_extra_diagnostic_never_receives_archival_exception(self):
        extra=self.expected+b'src/ceta/store/journal.py:1: trailing whitespace.\n+unsafe \n'
        with self.assertRaisesRegex(ValueError,'unexpected or missing full whitespace diagnostics'):self.check(full=SimpleNamespace(returncode=2,stdout=extra,stderr=b''))
        self.assertFalse(any('--' in args for args,_,_ in self.calls))
    def test_missing_archival_diagnostic_is_fatal(self):
        with self.assertRaisesRegex(ValueError,'unexpected or missing full whitespace diagnostics'):self.check(full=SimpleNamespace(returncode=2,stdout=self.expected[:-1],stderr=b''))
        self.assertFalse(any('--' in args for args,_,_ in self.calls))
    def test_unexpected_full_exit_status_or_stderr_is_fatal(self):
        for status,stdout,stderr in ((0,b'',b''),(1,self.expected,b''),(2,self.expected,b'controlled stderr')):
            with self.subTest(status=status,stderr=stderr),self.assertRaisesRegex(ValueError,'unexpected or missing full whitespace diagnostics'):self.check(full=SimpleNamespace(returncode=status,stdout=stdout,stderr=stderr))
    def test_strict_check_failure_outside_archival_pairs_is_fatal(self):
        for status,stdout,stderr in ((2,b'new canonical whitespace',b''),(0,b'unexpected output',b''),(0,b'',b'unexpected stderr')):
            with self.subTest(status=status,stdout=stdout,stderr=stderr),self.assertRaisesRegex(ValueError,'strict whitespace check failed outside exact archival pairs'):self.check(strict=SimpleNamespace(returncode=status,stdout=stdout,stderr=stderr))
    def test_policy_mutation_extra_missing_or_outside_pair_is_fatal(self):
        for kind in ('extra','missing','outside'):
            value=copy.deepcopy(self.policy)
            if kind=='extra':value['exceptions'].append(dict(value['exceptions'][0]))
            elif kind=='missing':value['exceptions'].pop()
            else:value['exceptions'][0]['destination']='src/ceta/unsafe.py'
            path=directory()/'policy.json';c.save(path,value)
            with self.subTest(kind=kind),patch.object(self.engine,'ARCHIVAL_POLICY_PATH',path):
                with self.assertRaisesRegex(ValueError,'archival policy drift'):self.check()
        self.assertEqual(self.calls,[])
    def test_strict_pathspec_has_only_seven_exact_literal_exclusions(self):
        self.check();args=self.calls[-1][0];tail=args[args.index('--')+1:]
        self.assertEqual(tail,['.']+[':(top,exclude,literal)'+row['destination'] for row in self.policy['exceptions']]);self.assertEqual(len(tail),8);self.assertFalse(any('*' in path for path in tail));self.assertEqual(len(self.calls),9)
    def test_failed_attempt_verifier_and_failed_parent_cannot_be_promoted(self):
        with patch.object(self.engine,'git',side_effect=AssertionError('Git must not be reached')) as git:
            with self.assertRaisesRegex(ValueError,'only distinct prepared-0002'):self.engine.verify(c.W/'prepared-0001/PREPARED.json')
            git.assert_not_called()
        changed=copy.deepcopy(self.prepared);changed['parent']='8b8142c56d23a338262894e9d4601195bc26f652'
        with self.assertRaisesRegex(ValueError,'wrong successor root or parent'):self.check(changed)
        self.assertEqual(self.calls,[])

class HostileCustodyControls(unittest.TestCase):
    def preparation_failure(self,close_fault):
        import run_prepare
        root=directory();c.save(root/'CANONICAL-BEFORE-0002.json',dict(final_input_sha256='f'*64));trace=[];writes=[]
        class Hostile(KeyboardInterrupt):
            def __setattr__(self,name,value):
                if name=='__traceback__':writes.append(name);raise RuntimeError('hostile traceback mutation refused')
                BaseException.__setattr__(self,name,value)
        original=Hostile('exact original interrupt')
        class Engine:
            COMMAND_AUDITOR=None
            def prepare(self,path):
                try:raise original
                except BaseException:trace.append(sys.exc_info()[2]);raise
        original_open=Path.open
        class CloseFault:
            def __init__(self,stream):self.stream=stream
            def __getattr__(self,name):return getattr(self.stream,name)
            def close(self):self.stream.close();raise OSError('controlled journal close fault')
        def opening(path,*args,**kwargs):
            stream=original_open(path,*args,**kwargs)
            return CloseFault(stream) if close_fault and path.name=='PREPARATION-COMMANDS-0002.jsonl' else stream
        caught=None
        with patch.object(c,'W',root),patch.object(c,'preparation_claim',return_value={}),patch.object(c,'load_final',return_value=None),patch.object(c,'engine',return_value=Engine()),patch.object(Path,'open',new=opening):
            try:run_prepare.prepare('f'*64)
            except BaseException as error:
                caught=error;self.assertIs(error,original);self.assertEqual(BaseException.__dict__['args'].__get__(error),('exact original interrupt',));tb=BaseException.__dict__['__traceback__'].__get__(error);chain=[]
                while tb is not None:chain.append(tb);tb=tb.tb_next
                self.assertTrue(any(item is trace[0] for item in chain));self.assertEqual(len(BaseException.__dict__['__dict__'].__get__(error)['checkpoint_secondary_errors']),int(close_fault))
        self.assertIs(caught,original);self.assertEqual(writes,[]);self.assertFalse((root/'PRIVATE-PREPARATION-RESULT-0002.json').exists())
    def test_manual_preparation_custody_preserves_hostile_original(self):self.preparation_failure(False)
    def test_manual_preparation_close_fault_preserves_hostile_original(self):self.preparation_failure(True)
    def publisher_failure(self,secondary_faults):
        import publish_checkpoint as publisher
        root=directory();work=root/'work';control=root/'publication-control';(work/'prepared-0002/pack').mkdir(parents=True);control.mkdir();(root/'.git/hooks').mkdir(parents=True)
        pack=work/'prepared-0002/pack'/('checkpoint-'+'a'*40+'.pack');pack.write_bytes(b'controlled pack bytes; never imported')
        (root/'.git/index').write_bytes(b'controlled index; no repository');(root/'.git/HEAD').write_bytes(b'controlled HEAD; no repository');hook=root/'.git/hooks/pre-push';hook.write_bytes(b'git lfs pre-push')
        utility=c.engine();stable=utility.stable_read;c.save(work/'WORK-FREEZE.json',dict(controlled=True))
        prepared=dict(pack_files={str(pack):c.sha(pack.read_bytes())},checkout_before={},commit='c'*40,exports={});c.save(work/'prepared-0002/PREPARED.json',prepared)
        c.save(work/'CANONICAL-BEFORE-0002.json',dict(normal_index_native=stable(root/'.git/index')[1],HEAD_native=stable(root/'.git/HEAD')[1],canonical_pins={}))
        spec=dict(work_freeze_sha256=c.sha((work/'WORK-FREEZE.json').read_bytes()),final_input_sha256='f'*64,prepared_sha256=c.sha((work/'prepared-0002/PREPARED.json').read_bytes()),commit=prepared['commit'],pack_id='a'*40,pre_push_hook_sha256=c.sha(hook.read_bytes()),git_scope=e.scope_paths('a'*40));trace=[];writes=[]
        class Hostile(KeyboardInterrupt):
            def __setattr__(self,name,value):
                if name=='__traceback__':writes.append(name);raise RuntimeError('hostile traceback mutation refused')
                BaseException.__setattr__(self,name,value)
        original=Hostile('exact original publication interrupt')
        class Engine:
            COMMAND_AUDITOR=None
            def checkout_state(self,path):return {}
            def git(self,path,args,**kwargs):
                if 'index-pack' in args:
                    try:raise original
                    except BaseException:trace.append(sys.exc_info()[2]);raise
                if args[0]=='for-each-ref':return (c.REF+' '+c.PARENT+'\nrefs/remotes/origin/development/checkpoints '+c.PARENT+'\n').encode()
                if args[0]=='ls-remote':return (c.PARENT+'\t'+c.REF+'\n').encode()
                if args[0]=='config':return b''
                raise AssertionError(('unexpected controlled Git call',args))
        snapshot_calls=[]
        def snapshot(path):
            snapshot_calls.append(path)
            if secondary_faults and len(snapshot_calls)==2:raise OSError('controlled postcheck fault')
            return {}
        original_save=c.save
        def saving(path,value):
            if secondary_faults and path.name=='INTEGRATION-RESULT.json':raise OSError('controlled result persistence fault')
            return original_save(path,value)
        caught=None
        with patch.object(c,'F',root),patch.object(c,'W',work),patch.object(c,'engine',return_value=Engine()),patch.object(c,'stable',new=stable),patch.object(c,'save',new=saving),patch.object(e,'CONTROL',control),patch.object(e,'packet',return_value=spec),patch.object(publisher,'audit',return_value={}),patch.object(publisher,'current_claim',return_value={'input_hash':'controlled'}),patch.object(publisher,'files',new=snapshot):
            try:publisher.publish('f'*64)
            except BaseException as error:
                caught=error;self.assertIs(error,original);tb=BaseException.__dict__['__traceback__'].__get__(error);chain=[]
                while tb is not None:chain.append(tb);tb=tb.tb_next
                self.assertTrue(any(item is trace[0] for item in chain));self.assertEqual(len(BaseException.__dict__['__dict__'].__get__(error)['checkpoint_secondary_exc_infos']),2 if secondary_faults else 0)
        self.assertIs(caught,original);self.assertEqual(writes,[]);self.assertTrue((control/'INTEGRATION-START.json').exists())
    def test_manual_publisher_custody_preserves_hostile_original(self):self.publisher_failure(False)
    def test_manual_publisher_postcheck_and_persistence_preserve_hostile_original(self):self.publisher_failure(True)
    def test_production_tools_have_no_generator_contextmanager_wrappers(self):
        for name in ('checkpoint_core.py','assemble_checkpoint.py','run_prepare.py','verify_prepared.py','verify_publication.py','freeze_preparation.py','exact_git_scope.py','publish_checkpoint.py'):
            tree=ast.parse((c.W/name).read_bytes())
            self.assertFalse(any(isinstance(node,(ast.Yield,ast.YieldFrom)) for node in ast.walk(tree)),name)

if __name__=='__main__':unittest.main(verbosity=2)
