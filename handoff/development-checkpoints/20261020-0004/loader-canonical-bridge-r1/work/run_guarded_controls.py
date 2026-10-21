"""Run bridge data controls under native/process/network/config effect guards."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import ctypes
import hashlib
import json
import os
import subprocess
import sys
import threading
import unittest
import unittest.mock
import traceback

W=Path(__file__).resolve().parent
sys.dont_write_bytecode=True


def hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in W.glob('*.py')}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--attempt',required=True)
    args=parser.parse_args()
    assert args.attempt.isascii() and args.attempt.replace('-','').isalnum()
    output=W/'controls'/args.attempt
    output.mkdir(parents=True,exist_ok=False)
    before=hashes();denied=[];threads=set(threading.enumerate())
    def deny(name):
        def prohibited(*a,**kw):
            denied.append(name)
            raise RuntimeError('DATA_ONLY_EFFECT_DENIED:'+name)
        return prohibited
    def own_write(path):
        if type(path) is int:return path in (1,2)
        path=Path(path).resolve()
        return path.is_relative_to(W) and not any(getattr(p.lstat(),'st_file_attributes',0)&0x400
            for p in [path,*path.parents] if p.exists() and p.is_relative_to(W))
    def audit(event,values):
        if event.startswith(('subprocess.','socket.','winreg.')) or event in (
            'ctypes.dlopen','ctypes.dlsym','ctypes.dlsym/handle','ctypes.call_function',
            'sqlite3.connect','os.system','os.startfile','os.kill'):
            deny(event)()
        if event=='open':
            path,mode,flags=values
            if (mode and any(c in mode for c in 'wax+')) or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                if not own_write(path):deny('write-outside-work')()
        if event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime') and not own_write(values[0]):
            deny(event+'-outside-work')()
        if event in ('os.rename','os.replace') and not all(own_write(p) for p in values[:2]):
            deny(event+'-outside-work')()
    for name in ('WinDLL','CDLL','OleDLL','PyDLL','WINFUNCTYPE','CFUNCTYPE'):
        if hasattr(ctypes,name):setattr(ctypes,name,deny('ctypes.'+name))
    subprocess.Popen=deny('subprocess.Popen')
    import _winapi
    _winapi.CreateProcess=deny('_winapi.CreateProcess')
    sys.addaudithook(audit)
    sys.path.insert(0,str(W))
    started=datetime.now(timezone.utc).isoformat();status=1
    report=dict(kind='GUARDED_BRIDGE_DATA_CONTROLS_V1',started_at=started,argv=sys.orig_argv,
        python=sys.executable,before_hashes=before,synthetic_approval_records='CONTROLLED DATA ONLY; not real consent',
        native_execution=False,profile_execution=False,product_acceptance=False)
    with (output/'RAW.txt').open('x',encoding='utf8') as stream:
        try:
            loader=unittest.TestLoader();suite=loader.discover(str(W),pattern='test_bridge.py')
            def ids(group):
                if isinstance(group,unittest.TestSuite):
                    for item in group:yield from ids(item)
                else:yield group.id()
            expected=list(ids(suite));result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
            report.update(expected_ids=expected,tests_run=result.testsRun,
                failures=[(t.id(),s) for t,s in result.failures],errors=[(t.id(),s) for t,s in result.errors],
                skips=[(t.id(),s) for t,s in result.skipped],loader_errors=loader.errors)
            status=0 if result.wasSuccessful() and result.testsRun==len(expected) and not result.skipped and not loader.errors else 1
        except BaseException as error:
            traceback.print_exc(file=stream);report['runner_failure']=dict(type=type(error).__name__,message=str(error))
    report.update(finished_at=datetime.now(timezone.utc).isoformat(),after_hashes=hashes(),denied_calls=denied,
        remaining_threads=[t.name for t in set(threading.enumerate())-threads if t.is_alive()])
    report['code_unchanged']=report['before_hashes']==report['after_hashes']
    if denied or report['remaining_threads'] or not report['code_unchanged']:status=1
    report['exit_status']=status
    (output/'RESULT.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    print(json.dumps(dict(path=str(output/'RESULT.json'),sha256=hashlib.sha256((output/'RESULT.json').read_bytes()).hexdigest(),
                         exit_status=status,tests_run=report.get('tests_run'))))
    return status


if __name__=='__main__':raise SystemExit(main())
