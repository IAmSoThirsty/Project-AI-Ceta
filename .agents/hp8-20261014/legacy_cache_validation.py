"""Exact W045 legacy evidence consumer and bounded canonical native transport.

Neither this module nor its fixed worker issues policy authority. A caller must
already permit the subject and every generator alias, and must recheck current
denials before accepting any returned content-provenance receipt. This module
validates the exact independently inspected historical structural match only.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
import time
import msvcrt

P=Path(r'T:\00-Active\Project-AI-CETA')
X=Path(r'T:\00-Active\Architecture-Rebuild-CETA-Epoch-Ready-v0.3.0')
IMAGE=Path(r'C:\Users\Quencher\AppData\Local\Programs\Python\Python311\python.exe')
IMAGE_SHA256='5f7b89a612c9b8af1d6456cdfcd1dbe5ca630849e79aebced9bee9a6694952ec'
WORKER=Path(__file__).with_name('legacy_cache_worker311.py')
WORKER_SHA256='f403ceb9345ba1152d4f104cf0091c50a42bb786f4349582829ca11ec0a3c54d'
NATIVE_PORT=P/'src/ceta/supervisor/windows_jobs.py'
NATIVE_PORT_SHA256='02b6306c3ea32bebf887e19c3ba24367d4f041a77d52add62ac4da8719926f0e'
READER=P/'.agents/runtime/legacy-cache-provenance-20261014/generator-search.json'
READER_SHA256='65fad987e0825c70648929c5f5f7451bfe1ed0b9a52bbbacaf0109152a5260fd'
REVIEW=P/'.agents/runtime/legacy-cache-root-review-20261014/review.json'
REVIEW_SHA256='5df697496c7e26ec7b491340794cbb9dfa020b7e4b98327d114c57eecc0f1b9b'
CACHE_PATH='scripts/__pycache__/hostile_audit.cpython-311.pyc'
CACHE_SHA256='84d238316c9e49f83111c9f782080ca03b6e74c5f656c79587e129ba6b7ef29f'
SOURCE_SHA256='b7b4a33a9614167f04675f96511d7e73ff7dea3155e949bf4a08a33aeae80f17'
SOURCE_OID='6a0bd77529ed73fa28167777a8cbc831f11ba186'
ALIASES=['scripts/hostile_audit.py']
SCHEMA='ceta.w045.data-only.v1'
MAX_REQUEST,MAX_RESPONSE,MAX_STDERR=65536,8192,1024
EXECUTION_SECONDS,CLEANUP_SECONDS=5,5

class _PipeCustody:
    """Fence target entry before retiring an ambiguously started descriptor."""
    def __init__(self,descriptor):
        self.descriptor=descriptor
        self.entered=self.fenced=self.retired=False
        self.lock=threading.Lock()
    def enter(self):
        with self.lock:
            if self.fenced:return False
            self.entered=True
            return True
    def finish(self,result):
        with self.lock:
            if self.retired:return
            try:os.close(self.descriptor)
            except OSError as error:result.update(error=True,close_error=error,unclosed_descriptor=self.descriptor)
            else:self.retired=True
    def fence_unused(self):
        with self.lock:
            self.fenced=True
            if not self.entered and not self.retired:
                os.close(self.descriptor)
                self.retired=True
    def open_descriptor(self):
        with self.lock:return None if self.retired else self.descriptor

class _DescriptorView:
    """Read current ownership instead of retaining numbers retired by a thread."""
    def __init__(self,reader):self.reader=reader
    def __iter__(self):return iter(self.reader())
    def __len__(self):return len(self.reader())
    def __bool__(self):return bool(self.reader())
    def __eq__(self,other):return self.reader()==tuple(other)

class LegacyValidationError(RuntimeError):
    """Typed safe error; unresolved real ownership must propagate to the caller."""
    def __init__(self,code,*,owned_process=None,threads=(),worker_lease=None,native_failure=None,pipe_descriptors=(),primary_failure=None):
        super().__init__(code)
        self.code,self.owned_process,self.threads,self.worker_lease=code,owned_process,threads,worker_lease
        self.native_failure,self.pipe_descriptors=native_failure,pipe_descriptors
        self.primary_failure=primary_failure

def need(condition,code):
    if not condition:raise LegacyValidationError(code)

def digest(data):return hashlib.sha256(data).hexdigest()

def unique_pairs(pairs):
    output={}
    for name,value in pairs:
        if name in output:raise ValueError('duplicate protocol field')
        output[name]=value
    return output

def exact_entry(base,entry,record,source_root,aliases):
    return (type(entry) is dict and entry.get('entry_id')=='W045' and entry.get('kind')=='generated_cache'
            and base.same_path(source_root,X) and entry.get('path')==CACHE_PATH and entry.get('sha256')==CACHE_SHA256
            and record.get('classification')=='LEGACY_CACHE_GENERATOR_UNRESOLVED' and record.get('kind')=='working'
            and record.get('path')==CACHE_PATH and record.get('whole_file_sha256')==CACHE_SHA256 and record.get('bytes')==10572
            and aliases.get(SOURCE_OID)==ALIASES)

def proof(base):
    reader_raw=base.bounded_proof_read(base.safe_components(READER));review_raw=base.bounded_proof_read(base.safe_components(REVIEW))
    need(digest(reader_raw)==READER_SHA256 and digest(review_raw)==REVIEW_SHA256,'LEGACY_PROOF_CHANGED')
    reader=base.strict_proof_json(reader_raw);review=base.strict_proof_json(review_raw)
    need(reader.get('disposition')=='MATCHED_UNIQUE_GENERATOR_BYTES' and review.get('decision')=='approved_finite_structural_provenance'
         and review.get('exit_status')==0 and review.get('reviewed_reader_report_sha256')==READER_SHA256,'LEGACY_PROOF_DECISION')
    need(reader['cache']['sha256']==review['cache_sha256']==CACHE_SHA256 and reader['cache']['bytes']==review['cache_bytes']==10572
         and reader['cache']['magic_hex']=='a70d0d0a' and reader['cache']['header_flags']==0
         and reader['cache']['marshal_all_body_consumed'] is True,'LEGACY_CACHE_PROOF')
    need(reader['unique_matching_source_sha256']==[SOURCE_SHA256] and review['generator_oid']==SOURCE_OID
         and review['generator_sha256']==SOURCE_SHA256 and review['generator_bytes']==6316 and review['all_tree_aliases']==ALIASES,'LEGACY_GENERATOR_PROOF')
    need(reader['compiler']['executable']==review['compiler_executable']==str(IMAGE)
         and reader['compiler']['executable_sha256']==review['compiler_sha256']==IMAGE_SHA256,'LEGACY_COMPILER_PROOF')
    levels=review['matching_compile_levels'];need(type(levels) is list and [row['optimization'] for row in levels]==[0,1,2]
         and all(row['all_listed_fields_and_constants_equal'] is True for row in levels),'LEGACY_COMPILE_PROOF')
    descriptor={'source_root':str(X),'kind':'historical_blob','git_oid':SOURCE_OID,'aliases':list(ALIASES),'sha256':SOURCE_SHA256,'bytes':6316}
    descriptor['member']=digest(base.canonical_proof(descriptor))+'.py'
    cache={'id':'W045','sha256':CACHE_SHA256,'marshal_all_body_consumed':True,'interpreter':reader['compiler']['version'],'magic_hex':'a70d0d0a',
           'legacy_structural_proof':{'reader_sha256':READER_SHA256,'review_sha256':REVIEW_SHA256,'matching_compile_levels':[0,1,2],
                                      'original_producer_custody':'UNPROVED','original_optimization':'UNPROVED'}}
    return cache,descriptor

def _port(base):
    need(digest(base.read_bytes(base.safe_components(NATIVE_PORT)))==NATIVE_PORT_SHA256,'NATIVE_CUSTODY_PORT_CHANGED')
    source=str(P/'src')
    if source not in sys.path:sys.path.insert(0,source)
    from ceta.supervisor import windows_jobs
    need(Path(windows_jobs.__file__)==NATIVE_PORT,'NATIVE_CUSTODY_PORT_IDENTITY')
    return windows_jobs.WindowsOwnedProcess

def _environment():
    values={name:value for name,value in os.environ.items() if name.upper() in {'SYSTEMROOT','WINDIR','SYSTEMDRIVE','COMSPEC'}}
    values.update(PYTHONDONTWRITEBYTECODE='1',PYTHONUTF8='1')
    return values

def _exchange(base,request):
    """No bytes in argv/files/logs. Pipe threads retain their exact own descriptors."""
    need(os.name=='nt' and sys.version_info[:2]==(3,12),'PARENT_RUNTIME_IDENTITY')
    need(type(request) is bytes and len(request)<=MAX_REQUEST,'REQUEST_BOUND')
    image=base.safe_components(IMAGE)
    size,image_hash,_=base.hash_file(image);need(image_hash==IMAGE_SHA256,'LEGACY_IMAGE_CHANGED')
    worker=base.safe_components(WORKER)
    need(worker.parent==Path(__file__).parent and worker.parent.name=='hp8-20261014','LEGACY_WORKER_PATH')
    launch=_port(base).launch
    lease=base.open_source(worker,exclusive=True);stream=lease.__enter__()
    owned=None;threads=[];main_fds=[];pipes={};failure=None;began=time.monotonic();native=None;primary=None;retained=False
    pipe_slots={};cleanup_lock=threading.RLock();returned_error=None
    start_requested=set();start_returned=set()
    delegated_failure=None
    def descriptors():
        slotted={slot.descriptor for slot in pipe_slots.values()}
        return tuple(dict.fromkeys([value for value in main_fds if value not in slotted]+[value for slot in pipe_slots.values()
                     if (value:=slot.open_descriptor()) is not None]))
    def expose(error,cleanup_failure=None):
        nonlocal returned_error
        returned_error=error
        error.owned_process=owned if owned is not None else getattr(delegated_failure,'owned_process',None)
        error.native_failure=delegated_failure
        error.threads,error.worker_lease=tuple(threads),lease
        error.pipe_descriptors=_DescriptorView(descriptors)
        error.close_cleanup=recover
        error.pipe_custody=tuple(pipe_slots.values())
        if cleanup_failure is not None or not hasattr(error,'cleanup_failure'):error.cleanup_failure=cleanup_failure
        error.thread_start_ambiguity=tuple(thread for thread in threads
                                           if thread in start_requested and thread not in start_returned)
    def recover():
        """Close only exact owned resources; return pending threads explicitly."""
        nonlocal owned,lease,delegated_failure
        with cleanup_lock:
            # A fenced target that has not entered cannot read, write or close
            # this descriptor even if native startup completes after return.
            for slot in pipe_slots.values():slot.fence_unused()
            if delegated_failure is not None:
                # This is the existing native owner's explicit recovery, not
                # another process/handle owner or an inferred successful close.
                delegated_failure.close_cleanup()
                delegated_failure=None
            if owned is not None:
                owned.terminate(125)
                need(owned.wait(CLEANUP_SECONDS) and owned.active_process_count()==0,'LEGACY_CUSTODY_UNRESOLVED')
            pending=[]
            for thread in threads:
                if thread not in start_requested:continue
                try:thread.join(CLEANUP_SECONDS)
                except RuntimeError:
                    # join-before-start is uncertainty, not proof of no start.
                    pending.append(thread)
                else:
                    if thread.is_alive():pending.append(thread)
            if owned is not None:owned.close();owned=None
            slotted={slot.descriptor for slot in pipe_slots.values()}
            for descriptor in tuple(main_fds):
                # Slot assignment establishes ownership atomically. Even an
                # interrupt between subsequent bookkeeping removals cannot
                # make the main list retire a slot's descriptor a second time.
                if descriptor not in slotted:os.close(descriptor)
                main_fds.remove(descriptor)
            # Only the target can retire a descriptor after it entered. A
            # still-running target and its exact open FD remain caller-owned.
            for slot in pipe_slots.values():
                if slot.open_descriptor() is not None:
                    need(not pending,'LEGACY_PIPE_CUSTODY_UNRESOLVED')
                    # A stopped target can leave a failed-close descriptor.
                    os.close(slot.descriptor);slot.retired=True
            if lease is not None:lease.__exit__(None,None,None);lease=None
            if returned_error is not None:expose(returned_error)
            return {'pending_threads':tuple(pending),'pipe_descriptors':descriptors(),
                    'owned_process':owned,'worker_lease':lease,
                    'future_pipe_IO_fenced':all(slot.fenced for slot in pipe_slots.values())}
    try:
        need(digest(stream.read(MAX_REQUEST+1))==WORKER_SHA256,'LEGACY_WORKER_CHANGED')
        in_read,in_write=os.pipe();main_fds.extend((in_read,in_write))
        out_read,out_write=os.pipe();main_fds.extend((out_read,out_write))
        err_read,err_write=os.pipe();main_fds.extend((err_read,err_write))
        for descriptor in (in_read,out_write,err_write):os.set_inheritable(descriptor,True)
        for descriptor in (in_write,out_read,err_read):os.set_inheritable(descriptor,False)
        try:
            owned=launch(str(image),('-I','-S','-B','-X','utf8',str(worker)),cwd=str(worker.parent),environment=_environment(),
                         standard_handles=tuple(msvcrt.get_osfhandle(value) for value in (in_read,out_write,err_write)),expected_image_sha256=IMAGE_SHA256)
        except Exception as native_error:
            if hasattr(native_error,'close_cleanup'):
                try:native_error.close_cleanup()
                except Exception:
                    delegated_failure=native_error
                    raise LegacyValidationError('LEGACY_NATIVE_CUSTODY_UNRESOLVED',owned_process=getattr(native_error,'owned_process',None),
                          native_failure=native_error,worker_lease=lease,pipe_descriptors=tuple(main_fds)) from None
            raise LegacyValidationError('LEGACY_NATIVE_LAUNCH_FAILED') from None
        pid,creation=owned.pid,owned.creation_time
        for descriptor in (in_read,out_write,err_write):os.close(descriptor);main_fds.remove(descriptor)
        pipe_slots={'stdin':_PipeCustody(in_write),'stdout':_PipeCustody(out_read),'stderr':_PipeCustody(err_read)}
        # Sole ownership moves to the fenced slots before Thread construction
        # or any start attempt. No cleanup list can close the same pipe twice.
        for descriptor in (in_write,out_read,err_read):main_fds.remove(descriptor)
        def send():
            if not pipe_slots['stdin'].enter():return
            result={'written':0,'error':False}
            try:
                while result['written']<len(request):
                    amount=os.write(in_write,request[result['written']:]);need(amount>0,'PIPE_WRITE_FAILED');result['written']+=amount
            except BaseException:result['error']=True
            finally:
                pipe_slots['stdin'].finish(result)
                pipes['stdin']=result
        def receive(label,descriptor,bound):
            if not pipe_slots[label].enter():return
            result={'data':b'','overflow':False,'error':False}
            try:
                chunks=[];count=0
                while True:
                    block=os.read(descriptor,min(4096,bound+1-count))
                    if not block:break
                    count+=len(block);chunks.append(block)
                    if count>bound:result['overflow']=True;break
                result['data']=b''.join(chunks)
            except BaseException:result['error']=True
            finally:
                pipe_slots[label].finish(result)
                pipes[label]=result
        functions=[(send,(),in_write),(receive,('stdout',out_read,MAX_RESPONSE),out_read),(receive,('stderr',err_read,MAX_STDERR),err_read)]
        for function,args,descriptor in functions:
            thread=threading.Thread(target=function,args=args,daemon=True)
            threads.append(thread)
        for thread in threads:
            start_requested.add(thread)
            try:thread.start()
            except Exception:raise LegacyValidationError('LEGACY_PIPE_THREAD_FAILED') from None
            start_returned.add(thread)
        if not owned.wait(EXECUTION_SECONDS):failure='LEGACY_WORKER_DEADLINE'
        exit_code=owned.poll()
        deadline=time.monotonic()+CLEANUP_SECONDS
        while owned.active_process_count() and time.monotonic()<deadline:time.sleep(.01)
        if owned.active_process_count():failure=failure or 'LEGACY_CHILD_LIFETIME_PENDING'
        if failure:
            owned.terminate(125)
            if not owned.wait(CLEANUP_SECONDS):raise LegacyValidationError('LEGACY_CUSTODY_UNRESOLVED',owned_process=owned,threads=tuple(threads),worker_lease=lease)
            deadline=time.monotonic()+CLEANUP_SECONDS
            while owned.active_process_count() and time.monotonic()<deadline:time.sleep(.01)
        if owned.active_process_count():raise LegacyValidationError('LEGACY_CUSTODY_UNRESOLVED',owned_process=owned,threads=tuple(threads),worker_lease=lease)
        for thread in threads:thread.join(CLEANUP_SECONDS)
        if any(thread.is_alive() for thread in threads):raise LegacyValidationError('LEGACY_PIPE_CUSTODY_UNRESOLVED',owned_process=owned,threads=tuple(threads),worker_lease=lease)
        unclosed=[value for value in pipes.values() if 'unclosed_descriptor' in value]
        if unclosed:
            raise LegacyValidationError('LEGACY_PIPE_DESCRIPTOR_UNRESOLVED',owned_process=owned,threads=tuple(threads),worker_lease=lease,
                  pipe_descriptors=descriptors(),primary_failure=unclosed[0]['close_error'])
        native={'pid':pid,'creation_time_100ns':creation,'image_sha256':IMAGE_SHA256,'worker_sha256':WORKER_SHA256,
                'exit_status':exit_code,'observed_empty_job':True,'pipe_threads_joined':True,'request_bytes':len(request),
                'response_bytes':len(pipes['stdout']['data']),'stderr_bytes':len(pipes['stderr']['data']),'elapsed_seconds':time.monotonic()-began,
                'native_start_occupancy':'Synchronous canonical native launch; OS/kernel/driver occupancy is not fully time-bounded'}
        owned.close();owned=None
        if failure:raise LegacyValidationError(failure)
        need(set(pipes)=={'stdin','stdout','stderr'} and pipes['stdin']['written']==len(request)
             and not any(value['error'] for value in pipes.values()),'LEGACY_PIPE_FAILED')
        need(not pipes['stdout']['overflow'] and not pipes['stderr']['overflow'],'LEGACY_OUTPUT_BOUND')
        need(not pipes['stderr']['data'],'LEGACY_WORKER_STDERR')
        try:response=json.loads(pipes['stdout']['data'].decode('utf-8'),object_pairs_hook=unique_pairs,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('invalid number')))
        except (ValueError,TypeError,UnicodeError,RecursionError):raise LegacyValidationError('LEGACY_RESPONSE_FORMAT') from None
        need(type(response) is dict and response.get('schema')==SCHEMA and type(response.get('ok')) is bool,'LEGACY_RESPONSE_SCHEMA')
        if response['ok'] is False:
            need(set(response)=={'schema','ok','error_code'} and type(response['error_code']) is str and len(response['error_code'])<=64,'LEGACY_RESPONSE_SCHEMA')
            raise LegacyValidationError('LEGACY_DATA_REJECTED')
        need(exit_code==0,'LEGACY_WORKER_EXIT')
        return response,native
    except BaseException as error:
        primary=error
        if isinstance(error,LegacyValidationError) and (error.owned_process is not None or error.native_failure is not None):
            expose(error)
            retained=True  # caller receives every unresolved process, thread, descriptor and lease
        if isinstance(error,Exception) and not isinstance(error,LegacyValidationError):
            raise LegacyValidationError('LEGACY_NATIVE_OPERATION_FAILED',primary_failure=error) from None
        raise
    finally:
        if not retained:
            try:
                outcome=recover()
                if primary is not None and outcome['pending_threads']:expose(primary)
            except BaseException as cleanup_error:
                if isinstance(primary,(KeyboardInterrupt,SystemExit)):
                    expose(primary,cleanup_error)
                    # The original control exception is already propagating.
                    # Preserve its identity while attaching exact recovery.
                    pass
                else:
                    code=cleanup_error.code if isinstance(cleanup_error,LegacyValidationError) else 'LEGACY_CLEANUP_UNRESOLVED'
                    unresolved=LegacyValidationError(code,owned_process=owned,threads=tuple(threads),worker_lease=lease,
                         pipe_descriptors=descriptors(),primary_failure=primary)
                    expose(unresolved,cleanup_error)
                    raise unresolved from None

def verify(base,cache,source,*,aliases,permitted):
    need(type(cache) is bytes and len(cache)==10572 and digest(cache)==CACHE_SHA256,'LEGACY_CACHE_IDENTITY')
    need(type(source) is bytes and len(source)==6316 and digest(source)==SOURCE_SHA256,'LEGACY_SOURCE_IDENTITY')
    need(type(aliases) is list and aliases==ALIASES,'LEGACY_GENERATOR_ALIASES')
    need(callable(permitted) and permitted() is True,'LEGACY_CURRENT_DENIAL')
    positions=base.protected_positions(source)
    need(positions['userinfo']==[],'LEGACY_GENERATOR_CREDENTIAL')
    base.python_literal_constraints(source,positions,owned_test=False)
    proof(base)
    request=json.dumps({'schema':SCHEMA,'cache_base64':base64.b64encode(cache).decode('ascii'),'source_base64':base64.b64encode(source).decode('ascii')},separators=(',',':'),allow_nan=False).encode('ascii')
    response,native=_exchange(base,request)
    expected={'schema','ok','error_code','cache_sha256','source_sha256','cache_bytes','source_bytes','magic_hex','header_flags','marshal_all_body_consumed','matching_compile_levels','comparisons','private_marker_constants_validated','filename_excluded_from_equivalence','marshal_reference_encoding_excluded','source_or_cache_execution'}
    need(set(response)==expected and response['ok'] is True and response['error_code'] is None,'LEGACY_RESPONSE_SCHEMA')
    need(response['cache_sha256']==CACHE_SHA256 and response['source_sha256']==SOURCE_SHA256 and response['magic_hex']=='a70d0d0a','LEGACY_RESPONSE_IDENTITY')
    need(type(response['cache_bytes']) is int and response['cache_bytes']==10572 and type(response['source_bytes']) is int and response['source_bytes']==6316
         and type(response['header_flags']) is int and response['header_flags']==0,'LEGACY_RESPONSE_TYPES')
    need(response['marshal_all_body_consumed'] is True and response['filename_excluded_from_equivalence'] is True
         and response['marshal_reference_encoding_excluded'] is True and response['source_or_cache_execution'] is False,'LEGACY_RESPONSE_SEMANTICS')
    need(type(response['matching_compile_levels']) is list and len(response['matching_compile_levels'])==3
         and all(type(value) is int and value==level for level,value in enumerate(response['matching_compile_levels'])) and type(response['private_marker_constants_validated']) is int
         and response['private_marker_constants_validated']==2,'LEGACY_RESPONSE_STRUCTURE')
    comparisons=response['comparisons'];need(type(comparisons) is list and len(comparisons)==3,'LEGACY_RESPONSE_TYPES')
    for level,row in enumerate(comparisons):
        need(type(row) is dict and set(row)=={'optimization','code_pairs','constant_pairs'}
             and type(row['optimization']) is int and row['optimization']==level
             and type(row['code_pairs']) is int and 0<row['code_pairs']<=10000
             and type(row['constant_pairs']) is int and 0<row['constant_pairs']<=100000,'LEGACY_RESPONSE_TYPES')
    need(permitted() is True,'LEGACY_CURRENT_DENIAL')
    proof(base)
    return {'validation':'EXACT_LEGACY_STRUCTURAL_EQUIVALENCE','reader_sha256':READER_SHA256,'review_sha256':REVIEW_SHA256,
            'matching_compile_levels':[0,1,2],'comparison_counts':comparisons,'private_marker_constants_validated':2,'marshal_all_body_consumed':True,
            'original_producer_custody':'UNPROVED','original_optimization':'UNPROVED','source_or_cache_execution':False,'native':native}
