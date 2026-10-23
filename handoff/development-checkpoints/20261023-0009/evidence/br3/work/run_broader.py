"""Current 28-selector controlled cohort, one attempt, eight exact Root leases."""
from pathlib import Path
import argparse,hashlib,importlib,importlib.util,json,os,sys,unittest
import complete_observer as o
from bound_runtime import BoundRuntime,require_live

F=Path('T:/00-Active/Project-AI-CETA');W=Path(__file__).resolve().parent;B=W.parent
RUN='ceta-br23-r3'
PACKET_SHA='fd4593d75ff3c6ea5e6badad9edeed67b5247089c591087a8e7a5957e34d0eb9'
PLAN_SHA='8e6bae1857e2b02e2f1558e883f77d6e2b2f4aaf5646f5e5ff8d25f735ec45db'
TIMING_INPUT_SHA='534526bb286fd7602aad31e6da7a516858778711dc797dbe2ffceabbdd5859ff'
J2=F/'.agents/runtime/oq23/jr2'
sha=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert sha(J2/'work/MANIFEST.json')=='771fa4d915c6b9d6fb2f1f042d3c313448fb4f2cea8607420fcccca65bf4df53'
assert sha(J2/'work/run_canonical_journal.py')=='37ca7bbfa361475ea42398c5d3bda42f8c1f95a0f3329154176f286a262d17ed'
spec=importlib.util.spec_from_file_location('br_accepted_jr2',J2/'work/run_canonical_journal.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def packet():
    assert B==F/'.agents/runtime/oq23/br3' and sys.flags.optimize==0
    assert sha(B/'packet/INPUTS.json')==PACKET_SHA and sha(B/'packet/PLAN.md')==PLAN_SHA
    value=json.loads((B/'packet/INPUTS.json').read_bytes())
    assert value['project']==str(F) and len(value['selected'])==28 and len(value['selected_sha256'])==26
    assert value['logical_execution_claims']==8 and value['one_sequential_Root_test_process'] is True
    assert Path(sys.executable).resolve()==Path(value['python']).resolve() and sha(Path(sys.executable))==value['python_sha256']
    return value

def environment(value):
    expected={'CETA_JS9_FIXTURE_ROOT':str(F/'.agents/fixtures/js9-b23-r3')}
    assert value['fixture_environment']==expected
    removed=sorted(k for k in os.environ if k.startswith('CETA_'))
    for name in removed:os.environ.pop(name)
    os.environ.update(expected)
    assert {k:v for k,v in os.environ.items() if k.startswith('CETA_')}==expected
    return dict(removed_names=removed,fixture_environment=expected,native_enable_switches_inherited=False)

def collect(value):
    sys.path[:0]=[str(F/'src'),str(F/'tests/contract')]
    modules={}
    for selector in value['selected']:
        name=selector.partition('.')[0];module=importlib.import_module(name)
        path=F/'tests/contract'/(name+'.py')
        assert Path(module.__file__).resolve()==path and sha(path)==value['selected_sha256'][name]
        if 'ROOT' in vars(module):assert module.ROOT==F,('foreign test ROOT',name)
        modules[name]=r.module_origin(module)
    for name,module in tuple(sys.modules.items()):
        if module is None:continue
        if name=='ceta' or name.startswith('ceta.'):
            canonical_origin(name,module)
            if 'ROOT' in vars(module):assert module.ROOT==F,('foreign product ROOT',name)
        elif name.startswith('test_') and name!='test_br_controls':
            assert Path(module.__file__).resolve().is_relative_to(F/'tests/contract'),('foreign test helper',name)
            if 'ROOT' in vars(module):assert module.ROOT==F,('foreign helper ROOT',name)
    suite=unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromName(n) for n in value['selected'])
    ids=r.identities(suite)
    assert ids and len(ids)==len(set(ids)) and not any('_FailedTest' in n for n in ids)
    return suite,ids,modules

