"""Execute exact CT4 wrappers against finite, reviewer-owned native file fixtures."""
from ct4_support import *
import ast, copy, unittest, uuid
from unittest.mock import patch

PUB=R/'apply_reviewed_status.py';INTEGRATE=R/'integrate_status.py'
M='2e8cdfd1bcd8e1b2c250c33f156df450c03bbc34f60efbdce90c9de3edf08efe'
H='d667f4edcfcba670af85ee06620ac3ee84c713d4f599e36d6cd36d215ca34664'
I='447f7a9149781e1b71aabf7f8bbeb3c54859fafd7f201292909746d117bdb3ed'
assert sha(PUB)==H and sha(INTEGRATE)==I and sha(Q/'TRANSFER-MANIFEST.json')==M
spec=importlib.util.spec_from_file_location('ct4_exact_publication_wrapper',PUB)
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
native,nfs=helper.native,helper.native.fs
real_publish=native.publish_prepared
real_hash,real_safe,real_lstat,real_exists,real_open=native.exact_hash,nfs.safe_components,nfs.lstat,nfs.exists,nfs.open_source
manifest=read(Q/'TRANSFER-MANIFEST.json');original_read=helper.read
inspection=read(V/'candidate-inspection.json');observations=[]

class World:
    def __init__(self,label,phase=None):
        self.root=V/('wrapper-'+label+'-'+uuid.uuid4().hex)
        self.mirror,self.runtime,self.out=self.root/'targets',self.root/'runtime',self.root/'application'
        self.mirror.mkdir(parents=True,exist_ok=False)
        self.paths={F/row['relative_path']:self.mirror/row['relative_path'] for row in manifest['payloads']}
        self.initial={};self.full_initial={}
        for logical,physical in self.paths.items():
            physical.parent.mkdir(parents=True,exist_ok=True)
            nfs.write_new(physical,logical.read_bytes());self.initial[logical.relative_to(F).as_posix()]=nfs.file_identity(real_lstat(physical))
            self.full_initial[logical.relative_to(F).as_posix()]=physical.stat()
        (self.runtime/RUN/'receipts').mkdir(parents=True)
        (self.runtime/'independent-review').mkdir()
        local={'schema_version':1,'run_id':RUN,'node_id':'review','executor_id':ACTOR,
            'started_at':'2026-10-14T22:00:00+00:00','finished_at':'2026-10-14T22:00:01+00:00',
            'input_hash':'a'*64,'changed_files':[],'result':{'manifest_sha256':M,'integration_script_sha256':I},
            'commands':[],'validations':[],'exit_status':0,'decision':'approved'}
        records={self.runtime/RUN/'claims.json':{'integrate':{'executor_id':'/root','workspace':str(F),'input_hash':'reviewer-owned-synthetic-claim'}},
            self.runtime/RUN/'state.json':{'sequence':9,'nodes':{'review':{'state':'SUCCEEDED'},'validate':{'state':'SUCCEEDED'}}},
            self.runtime/RUN/'receipts/review.json':{**copy.deepcopy(local),'git_baseline':{},'observed_git':{},'receipt_hash':'b'*64},
            self.runtime/'independent-review/review.json':local,
            self.runtime/'independent-review/publication-helper-review.json':{'decision':'approved','exit_status':0,'publication_script_sha256':H,'manifest_sha256':M}}
        for path,value in records.items():nfs.write_json(path,value)
        nfs.write_new(self.runtime/'ACCEPTED-SOURCE-BASELINE.json',(R/'ACCEPTED-SOURCE-BASELINE.json').read_bytes())
        nfs.write_new(self.runtime/'apply_reviewed_status.py',PUB.read_bytes())
        self.phase,self.changed,self.published,self.substitutions=phase,False,[],[]
        self.trigger='build/progress.json';self.trigger_target=self.paths[F/self.trigger]
        self.trigger_backup=self.out/'native-backups'/(self.trigger+'.original')
    def mapped(self,path):return self.paths.get(Path(path),Path(path))
    def read(self,path):
        value=original_read(self.mapped(path))
        if Path(path)==Q/'TRANSFER-MANIFEST.json':
            value=copy.deepcopy(value)
            for row in value['payloads']:
                facts=self.full_initial[row['relative_path']]
                row['source_native_identity']={'device':facts.st_dev,'inode':facts.st_ino,'mode':facts.st_mode,'bytes':facts.st_size,'mtime_ns':facts.st_mtime_ns,'attributes':facts.st_file_attributes}
        return value
    def substitute(self,path):
        self.changed=True;custody=self.root/'substitution-originals';custody.mkdir(exist_ok=True)
        stage,backup=custody/(str(len(self.substitutions))+'.stage'),custody/(str(len(self.substitutions))+'.before')
        data=path.read_bytes();before=nfs.file_identity(real_lstat(path));nfs.write_new(stage,data)
        real_publish(stage,path,backup,hashlib.sha256(data).hexdigest(),hashlib.sha256(data).hexdigest())
        after=nfs.file_identity(real_lstat(path));assert before['inode']!=after['inode'] and nfs.file_identity(real_lstat(backup))==before
        self.substitutions.append({'target':str(path),'before':before,'after':after,'retained_original':str(backup),'sha256':hashlib.sha256(data).hexdigest()})
    def safe(self,path,**kwargs):return real_safe(self.mapped(path),**kwargs)
    def lstat(self,path):
        if self.phase=='before_replace' and not self.changed and Path(path)==F/self.trigger and (self.out/'STARTED.json').exists():self.substitute(self.trigger_target)
        return real_lstat(self.mapped(path))
    def opened(self,path,**kwargs):
        physical=self.mapped(path)
        if self.phase=='before_preserve' and not self.changed and physical==self.trigger_target and (self.out/'staged'/self.trigger).exists():self.substitute(physical)
        if self.phase=='final_backup' and not self.changed and len(self.published)==2 and physical==self.trigger_backup:self.substitute(physical)
        return real_open(physical,**kwargs)
    def publish(self,stage,target,backup,before,candidate):
        assert Path(target) in self.paths and self.paths[Path(target)].is_relative_to(self.mirror)
        if self.phase=='second_fail' and len(self.published)==1:raise OSError('owned second native publication denial')
        real_publish(stage,self.paths[Path(target)],backup,before,candidate)
        self.published.append({'logical_target':str(target),'physical_target':str(self.paths[Path(target)]),'native_backup':str(backup),'before_sha256':before,'candidate_sha256':candidate})
        if self.phase=='after_replace' and not self.changed and Path(target)==F/self.trigger:self.substitute(backup)
    def execute(self):
        with patch.object(helper,'R',self.runtime),patch.object(helper,'OUT',self.out),patch.object(helper,'read',side_effect=self.read), \
             patch.object(native,'exact_hash',side_effect=lambda p:real_hash(self.mapped(p))),patch.object(nfs,'safe_components',side_effect=self.safe), \
             patch.object(nfs,'lstat',side_effect=self.lstat),patch.object(nfs,'exists',side_effect=lambda p:real_exists(self.mapped(p))), \
             patch.object(nfs,'open_source',side_effect=self.opened),patch.object(native,'publish_prepared',side_effect=self.publish):helper.main()
    def record(self,test_id,result):
        observations.append({'test_id':test_id,'result':result,'root':str(self.root),'published':self.published,'substitutions':self.substitutions,
            'APPLIED_present':(self.out/'APPLIED.json').exists(),'FAILED_present':(self.out/'FAILED.json').exists(),
            'fixtures':[{'path':p.relative_to(self.root).as_posix(),**ordinary(p)} for p in sorted(self.root.rglob('*')) if p.is_file()]})
    def mutate_json(self,path,mutate):
        value=read(path);mutate(value);path.write_text(json.dumps(value,allow_nan=False),encoding='utf-8')

