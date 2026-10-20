"""Actual ordinary supervisor child. Never changes argv or source identity."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import io
import json
import os
import sys
import time
import threading

W=Path(__file__).resolve().parent


class OutputBoundError(RuntimeError):pass


class CappedBinary:
    def __init__(self,stream,bound):
        if type(bound) is not int or bound<=0:raise ValueError('OUTER_OUTPUT_BOUND')
        self.stream,self.bound,self.count,self.exceeded=stream,bound,0,False
        self.reserved=0;self.state='READY';self.uncertain=False;self._lock=threading.Lock()
    def write(self,raw):
        if type(raw) is not bytes:raise TypeError('OUTER_OUTPUT_BYTES_REQUIRED')
        with self._lock:
            if self.state!='READY':raise OutputBoundError('OUTER_OUTPUT_FAILED_OR_UNCERTAIN_NO_RETRY')
            available=self.bound-self.reserved;admitted=raw[:available]
            self.reserved+=len(admitted);self.state='WRITE_IN_FLIGHT'
            try:
                written=self.stream.write(admitted)
                if type(written) is not int or not 0<=written<=len(admitted):
                    raise OSError('OUTER_INVALID_OUTPUT_WRITE_COUNT')
                self.count+=written
                if written!=len(admitted):raise OSError('OUTER_SHORT_OUTPUT_WRITE')
            except BaseException:
                self.state='FAILED_UNCERTAIN';self.uncertain=True;raise
            if len(raw)>available:
                self.exceeded=True;self.state='BOUND_EXCEEDED'
                raise OutputBoundError('OUTER_STDIO_BOUND_EXCEEDED')
            self.state='READY';return written
    def flush(self):
        with self._lock:
            if self.state!='READY':raise OutputBoundError('OUTER_OUTPUT_FAILED_OR_UNCERTAIN_NO_RETRY')
            self.state='FLUSH_IN_FLIGHT'
            try:self.stream.flush()
            except BaseException:self.state='FAILED_UNCERTAIN';self.uncertain=True;raise
            self.state='READY'


class CappedText:
    """No finalizer: unknown writes cannot be implicitly flushed or retried."""
    def __init__(self,buffer):self._buffer=buffer
    @property
    def encoding(self):return 'utf-8'
    @property
    def errors(self):return 'strict'
    @property
    def buffer(self):return self._buffer
    def writable(self):return True
    def isatty(self):return False
    def write(self,text):
        if type(text) is not str:raise TypeError('OUTER_OUTPUT_TEXT_REQUIRED')
        self._buffer.write(text.encode('utf8'));return len(text)
    def flush(self):self._buffer.flush()


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--envelope',type=Path,required=True)
    parser.add_argument('--sha256',required=True);args=parser.parse_args()
    # This is the exact on-disk script and normal Python argument vector. The
    # parent pinned both files before launch; no code filename/argv substitution.
    spec=importlib.util.spec_from_file_location('loader_bridge_supervisor',W/'supervisor.py')
    outer=importlib.util.module_from_spec(spec);sys.modules[spec.name]=outer;spec.loader.exec_module(outer)
    envelope_ref=dict(repository_relative_path=args.envelope.relative_to(outer.F).as_posix(),sha256=args.sha256)
    envelope=outer.read_ref(envelope_ref)
    outer.require(envelope['kind']=='CETA_LOADER_BRIDGE_OUTER_ENVELOPE_V1'
        and envelope['supervisor_file']==outer.ref(W/'supervisor.py'),'OUTER_ENVELOPE_SOURCE')
    plan=outer.admission(envelope['outer_request'],child=True);request=plan['request'];paths=plan['paths']
    outer.require(envelope['nonce']==request['nonce'] and args.envelope==paths['envelope']
        and envelope['supervisor_freeze']==request['supervisor_freeze'],'OUTER_ENVELOPE_BINDING')
    marker=outer.read_ref(outer.ref(paths['marker']))
    outer.require(marker['outer_request']==plan['request_reference'] and marker['nonce']==request['nonce']
        and marker['automatic_retry'] is False,'OUTER_PARENT_ATTEMPT_MARKER')
    hello=dict(pid=os.getpid(),argv=list(sys.orig_argv),sys_executable=sys.executable,
        base_executable=getattr(sys,'_base_executable',None),nonce=request['nonce'],outer_request=plan['request_reference'])
    outer.save_new(paths['hello'],hello)
    os.link(paths['hello'],paths['hello_ready'])
    # The canonical constructor resumes before returning. Wait only for the
    # exact parent's emitted owner observation; never reopen a numeric PID.
    deadline=time.monotonic()+5
    while not paths['owner_ready'].exists():
        outer.require(time.monotonic()<deadline,'OUTER_PARENT_OWNER_OBSERVATION_MISSING')
        time.sleep(.01)
    owner=outer.read_ref(outer.ref(paths['owner_ready']))
    outer.require(outer.ref(paths['owner_ready'])['sha256']==outer.ref(paths['owner'])['sha256'],
        'OUTER_OWNER_READY_BYTES_CHANGED')
    interpreter=owner['interpreter']
    outer.require(interpreter['pid']==os.getpid() and interpreter['reported_argv']==list(sys.orig_argv)
        and interpreter['member_of_exact_retained_job'] is True and interpreter['rights']==0x101000
        and type(interpreter['creation_time']) is int and interpreter['creation_time']>0,
        'OUTER_EXACT_OWNED_JOB_INTERPRETER_REQUIRED')
    out_file=err_file=None;old_out,old_err=sys.stdout,sys.stderr
    out=err=None;primary=None;bridge_result=None;status=1;close_errors=[]
    try:
        out_file=paths['stdout'].open('xb',buffering=0)
        err_file=paths['stderr'].open('xb',buffering=0)
        out=CappedBinary(out_file,request['stdio_bound']);err=CappedBinary(err_file,request['stdio_bound'])
        sys.stdout,sys.stderr=CappedText(out),CappedText(err)
        # Import resolution is the exact reviewed successor bridge directory.
        # Its run method is unchanged and repeats its full pre-effect checks.
        sys.path.insert(0,str(outer.ref_path(request['bridge_freeze']).parent))
        bridge_result=plan['bridge'].run(request['bridge_request'])
        status=0 if (bridge_result['diagnostic_completed'] and bridge_result['all_owned_resources_retired']
            and bridge_result['isolation_oracle_passed'] and not bridge_result['failures']
            and bridge_result['profile_cleanup']=='DELETE_SUCCEEDED_AND_FOLDER_ABSENCE_OBSERVED') else 1
    except BaseException as error:primary=error
    finally:
        # Returning to original streams does not change argv/orig_argv. Log
        # flush/close failures survive and are never called proof of bridge cleanup.
        sys.stdout,sys.stderr=old_out,old_err
        for stream,writer in ((out_file,out),(err_file,err)):
            if stream is not None:
                try:
                    if writer is None or not writer.uncertain:
                        stream.flush();os.fsync(stream.fileno())
                    stream.close()
                except BaseException as error:
                    close_errors.append(outer.error_record(error))
                    if primary is None:primary=error
    if primary is not None or close_errors or any(writer is not None and writer.state!='READY' for writer in (out,err)):status=1
    result=dict(kind='CETA_LOADER_BRIDGE_OUTER_CHILD_V1',nonce=request['nonce'],outer_request=plan['request_reference'],
        bridge_request=request['bridge_request'],supervisor_freeze=request['supervisor_freeze'],
        argv=list(sys.orig_argv),pid=os.getpid(),parent_observed_creation_time=interpreter['creation_time'],
        parent_identity_observation='From retained query-only interpreter handle confirmed in the exact canonical outer job',
        exit_status=status,original_error=None if primary is None else outer.error_record(primary),close_errors=close_errors,
        bridge_result=bridge_result,stdio_bound_exceeded=(out is not None and out.exceeded) or (err is not None and err.exceeded),
        stdio_uncertain=(out is not None and out.uncertain) or (err is not None and err.uncertain),
        profile_cleanup_by_supervisor=False,native_qualification=False,product_acceptance=False)
    try:
        for name in ('stdout','stderr'):
            raw=outer.read(paths[name],request['stdio_bound'])
            result[name+'_bytes']=len(raw);result[name+'_sha256']=outer.digest(raw)
        outer.require(len(outer.canonical(result))<=request['child_result_bound'],'OUTER_CHILD_RESULT_BOUND')
        outer.save_new(paths['child'],result)
    except BaseException as evidence_error:
        if primary is not None:
            outer.attach(primary,outer_child_evidence_error=evidence_error,outer_child_result=result)
            raise primary
        outer.attach(evidence_error,outer_child_result=result);raise
    return status


if __name__=='__main__':raise SystemExit(main())