def canonical_origin(name,module):
    expected=F/'src'/Path(*name.split('.'));identity=r.module_origin(module)
    if identity['file']:
        assert Path(identity['origin']) in (expected.with_suffix('.py'),expected/'__init__.py'),('foreign product module',name,identity)
        return identity
    assert name=='ceta.effects' and expected==F/'src/ceta/effects','unapproved fileless module'
    values=vars(module);spec=values.get('__spec__')
    assert values.get('__file__') is None and type(values.get('__loader__')) is importlib.machinery.NamespaceLoader
    assert spec is not None and spec.origin is None
    assert list(values.get('__path__',[]))==[str(expected)],('foreign/ambiguous namespace',name)
    o.ancestors(F,expected)
    try:o.physical(expected/'__init__.py').lstat()
    except FileNotFoundError:pass
    else:raise AssertionError('namespace unexpectedly has __init__.py')
    return dict(file=False,origin=None,namespace_path=str(expected),directory_native=o.native(o.plain(expected)),
        loader='NamespaceLoader',namespace_init_absent=True)

def product_origins():
    return {n:canonical_origin(n,m) for n,m in tuple(sys.modules.items())
        if m is not None and (n=='ceta' or n.startswith('ceta.'))}

def source_observation(binding):
    out={}
    for name,pin in binding['source_native'].items():
        path=Path(name);o.ancestors(F,path.parent);now=o.stable(path)
        assert now==pin,('canonical source/native drift',name);out[name]=now
    readonly={}
    for name,item in binding.get('read_only_fixtures',{}).items():
        now=o.snapshot(Path(item['path']))
        assert now==item['observation'],('read-only failed fixture drift',name)
        readonly[name]=now
    return dict(source_native=out,Git=r.git_observation(binding['Git']),read_only_fixtures=readonly)

class _ReporterObservation:
    def __init__(self,snapshot):self.snapshot=snapshot;self.entered=False;self.closed=False;self.installed=set()
    def __enter__(self):
        assert not self.entered,'reporter observation context reused'
        self.entered=True;self.owner=r
        self.original={'snapshot':r.snapshot,'preservation':r.preservation}
        self.selected={'snapshot':self.snapshot,'preservation':o.preservation}
        try:
            for name,value in self.selected.items():
                setattr(self.owner,name,value);self.installed.add(name)
        except BaseException:
            self._restore(sys.exc_info())
            raise
        return None
    def _restore(self,primary):
        assert not self.closed,'reporter observation context already closed'
        self.closed=True;secondary=[]
        for name,value in self.original.items():
            try:
                if name in self.installed and getattr(self.owner,name) is not self.selected[name]:
                    raise RuntimeError('BR_REPORTER_HOOK_CHANGED: '+name+'; original restoration attempted')
            except BaseException:secondary.append(sys.exc_info())
            try:setattr(self.owner,name,value)
            except BaseException:secondary.append(sys.exc_info())
        return o.custody(primary,secondary,'reporter')
    def __exit__(self,kind,error,traceback):
        return self._restore(None if error is None else (kind,error,traceback))

def reporter_observation(snapshot=o.snapshot):
    return _ReporterObservation(snapshot)

def execution_complete(output,code):
    with reporter_observation():return r.execution_complete(output,code)

def cohort(suite,ids,output,fixtures,observe,authorize,*,metadata=None,preserved=None):
    """Keep accepted report custody; compare each initial view to actual claim.

    Reuse the already-read complete observation for this comparison instead of
    hashing each fixture tree again on every authority reread. No pre-claim bytes
    may disappear or change between the actual complete lease and first write.
    """
    first={};latest=[None]
    def authority():latest[0]=authorize();return latest[0]
    def snapshot(path):
        observed=o.snapshot(path)
        name=next(n for n,p in fixtures.items() if str(p)==str(path))
        if name not in first:
            claim=latest[0][name];expected=claim['baseline_snapshot']
            projected=project_observation(path,Path(metadata['graph_root']),observed)
            assert projected==expected,('fixture differs from actual claim baseline',name)
            if preserved is not None:
                if preserved[name]=={'absent':True}:assert set(observed)=={'.'},'fresh bootstrapped JS9 must remain empty'
                else:o.preservation(preserved[name],observed)
            first[name]=observed
        return observed
    with reporter_observation(snapshot):
        return r.run_observed(suite,ids,output,fixtures,observe,authority,metadata=metadata)