tree=ast.parse(INTEGRATE.read_text(encoding='utf-8'))
start=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.Assert) and ast.unparse(n.test)=='sys.flags.optimize == 0')
branch=next(i for i,n in enumerate(tree.body) if isinstance(n,ast.If) and ast.unparse(n.test)=="mode == 'claim'")
stop=next(i for i,n in enumerate(tree.body[branch+1:],branch+1) if isinstance(n,ast.Assign) and ast.unparse(n.targets[0])=='sys.path[:0]')
claim_stop=next(i for i,n in enumerate(tree.body[branch].body) if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='invoke')
def prefix(world,mode):
    env={'__file__':str(INTEGRATE),'__name__':'ct4_read_only_integrate_prefix'}
    exec(compile(ast.fix_missing_locations(ast.Module(body=copy.deepcopy(tree.body[:start]),type_ignores=[])),str(INTEGRATE),'exec'),env)
    env.update({'R':world.runtime,'OUT':world.out,'read':world.read,'sha':lambda p:sha(world.mapped(p))})
    body=tree.body[start:branch]
    body=body+(tree.body[branch].body[:claim_stop] if mode=='claim' else tree.body[branch+1:stop])
    with patch.object(sys,'argv',[str(INTEGRATE),mode]):exec(compile(ast.fix_missing_locations(ast.Module(body=copy.deepcopy(body),type_ignores=[])),str(INTEGRATE),'exec'),env)

