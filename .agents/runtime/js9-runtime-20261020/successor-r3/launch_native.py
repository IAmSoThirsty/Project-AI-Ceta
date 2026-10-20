"""One owned native child and independent parent Git/source corroboration.

The child audit remains strict. The parent reuses the reviewed bounded custody
primitive and records the actual child exit before accepting its component cut.
This is engineering evidence, not product authorization or release acceptance.
"""
from pathlib import Path
import argparse,json,sys,time
import js9_support as j
from js9_support import s,F,Q,R,PY
from bounded_custody import run_owned,failure

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('native-store','native-observer'))
    parser.add_argument('label');parser.add_argument('--release-path',type=Path,required=True)
    parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
    assert args.label.isidentifier()
    release=j.require_release(args.release_path,args.release_sha256,args.phase)
    v=j.verify(source='before');interpreter=j.interpreter_observation(v)
    assert not any(name=='ceta' or name.startswith('ceta.') for name in sys.modules)
    script='run_native_store.py' if args.phase=='native-store' else 'run_native_observer.py'
    child_args=('-B','-X','utf8',str(R/script),args.label,'--release-path',str(args.release_path),
                '--release-sha256',args.release_sha256)
    command=[str(PY),*child_args]
    terminal=R/args.label/('RESULT.json' if args.phase=='native-store' else 'native.json')
    started=time.time_ns()
    # This create-only file precedes launch. Reusing a label cannot run twice.
    s.write_new(R/(args.label+'-LAUNCH-ATTEMPT.json'),dict(at=s.utc(),phase=args.phase,
        child_argv=command,cwd=str(R),packet=j.exact_ref(R/'PACKET.json'),
        release=j.exact_ref(args.release_path),automatic_retry=False))
    temporary=R/(args.label+'-temporary');temporary.mkdir(exist_ok=False)
    environment=j.child_environment(temporary)
    sys.path.insert(0,str(Q/'src'))
    from ceta.supervisor.windows_jobs import WindowsOwnedProcess
    primary=record=native_reference=post=None
    def launch():
        return WindowsOwnedProcess.launch(str(PY),child_args,cwd=str(R),environment=environment,
            expected_image_sha256=v['python']['sha256'])
    def emit(owner):s.write_new(R/(args.label+'-LAUNCH-OWNER.json'),owner)
    def read_child():
        nonlocal native_reference
        native_reference=j.exact_ref(terminal)
        value=j.require_native_terminal(native_reference,args.phase)
        assert value['observed_argv']==[v['base_python']['path'],*child_args]
        assert value['cwd']==str(R)
        return native_reference
    try:
        record=run_owned(launch,emit,read_child,timeout=300)
        assert record['child_exit']==0
        assert record['native_owner_after'] and all(record['native_owner_after'].values())
        assert record['primary_error'] is None and record['retirement_error'] is None
        # No native audit is installed in this separate parent. This default
        # path really executes both pinned read-only Git subprocesses.
        post=j.verify(source='before')
        assert j.interpreter_observation(post)==interpreter
    except BaseException as error:
        primary=error
        data=BaseException.__dict__['__dict__'].__get__(error)
        record=dict.get(data,'full_runner_report',record)
    report=dict(phase=args.phase,packet=j.exact_ref(R/'PACKET.json'),candidate_manifest=j.manifest_reference(),
        started_at_ns=started,finished_at_ns=time.time_ns(),parent_argv=list(sys.orig_argv),
        native_child_argv=command,native_child_cwd=str(R),native_child_process=record,
        native_terminal=native_reference,native_release=j.exact_ref(args.release_path),
        parent_runner_sha256=s.sha(Path(__file__)),interpreter=interpreter,
        Git_observed=None if post is None else post['Git_observed'],
        Source_before=j.packet()['Source_before'],environment=j.packet()['environment'],
        Source_observed=None,fixture_dependencies_observed=None,
        primary_error=None if primary is None else failure(primary),
        accepted=False,status='PENDING_OR_FAILED_NATIVE_ENGINEERING_SCOPE',
        source_publication=False,product_acceptance=False,automatic_retry=False)
    if primary is None:
        try:
            _,before=j.proof(j.packet()['Source_before'])
            observed={}
            for name,row in before['targets'].items():
                if row is None:
                    try:s.fs.lstat(F/name)
                    except FileNotFoundError:observed[name]=None
                    else:raise AssertionError('ABSENT_SOURCE_TARGET_NOW_EXISTS:'+name)
                else:observed[name]=s.ordinary(F/name)
            report['Source_observed']=observed
            assert report['Source_observed']==before['targets']
            report['fixture_dependencies_observed']={name:s.ordinary(Path(row['path']))
                for name,row in j.packet()['fixture_dependencies'].items()}
            assert report['fixture_dependencies_observed']==j.packet()['fixture_dependencies']
            # Recheck terminal bytes after all parent observations.
            assert j.exact_ref(terminal)==native_reference
            report.update(accepted=True,status='ACCEPTED_NATIVE_ENGINEERING_SCOPE')
        except BaseException as error:
            primary=error;report['primary_error']=failure(error)
    report['exit_status']=0 if primary is None else 1
    path=R/(args.label+'-CORROBORATION.json')
    try:s.write_new(path,report)
    except BaseException as error:
        if primary is None:raise
        j.retain(primary,error,'native-parent-terminal-writer',record)
    if primary is not None:raise primary
    j.require_native_corroboration(j.exact_ref(path),args.phase)
    print(json.dumps(dict(receipt=j.exact_ref(path),accepted=True,child_exit=record['child_exit'])),flush=True)
    return 0
if __name__=='__main__':sys.exit(main())
