"""One released180-case child, bounded by the exact canonical owned job."""
from pathlib import Path
import argparse
import json
import sys
from review_support import F,R,Q,V,PY,PIN,j,s,require_delivery_release
from bounded_custody import run_owned,failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--release-path',type=Path,required=True)
    parser.add_argument('--release-sha256',required=True);args=parser.parse_args()
    release=require_delivery_release(args.release_path,args.release_sha256)
    assert not any(name=='ceta' or name.startswith('ceta.') for name in sys.modules)
    temporary=V/'outer-temporary';temporary.mkdir(exist_ok=False);environment=j.child_environment(temporary)
    command=('-B','-X','utf8',str(V/'run_delivered.py'),'--release-path',str(args.release_path),'--release-sha256',args.release_sha256)
    s.write_new(V/'LAUNCH-ATTEMPT.json',dict(at=s.utc(),argv=[str(PY),*command],manifest_sha256=PIN,
        timeout_seconds=600,automatic_retry=False,release=j.exact_ref(args.release_path)))
    sys.path.insert(0,str(F/'src'))
    from ceta.supervisor.windows_jobs import WindowsOwnedProcess
    image=s.ordinary(PY)['sha256']
    def launch():return WindowsOwnedProcess.launch(str(PY),command,cwd=str(V),environment=environment,expected_image_sha256=image)
    def emit(owner):s.write_new(V/'LAUNCH-OWNER.json',owner)
    def child():
        path=V/'delivered-r1/RESULT.json';proof=j.current_json(path)
        assert type(proof['exit_status']) is int and proof['exit_status']==0
        assert proof['expected_ids']==proof['executed_ids']==proof['stopped_ids']==j.manifest()['required_independent_ids']
        assert proof['owned_resources_closed'] is True and proof['remaining_resources']==proof['remaining_threads']==[]
        return j.exact_ref(path)
    primary=record=None
    try:
        record=run_owned(launch,emit,child,timeout=600);assert record['child_exit']==0
        j.verify(source='after')
    except BaseException as error:
        primary=error;data=BaseException.__dict__['__dict__'].__get__(error);record=dict.get(data,'full_runner_report',record)
    report=dict(at=s.utc(),manifest_sha256=PIN,application=release['application'],record=record,
        primary_error=failure(primary) if primary is not None else None,argv=list(sys.orig_argv),child_argv=[str(PY),*command],
        exit_status=0 if primary is None else 1,own_job_only=True,release=j.exact_ref(args.release_path),Source_publication=False,Source_accepted=False)
    try:j.write_bytes(V/'LAUNCH-RESULT.json',(json.dumps(report,indent=2,allow_nan=False)+'\n').encode())
    except BaseException as error:
        if primary is None:raise
        j.retain(primary,error,'delivered-outer-result-writer')
    if primary is not None:raise primary
    return 0


if __name__=='__main__':sys.exit(main())