class WrapperTests(unittest.TestCase):
    def test_two_actual_native_replacements_keep_both_exact_originals(self):
        w=World('positive');w.execute();self.assertEqual(len(w.published),2)
        for row in manifest['payloads']:
            rel=row['relative_path'];self.assertEqual(sha(w.mirror/rel),row['candidate_sha256']);self.assertEqual(nfs.file_identity(real_lstat(w.out/'native-backups'/(rel+'.original'))),w.initial[rel])
        w.record(self.id(),'EXACT_TWO_NATIVE_REPLACEMENTS_AND_TWO_ORIGINALS')
    def identity_rejection(self,phase,message):
        w=World(phase,phase)
        with self.assertRaisesRegex(AssertionError,message):w.execute()
        self.assertTrue(w.changed);self.assertFalse((w.out/'APPLIED.json').exists())
        for row in w.substitutions:self.assertEqual(sha(Path(row['retained_original'])),row['sha256']);self.assertEqual(nfs.file_identity(real_lstat(Path(row['retained_original']))),row['before'])
        w.record(self.id(),'IDENTITY_SUBSTITUTION_DENIED_AT_'+phase)
    def test_original_identity_before_preservation(self):self.identity_rejection('before_preserve','Original identity changed before preservation')
    def test_original_identity_before_replace(self):self.identity_rejection('before_replace','Original identity changed before replacement')
    def test_native_backup_identity_after_replace(self):self.identity_rejection('after_replace','Retained original identity differs')
    def test_native_backup_identity_final_recheck(self):self.identity_rejection('final_backup','')
    def test_stale_status_bytes_deny_before_publication(self):
        w=World('stale');path=w.trigger_target;path.write_bytes(path.read_bytes()+b'\n');original=ordinary(path)
        with self.assertRaises(AssertionError):w.execute()
        self.assertEqual(ordinary(path),original);self.assertFalse(w.out.exists());w.record(self.id(),'STALE_STATUS_DENIED_BEFORE_OUTPUT_CREATION')
    def test_typed_persisted_review_substitution_denied(self):
        w=World('typed-persisted');w.mutate_json(w.runtime/RUN/'receipts/review.json',lambda v:v.update(exit_status=False))
        with self.assertRaises(AssertionError):w.execute()
        self.assertFalse(w.out.exists());w.record(self.id(),'PERSISTED_BOOL_IS_NOT_INTEGER_ZERO')
    def test_matching_local_and_stored_boolean_exit_denied(self):
        w=World('typed-both')
        for p in [w.runtime/'independent-review/review.json',w.runtime/RUN/'receipts/review.json']:w.mutate_json(p,lambda v:v.update(exit_status=False))
        with self.assertRaises(AssertionError):w.execute()
        self.assertFalse(w.out.exists());w.record(self.id(),'MATCHING_BOOL_FALSE_CANNOT_APPROVE')
    def test_boolean_helper_exit_denied(self):
        w=World('typed-helper');w.mutate_json(w.runtime/'independent-review/publication-helper-review.json',lambda v:v.update(exit_status=False))
        with self.assertRaises(AssertionError):w.execute()
        self.assertFalse(w.out.exists());w.record(self.id(),'HELPER_BOOL_FALSE_CANNOT_APPROVE')
    def test_primary_control_preserved_when_journal_and_annotation_fail(self):
        class Primary(KeyboardInterrupt):
            def add_note(self,value):raise RuntimeError('owned annotation failure')
        w=World('primary');primary=Primary('owned native boundary');original_save=helper.save
        def fail_publish(*args):raise primary
        def save(path,value):
            if path.name=='FAILED.json':raise OSError('owned failure journal denial')
            return original_save(path,value)
        w.publish=fail_publish
        with patch.object(helper,'save',side_effect=save):
            with self.assertRaises(Primary) as caught:w.execute()
        self.assertIs(caught.exception,primary);self.assertEqual(w.published,[]);w.record(self.id(),'EXACT_PRIMARY_OBJECT_PRESERVED')
    def test_second_publication_failure_preserves_partial_result_and_originals(self):
        w=World('second-failure','second_fail')
        with self.assertRaisesRegex(OSError,'owned second native publication denial'):w.execute()
        failure=read(w.out/'FAILED.json');self.assertEqual(len(failure['completed']),1);self.assertEqual(len(failure['before_images']),2)
        self.assertEqual(sha(w.trigger_backup),manifest['payloads'][0]['active_before_sha256'])
        self.assertEqual(sha(w.mirror/'handoff/continuity.json'),manifest['payloads'][1]['active_before_sha256'])
        self.assertFalse((w.out/'APPLIED.json').exists());w.record(self.id(),'PARTIAL_TWO_PATH_PUBLICATION_EXPLICIT_AND_RECOVERABLE')
    def test_occupied_output_directory_denied(self):
        w=World('occupied-output');w.out.mkdir();sentinel=w.out/'sentinel';nfs.write_new(sentinel,b'owned existing output');original=ordinary(sentinel)
        with self.assertRaises(FileExistsError):w.execute()
        self.assertEqual(ordinary(sentinel),original);self.assertEqual(w.published,[]);w.record(self.id(),'EXISTING_APPLICATION_ROOT_NOT_REUSED')
    def test_exact_claim_prefix_passes_without_lifecycle_calls(self):
        w=World('claim-positive');(w.runtime/RUN/'claims.json').write_text('{}',encoding='utf8');prefix(w,'claim');w.record(self.id(),'EXACT_CLAIM_PREFIX_PASSES_BEFORE_INVOKE')
    def test_exact_claim_prefix_denies_changed_current_status(self):
        w=World('claim-stale');(w.runtime/RUN/'claims.json').write_text('{}',encoding='utf8');w.trigger_target.write_bytes(w.trigger_target.read_bytes()+b'\n')
        with self.assertRaises(AssertionError):prefix(w,'claim')
        self.assertFalse(w.out.exists());w.record(self.id(),'EXACT_CLAIM_PREFIX_DENIES_STALE_STATUS')
    def test_exact_completion_prefix_passes_with_native_fixture_publication(self):
        w=World('complete-positive');w.execute();prefix(w,'complete');w.record(self.id(),'EXACT_COMPLETION_PREFIX_WITH_NATIVE_ORIGINALS_PASSES')
    def test_exact_completion_prefix_denies_same_bytes_changed_backup_identity(self):
        w=World('complete-backup');w.execute();w.substitute(w.trigger_backup)
        with self.assertRaises(AssertionError):prefix(w,'complete')
        w.record(self.id(),'EXACT_COMPLETION_PREFIX_DENIES_ORIGINAL_IDENTITY_DRIFT')
    def test_exact_completion_prefix_denies_baseline_artifact_drift(self):
        w=World('complete-baseline');w.execute();path=w.runtime/'ACCEPTED-SOURCE-BASELINE.json';path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaises(AssertionError):prefix(w,'complete')
        w.record(self.id(),'EXACT_COMPLETION_PREFIX_DENIES_BASELINE_HASH_DRIFT')

