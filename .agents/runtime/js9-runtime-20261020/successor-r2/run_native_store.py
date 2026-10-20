"""Dormant original18 file-binding contract cases; exact Root release required.

Actual disposable Windows files and SQLite are used. No child, listener,
profile, approval ceremony or CPU Set is allowed by this adapter.
"""
from pathlib import Path
import argparse,contextlib,json,os,sys,threading,time,traceback,unittest
from unittest.mock import patch
import js9_support as j
from js9_support import s,F,Q,R
from bounded_custody import failure

def main():
    parser=argparse.ArgumentParser();parser.add_argument('label')
    parser.add_argument('--release-path',type=Path,required=True);parser.add_argument('--release-sha256',required=True)
    args=parser.parse_args();assert args.label.isidentifier()
    release=j.require_release(args.release_path,args.release_sha256,'native-store')
    v=j.verify(source='before');interpreter=j.interpreter_observation(v)
    output=R/args.label;output.mkdir(exist_ok=False)
    blocked=[]
    def audit(event,details):
        bad=False
        if event in ('subprocess.Popen','os.system','os.startfile','os.startfile/2') or event.startswith('socket.'):
            bad=True
        elif event=='open' and isinstance(details[0],(str,bytes,os.PathLike)):
            flags=details[2]
            if isinstance(flags,int) and flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                bad=not Path(os.fsdecode(details[0])).resolve().is_relative_to(output)
        elif event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime','os.truncate'):
            bad=not Path(os.fsdecode(details[0])).resolve().is_relative_to(output)
        elif event in ('os.rename','os.link','os.symlink'):
            bad=not all(Path(os.fsdecode(path)).resolve().is_relative_to(output) for path in details[:2])
        if bad:blocked.append(dict(event=event,details=repr(details)));raise RuntimeError('JS9_NATIVE_STORE_BOUNDARY')
    sys.addaudithook(audit)
    sys.path[:0]=[str(Q/'src'),str(Q/'tests/contract')]
    from ceta.store.sqlite_runtime import load_sqlite,runtime_identity
    load_sqlite();sqlite_identity=runtime_identity()
    import sqlite3
    from resource_observer import Observer
    physical=Observer(sqlite3);physical.install()
    from ceta.identity.native_owner_view import NativeStoreBinding
    from ceta.supervisor.windows_jobs import WindowsOwnedProcess
    from ceta.identity.native_approval import NativeApprovalOwner
    import ceta.kernel.cpu_execution as execution
    bindings=[];original=NativeStoreBinding.__init__
    def capture(owner,*args,**kwargs):
        bindings.append(owner);return original(owner,*args,**kwargs)
    def deny(*args,**kwargs):
        blocked.append(dict(event='NATIVE_EFFECT_NOT_IN_STORE_SCOPE'))
        raise RuntimeError('JS9_NATIVE_STORE_EFFECT_FORBIDDEN')
    controls=[patch.object(NativeStoreBinding,'__init__',capture),
        patch.object(WindowsOwnedProcess,'launch',staticmethod(deny)),
        patch.object(NativeApprovalOwner,'_start_session',deny),
        patch.object(execution,'_APPLY',deny),patch.object(execution,'_RESTORE',deny)]
    expected=j.packet()['native_store_ids'];events=[];result=None;primary=None
    threads=set(threading.enumerate());started=s.utc();tick=time.perf_counter()
    class Result(unittest.TextTestResult):
        def startTest(self,test):events.append(dict(event='START',id=test.id(),at=s.utc()));super().startTest(test)
        def stopTest(self,test):events.append(dict(event='STOP',id=test.id(),at=s.utc()));super().stopTest(test)
    with (output/'RAW.txt').open('x',encoding='utf8') as log,contextlib.ExitStack() as stack:
        try:
            for control in controls:stack.enter_context(control)
            import test_native_owner_view as tests
            tests.ROOT=output
            suite=unittest.defaultTestLoader.loadTestsFromTestCase(tests.NativeStoreBindingTests)
            assert list(j.ids(suite))==expected and len(expected)==18
            result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=Result).run(suite)
        except BaseException as error:primary=error;traceback.print_exc(file=log)
        finally:
            try:physical.uninstall()
            except BaseException as error:
                if primary is None:primary=error
                else:j.retain(primary,error,'physical-observer-uninstall')
    proof=physical.finish()
    rows=[dict(closed=owner.closed,pending=owner.pending_native_resources,
        pins=[dict(path=str(row['path']),handle=row['handle'],enrolled=row['enrolled'],
            open_state=row['open_state']) for row in owner._pins]) for owner in bindings]
    remaining=[dict(name=t.name,native_id=t.native_id) for t in set(threading.enumerate())-threads if t.is_alive()]
    starts=[row['id'] for row in events if row['event']=='START'];stops=[row['id'] for row in events if row['event']=='STOP']
    j.verify(source='before',verify_git=False);assert j.interpreter_observation(v)==interpreter
    passed=(primary is None and result is not None and result.wasSuccessful() and not result.skipped
        and result.testsRun==18 and expected==starts==stops and not remaining and not blocked
        and bool(rows) and all(row['closed'] and not row['pending'] for row in rows)
        and proof['owned_resources_closed'] is True)
    report=dict(phase='native-store',started_at=started,finished_at=s.utc(),elapsed_seconds=time.perf_counter()-tick,
        packet=j.exact_ref(R/'PACKET.json'),runner_sha256=s.sha(Path(__file__)),post_CAS_verified=True,
        Git_corroboration=dict(status='PENDING_ROOT_CORROBORATION',before=v['Git_observed'],after=None),
        acceptance_complete=False,
        command=list(sys.orig_argv),observed_argv=list(sys.orig_argv),cwd=str(Path.cwd()),
        interpreter=interpreter,release=j.exact_ref(args.release_path),
        candidate_manifest=j.manifest_reference(),expected_ids=expected,events=events,
        tests_run=0 if result is None else result.testsRun,
        failures=[] if result is None else [(t.id(),detail) for t,detail in result.failures],
        errors=[] if result is None else [(t.id(),detail) for t,detail in result.errors],
        skips=[] if result is None else [(t.id(),reason) for t,reason in result.skipped],
        primary_error=None if primary is None else failure(primary),
        binding_custody=rows,physical_custody=proof,sqlite_runtime=sqlite_identity,
        remaining_threads=remaining,boundary_violations=blocked,
        actual_disposable_native_file_operations=True,host_profiles=False,Source_publication=False,
        Source_accepted=False,passed=passed,exit_status=0 if passed else 1)
    j.write_bytes(output/'RESULT.json',(json.dumps(report,indent=2,allow_nan=False)+'\n').encode())
    if primary is not None:raise primary
    print(json.dumps(dict(result=j.exact_ref(output/'RESULT.json'),passed=passed)),flush=True)
    return report['exit_status']
if __name__=='__main__':sys.exit(main())
