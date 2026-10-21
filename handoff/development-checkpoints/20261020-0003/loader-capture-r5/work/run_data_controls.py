"""Executable data-only controls with native/process/network/write guards."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import ctypes
import hashlib
import importlib
import json
import os
import subprocess
import sys
import threading
import traceback
import unittest
import unittest.mock  # Import stdlib async definitions before process constructors are guarded.

W=Path(__file__).resolve().parent


def hashes():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in W.glob('*.py')}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('stage',choices=('tests','inventory'))
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
    def safe_write(path):
        if type(path) is int:
            # Only inherited stdio is used; candidate code cannot open a handle
            # by numeric ID through this control.
            return path in (1,2)
        resolved=Path(path).resolve()
        if not resolved.is_relative_to(W):return False
        current=W
        for part in resolved.relative_to(W).parts:
            current/=part
            if current.exists() and current.stat().st_file_attributes&0x400:return False
        return True
    def audit(event, values):
        if event.startswith(('subprocess.','socket.','winreg.')) or event in (
            'ctypes.dlopen','ctypes.dlsym','ctypes.dlsym/handle','ctypes.call_function',
            'sqlite3.connect','os.system','os.startfile','os.kill'):
            deny(event)()
        if event=='open':
            path,mode,flags=values
            if (mode and any(letter in mode for letter in 'wax+')) or flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND):
                if not safe_write(path):deny('write-outside-work')()
        if event in ('os.mkdir','os.remove','os.rmdir','os.chmod','os.utime'):
            if not safe_write(values[0]):deny(event+'-outside-work')()
        if event in ('os.rename','os.replace'):
            if not all(safe_write(p) for p in values[:2]):deny(event+'-outside-work')()
    for name in ('WinDLL','CDLL','OleDLL','PyDLL'):
        if hasattr(ctypes,name):setattr(ctypes,name,deny('ctypes.'+name))
    subprocess.Popen=deny('subprocess.Popen')
    import _winapi
    _winapi.CreateProcess=deny('_winapi.CreateProcess')
    sys.addaudithook(audit)
    sys.path.insert(0,str(W))
    started=datetime.now(timezone.utc).isoformat()
    report=dict(stage=args.stage,started_at=started,argv=sys.orig_argv,
                python=sys.executable,before_hashes=before,native_effects_authorized=False,
                native_functions='Controlled Python fixtures only',actual_native_qualification=False)
    status=1
    with (output/'RAW.txt').open('x',encoding='utf8') as stream:
        try:
            if args.stage=='inventory':
                importlib.import_module('freeze_inputs').main()
                report['inventory_completed']=True
                passed=True
            else:
                loader=unittest.TestLoader()
                suite=loader.discover(str(W),pattern='test_loader*.py')
                def ids(group):
                    if isinstance(group,unittest.TestSuite):
                        for item in group:yield from ids(item)
                    else:yield group.id()
                expected=list(ids(suite))
                result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
                report.update(expected_ids=expected,tests_run=result.testsRun,
                    failures=[(t.id(),message) for t,message in result.failures],
                    errors=[(t.id(),message) for t,message in result.errors],
                    skips=[(t.id(),reason) for t,reason in result.skipped],loader_errors=loader.errors)
                passed=result.wasSuccessful() and result.testsRun==len(expected) and not result.skipped and not loader.errors
            status=0 if passed else 1
        except BaseException as error:
            traceback.print_exc(file=stream)
            report['runner_failure']=dict(type=type(error).__name__,message=str(error))
    report.update(finished_at=datetime.now(timezone.utc).isoformat(),after_hashes=hashes(),
        denied_calls=denied,remaining_threads=[t.name for t in set(threading.enumerate())-threads if t.is_alive()])
    report['code_unchanged']=report['before_hashes']==report['after_hashes']
    if denied or report['remaining_threads'] or not report['code_unchanged']:status=1
    report['exit_status']=status
    with (output/'RESULT.json').open('x',encoding='utf8') as stream:
        json.dump(report,stream,indent=2,allow_nan=False);stream.write('\n')
    print(json.dumps(dict(result=str(output/'RESULT.json'),exit_status=status,
                         tests_run=report.get('tests_run'),sha256=hashlib.sha256((output/'RESULT.json').read_bytes()).hexdigest())))
    return status


if __name__=='__main__':raise SystemExit(main())
