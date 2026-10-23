"""Process-local snapshot dispatch for exactly this reviewed execution context.

All transitions, scopes, capacity, locks, receipts, hashes, event-chain and graph
checks are the installed stock methods. Only their snapshot port is dispatched:
eight exact Root execution workspaces get complete logical projections; every
preparation/review/packet workspace retains the original stock snapshot semantics.
"""
from pathlib import Path
import hashlib,json,os,sys,threading
import complete_observer as o

F=Path('T:/00-Active/Project-AI-CETA');B=Path(__file__).resolve().parent.parent
RUN='ceta-br23-r3';PACKET_SHA='fd4593d75ff3c6ea5e6badad9edeed67b5247089c591087a8e7a5957e34d0eb9'
sys.path.insert(0,'T:/01-Projects/TAAR-Agent-Taskforce/TAAR-Agent-Taskforce')
from taar import orchestration_runtime as stock
from taar.orchestration_graph import compile_graph

def expected_context():
    assert B==F/'.agents/runtime/oq23/br3'
    raw=(B/'packet/INPUTS.json').read_bytes();assert hashlib.sha256(raw).hexdigest()==PACKET_SHA
    packet=json.loads(raw)
    return dict(run_id=RUN,graph_root=str(Path('T:/')),control=str(B/'control'),
        workspaces=dict(integrate=str(B/'delivery'),**packet['fixture_workspaces']))

class BoundRuntime(stock.OrchestrationRuntime):
    def __init__(self,binding):
        expected=expected_context()
        assert all(binding[k]==expected[k] for k in expected),'unbound runtime context'
        self.binding=binding;self.paths={n:o.logical(p) for n,p in binding['workspaces'].items()}
        assert len(self.paths)==8 and len({str(p).casefold() for p in self.paths.values()})==8
        self.root=o.logical(binding['graph_root'])
        for a in self.paths.values():
            assert a.is_relative_to(self.root)
            for b in self.paths.values():
                assert a==b or not (a.is_relative_to(b) or b.is_relative_to(a)),'overlapping context'
        super().__init__(Path(binding['control']))
        self._check_graph()

    def _check_graph(self):
        assert str(self.runtime_root)==self.binding['control'],'wrong runtime control'
        graph=compile_graph(self.root,self.runtime_root)
        assert graph.fingerprint==self.binding['graph_fingerprint'],'wrong graph fingerprint'
        assert graph.policy==dict(fail_closed=True,max_parallel=8,prohibit_scope_overlap=True,
            prohibit_self_review=True,require_receipts=True),'stock policies changed'
        for node,path in self.paths.items():
            assert graph.nodes[node]['access']=='write_scoped'
            assert graph.nodes[node]['write_scope']==[path.relative_to(self.root).as_posix()+'/**'],'widened/unknown scope'
        return graph

    def _guard(self,run):
        assert run==self.binding['run_id'],'wrong run'
        graph=self._check_graph()
        state=json.loads((self.runtime_root/run/'state.json').read_bytes())
        assert state['run_id']==run and state['graph_fingerprint']==graph.fingerprint
        assert state['graph_root']==str(self.root) and state['scope']==str(self.runtime_root)
        nodes=state['nodes']
        assert nodes['review']['state']=='SUCCEEDED' and nodes['review']['decision']=='approved'
        assert nodes['review']['executor_id']!=nodes['implement']['executor_id'],'self review'
        assert nodes['validate']['state']=='SUCCEEDED' and nodes['validate']['validation_passed'] is True
        review=json.loads((self.runtime_root/run/nodes['review']['receipt_ref']).read_bytes())
        assert review['result']['manifest_sha256']==self.binding['prepared_manifest_sha256'],'wrong reviewed manifest'
        gate=json.loads((self.runtime_root/run/nodes['validate']['receipt_ref']).read_bytes())
        expected=[dict(command=c,exit_status=0) for c in graph.nodes['validate']['commands']]
        assert gate['commands']==expected
        assert [dict(command=c['command'],exit_status=c['exit_status']) for c in gate['result']['commands']]==expected
        return graph,state

    def observation_port(self,run):
        return _ObservationPort(self,run)

    def claim(self,run,node,executor,capabilities=(),workspace=None):
        assert node in self.paths and executor=='/root','unknown node/wrong executor'
        assert workspace is not None and str(workspace)==str(self.paths[node]),'explicit exact workspace required'
        o.ancestors(self.root,workspace)
        with self.observation_port(run):return super().claim(run,node,executor,capabilities,workspace)

    def complete(self,run,node,receipt_path):
        assert node in self.paths,'unknown execution node'
        with self.observation_port(run):
            state=json.loads((self.runtime_root/run/'state.json').read_bytes());claim=state['nodes'][node].get('claim')
            assert claim and claim['executor_id']=='/root' and claim['workspace']==str(self.paths[node]),'wrong actual claim'
            assert self.paths[node].relative_to(self.root).as_posix() in claim['baseline_snapshot'],'partial stock baseline'
            return super().complete(run,node,receipt_path)

    def changed_files(self,run,node):
        assert node in self.paths
        with self.observation_port(run):
            state=json.loads((self.runtime_root/run/'state.json').read_bytes());claim=state['nodes'][node]['claim']
            assert claim['executor_id']=='/root' and claim['workspace']==str(self.paths[node])
            assert self.paths[node].relative_to(self.root).as_posix() in claim['baseline_snapshot'],'partial stock baseline'
            return stock._changed_files(claim['baseline_snapshot'],stock._snapshot_workspace(self.paths[node],self.root))

    def ready(self,run):
        with self.observation_port(run):return super().ready(run)
    def verify(self,run):
        with self.observation_port(run):return super().verify(run)
    def status(self,run):
        with self.observation_port(run):return super().status(run)
    def fail(self,run,node,executor,reason):
        assert node in self.paths and executor=='/root'
        with self.observation_port(run):return super().fail(run,node,executor,reason)
    def cancel(self,run,node,executor,reason):
        assert node in self.paths and executor=='/root'
        with self.observation_port(run):return super().cancel(run,node,executor,reason)