def project_observation(base,root,observed):
    # Same deterministic schema as the adapter projection, without another read.
    out={}
    for key,item in observed.items():
        name=(base if key=='.' else base/key.rstrip('/')).relative_to(root).as_posix()
        value=item if item['kind']=='file' else {k:item[k] for k in ('kind','device','inode','mode')}
        assert name not in out
        out[name]=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)
    return out

def load_prepared(pin):
    value=packet();assert sha(W/'MANIFEST.json')==pin
    manifest=json.loads((W/'MANIFEST.json').read_bytes())
    for name,expected in manifest['work_hashes'].items():assert o.stable(W/name)['sha256']==expected
    for name,expected in manifest['external_pins'].items():assert sha(Path(name))==expected
    binding=json.loads((W/'BINDING.json').read_bytes());binding['prepared_manifest_sha256']=pin
    assert binding['run_id']==RUN and binding['control']==str(B/'control') and binding['graph_root']==str(Path('T:/'))
    assert binding['workspaces']==dict(integrate=str(B/'delivery'),**value['fixture_workspaces'])
    assert sha(Path(value['failed_broader_predecessor']['closure']))==value['failed_broader_predecessor']['closure_sha256']
    return value,binding

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-sha256',required=True)
    parser.add_argument('--lease',choices=['claim','changed','complete','ready','verify','status','fail','cancel'])
    parser.add_argument('--node');parser.add_argument('--workspace',type=Path);parser.add_argument('--receipt',type=Path);parser.add_argument('--reason')
    args=parser.parse_args();value,binding=load_prepared(args.manifest_sha256)
    source_observation(binding)
    if args.lease:
        runtime=BoundRuntime(binding)
        if args.lease=='claim':answer=runtime.claim(RUN,args.node,'/root',workspace=args.workspace)
        elif args.lease=='changed':answer=runtime.changed_files(RUN,args.node)
        elif args.lease=='complete':answer=runtime.complete(RUN,args.node,args.receipt)
        elif args.lease in ('fail','cancel'):answer=getattr(runtime,args.lease)(RUN,args.node,'/root',args.reason)
        else:answer=getattr(runtime,args.lease)(RUN)
        print(json.dumps(answer,indent=2));return 0
    claims=require_live(binding);env=environment(value)
    suite,ids,modules=collect(value);assert ids==json.loads((W/'COLLECTION.json').read_bytes())['test_ids']
    from ceta.store.sqlite_runtime import runtime_identity
    sqlite=runtime_identity();assert Path(sqlite['dll_path'])==F/'native/sqlite_runtime/win-x64/sqlite3.dll'
    metadata=dict(graph_root=binding['graph_root'],source_root=str(F),ordinary_imports=True,ROOT_override=False,module_overlay=False,
        selected=value['selected'],test_modules=modules,product_modules=product_origins(),environment=env,dependencies=r.dependency_identities(),sqlite=sqlite,
        actual_logical_claims=8,sequential_test_process=True,prior_evidence=json.loads((W/'PRIOR-EVIDENCE.json').read_bytes()))
    assert require_live(binding)==claims
    metadata['controlled_process_effects']=value['controlled_process_effects']
    metadata['failed_broader_predecessor']=value['failed_broader_predecessor']
    return cohort(suite,ids,B/'delivery',{n:Path(p) for n,p in value['fixture_workspaces'].items()},
        lambda:source_observation(binding),lambda:require_live(binding),metadata=metadata,
        preserved=json.loads((W/'FREEZE-OBSERVATION.json').read_bytes())['fixtures'])

if __name__=='__main__':raise SystemExit(main())
