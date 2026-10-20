"""Dormant canonical job wrapper: exact reviewed full command, one attempt."""
from pathlib import Path
import argparse,json,sys
import js8_support as j
from js8_support import s,F,Q,R,PY
from bounded_custody import run_owned,failure

def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('candidate-full','destination-full'))
    parser.add_argument('--release-path',type=Path,required=True);parser.add_argument('--release-sha256',required=True)
    args=parser.parse_args();j.require_release(args.release_path,args.release_sha256,args.phase)
    v=j.verify(source='after' if args.phase=='destination-full' else 'before');child_environment=j.child_environment(R)
    interpreter=j.interpreter_observation(v)
    assert not any(name=='ceta' or name.startswith('ceta.') for name in sys.modules)
    root=F if args.phase=='destination-full' else Q
    command=('-B','-X','utf8',str(R/'run_full.py'),args.phase,'--release-path',str(args.release_path),'--release-sha256',args.release_sha256)
    attempt=R/(args.phase+'-LAUNCH-ATTEMPT.json')
    s.write_new(attempt,{'at':s.utc(),'phase':args.phase,'argv':[str(PY),*command],'timeout_seconds':900,
        'release':j.exact_ref(args.release_path),'automatic_retry':False,'Source_accepted':False})
    sys.path.insert(0,str(root/'src'));from ceta.supervisor.windows_jobs import WindowsOwnedProcess
    record=primary=None
    def launch():return WindowsOwnedProcess.launch(str(PY),command,cwd=str(R),environment=child_environment,expected_image_sha256=v['python']['sha256'])
    def emit(owner):s.write_new(R/(args.phase+'-LAUNCH-OWNER.json'),owner)
    def child():
        path=R/args.phase/'RESULT.json';full=j.current_json(path)
        j.require_case_ids(full['expected_ids']);assert full['exit_status']==0
        return j.exact_ref(path)
    try:
        record=run_owned(launch,emit,child,timeout=900)
        assert record['child_exit']==0
        j.verify(source='after' if args.phase=='destination-full' else 'before')
        assert j.interpreter_observation(v)==interpreter
    except BaseException as error:
        primary=error;data=BaseException.__dict__['__dict__'].__get__(error);record=dict.get(data,'full_runner_report',record)
    report={'phase':args.phase,'at':s.utc(),'record':record,'primary_error':failure(primary) if primary is not None else None,
        'argv':list(sys.orig_argv),'interpreter':interpreter,'child_argv':[str(PY),*command],
        'exit_status':0 if primary is None else 1,'own_job_only':True,'Source_accepted':False,'release':j.exact_ref(args.release_path)}
    try:j.write_bytes(R/(args.phase+'-LAUNCH-RESULT.json'),(json.dumps(report,indent=2)+'\n').encode())
    except BaseException as error:
        if primary is None:raise
        j.retain(primary,error,'outer-result-writer')
    if primary is not None:raise primary
    return 0
if __name__=='__main__':sys.exit(main())