class _ObservationPort:
    """One scoped hook owner; exact body exception propagates automatically."""
    def __init__(self,bound,run):
        self.bound=bound;self.run=run;self.entered=False;self.closed=False;self.installed=False
    def __enter__(self):
        assert not self.entered,'snapshot context reused'
        self.entered=True;bound=self.bound;run=self.run
        bound._guard(run)
        self.original=stock._snapshot_workspace;owner=threading.get_ident()
        assert not getattr(self.original,'_br_bound_port',False),'nested snapshot hook'
        known={str(p) for p in bound.paths.values()};original=self.original
        def snapshot(workspace,graph_root):
            if str(workspace) in known:
                assert threading.get_ident()==owner,'snapshot used by another execution thread'
                assert str(graph_root)==str(bound.root),'wrong graph root for complete snapshot'
                o.ancestors(bound.root,workspace)
                return o.projection(workspace,bound.root)
            return original(workspace,graph_root)
        snapshot._br_bound_port=True;self.snapshot=snapshot
        names=('GIT_OPTIONAL_LOCKS','GIT_CONFIG_COUNT','GIT_CONFIG_KEY_0','GIT_CONFIG_VALUE_0')
        self.previous={n:os.environ.get(n) for n in names}
        try:
            os.environ.update(GIT_OPTIONAL_LOCKS='0',GIT_CONFIG_COUNT='1',GIT_CONFIG_KEY_0='core.fsmonitor',GIT_CONFIG_VALUE_0='false')
            stock._snapshot_workspace=snapshot;self.installed=True
            verified=stock.OrchestrationRuntime.verify(bound,run)
            assert verified['allowed'] is True and verified['receipts_valid'] is True
            bound._guard(run)
        except BaseException:
            self._restore(sys.exc_info())
            raise
        return None
    def _restore(self,primary):
        assert not self.closed,'snapshot context already closed'
        self.closed=True;secondary=[]
        try:
            if self.installed and stock._snapshot_workspace is not self.snapshot:
                raise RuntimeError('BR_SNAPSHOT_HOOK_CHANGED; original restoration attempted')
        except BaseException:secondary.append(sys.exc_info())
        try:stock._snapshot_workspace=self.original
        except BaseException:secondary.append(sys.exc_info())
        for name,value in self.previous.items():
            try:
                if value is None:os.environ.pop(name,None)
                else:os.environ[name]=value
            except BaseException:secondary.append(sys.exc_info())
        return o.custody(primary,secondary,'snapshot')
    def __exit__(self,kind,error,traceback):
        return self._restore(None if error is None else (kind,error,traceback))

def require_live(binding):
    runtime=BoundRuntime(binding);verified=runtime.verify(binding['run_id'])
    assert verified['allowed'] and verified['receipts_valid']
    graph,state=runtime._guard(binding['run_id']);claims={}
    for node,path in runtime.paths.items():
        entry=state['nodes'][node];claim=entry.get('claim')
        assert entry['state']=='RUNNING' and claim,('claim not running',node)
        assert claim['executor_id']=='/root' and claim['node_id']==node
        assert claim['workspace']==str(path)
        assert claim['effective_write_scope']==[path.relative_to(runtime.root).as_posix()+'/**']
        assert claim['input_hash']==runtime._input_hash(graph,state,node),'stale actual input'
        assert path.relative_to(runtime.root).as_posix() in claim['baseline_snapshot'],'stock partial claim is not complete authority'
        o.ancestors(runtime.root,path);claims[node]=claim
    return claims
