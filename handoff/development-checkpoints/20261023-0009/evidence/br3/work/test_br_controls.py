"""Disposable actual-runtime and complete-observation guards; no product bodies."""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
import copy,json,os,sys,unittest,uuid
from unittest.mock import patch
import complete_observer as o
import bound_runtime as a
import run_broader as b

W=Path(__file__).resolve().parent
class Controls(unittest.TestCase):
    def setUp(self):
        self.base=W/'controls'/uuid.uuid4().hex[:8];self.base.mkdir(parents=True)
        self.fixture=self.base/'fixture';self.fixture.mkdir();self.output=self.base/'output';self.output.mkdir()

    def receipt(self,runtime,run,node,executor,workspace,result=None,decision=None,reported=None):
        state=json.loads((runtime.runtime_root/run/'state.json').read_bytes());c=state['nodes'][node]['claim']
        changed=(a.stock._changed_files(c['baseline_snapshot'],a.stock._snapshot_workspace(workspace,self.base))
            if reported is None else reported)
        value=dict(schema_version=1,run_id=run,node_id=node,executor_id=executor,started_at=c['claimed_at'],
            finished_at=datetime.now(timezone.utc).isoformat(),input_hash=c['input_hash'],changed_files=changed,
            result=result or {'manifest_sha256':'controlled'},commands=[],validations=[],exit_status=0)
        if decision:value['decision']=decision
        path=self.base/(node+'-'+uuid.uuid4().hex[:5]+'.json');b.r.save(path,value);return path

    def live(self,through='validate',claim_all=False,bad_gate=False):
        control=self.base/'control';control.mkdir();packet=self.base/'packet';packet.mkdir()
        producer=self.base/'producer';producer.mkdir();review=self.base/'review';review.mkdir()
        paths={n:self.base/n for n in ['integrate',*(f'fixture_{i}' for i in range(6)),'js9']}
        for p in paths.values():p.mkdir()
        nodes={n:dict(kind='agent',role=role,access='read_only') for n,role in [('discover','explorer'),('plan','architect')]}
        nodes.update(implement=dict(kind='agent',role='worker',access='write_scoped',write_scope=['producer/**']),
            review=dict(kind='agent',role='reviewer',access='write_scoped',write_scope=['review/**']),
            validate=dict(kind='gate',access='read_only',commands=['"'+sys.executable+'" -B -c "'+('raise SystemExit(1)' if bad_gate else 'print(1)')+'"']))
        for node,path in paths.items():nodes[node]=dict(kind='integration' if node=='integrate' else 'agent',role='integrator' if node=='integrate' else 'worker',access='write_scoped',write_scope=[node+'/**'])
        # A stock-only adversary lets controls exercise capacity/overlap checks.
        nodes['extra']=dict(kind='agent',role='worker',access='write_scoped',write_scope=['fixture_0/**'])
        edges=[dict(id='e'+str(i),**{'from':x,'to':y,'type':t}) for i,(x,y,t) in enumerate([
            ('discover','plan','depends_on'),('plan','implement','delegates_to'),('implement','review','requires_review'),
            ('review','validate','authorizes'),('validate','integrate','gates'),*[('validate',n,'depends_on') for n in paths if n!='integrate'],('validate','extra','depends_on')])]
        doc=dict(version=1,graph=dict(id='t_drive_repository_change',policy=dict(fail_closed=True,max_parallel=8,
            prohibit_scope_overlap=True,prohibit_self_review=True,require_receipts=True),nodes=nodes,edges=edges))
        (control/'AGENTS.md').write_text('```agents-graph\n'+json.dumps(doc)+'\n```\n')
        graph=a.compile_graph(self.base,control);runtime=a.stock.OrchestrationRuntime(control);run='disposable'
        runtime.init_run(graph,run)
        for node in ('discover','plan','implement','review','validate'):
            workspace=producer if node=='implement' else review if node=='review' else packet
            executor='astra' if node=='review' else 'author'
            runtime.claim(run,node,executor,workspace=workspace)
            if node in ('implement','review'):
                (workspace/'visible').write_bytes(b'completed visible artifact')
                (workspace/'.agents').mkdir();(workspace/'.agents/ignored').write_bytes(b'complete manifest covers this separately')
            if node=='validate':
                try:runtime.run_gate(run,node)
                except Exception:
                    if not bad_gate:raise
            else:runtime.complete(run,node,self.receipt(runtime,run,node,executor,workspace,decision='approved' if node=='review' else None))
            if node==through:break
        binding=dict(run_id=run,control=str(control),graph_root=str(self.base),graph_fingerprint=graph.fingerprint,
            prepared_manifest_sha256='controlled',workspaces={n:str(p) for n,p in paths.items()})
        expected={k:copy.deepcopy(binding[k]) for k in ('run_id','control','graph_root','workspaces')}
        context=patch.object(a,'expected_context',return_value=expected);context.start();self.addCleanup(context.stop)
        bound=a.BoundRuntime(binding)
        if claim_all:
            for node,p in paths.items():bound.claim(run,node,'/root',workspace=p)
        return binding,bound,runtime,paths

    def test_complete_ignored_empty_native_and_projection_bijection(self):
        nested=self.fixture/'.agents/deep/empty';nested.mkdir(parents=True)
        (self.fixture/'.agents/deep/data').write_bytes(b'ignored bytes')
        (self.fixture/'.project-ai/automation').mkdir(parents=True)
        before=o.snapshot(self.fixture);self.assertIn('.',before);self.assertIn('.agents/deep/empty/',before)
        projected=o.projection(self.fixture,self.base)
        self.assertEqual(projected,b.project_observation(self.fixture,self.base,before))
        self.assertEqual(len(projected),len(before));self.assertTrue(all('\\\\?\\' not in k for k in projected))
        (self.fixture/'new').mkdir();self.assertTrue(o.preservation(before,o.snapshot(self.fixture)))

    def test_actual_extended_path_longer_than_260_is_complete(self):
        p=self.fixture
        for i in range(6):p=p/(str(i)+'x'*48);o.physical(p).mkdir()
        file=p/'payload';o.physical(file).write_bytes(b'long-path controlled bytes')
        self.assertGreater(len(str(file)),260)
        if sys.platform=='win32':self.assertTrue(str(o.physical(file)).startswith('\\\\?\\'))
        observed=o.snapshot(self.fixture);key=file.relative_to(self.fixture).as_posix()
        self.assertEqual(observed[key]['sha256'],b.hashlib.sha256(b'long-path controlled bytes').hexdigest())
        self.assertIn(key,o.snapshot(self.fixture))

    def test_root_and_nested_permission_errors_keep_exact_identity(self):
        nested=self.fixture/'nested';nested.mkdir();original=o.os.scandir
        for target in (self.fixture,nested):
            error=PermissionError('exact scandir refusal')
            def scan(path):
                if str(path)==str(o.physical(target)):raise error
                return original(path)
            with self.subTest(target=target.name),patch.object(o.os,'scandir',scan),self.assertRaises(PermissionError) as caught:o.snapshot(self.fixture)
            self.assertIs(caught.exception,error)

    def test_ignored_file_native_and_empty_directory_replacement_refuse(self):
        file=self.fixture/'.agents/data';file.parent.mkdir();file.write_bytes(b'before')
        empty=self.fixture/'empty';empty.mkdir();before=o.snapshot(self.fixture)
        file.write_bytes(b'after')
        with self.assertRaises(AssertionError):o.preservation(before,o.snapshot(self.fixture))
        file.write_bytes(b'before');before=o.snapshot(self.fixture)
        replacement=self.base/'replacement';replacement.mkdir();empty.rmdir();replacement.rename(empty)
        with self.assertRaises(AssertionError):o.preservation(before,o.snapshot(self.fixture))

    def test_physical_alias_input_and_hardlink_refuse(self):
        with self.assertRaises(AssertionError):o.logical('\\\\?\\'+str(self.fixture))
        with self.assertRaises(AssertionError):o.logical(self.fixture/'..'/'outside')
        with self.assertRaises(AssertionError):o.logical(str(self.fixture/'ambiguous')+' ')
        first=self.fixture/'a';first.write_bytes(b'linked');os.link(o.physical(first),o.physical(self.fixture/'b'))
        with self.assertRaisesRegex(AssertionError,'alias'):o.snapshot(self.fixture)
        b.r.save(self.base/'hardlink-negative.json',dict(first_native=o.native(o.physical(first).lstat()),
            second_native=o.native(o.physical(self.fixture/'b').lstat()),bytes_sha256=b.hashlib.sha256(b'linked').hexdigest(),
            observed_alias_refused=True,known_disposable_second_alias_retired=True,original_bytes_preserved_at='fixture/a'))
        assert first.resolve(strict=True).is_relative_to(W.resolve(strict=True))
        assert (self.fixture/'b').resolve(strict=True).is_relative_to(W.resolve(strict=True))
        o.physical(self.fixture/'b').unlink()
        self.assertEqual(o.physical(first).read_bytes(),b'linked')

    def test_reparse_entry_refuses_before_child_read(self):
        target=self.fixture/'junction';target.mkdir();original=Path.lstat;read=[]
        def lstat(path,*args,**kwargs):
            actual=original(path,*args,**kwargs)
            if str(path)==str(o.physical(target)):
                return SimpleNamespace(st_mode=actual.st_mode,st_file_attributes=o.stat.FILE_ATTRIBUTE_REPARSE_POINT)
            return actual
        def scan(path):read.append(str(path));return original_scan(path)
        original_scan=o.os.scandir
        with patch.object(Path,'lstat',lstat),patch.object(o.os,'scandir',scan),self.assertRaisesRegex(AssertionError,'reparse'):o.snapshot(self.fixture)
        self.assertNotIn(str(o.physical(target)),read)

    def test_changed_directory_enumeration_refuses_partial_snapshot(self):
        original=o.os.scandir;calls=[0]
        def scan(path):
            calls[0]+=1
            if calls[0]==2:(self.fixture/'late').write_bytes(b'changed during view')
            return original(path)
        with patch.object(o.os,'scandir',scan),self.assertRaisesRegex(AssertionError,'directory changed'):o.snapshot(self.fixture)

    def test_complete_hook_only_eight_bases_stock_artifacts_unchanged(self):
        binding,bound,stock,paths=self.live();run=binding['run_id'];original=a.stock._snapshot_workspace
        before=json.loads((bound.runtime_root/run/'state.json').read_bytes())
        (paths['fixture_0']/'.agents/empty').mkdir(parents=True)
        (paths['fixture_0']/'.agents/bytes').write_bytes(b'bound ignored data')
        claimed=bound.claim(run,'fixture_0','/root',workspace=paths['fixture_0'])['claim']
        self.assertIn('fixture_0/.agents/bytes',claimed['baseline_snapshot']);self.assertIn('fixture_0/.agents/empty',claimed['baseline_snapshot'])
        self.assertIs(a.stock._snapshot_workspace,original)
        bound.verify(run)
        after=json.loads((bound.runtime_root/run/'state.json').read_bytes())
        for n in ('implement','review'):
            self.assertEqual(before['nodes'][n]['artifact_hash'],after['nodes'][n]['artifact_hash'])
            self.assertEqual(after['nodes'][n]['state'],'SUCCEEDED')
        self.assertTrue((self.base/'producer/.agents/ignored').is_file())

    def test_eight_real_leases_accept_ready_missing_wrong_contexts_refuse(self):
        binding,bound,stock,paths=self.live();run=binding['run_id']
        with self.assertRaises(AssertionError):a.require_live(binding)
        for key,value in [('run_id','wrong'),('control',str(self.fixture)),('graph_root',str(self.fixture)),('graph_fingerprint','wrong')]:
            wrong=copy.deepcopy(binding);wrong[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):a.BoundRuntime(wrong).verify(wrong['run_id'])
        for node,p in paths.items():bound.claim(run,node,'/root',workspace=p)
        claims=a.require_live(binding);self.assertEqual(set(claims),set(paths));self.assertEqual(len(claims),8)
        with self.assertRaises(a.stock.TransitionDenied) as caught:
            with bound.observation_port(run):stock.claim(run,'extra','/root',workspace=paths['fixture_0'])
        self.assertEqual(caught.exception.code,'EXECUTION_CAPACITY_EXHAUSTED')

    def test_implicit_widened_alias_unknown_and_wrong_executor_claims_refuse(self):
        binding,bound,stock,paths=self.live();run=binding['run_id'];before=(bound.runtime_root/run/'state.json').read_bytes()
        for node,executor,workspace in [('fixture_0','/root',None),('fixture_0','/root',self.base),
            ('fixture_0','other',paths['fixture_0']),('unknown','/root',self.fixture),
            ('fixture_0','/root',o.physical(paths['fixture_0']))]:
            with self.subTest(node=node,executor=executor,workspace=str(workspace)),self.assertRaises(AssertionError):bound.claim(run,node,executor,workspace=workspace)
        self.assertEqual((bound.runtime_root/run/'state.json').read_bytes(),before)

    def test_stock_overlap_check_is_preserved(self):
        binding,bound,stock,paths=self.live();run=binding['run_id']
        with bound.observation_port(run):stock.claim(run,'extra','/root',workspace=paths['fixture_0'])
        with self.assertRaises(a.stock.TransitionDenied) as caught:bound.claim(run,'fixture_0','/root',workspace=paths['fixture_0'])
        self.assertEqual(caught.exception.code,'WRITE_SCOPE_OVERLAP')

    def test_stock_self_review_and_actual_failed_gate_are_preserved(self):
        binding,bound,stock,paths=self.live(through='implement',bad_gate=True);run=binding['run_id']
        with self.assertRaises(a.stock.TransitionDenied) as caught:stock.claim(run,'review','author',workspace=self.base/'review')
        self.assertEqual(caught.exception.code,'SELF_REVIEW_PROHIBITED')
        stock.claim(run,'review','astra',workspace=self.base/'review')
        stock.complete(run,'review',self.receipt(stock,run,'review','astra',self.base/'review',decision='approved'))
        stock.claim(run,'validate','author',workspace=self.base/'packet')
        with self.assertRaises(a.stock.TransitionDenied):stock.run_gate(run,'validate')
        with self.assertRaises(AssertionError):bound.claim(run,'fixture_0','/root',workspace=paths['fixture_0'])
        state=json.loads((bound.runtime_root/run/'state.json').read_bytes());self.assertEqual(state['nodes']['validate']['state'],'FAILED')

    def test_stock_partial_claim_cannot_become_complete_authority(self):
        binding,bound,stock,paths=self.live();run=binding['run_id']
        stock.claim(run,'fixture_0','/root',workspace=paths['fixture_0'])
        for n,p in paths.items():
            if n!='fixture_0':bound.claim(run,n,'/root',workspace=p)
        with self.assertRaisesRegex(AssertionError,'partial claim'):a.require_live(binding)
        with self.assertRaisesRegex(AssertionError,'partial stock'):bound.changed_files(run,'fixture_0')

    def test_wrong_actual_executor_and_stale_actual_input_refuse(self):
        binding,bound,stock,paths=self.live(claim_all=True);run=binding['run_id'];path=bound.runtime_root/run/'state.json'
        original=json.loads(path.read_bytes())
        for field,value in [('executor_id','other'),('input_hash','stale')]:
            state=copy.deepcopy(original);state['nodes']['fixture_0']['claim'][field]=value
            path.write_text(json.dumps(state))
            with self.subTest(field=field),self.assertRaises(AssertionError):a.require_live(binding)
        self.assertEqual(list(paths['integrate'].iterdir()),[])

    def test_invalid_receipt_and_event_chain_remain_rejected(self):
        binding,bound,stock,paths=self.live();run=binding['run_id'];path=bound.runtime_root/run/'receipts/review.json'
        value=json.loads(path.read_bytes());value['result']['tampered_field']='tampered';path.write_text(json.dumps(value))
        with self.assertRaises(a.stock.TransitionDenied) as caught:bound.verify(run)
        self.assertEqual(caught.exception.code,'RECEIPT_VERIFICATION_FAILED')
        events=bound.runtime_root/run/'events.jsonl';rows=events.read_bytes().splitlines()
        first=json.loads(rows[0]);first['reason']='tampered event';rows[0]=json.dumps(first).encode()
        events.write_bytes(b'\n'.join(rows)+b'\n')
        with self.assertRaises(a.stock.TransitionDenied) as caught:bound.verify(run)
        self.assertEqual(caught.exception.code,'EVENT_LEDGER_CORRUPT')
        self.assertEqual(list(paths['integrate'].iterdir()),[])

    def test_completed_stock_artifact_mutation_invalidates_downstream(self):
        binding,bound,stock,paths=self.live();run=binding['run_id']
        (self.base/'producer/visible').write_bytes(b'mutated completed producer')
        with self.assertRaises(AssertionError):bound.verify(run)
        state=json.loads((bound.runtime_root/run/'state.json').read_bytes())
        self.assertNotEqual(state['nodes']['review']['state'],'SUCCEEDED')

    def test_complete_receipt_tracks_ignored_files_and_empty_directories(self):
        binding,bound,stock,paths=self.live();run=binding['run_id'];path=paths['fixture_0']
        bound.claim(run,'fixture_0','/root',workspace=path)
        (path/'.agents/empty').mkdir(parents=True);(path/'.agents/bytes').write_bytes(b'new controlled data')
        changed=bound.changed_files(run,'fixture_0');self.assertIn('fixture_0/.agents/empty',changed)
        receipt=self.receipt(stock,run,'fixture_0','/root',path,reported=changed)
        bound.complete(run,'fixture_0',receipt)
        self.assertEqual(bound.verify(run)['states']['fixture_0'],'SUCCEEDED')

    def test_out_of_scope_completion_is_still_denied_by_stock(self):
        binding,bound,stock,paths=self.live();run=binding['run_id'];path=paths['fixture_0']
        bound.claim(run,'fixture_0','/root',workspace=path)
        original=o.projection
        def projection(base,root):
            actual=original(base,root)
            if str(base)==str(path):actual['outside-assigned-base']='injected adverse observer value'
            return actual
        with patch.object(o,'projection',projection):
            changed=bound.changed_files(run,'fixture_0');receipt=self.receipt(stock,run,'fixture_0','/root',path,reported=changed)
            with self.assertRaises(a.stock.TransitionDenied) as caught:bound.complete(run,'fixture_0',receipt)
        self.assertEqual(caught.exception.code,'WRITE_SCOPE_VIOLATION')

    def engine(self,action=lambda:None,source=None,snapshot=None):
        case=unittest.FunctionTestCase(action);claims={'fixture':dict(baseline_snapshot=o.projection(self.fixture,self.base))}
        if snapshot is None:return b.cohort(unittest.TestSuite([case]),[case.id()],self.output,{'fixture':self.fixture},source or (lambda:{}),lambda:claims,metadata={'graph_root':str(self.base)})
        with patch.object(o,'snapshot',snapshot):return b.cohort(unittest.TestSuite([case]),[case.id()],self.output,{'fixture':self.fixture},source or (lambda:{}),lambda:claims,metadata={'graph_root':str(self.base)})

    def test_initial_fixture_drift_fails_before_first_test_or_report_write(self):
        file=self.fixture/'existing';file.write_bytes(b'baseline');claims={'fixture':dict(baseline_snapshot=o.projection(self.fixture,self.base))}
        file.write_bytes(b'drift');called=[];case=unittest.FunctionTestCase(lambda:called.append(True))
        with self.assertRaisesRegex(AssertionError,'actual claim baseline'):
            b.cohort(unittest.TestSuite([case]),[case.id()],self.output,{'fixture':self.fixture},lambda:{},lambda:claims,metadata={'graph_root':str(self.base)})
        self.assertEqual(called,[]);self.assertEqual(list(self.output.iterdir()),[])

    def test_frozen_fixture_drift_before_actual_lease_and_nonempty_bootstrap_refuse(self):
        file=self.fixture/'existing';file.write_bytes(b'frozen');frozen=o.snapshot(self.fixture)
        file.write_bytes(b'drift before lease');claims={'fixture':dict(baseline_snapshot=o.projection(self.fixture,self.base))}
        called=[];case=unittest.FunctionTestCase(lambda:called.append(True))
        for preserved in ({'fixture':frozen},{'fixture':{'absent':True}}):
            with self.subTest(frozen=preserved is frozen),self.assertRaises(AssertionError):
                b.cohort(unittest.TestSuite([case]),[case.id()],self.output,{'fixture':self.fixture},lambda:{},lambda:claims,
                    metadata={'graph_root':str(self.base)},preserved=preserved)
            self.assertEqual(called,[]);self.assertEqual(list(self.output.iterdir()),[])

    def test_primary_partial_write_cleanup_and_result_custody(self):
        primary=KeyboardInterrupt('original exact body failure');BaseException.__dict__['__dict__'].__get__(primary)[7]='legal'
        cleanup=PermissionError('after view');calls=[0];original=o.snapshot
        def source():
            calls[0]+=1
            if calls[0]>1:raise cleanup
            return {'source':'pinned'}
        def action():(self.fixture/'partial').write_bytes(b'preserved partial');raise primary
        with self.assertRaises(KeyboardInterrupt) as caught:self.engine(action,source=source)
        self.assertIs(caught.exception,primary)
        self.assertIs(BaseException.__dict__['__dict__'].__get__(primary)['runner_secondary_errors'][0],cleanup)
        self.assertEqual((self.fixture/'partial').read_bytes(),b'preserved partial')
        self.assertTrue((self.output/'RESULT.json').is_file());self.assertFalse(b.execution_complete(self.output,0))

    def test_second_after_view_attempted_after_first_permission_failure(self):
        other=self.base/'other';other.mkdir();fixtures={'first':self.fixture,'second':other}
        claims={n:dict(baseline_snapshot=o.projection(p,self.base)) for n,p in fixtures.items()}
        error=PermissionError('first after');original=o.snapshot;calls=[]
        def snapshot(path):
            calls.append(path)
            if len(calls)>2 and path==self.fixture:raise error
            return original(path)
        case=unittest.FunctionTestCase(lambda:None)
        with patch.object(o,'snapshot',snapshot),self.assertRaises(PermissionError) as caught:
            b.cohort(unittest.TestSuite([case]),[case.id()],self.output,fixtures,lambda:{},lambda:claims,metadata={'graph_root':str(self.base)})
        self.assertIs(caught.exception,error);self.assertEqual(calls,[self.fixture,other,self.fixture,other])
        self.assertIn('second',json.loads((self.output/'RESULT.json').read_bytes())['fixtures_after'])

    def test_report_fault_never_succeeds_and_replay_never_overwrites(self):
        error=OSError('uncertain RESULT persistence');save=b.r.save
        def faulty(path,value):
            save(path,value)
            if path.name=='RESULT.json':raise error
        with patch.object(b.r,'save',faulty),self.assertRaises(OSError) as caught:self.engine()
        self.assertIs(caught.exception,error);before=(self.output/'RESULT.json').read_bytes()
        self.assertFalse(b.execution_complete(self.output,0))
        with self.assertRaises(AssertionError):self.engine()
        self.assertEqual((self.output/'RESULT.json').read_bytes(),before)

    def test_safe_failure_message_and_success_seal_both_preserved(self):
        self.assertEqual(self.engine(lambda:(_ for _ in ()).throw(RuntimeError('unrelated full controlled failure'))),1)
        report=json.loads((self.output/'RESULT.json').read_bytes())
        self.assertEqual(report['test_error_details'][0]['error']['message'],'unrelated full controlled failure')
        self.assertIn('unrelated full controlled failure',(self.output/'TESTS.log').read_text())
        self.assertFalse(b.execution_complete(self.output,0))
        self.output=self.base/'success';self.output.mkdir()
        self.assertEqual(self.engine(lambda:(self.fixture/'new').write_bytes(b'new controlled sample')),0)
        self.assertTrue(b.execution_complete(self.output,0));self.assertFalse(b.execution_complete(self.output,1))

    def test_environment_all_native_switches_removed_only_bound_js9_retained(self):
        packet=b.packet()
        with patch.dict(os.environ,{'CETA_NATIVE_CPU':'1','CETA_OTHER_FIXTURE_ROOT':'unknown','CETA_JS9_FIXTURE_ROOT':'wrong'}):
            observed=b.environment(packet)
            self.assertEqual({k:v for k,v in os.environ.items() if k.startswith('CETA_')},packet['fixture_environment'])
            self.assertIn('CETA_NATIVE_CPU',observed['removed_names'])

    def test_collector_ROOT_or_module_copy_substitution_refuses(self):
        from types import ModuleType
        packet=b.packet();name=packet['selected'][0];module=ModuleType(name)
        module.__file__=str(b.F/'tests/contract'/(name+'.py'));module.ROOT=self.base
        with patch.object(b.importlib,'import_module',return_value=module),self.assertRaises(AssertionError):b.collect(packet)
        module.ROOT=b.F;module.__file__=str(self.base/'copy.py')
        with patch.object(b.importlib,'import_module',return_value=module),self.assertRaises(AssertionError):b.collect(packet)
        self.assertEqual(list(self.output.iterdir()),[])

    def test_namespace_requires_real_loader_single_exact_canonical_directory(self):
        from types import ModuleType
        import importlib
        name='ceta.effects';expected=b.F/'src/ceta/effects';module=ModuleType(name)
        sys.path.insert(0,str(b.F/'src'));actual=importlib.import_module(name)
        module.__file__=None;module.__loader__=actual.__loader__
        module.__spec__=SimpleNamespace(origin=None);module.__path__=[str(expected)]
        self.assertEqual(b.canonical_origin(name,module)['namespace_path'],str(expected))
        module.__path__.append(str(self.fixture))
        with self.assertRaises(AssertionError):b.canonical_origin(name,module)
        module.__path__=[str(self.fixture)]
        with self.assertRaises(AssertionError):b.canonical_origin(name,module)

    def test_file_open_failure_propagates_exact_object_without_partial_success(self):
        target=self.fixture/'unreadable';target.write_bytes(b'preserved')
        error=PermissionError('independent exact file read refusal');original=Path.open
        def open_file(path,*args,**kwargs):
            if str(path)==str(o.physical(target)):raise error
            return original(path,*args,**kwargs)
        with patch.object(Path,'open',open_file),self.assertRaises(PermissionError) as caught:o.snapshot(self.fixture)
        self.assertIs(caught.exception,error)
        self.assertEqual(target.read_bytes(),b'preserved')
    def test_hook_and_environment_restore_after_projection_failure(self):
        binding,bound,stock,paths=self.live();run=binding['run_id']
        original=a.stock._snapshot_workspace
        names=('GIT_OPTIONAL_LOCKS','GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0')
        previous={n:os.environ.get(n) for n in names}
        error=PermissionError('independent projection refusal')
        with patch.object(o,'projection',side_effect=error),self.assertRaises(PermissionError) as caught:
            bound.claim(run,'fixture_0','/root',workspace=paths['fixture_0'])
        self.assertIs(caught.exception,error)
        self.assertIs(a.stock._snapshot_workspace,original)
        self.assertEqual({n:os.environ.get(n) for n in names},previous)
        state=json.loads((bound.runtime_root/run/'state.json').read_bytes())
        self.assertEqual(state['nodes']['fixture_0']['state'],'READY')
        self.assertIsNone(state['nodes']['fixture_0']['claim'])
    def test_completed_ignored_artifact_mutation_invalidates_actual_receipt(self):
        binding,bound,stock,paths=self.live();run=binding['run_id'];path=paths['fixture_0']
        bound.claim(run,'fixture_0','/root',workspace=path)
        (path/'.agents').mkdir();target=path/'.agents/evidence';target.write_bytes(b'original')
        changed=bound.changed_files(run,'fixture_0')
        self.assertIn('fixture_0/.agents/evidence',changed)
        receipt=self.receipt(stock,run,'fixture_0','/root',path,reported=changed)
        bound.complete(run,'fixture_0',receipt)
        self.assertEqual(bound.verify(run)['states']['fixture_0'],'SUCCEEDED')
        target.write_bytes(b'mutated ignored evidence')
        observed=bound.verify(run)
        self.assertNotEqual(observed['states']['fixture_0'],'SUCCEEDED')

    def failure_facts(self,error):
        storage=BaseException.__dict__['__dict__'].__get__(error)
        keys=storage['observer_native_fields']
        return dict(phase=storage['observer_phase'],path=storage['observer_path'],
            differing_fields=storage['observer_differing_fields'],
            expected=dict(zip(keys,storage['observer_expected_values'])),observed=dict(zip(keys,storage['observer_observed_values'])))

    def native_pair(self):
        handle=dict(device=1,inode=2,bytes=3,mtime_ns=4,mode=0o100666,links=1)
        return dict(handle,mode=handle['mode']|0o111),handle

    def test_real_harmless_executable_suffixes_record_both_native_APIs(self):
        self.assertEqual(sys.platform,'win32','this qualification requires the actual Windows host')
        for index,suffix in enumerate(('.exe','.ExE','.bat','.CmD','.com')):
            target=self.fixture/('harmless'+str(index)+suffix)
            with o.physical(target).open('xb') as stream:stream.write(b'CONTROLLED FILE ONLY; NEVER EXECUTED')
            observed=o.stable(target);raw=observed['api_metadata']
            self.assertEqual(raw['path_before'],raw['path_after'])
            self.assertEqual(raw['handle_before'],raw['handle_after'])
            self.assertEqual(raw['path_before'],dict(raw['handle_before'],mode=raw['handle_before']['mode']|0o111))
            self.assertEqual(observed['cross_api_qualification'],'CPYTHON_WIN32_SUFFIX_EXECUTE_BITS')
            self.assertEqual(observed['sha256'],b.hashlib.sha256(b'CONTROLLED FILE ONLY; NEVER EXECUTED').hexdigest())
        snapshot=o.snapshot(self.fixture)
        self.assertEqual(sum(item['kind']=='file' for item in snapshot.values()),5)
        b.r.save(self.base/'REAL-SUFFIX-QUALIFICATION.json',snapshot)

    def test_directional_suffix_rule_accepts_exact_casefold_only(self):
        path_view,handle=self.native_pair()
        for suffix in ('.exe','.EXE','.bat','.CMD','.com'):
            self.assertEqual(o.cross_api(self.fixture/('x'+suffix),path_view,handle),'CPYTHON_WIN32_SUFFIX_EXECUTE_BITS')
        self.assertEqual(o.cross_api(self.fixture/'x.txt',handle,handle),'EXACT')
        for suffix in ('.txt','.exe.txt','.exe.more',''):
            with self.subTest(suffix=suffix),self.assertRaises(AssertionError):o.cross_api(self.fixture/('x'+suffix),path_view,handle)

    def test_reversed_and_partial_execute_bit_differences_refuse(self):
        path_view,handle=self.native_pair();target=self.fixture/'x.exe'
        with self.assertRaises(AssertionError):o.cross_api(target,handle,path_view)
        for bits in (0o1,0o10,0o100,0o101):
            with self.subTest(bits=bits),self.assertRaises(AssertionError):o.cross_api(target,dict(handle,mode=handle['mode']|bits),handle)
        with self.assertRaises(AssertionError):o.cross_api(target,dict(path_view,mode=path_view['mode']|0o4000),handle)

    def test_non_windows_suffix_mode_difference_refuses(self):
        path_view,handle=self.native_pair()
        with patch.object(o.sys,'platform','linux'),self.assertRaises(AssertionError):o.cross_api(self.fixture/'x.exe',path_view,handle)

    def test_every_nonmode_cross_API_field_must_match(self):
        path_view,handle=self.native_pair()
        for name in ('device','inode','bytes','mtime_ns','links'):
            with self.subTest(field=name),self.assertRaises(AssertionError) as caught:
                o.cross_api(self.fixture/'x.exe',path_view,dict(handle,**{name:handle[name]+1}))
            facts=self.failure_facts(caught.exception)
            self.assertIn(name,facts['differing_fields'])
            self.assertEqual(facts['path'],str(self.fixture/'x.exe'))
            self.assertEqual(facts['expected'],path_view)
        with self.assertRaises(AssertionError):o.cross_api(self.fixture/'x.exe',path_view,dict(handle,unexpected=1))

    def test_wrong_cross_API_file_type_and_hardlink_refuse(self):
        path_view,handle=self.native_pair()
        with self.assertRaises(AssertionError):o.cross_api(self.fixture/'x.exe',path_view,dict(handle,mode=0o40777))
        with self.assertRaises(AssertionError):o.cross_api(self.fixture/'x.exe',dict(path_view,links=2),dict(handle,links=2))

    def stat_clone(self,info,**changes):
        fields={name:getattr(info,name) for name in ('st_dev','st_ino','st_size','st_mtime_ns','st_mode','st_nlink')}
        fields['st_file_attributes']=getattr(info,'st_file_attributes',0)
        fields.update(changes);return SimpleNamespace(**fields)

    def test_full_handle_before_after_metadata_drift_refuses(self):
        target=self.fixture/'metadata.exe';target.write_bytes(b'controlled')
        original=o.os.fstat
        for field in ('st_dev','st_ino','st_size','st_mtime_ns','st_mode','st_nlink'):
            calls=[0]
            def view(fd):
                info=original(fd);calls[0]+=1
                return self.stat_clone(info,**{field:getattr(info,field)+1}) if calls[0]==2 else info
            with self.subTest(field=field),patch.object(o.os,'fstat',view),self.assertRaises(AssertionError) as caught:o.stable(target)
            self.assertEqual(self.failure_facts(caught.exception)['phase'],'handle_before_after')
            self.assertEqual(self.failure_facts(caught.exception)['path'],str(target))

    def test_full_path_before_after_metadata_drift_refuses(self):
        target=self.fixture/'metadata.exe';target.write_bytes(b'controlled')
        original=o.plain
        for field in ('st_dev','st_ino','st_size','st_mtime_ns','st_mode','st_nlink'):
            calls=[0]
            def view(path):
                info=original(path)
                if path==target:
                    calls[0]+=1
                    if calls[0]==2:return self.stat_clone(info,**{field:getattr(info,field)+1})
                return info
            with self.subTest(field=field),patch.object(o,'plain',view),self.assertRaises(AssertionError) as caught:o.stable(target)
            self.assertEqual(self.failure_facts(caught.exception)['phase'],'path_before_after')

    def test_bounded_read_count_refuses_short_or_extra_bytes(self):
        target=self.fixture/'read-bound.exe';target.write_bytes(b'controlled')
        original=Path.open
        class Reader:
            def __init__(self,raw,overlong):self.raw=raw;self.overlong=overlong;self.calls=0
            def fileno(self):return self.raw.fileno()
            def close(self):return self.raw.close()
            def read(self,count):
                self.calls+=1
                if self.overlong:return self.raw.read(count)+b'X'
                return self.raw.read(2) if self.calls==1 else b''
        for overlong,phase in ((False,'read_count'),(True,'read_exceeds_bound')):
            def opened(path,*args,**kwargs):return Reader(original(path,*args,**kwargs),overlong)
            with self.subTest(overlong=overlong),patch.object(Path,'open',opened),self.assertRaises(AssertionError) as caught:o.stable(target)
            self.assertEqual(self.failure_facts(caught.exception)['phase'],phase)

    def test_observer_read_primary_survives_close_failure(self):
        target=self.fixture/'custody.exe';target.write_bytes(b'controlled')
        primary=KeyboardInterrupt('original exact read failure');close_fault=OSError('secondary close failure');original=Path.open
        class Reader:
            def __init__(self,raw):self.raw=raw
            def fileno(self):return self.raw.fileno()
            def read(self,count):raise primary
            def close(self):self.raw.close();raise close_fault
        def opened(path,*args,**kwargs):return Reader(original(path,*args,**kwargs))
        with patch.object(Path,'open',opened),self.assertRaises(KeyboardInterrupt) as caught:o.stable(target)
        self.assertIs(caught.exception,primary)
        storage=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(storage['observer_primary_exc_info'][1],primary)
        self.assertIs(storage['observer_secondary_errors'][0],close_fault)
        self.assertEqual(target.read_bytes(),b'controlled')

    def test_observer_close_only_failure_cannot_succeed(self):
        target=self.fixture/'close.exe';target.write_bytes(b'controlled');fault=OSError('close only');original=Path.open
        class Reader:
            def __init__(self,raw):self.raw=raw
            def fileno(self):return self.raw.fileno()
            def read(self,count):return self.raw.read(count)
            def close(self):self.raw.close();raise fault
        def opened(path,*args,**kwargs):return Reader(original(path,*args,**kwargs))
        with patch.object(Path,'open',opened),self.assertRaises(OSError) as caught:o.stable(target)
        self.assertIs(caught.exception,fault)

    def test_snapshot_hook_conflict_preserves_primary_and_restores_original(self):
        binding,bound,stock,paths=self.live();original=a.stock._snapshot_workspace
        primary=KeyboardInterrupt('exact hook body failure')
        with self.assertRaises(KeyboardInterrupt) as caught:
            with bound.observation_port(binding['run_id']):
                a.stock._snapshot_workspace=lambda *args:{}
                raise primary
        self.assertIs(caught.exception,primary);self.assertIs(a.stock._snapshot_workspace,original)
        storage=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(storage['snapshot_primary_exc_info'][1],primary)
        self.assertIn('BR_SNAPSHOT_HOOK_CHANGED',str(storage['snapshot_secondary_errors'][0]))

    def test_environment_restore_fault_cannot_replace_primary_and_attempts_all_names(self):
        binding,bound,stock,paths=self.live();primary=KeyboardInterrupt('original environment body failure')
        fault=PermissionError('secondary environment restore failure');original_hook=a.stock._snapshot_workspace
        values={n:os.environ.get(n) for n in ('GIT_OPTIONAL_LOCKS','GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0')}
        class Environment(dict):
            armed=False
            def __setitem__(self,name,value):
                if self.armed and name=='GIT_OPTIONAL_LOCKS':raise fault
                super().__setitem__(name,value)
            def pop(self,name,*args):
                if self.armed and name=='GIT_OPTIONAL_LOCKS':raise fault
                return super().pop(name,*args)
        environment=Environment(os.environ)
        with patch.object(a.os,'environ',environment),self.assertRaises(KeyboardInterrupt) as caught:
            with bound.observation_port(binding['run_id']):
                environment.armed=True
                raise primary
        self.assertIs(caught.exception,primary);self.assertIs(a.stock._snapshot_workspace,original_hook)
        storage=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(storage['snapshot_secondary_errors'][0],fault)
        for name in values:
            if name!='GIT_OPTIONAL_LOCKS':self.assertEqual(environment.get(name),values[name])

    def test_structured_metadata_failure_survives_original_reporter(self):
        expected,actual=self.native_pair();fault=None
        try:o.cross_api(self.fixture/'report.txt',expected,actual)
        except AssertionError as error:fault=error
        self.assertIsNotNone(fault)
        code=self.engine(lambda:(_ for _ in ()).throw(fault))
        self.assertEqual(code,1)
        report=json.loads((self.output/'RESULT.json').read_bytes())
        self.assertIn('report.txt',(self.output/'TESTS.log').read_text())
        self.assertEqual(report['test_error_details'][0]['error']['type'],'AssertionError')
        stored={item['key']:item['value'] for item in report['test_error_details'][0]['error']['storage']}
        self.assertEqual(stored['observer_phase'],'cross_API_path_handle')
        self.assertEqual(stored['observer_path'],str(self.fixture/'report.txt'))
        self.assertEqual(stored['observer_native_fields']['items'],sorted(expected))
        self.assertEqual(stored['observer_expected_values']['items'],[expected[k] for k in sorted(expected)])
        self.assertEqual(stored['observer_observed_values']['items'],[actual[k] for k in sorted(actual)])
        self.assertFalse(b.execution_complete(self.output,0))

    def hostile(self,message):
        class Hostile(KeyboardInterrupt):
            def __setattr__(self,name,value):
                if name=='__traceback__':
                    store=BaseException.__dict__['__dict__'].__get__(self)
                    dict.__setitem__(store,'setter_calls',store.get('setter_calls',0)+1)
                    raise RuntimeError('HOSTILE_TRACEBACK_ASSIGNMENT_FORBIDDEN')
                return BaseException.__setattr__(self,name,value)
        return Hostile(message)

    def hostile_body(self,manager,prefix,action=None,secondary=()):
        primary=self.hostile('exact '+prefix+' body');saved=None;observed=None
        try:
            with manager as value:
                try:
                    if action is not None:action(value,primary)
                    raise primary
                except BaseException:
                    saved=sys.exc_info()
                    raise
        except BaseException as error:observed=error
        self.assertIs(observed,primary)
        attrs=BaseException.__dict__['__dict__'].__get__(primary)
        info=attrs[prefix+'_primary_exc_info']
        self.assertIs(info[0],type(primary));self.assertIs(info[1],primary);self.assertIs(info[2],saved[2])
        self.assertIs(BaseException.__dict__['__traceback__'].__get__(observed),saved[2])
        self.assertEqual(attrs.get('setter_calls',0),0)
        errors=attrs[prefix+'_secondary_errors'];triples=attrs[prefix+'_secondary_exc_info']
        self.assertEqual(len(errors),len(triples))
        for expected in secondary:
            self.assertTrue(any(item is expected for item in errors))
        for error,triple in zip(errors,triples):
            self.assertIs(triple[0],type(error));self.assertIs(triple[1],error)
        return primary,attrs

    def observer_hostile(self,close_fault=None):
        target=self.fixture/'direct-hostile.exe';target.write_bytes(b'CONTROLLED NEVER EXECUTED')
        original=Path.open;closes=[]
        class Reader:
            def __init__(self,raw):self.raw=raw
            def read(self,error):raise error
            def close(self):
                self.raw.close();closes.append(True)
                if close_fault is not None:raise close_fault
        def opened(path,*args,**kwargs):return Reader(original(path,*args,**kwargs))
        with patch.object(Path,'open',opened):
            primary,attrs=self.hostile_body(o.file_stream(target),'observer',lambda stream,error:stream.read(error),
                () if close_fault is None else (close_fault,))
        self.assertEqual(closes,[True]);self.assertEqual(target.read_bytes(),b'CONTROLLED NEVER EXECUTED')
        return attrs

    def test_BR3_hostile_observer_body_exact_identity_and_traceback(self):
        self.assertEqual(self.observer_hostile()['observer_secondary_errors'],())

    def test_BR3_hostile_observer_read_and_close_combined_faults(self):
        fault=OSError('exact secondary close');attrs=self.observer_hostile(fault)
        self.assertEqual(len(attrs['observer_secondary_errors']),1)

    def test_BR3_hostile_observer_open_failure_identity(self):
        target=self.fixture/'unopened';primary=self.hostile('open failure');observed=None
        with patch.object(Path,'open',side_effect=primary):
            try:
                with o.file_stream(target):self.fail('open failure entered body')
            except BaseException as error:observed=error
        self.assertIs(observed,primary)
        self.assertEqual(BaseException.__dict__['__dict__'].__get__(primary).get('setter_calls',0),0)

    def test_BR3_hostile_snapshot_body_exact_identity_and_traceback(self):
        binding,bound,stock,paths=self.live();original=a.stock._snapshot_workspace
        primary,attrs=self.hostile_body(bound.observation_port(binding['run_id']),'snapshot')
        self.assertEqual(attrs['snapshot_secondary_errors'],());self.assertIs(a.stock._snapshot_workspace,original)

    def adverse_environment(self,fault):
        class Environment(dict):
            armed=False
            def __setitem__(self,name,value):
                if self.armed:
                    self.attempted.append(name)
                    if name=='GIT_OPTIONAL_LOCKS':raise fault
                super().__setitem__(name,value)
            def pop(self,name,*args):
                if self.armed:
                    self.attempted.append(name)
                    if name=='GIT_OPTIONAL_LOCKS':raise fault
                return super().pop(name,*args)
        environment=Environment(os.environ);environment.attempted=[]
        return environment

    def test_BR3_hostile_snapshot_body_hook_and_environment_combined_faults(self):
        binding,bound,stock,paths=self.live();original=a.stock._snapshot_workspace
        fault=PermissionError('exact environment restore');environment=self.adverse_environment(fault)
        def adverse(value,error):
            a.stock._snapshot_workspace=lambda *args:{};environment.armed=True
        with patch.object(a.os,'environ',environment):
            primary,attrs=self.hostile_body(bound.observation_port(binding['run_id']),'snapshot',adverse,(fault,))
        self.assertEqual(len(attrs['snapshot_secondary_errors']),2)
        self.assertIn('BR_SNAPSHOT_HOOK_CHANGED',str(attrs['snapshot_secondary_errors'][0]))
        self.assertEqual(environment.attempted,['GIT_OPTIONAL_LOCKS','GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0'])
        self.assertIs(a.stock._snapshot_workspace,original)

    def test_BR3_hostile_snapshot_setup_failure_unwinds_all_cleanup(self):
        binding,bound,stock,paths=self.live();original=a.stock._snapshot_workspace
        primary=self.hostile('exact stock verification setup');fault=OSError('setup environment cleanup')
        environment=self.adverse_environment(fault);observed=None
        def failed(*args):environment.armed=True;raise primary
        with patch.object(a.os,'environ',environment),patch.object(a.stock.OrchestrationRuntime,'verify',failed):
            try:
                with bound.observation_port(binding['run_id']):self.fail('failed setup entered body')
            except BaseException as error:observed=error
        self.assertIs(observed,primary);attrs=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(attrs['snapshot_primary_exc_info'][1],primary)
        self.assertIs(attrs['snapshot_secondary_errors'][0],fault);self.assertEqual(attrs.get('setter_calls',0),0)
        self.assertEqual(environment.attempted,['GIT_OPTIONAL_LOCKS','GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0'])
        self.assertIs(a.stock._snapshot_workspace,original)

    def test_BR3_snapshot_cleanup_only_combined_faults_are_fatal(self):
        binding,bound,stock,paths=self.live();original=a.stock._snapshot_workspace
        fault=PermissionError('cleanup only environment');environment=self.adverse_environment(fault);observed=None
        with patch.object(a.os,'environ',environment):
            try:
                with bound.observation_port(binding['run_id']):
                    a.stock._snapshot_workspace=lambda *args:{};environment.armed=True
            except BaseException as error:observed=error
        self.assertIsInstance(observed,RuntimeError)
        attrs=BaseException.__dict__['__dict__'].__get__(observed)
        self.assertIs(attrs['snapshot_secondary_errors'][1],fault);self.assertEqual(len(attrs['snapshot_secondary_errors']),2)
        self.assertIs(a.stock._snapshot_workspace,original);self.assertEqual(len(environment.attempted),4)

    def reporter_hooks(self):
        class Hooks:
            def __init__(self):
                object.__setattr__(self,'armed',False);object.__setattr__(self,'fault',None)
                object.__setattr__(self,'attempted',[]);object.__setattr__(self,'fail_name',None)
                self.snapshot=lambda *args:{};self.preservation=lambda *args:True
            def __setattr__(self,name,value):
                if name in ('snapshot','preservation') and self.armed:
                    self.attempted.append(name)
                    if name==self.fail_name:
                        object.__setattr__(self,'fail_name',None)
                        raise self.fault
                object.__setattr__(self,name,value)
        return Hooks()

    def test_BR3_hostile_reporter_body_exact_identity_and_traceback(self):
        original=(b.r.snapshot,b.r.preservation)
        primary,attrs=self.hostile_body(b.reporter_observation(),'reporter')
        self.assertEqual(attrs['reporter_secondary_errors'],())
        self.assertEqual((b.r.snapshot,b.r.preservation),original)

    def test_BR3_hostile_reporter_body_hook_and_restore_combined_faults(self):
        hooks=self.reporter_hooks();original=hooks.preservation;fault=PermissionError('reporter restore fault')
        def adverse(value,error):
            hooks.snapshot=lambda *args:{};hooks.fault=fault;hooks.fail_name='snapshot';hooks.armed=True
        with patch.object(b,'r',hooks):
            primary,attrs=self.hostile_body(b.reporter_observation(),'reporter',adverse,(fault,))
        self.assertEqual(len(attrs['reporter_secondary_errors']),2)
        self.assertIn('BR_REPORTER_HOOK_CHANGED',str(attrs['reporter_secondary_errors'][0]))
        self.assertEqual(hooks.attempted,['snapshot','preservation']);self.assertIs(hooks.preservation,original)

    def test_BR3_hostile_reporter_partial_setup_and_cleanup_faults(self):
        primary=self.hostile('reporter preservation setup');secondary=OSError('reporter snapshot unwind')
        original_snapshot=lambda *args:{};original_preservation=lambda *args:True
        class Hooks:
            def __init__(self):
                object.__setattr__(self,'snapshot',original_snapshot);object.__setattr__(self,'preservation',original_preservation)
                object.__setattr__(self,'attempted',[]);object.__setattr__(self,'setup_failed',False)
            def __setattr__(self,name,value):
                self.attempted.append(name)
                if name=='preservation' and not self.setup_failed:
                    object.__setattr__(self,'setup_failed',True);raise primary
                if name=='snapshot' and self.setup_failed:raise secondary
                object.__setattr__(self,name,value)
        hooks=Hooks();observed=None
        with patch.object(b,'r',hooks):
            try:
                with b.reporter_observation():self.fail('failed reporter setup entered body')
            except BaseException as error:observed=error
        self.assertIs(observed,primary);attrs=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(attrs['reporter_primary_exc_info'][1],primary);self.assertIs(attrs['reporter_secondary_errors'][0],secondary)
        self.assertEqual(attrs.get('setter_calls',0),0)
        self.assertEqual(hooks.attempted,['snapshot','preservation','snapshot','preservation'])
        self.assertIs(hooks.preservation,original_preservation)

    def test_BR3_reporter_cleanup_only_restore_fault_is_fatal(self):
        hooks=self.reporter_hooks();original=hooks.preservation;fault=OSError('only reporter cleanup');observed=None
        with patch.object(b,'r',hooks):
            try:
                with b.reporter_observation():
                    hooks.fault=fault;hooks.fail_name='snapshot';hooks.armed=True
            except BaseException as error:observed=error
        self.assertIs(observed,fault);attrs=BaseException.__dict__['__dict__'].__get__(fault)
        self.assertIs(attrs['reporter_primary_exc_info'][1],fault)
        self.assertEqual(hooks.attempted,['snapshot','preservation']);self.assertIs(hooks.preservation,original)

if __name__=='__main__':unittest.main(verbosity=2)

