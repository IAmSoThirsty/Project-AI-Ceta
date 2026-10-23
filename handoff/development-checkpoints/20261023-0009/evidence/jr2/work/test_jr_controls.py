"""Disposable observation/report/actual-runtime guards; no canonical case runs."""
from pathlib import Path
from datetime import datetime,timezone
from types import ModuleType,SimpleNamespace
import importlib.util,json,sys,unittest,uuid
from unittest.mock import patch
import run_canonical_journal as r

W=Path(__file__).resolve().parent
class Controls(unittest.TestCase):
    def setUp(self):
        self.base=W/'controls'/uuid.uuid4().hex[:6];self.base.mkdir(parents=True)
        self.fixture=self.base/'fixture';self.fixture.mkdir()
        self.output=self.base/'output';self.output.mkdir()
    def engine(self,action=lambda:None,source=None,authorize=None):
        class Case(unittest.TestCase):
            def runTest(self):action()
        case=Case();suite=unittest.TestSuite([case])
        return r.run_observed(suite,[case.id()],self.output,{'fixture':self.fixture},
            source or (lambda:{'source':'pinned'}),authorize or (lambda:{}))

    def test_complete_tree_includes_root_empty_and_nested_ignored_directories(self):
        p=self.fixture/'.agents/empty';p.mkdir(parents=True);(self.fixture/'.git').mkdir()
        (self.fixture/'.git/record').write_bytes(b'ignored-name-data')
        before=r.snapshot(self.fixture)
        self.assertIn('.',before);self.assertIn('.agents/empty/',before);self.assertIn('.git/record',before)
        (self.fixture/'new').mkdir();after=r.snapshot(self.fixture)
        self.assertTrue(r.preservation(before,after));self.assertEqual(before['.agents/empty/'],after['.agents/empty/'])

    def test_root_scandir_permission_error_is_exact_and_never_partial_success(self):
        error=PermissionError('root enumeration refused')
        with patch.object(r.os,'scandir',side_effect=error),self.assertRaises(PermissionError) as caught:r.snapshot(self.fixture)
        self.assertIs(caught.exception,error)

    def test_nested_scandir_permission_error_is_exact(self):
        nested=self.fixture/'nested';nested.mkdir();original=r.os.scandir;error=PermissionError('nested refused')
        def scan(path):
            if Path(path)==nested:raise error
            return original(path)
        with patch.object(r.os,'scandir',scan),self.assertRaises(PermissionError) as caught:r.snapshot(self.fixture)
        self.assertIs(caught.exception,error)

    def test_preexisting_file_bytes_and_native_identity_must_stay_exact(self):
        p=self.fixture/'existing';p.write_bytes(b'before');before=r.snapshot(self.fixture)
        p.write_bytes(b'after')
        with self.assertRaises(AssertionError):r.preservation(before,r.snapshot(self.fixture))

    def test_empty_directory_disappearance_is_not_preservation(self):
        p=self.fixture/'empty';p.mkdir();before=r.snapshot(self.fixture);p.rmdir()
        with self.assertRaises(AssertionError):r.preservation(before,r.snapshot(self.fixture))

    def test_replaced_empty_directory_identity_is_not_preservation(self):
        p=self.fixture/'empty';p.mkdir();replacement=self.base/'replacement';replacement.mkdir()
        before=r.snapshot(self.fixture);p.rmdir();replacement.rename(p);after=r.snapshot(self.fixture)
        self.assertNotEqual(before['empty/']['inode'],after['empty/']['inode'])
        with self.assertRaisesRegex(AssertionError,'directory replaced'):r.preservation(before,after)

    def test_module_spec_origin_is_a_path_not_the_spec_object(self):
        p=self.base/'dependency.py';p.write_bytes(b'identity only')
        module=ModuleType('controlled_dependency');module.__spec__=SimpleNamespace(origin=str(p))
        identity=r.module_origin(module)
        self.assertEqual(identity['origin'],str(p.resolve()));self.assertEqual(identity['native']['sha256'],r.sha(p))

    def test_Git_status_wire_uses_original_NUL_serialization_exactly(self):
        raw=b' M controlled-file\0?? controlled-new\0';commands=[]
        expected=dict(root=str(r.F),branch='refs/heads/controlled',head='controlled-head',origin='controlled-origin',
            status_sha256=r.hashlib.sha256(raw).hexdigest(),index_native={'controlled_native':True})
        def git(command,**kwargs):
            commands.append(command)
            if 'status' in command:
                self.assertEqual(command[-4:],['status','--porcelain=v1','-z','--untracked-files=all'])
                return raw
            if command[-2:]==['rev-parse','--show-toplevel']:return str(r.F).encode()+b'\n'
            if command[-3:]==['rev-parse','--git-path','index']:return b'.git/index\n'
            if command[-2:]==['symbolic-ref','HEAD']:return b'refs/heads/controlled\n'
            if command[-2:]==['rev-parse','HEAD']:return b'controlled-head\n'
            if command[-3:]==['remote','get-url','origin']:return b'controlled-origin\n'
            raise AssertionError(command)
        with patch.object(r.subprocess,'check_output',git),patch.object(r,'stable',return_value=({'controlled_native':True},b'')):
            self.assertEqual(r.git_observation(expected),expected)
        self.assertTrue(all(c[:4]==['git','--no-optional-locks','-c','core.fsmonitor=false'] for c in commands))

    def test_module_copy_and_ROOT_substitution_refused_before_case_loading(self):
        packet=json.loads((W.parent/'packet/INPUTS.json').read_bytes());name=packet['selected'][0]
        module=ModuleType(name);module.__file__=str(r.F/'tests/contract'/(name+'.py'));module.ROOT=self.base
        with patch.dict(sys.modules,{name:module}),self.assertRaises(AssertionError):r.canonical_suite(packet)
        module.__file__=str(self.base/'copied_module.py');module.ROOT=r.F
        with patch.dict(sys.modules,{name:module}),self.assertRaises(AssertionError):r.canonical_suite(packet)
        self.assertEqual(list(self.output.iterdir()),[])

    def test_synthetic_success_requires_process_zero_and_exact_seal(self):
        self.assertEqual(self.engine(lambda:(self.fixture/'new').write_bytes(b'new fixture')),0)
        self.assertTrue(r.execution_complete(self.output,0));self.assertFalse(r.execution_complete(self.output,1))
        self.assertFalse(r.execution_complete(self.output,True))
        with (self.output/'events.jsonl').open('ab') as stream:stream.write(b'changed')
        self.assertFalse(r.execution_complete(self.output,0))

    def test_failure_and_skip_never_report_cohort_success(self):
        self.assertEqual(self.engine(lambda:(_ for _ in ()).throw(AssertionError('controlled assertion'))),1)
        self.assertFalse(r.execution_complete(self.output,0))
        report=json.loads((self.output/'RESULT.json').read_bytes());self.assertEqual(report['failures'],1)
        self.assertIn('controlled assertion',report['test_error_details'][0]['error']['message'])

    def test_skip_is_retained_and_not_success(self):
        self.assertEqual(self.engine(lambda:(_ for _ in ()).throw(unittest.SkipTest('controlled skip'))),1)
        report=json.loads((self.output/'RESULT.json').read_bytes());self.assertEqual(len(report['skips']),1)
        self.assertFalse(r.execution_complete(self.output,0))

    def test_primary_and_fixture_observation_error_keep_exact_objects(self):
        primary=KeyboardInterrupt('controlled body');secondary=PermissionError('after unreadable');original=r.snapshot;calls=[0]
        def snapshot(base):
            calls[0]+=1
            if calls[0]>1:raise secondary
            return original(base)
        with patch.object(r,'snapshot',snapshot),self.assertRaises(KeyboardInterrupt) as caught:
            self.engine(lambda:(_ for _ in ()).throw(primary))
        self.assertIs(caught.exception,primary)
        self.assertIs(BaseException.__dict__['__dict__'].__get__(primary)['runner_secondary_errors'][0],secondary)
        report=json.loads((self.output/'RESULT.json').read_bytes())
        self.assertEqual(len(report['started_test_ids']),1);self.assertEqual(report['cleanup'][0]['type'],'PermissionError')
        self.assertFalse(r.execution_complete(self.output,1))

    def test_source_after_fault_is_not_silently_accepted(self):
        error=OSError('after source');calls=[0]
        def source():
            calls[0]+=1
            if calls[0]>1:raise error
            return {'source':'pin'}
        with self.assertRaises(OSError) as caught:self.engine(source=source)
        self.assertIs(caught.exception,error);self.assertTrue((self.output/'RESULT.json').is_file())
        self.assertFalse(r.execution_complete(self.output,0))

    def test_second_fixture_after_observation_runs_when_first_fails(self):
        second=self.base/'second';second.mkdir();original=r.snapshot;calls=[];error=PermissionError('first after unavailable')
        def snapshot(path):
            calls.append(path)
            if len(calls)>2 and path==self.fixture:raise error
            return original(path)
        case=unittest.FunctionTestCase(lambda:None)
        with patch.object(r,'snapshot',snapshot),self.assertRaises(PermissionError) as caught:
            r.run_observed(unittest.TestSuite([case]),[case.id()],self.output,{'first':self.fixture,'second':second},lambda:{'source':'pin'},lambda:{})
        self.assertIs(caught.exception,error);self.assertEqual(calls,[self.fixture,second,self.fixture,second])
        report=json.loads((self.output/'RESULT.json').read_bytes());self.assertIn('second',report['fixtures_after'])
        self.assertFalse(r.execution_complete(self.output,0))

    def test_result_writer_failure_after_bytes_written_never_becomes_success(self):
        error=OSError('RESULT fsync uncertainty');original=r.save
        def save(path,value):
            original(path,value)
            if path.name=='RESULT.json':raise error
        with patch.object(r,'save',save),self.assertRaises(OSError) as caught:self.engine()
        self.assertIs(caught.exception,error);self.assertTrue((self.output/'REPORT-ERROR.json').is_file())
        self.assertFalse(r.execution_complete(self.output,0))

    def test_seal_failure_after_bytes_written_never_becomes_success(self):
        error=OSError('SEAL close uncertainty');original=r.save
        def save(path,value):
            original(path,value)
            if path.name=='REPORT-SEAL.json':raise error
        with patch.object(r,'save',save),self.assertRaises(OSError) as caught:self.engine()
        self.assertIs(caught.exception,error);self.assertFalse(r.execution_complete(self.output,0))

    def test_create_only_replay_refused_before_test_body(self):
        self.engine();called=[]
        with self.assertRaises(AssertionError):self.engine(lambda:called.append(True))
        self.assertEqual(called,[])

    def live(self,claim_nodes=True):
        sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
        from taar.orchestration_graph import compile_graph
        from taar.orchestration_runtime import OrchestrationRuntime
        control=self.base/'c';control.mkdir();empty=self.base/'ro';empty.mkdir()
        paths={'integrate':self.output,'read_budget':self.base/'read-budget','opdiag':self.fixture}
        paths['read_budget'].mkdir()
        nodes={n:dict(kind='agent',role=role,access='read_only') for n,role in [('discover','explorer'),('plan','architect'),('implement','worker'),('review','reviewer')]}
        nodes['validate']=dict(kind='gate',access='read_only',commands=['"'+sys.executable+'" -B -c "print(1)"'])
        for n,p in paths.items():nodes[n]=dict(kind='integration' if n=='integrate' else 'agent',role='integrator' if n=='integrate' else 'worker',access='write_scoped',write_scope=[p.relative_to(self.base).as_posix()+'/**'])
        edges=[dict(id='e'+str(i),**{'from':a,'to':b,'type':t}) for i,(a,b,t) in enumerate([
            ('discover','plan','depends_on'),('plan','implement','delegates_to'),('implement','review','requires_review'),
            ('review','validate','authorizes'),('validate','integrate','gates'),('validate','read_budget','depends_on'),('validate','opdiag','depends_on')])]
        document=dict(version=1,graph=dict(id='t_drive_repository_change',policy=dict(fail_closed=True,max_parallel=8,require_receipts=True,prohibit_self_review=True,prohibit_scope_overlap=True),nodes=nodes,edges=edges))
        (control/'AGENTS.md').write_text('```agents-graph\n'+json.dumps(document)+'\n```\n')
        graph=compile_graph(self.base,control);runtime=OrchestrationRuntime(control);run='disposable';runtime.init_run(graph,run)
        for node in ('discover','plan','implement','review','validate'):
            executor='astra' if node=='review' else 'author'
            c=runtime.claim(run,node,executor,workspace=empty)['claim']
            if node=='validate':runtime.run_gate(run,node);continue
            receipt=dict(schema_version=1,run_id=run,node_id=node,executor_id=executor,started_at=c['claimed_at'],finished_at=datetime.now(timezone.utc).isoformat(),input_hash=c['input_hash'],changed_files=[],result={'manifest_sha256':'controlled'},commands=[],validations=[],exit_status=0)
            if node=='review':receipt['decision']='approved'
            p=self.base/(node+'.json');r.save(p,receipt);runtime.complete(run,node,p)
        if claim_nodes:
            for node,p in paths.items():runtime.claim(run,node,'/root',workspace=p)
        return dict(control=str(control),run_id=run,graph_root=str(self.base),graph_fingerprint=graph.fingerprint,prepared_manifest_sha256='controlled',workspaces={n:str(p) for n,p in paths.items()}),runtime

    def test_actual_three_Root_claims_accept_and_wrong_contexts_refuse(self):
        binding,runtime=self.live();claims=r.require_live(binding);self.assertEqual(set(claims),{'integrate','read_budget','opdiag'})
        for key,value in [('run_id','wrong'),('control',str(self.base/'wrong')),('graph_root',str(self.fixture)),('graph_fingerprint','wrong'),('prepared_manifest_sha256','wrong')]:
            wrong=dict(binding);wrong[key]=value
            with self.subTest(key=key),self.assertRaises(Exception):self.engine(authorize=lambda:r.require_live(wrong))
            self.assertEqual(list(self.output.iterdir()),[])

    def test_READY_only_authority_refuses_before_first_test_or_report_write(self):
        binding,runtime=self.live(False);called=[]
        with self.assertRaises(AssertionError):self.engine(lambda:called.append(True),authorize=lambda:r.require_live(binding))
        self.assertEqual(called,[]);self.assertEqual(list(self.output.iterdir()),[])

    def test_wrong_actual_executor_refuses_before_first_write(self):
        binding,runtime=self.live(False)
        for node,p in binding['workspaces'].items():runtime.claim(binding['run_id'],node,'other',workspace=Path(p))
        with self.assertRaises(AssertionError):self.engine(authorize=lambda:r.require_live(binding))
        self.assertEqual(list(self.output.iterdir()),[])

    def test_invalid_actual_stored_receipt_refuses_before_first_write(self):
        binding,runtime=self.live();path=Path(binding['control'])/binding['run_id']/'receipts/review.json'
        raw=path.read_bytes();r.save(self.base/'original-review.json',json.loads(raw))
        value=json.loads(raw);value['result']['manifest_sha256']='tampered';path.write_text(json.dumps(value))
        with self.assertRaises(Exception):self.engine(authorize=lambda:r.require_live(binding))
        self.assertEqual(list(self.output.iterdir()),[])

    def test_original_nonstring_exception_storage_keeps_primary_and_writes_result(self):
        primary=KeyboardInterrupt('original exact body failure')
        dict.__setitem__(BaseException.__dict__['__dict__'].__get__(primary),7,'legal storage')
        with self.assertRaises(KeyboardInterrupt) as caught:self.engine(lambda:(_ for _ in ()).throw(primary))
        self.assertIs(caught.exception,primary)
        attrs=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(attrs['runner_primary_exc_info'][1],primary)
        self.assertIsNotNone(attrs['runner_primary_exc_info'][2])
        report=json.loads((self.output/'RESULT.json').read_bytes())
        self.assertEqual(report['primary']['message'],'original exact body failure')
        self.assertIn({'key':7,'value':'legal storage'},report['primary']['storage'])
        self.assertFalse(report['test_cohort_passed']);self.assertFalse(r.execution_complete(self.output,0))

    def test_diagnostic_uses_raw_descriptors_and_never_hostile_formatters(self):
        called=[]
        class HostileError(Exception):
            def __str__(self):called.append('str');raise AssertionError('str called')
            def __repr__(self):called.append('repr');raise AssertionError('repr called')
            def __getattribute__(self,key):
                if key in ('args','__dict__','__traceback__','__cause__','__context__','__suppress_context__'):
                    called.append(key);raise AssertionError('property called')
                return super().__getattribute__(key)
        class HostileMeta(type):
            def __eq__(cls,other):called.append('type equality');raise RuntimeError('type equality called')
            def __hash__(cls):called.append('type hash');raise RuntimeError('type hash called')
            @property
            def __name__(cls):called.append('type name provider');raise AssertionError('type name provider called')
        class HostileValue(metaclass=HostileMeta):
            @property
            def __class__(self):called.append('class provider');raise RuntimeError('class provider called')
            def __str__(self):called.append('value str');raise AssertionError('value str called')
            def __repr__(self):called.append('value repr');raise AssertionError('value repr called')
        class HostileName(str):
            def __getitem__(self,key):called.append('name slice');raise AssertionError('name slice called')
        type.__dict__['__name__'].__set__(HostileValue,HostileName('HostileValue'))
        class HostileDictionary(dict):
            def __len__(self):called.append('dict len');raise AssertionError('dict len called')
            def items(self):called.append('dict items');raise AssertionError('dict items called')
        error=HostileError('raw message',HostileValue())
        BaseException.__dict__['__dict__'].__set__(error,HostileDictionary())
        attrs=BaseException.__dict__['__dict__'].__get__(error)
        dict.__setitem__(attrs,HostileValue(),HostileValue())
        observation=r.diagnostic(error);json.dumps(observation,allow_nan=False)
        self.assertEqual(observation['message'],'raw message');self.assertEqual(called,[])
        self.assertEqual(self.engine(lambda:(_ for _ in ()).throw(error)),1)
        self.assertEqual(called,[]);self.assertTrue((self.output/'RESULT.json').is_file())

    def test_diagnostic_bounds_cycles_large_storage_and_unsupported_values(self):
        error=ValueError('x'*2000);items=[];items.append(items)
        attrs=BaseException.__dict__['__dict__'].__get__(error)
        dict.__setitem__(attrs,'self',error);dict.__setitem__(attrs,'loop',items)
        for i in range(1000):dict.__setitem__(attrs,i,[object(),10**10000]*100)
        BaseException.__dict__['__cause__'].__set__(error,error)
        observation=r.diagnostic(error);wire=json.dumps(observation,allow_nan=False)
        self.assertLess(len(wire),20000);self.assertEqual(len(observation['message']),512)
        self.assertTrue(observation['storage_truncated']);self.assertIn('"cycle": true',wire)

    def test_primary_formatter_fault_is_secondary_with_exact_original_triple(self):
        primary=KeyboardInterrupt('original');fault=RuntimeError('primary formatter fault');original=r.diagnostic
        def formatter(error):
            if error is primary:raise fault
            return original(error)
        with patch.object(r,'diagnostic',formatter),self.assertRaises(KeyboardInterrupt) as caught:
            self.engine(lambda:(_ for _ in ()).throw(primary))
        self.assertIs(caught.exception,primary)
        attrs=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(attrs['runner_secondary_errors'][0],fault)
        triple=attrs['runner_primary_exc_info'];self.assertIs(triple[0],KeyboardInterrupt);self.assertIs(triple[1],primary)
        self.assertTrue((self.output/'RESULT.json').is_file());self.assertFalse(r.execution_complete(self.output,0))

    def test_secondary_formatter_fault_keeps_body_and_all_secondary_objects(self):
        primary=KeyboardInterrupt('original');cleanup=PermissionError('cleanup');fault=RuntimeError('secondary formatter')
        original_diag=r.diagnostic;calls=[0]
        def source():
            calls[0]+=1
            if calls[0]>1:raise cleanup
            return {'source':'pin'}
        def formatter(error):
            if error is cleanup:raise fault
            return original_diag(error)
        with patch.object(r,'diagnostic',formatter),self.assertRaises(KeyboardInterrupt) as caught:
            self.engine(lambda:(_ for _ in ()).throw(primary),source=source)
        self.assertIs(caught.exception,primary)
        errors=BaseException.__dict__['__dict__'].__get__(primary)['runner_secondary_errors']
        self.assertEqual(len(errors),2);self.assertIs(errors[0],cleanup);self.assertIs(errors[1],fault)
        self.assertTrue((self.output/'RESULT.json').is_file())

    def test_report_assembly_fault_is_secondary_and_fallback_result_is_create_only(self):
        primary=KeyboardInterrupt('original');fault=RuntimeError('report assembly')
        with patch.object(r,'result_fields',side_effect=fault),self.assertRaises(KeyboardInterrupt) as caught:
            self.engine(lambda:(_ for _ in ()).throw(primary))
        self.assertIs(caught.exception,primary)
        self.assertIs(BaseException.__dict__['__dict__'].__get__(primary)['runner_secondary_errors'][0],fault)
        report=json.loads((self.output/'RESULT.json').read_bytes());self.assertTrue(report['report_assembly_failed'])
        self.assertFalse(r.execution_complete(self.output,0));before=(self.output/'RESULT.json').read_bytes()
        with self.assertRaises(AssertionError):self.engine()
        self.assertEqual((self.output/'RESULT.json').read_bytes(),before)

    def test_formatter_fault_for_unittest_error_retains_body_object(self):
        primary=ValueError('unittest body');fault=RuntimeError('formatter');original=r.diagnostic
        def formatter(error):
            if error is primary:raise fault
            return original(error)
        with patch.object(r,'diagnostic',formatter),self.assertRaises(ValueError) as caught:
            self.engine(lambda:(_ for _ in ()).throw(primary))
        self.assertIs(caught.exception,primary)
        self.assertTrue(any(e is fault for e in BaseException.__dict__['__dict__'].__get__(primary)['runner_secondary_errors']))
        self.assertTrue((self.output/'RESULT.json').is_file())

    def test_nonstring_storage_subtest_failure_is_recorded_without_formatting_error(self):
        primary=AssertionError('subtest body');BaseException.__dict__['__dict__'].__get__(primary)[7]='legal'
        class Case(unittest.TestCase):
            def runTest(self):
                with self.subTest(index=7):raise primary
        case=Case()
        status=r.run_observed(unittest.TestSuite([case]),[case.id()],self.output,{'fixture':self.fixture},lambda:{},lambda:{})
        self.assertEqual(status,1);report=json.loads((self.output/'RESULT.json').read_bytes())
        self.assertEqual(report['failures'],1);self.assertEqual(report['test_error_details'][0]['kind'],'subtest')
        self.assertFalse(r.execution_complete(self.output,0))

if __name__=='__main__':unittest.main(verbosity=2)