suite=unittest.defaultTestLoader.loadTestsFromTestCase(WrapperTests);expected=[t.id() for t in suite];executed=[]
class Result(unittest.TextTestResult):
    def startTest(self,test):executed.append(test.id());super().startTest(test)
started=utc()
with (V/'wrapper-tests-r2.txt').open('x',encoding='utf-8') as stream:result=unittest.TextTestRunner(stream=stream,verbosity=2,resultclass=Result).run(suite)
source_after={rel:ordinary(F/rel) for rel in inspection['source_native']};active_after={rel:ordinary(F/rel) for rel in inspection['active_metadata_native']};candidate_after={rel:ordinary(Q/rel) for rel in inspection['candidate_native']}
conserved=source_after==inspection['source_native'] and active_after==inspection['active_metadata_native'] and candidate_after==inspection['candidate_native']
passed=result.wasSuccessful() and not result.skipped and expected==executed and conserved
proof={'executor':ACTOR,'started_at':started,'finished_at':utc(),'publication_script_sha256':H,'integration_script_sha256':I,'manifest_sha256':M,
    'tests_run':result.testsRun,'expected_ids':expected,'executed_ids':executed,'failures':len(result.failures),'errors':len(result.errors),'skips':len(result.skipped),
    'failed_details':[{'id':t.id(),'traceback':trace} for t,trace in result.failures+result.errors],'raw_output':ref(V/'wrapper-tests-r2.txt'),'observations':observations,
    'source290_metadata2_candidate3_native_conserved':conserved,'Source_mutations':[],'actual_lifecycle_transitions':[],'native_processes_launched':0,
    'qualification':'Exact publisher main and exact pre-transition integration assertions execute on fresh reviewer-owned native targets. Synthetic claims/review records are expressly unqualified as authority. Only manifest source identities are rebound to fresh fixture originals; all accepted ledgers, manifest SHA, candidate bytes and Source290 bindings remain real. Native ReplaceFileW effects stay inside reviewer scope. Completion prefix stops before consumer file outputs and installed lifecycle snapshot.',
    'exit_status':0 if passed else 1}
save(V/'wrapper-tests-r2.json',proof);print(json.dumps({k:proof[k] for k in ('tests_run','failures','errors','skips','exit_status')}),flush=True)
raise SystemExit(proof['exit_status'])
