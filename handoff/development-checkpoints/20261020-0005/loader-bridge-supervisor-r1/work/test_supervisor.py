"""Controlled data/resource ports only. No actual child or native operation."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import ast
import hashlib
import importlib.util
import io
import struct
import sys
import threading
import unittest

import supervisor as s
import owned_interpreter as identity
from child_entry import CappedBinary,CappedText,OutputBoundError

CUSTODY=Path('T:/00-Active/Project-AI-CETA/.agents/runtime/operational-resume-20261020/runner-repair-r1/work/tools/bounded_custody.py')
assert hashlib.sha256(CUSTODY.read_bytes()).hexdigest()=='715b88ab286a524f5815ec3c47b987ba82cc50709272fdc467b7ddc76eeba1b4'
spec=importlib.util.spec_from_file_location('controlled_existing_bounded_custody',CUSTODY)
custody=importlib.util.module_from_spec(spec);spec.loader.exec_module(custody)


def ref(name,pin='a'*64):return dict(repository_relative_path='CONTROLLED-DATA/'+name,sha256=pin)


class Owner:
    def __init__(self,*,timeout=False,code=0,close_error=None):
        self.pid=7;self.creation_time=11;self.image_sha256='b'*64
        self.lifetime_closed=False;self._cleanup_handles=[];self._process=1;self._thread=None;self._job=2
        self.timeout=timeout;self.code=code;self.waited=False;self.close_error=close_error;self.calls=[]
    def wait(self,timeout):
        self.calls.append(('wait',timeout))
        if self.timeout and not self.waited:self.waited=True;return False
        self.waited=True;return True
    def poll(self):return None if self.timeout and not any(x[0]=='terminate' for x in self.calls) else self.code
    def active_process_count(self):return 0
    def terminate(self,code):self.calls.append(('terminate',code));self.code=code
    def close(self):
        self.calls.append(('close',))
        if self.close_error:raise self.close_error
        self.lifetime_closed=True;self._process=self._thread=self._job=None


def child(code=0):return dict(receipt_valid=True,exit_status=code,profile_cleanup_proven=True,
                            bridge_capture_receipts_valid=True,interpreter_custody_proven=True,original_error=None)


class Custody(unittest.TestCase):
    def execute(self,owner,*,emit=lambda x:None,reader=lambda:child(),writer=lambda x:None):
        return s.execute_custody(custody,lambda:owner,emit,reader,writer,timeout=100)

    def test_actual_existing_primitive_success(self):
        owner=Owner();events=[]
        result=self.execute(owner,emit=lambda x:events.append('emit'),reader=lambda:(events.append('read') or child()))
        self.assertTrue(owner.lifetime_closed);self.assertEqual(events,['emit','read'])
        self.assertTrue(result['supervisor_custody_proven']);self.assertTrue(result['child_receipt_valid'])
        self.assertFalse(result['profile_cleanup_by_supervisor']);self.assertEqual(owner.calls.count(('close',)),1)

    def test_timeout_retires_only_returned_owner_once(self):
        owner=Owner(timeout=True)
        with self.assertRaisesRegex(TimeoutError,'BOUND_EXPIRED') as caught:self.execute(owner)
        self.assertEqual(owner.calls.count(('terminate',126)),1);self.assertEqual(owner.calls.count(('close',)),1)
        result=caught.exception.outer_terminal
        self.assertTrue(result['supervisor_custody_proven']);self.assertTrue(result['profile_state_requires_operator_inspection'])
        self.assertFalse(result['child_receipt_valid']);self.assertFalse(result['automatic_retry'])

    def test_emit_failure_still_retires(self):
        owner=Owner();original=OSError('CONTROLLED owner evidence failure')
        def emit(_):raise original
        with self.assertRaises(OSError) as caught:self.execute(owner,emit=emit)
        self.assertIs(caught.exception,original);self.assertTrue(owner.lifetime_closed)

    def test_evidence_failure_does_not_replace_original_error(self):
        owner=Owner();original=ValueError('CONTROLLED primary');secondary=OSError('CONTROLLED evidence')
        def emit(_):raise original
        def writer(_):raise secondary
        with self.assertRaises(ValueError) as caught:self.execute(owner,emit=emit,writer=writer)
        self.assertIs(caught.exception,original);self.assertIs(original.outer_terminal_evidence_error,secondary)
        self.assertTrue(owner.lifetime_closed)

    def test_success_then_terminal_evidence_failure_keeps_outcome(self):
        owner=Owner();secondary=OSError('CONTROLLED terminal evidence')
        def writer(_):raise secondary
        with self.assertRaises(OSError) as caught:self.execute(owner,writer=writer)
        self.assertIs(caught.exception,secondary);self.assertTrue(secondary.outer_terminal['supervisor_custody_proven'])

    def test_constructor_custody_never_adopted_or_retried(self):
        partial=Owner();original=RuntimeError('CONTROLLED constructor uncertain');original.owned_process=partial
        def launch():raise original
        with self.assertRaises(RuntimeError) as caught:
            s.execute_custody(custody,launch,lambda x:None,lambda:child(),lambda x:None,timeout=100)
        self.assertIs(caught.exception,original);self.assertEqual(partial.calls,[])
        report=original.outer_terminal['custody'];self.assertTrue(report['construction_custody']['retained_exact_owner'])

    def test_uncertain_close_has_no_retry(self):
        failure=OSError('CONTROLLED close uncertain');owner=Owner(close_error=failure)
        with self.assertRaises(OSError) as caught:self.execute(owner)
        self.assertIs(caught.exception,failure);self.assertEqual(owner.calls.count(('close',)),1)
        self.assertFalse(failure.outer_terminal['supervisor_custody_proven'])

    def test_child_read_failure_separate_from_job_retirement(self):
        owner=Owner();failure=ValueError('CONTROLLED child record invalid')
        def reader():raise failure
        with self.assertRaises(ValueError) as caught:self.execute(owner,reader=reader)
        self.assertIs(caught.exception,failure)
        self.assertTrue(failure.outer_terminal['supervisor_custody_proven'])
        self.assertFalse(failure.outer_terminal['child_receipt_valid'])

    def test_nonzero_child_never_relabelled_success(self):
        result=self.execute(Owner(code=23),reader=lambda:child(23))
        self.assertEqual(result['custody']['child_exit'],23);self.assertTrue(result['child_receipt_valid'])
        self.assertTrue(result['profile_state_requires_operator_inspection'])

    def test_child_declared_exit_conflict_refuses(self):
        result=self.execute(Owner(code=23),reader=lambda:child(0))
        self.assertFalse(result['child_exit_consistent']);self.assertFalse(result['child_receipt_valid'])

    def test_success_predicate_clean(self):self.assertTrue(s.succeeded(self.execute(Owner())))

    def test_success_predicate_mismatched_exit(self):
        self.assertFalse(s.succeeded(self.execute(Owner(code=23),reader=lambda:child(0))))

    def test_status_zero_cleanup_false_cannot_succeed(self):
        value=child();value['profile_cleanup_proven']=False
        result=self.execute(Owner(),reader=lambda:value)
        self.assertTrue(result['profile_state_requires_operator_inspection']);self.assertFalse(s.succeeded(result))

    def test_status_zero_missing_capture_receipts_cannot_succeed(self):
        value=child();value['bridge_capture_receipts_valid']=False
        self.assertFalse(s.succeeded(self.execute(Owner(),reader=lambda:value)))

    def test_status_zero_missing_interpreter_custody_cannot_succeed(self):
        value=child();value['interpreter_custody_proven']=False
        self.assertFalse(s.succeeded(self.execute(Owner(),reader=lambda:value)))

    def test_child_original_error_cannot_succeed(self):
        value=child();value['original_error']={'type':'CONTROLLED error'}
        self.assertFalse(s.succeeded(self.execute(Owner(),reader=lambda:value)))

    def test_missing_or_malformed_result_never_succeeds(self):
        for value in (None,{},dict(custody=None),dict(custody=dict(child_result=None))):
            self.assertFalse(s.succeeded(value))

    def test_boolean_exit_not_treated_as_zero(self):
        result=self.execute(Owner(),reader=lambda:child(False))
        self.assertFalse(s.succeeded(result))

    def test_closed_owner_handles_never_polled_again(self):
        owner=Owner();owner.lifetime_closed=True;owner._process=owner._thread=owner._job=None
        owner.poll=lambda:(_ for _ in ()).throw(AssertionError('must not poll closed owner'))
        custody.retire(owner);self.assertEqual(owner.calls,[])


def domain():
    nonce='a'*32;now=1000_000_000_000
    bridge=dict(nonce=nonce,bridge_freeze=ref('bridge'),lease=dict(typed='CONTROLLED'),
        expires_at_ns=now+600_000_000_000,filesystem_scopes=['00-Active/Project-AI-CETA/CONTROLLED-BRIDGE/**'],
        action_review=ref('bridge-action'))
    plan=SimpleNamespace(request=bridge,inputs=dict(trusted_owner_ingress_reference=ref('trusted-root')))
    request=dict(schema_version=1,kind=s.KIND,repository=str(s.F),executor='/root',nonce=nonce,
        issued_at_ns=now-1,expires_at_ns=now+500_000_000_000,bridge_request=ref('bridge-request'),
        bridge_freeze=bridge['bridge_freeze'],supervisor_freeze=ref('supervisor'),action_review=ref('action'),
        root_ingress=plan.inputs['trusted_owner_ingress_reference'],lease=bridge['lease'],
        filesystem_scopes=sorted(bridge['filesystem_scopes']+s.extra_scopes(nonce)),timeout_seconds=100,
        stdio_bound=1048576,child_result_bound=262144)
    inputs=dict(code_hashes={'supervisor.py':'a'*64,'child_entry.py':'b'*64})
    anchor=dict(outer_supervisor=dict(code_hashes=inputs['code_hashes'],nonce=nonce,effects=s.EFFECTS[:],
        filesystem_scopes=request['filesystem_scopes'],maximum_timeout_seconds=100))
    action=dict(decision='approve',exit_status=0,executor_id='/root',result={
        **{k:request[k] for k in ('supervisor_freeze','bridge_freeze','root_ingress','bridge_request')},
        'bridge_action_review':bridge['action_review'],'effects':s.EFFECTS[:],
        'filesystem_scopes':request['filesystem_scopes'],'scope':'ONE_ORDINARY_SUPERVISOR_AND_ONE_CANONICAL_BRIDGE_ATTEMPT'})
    return request,plan,action,anchor,inputs,now


class Admission(unittest.TestCase):
    def test_controlled_complete_domain(self):self.assertIn('directory',s.validate_domain(*domain()))

    def test_missing_outer_effects_cannot_reuse_bridge_grant(self):
        rows=list(domain());rows[3]={}
        with self.assertRaisesRegex(s.SupervisorError,'EXPLICIT_ROOT_INGRESS_EFFECTS'):s.validate_domain(*rows)

    def test_supplied_other_root_anchor_refused(self):
        rows=list(domain());rows[0]['root_ingress']=ref('untrusted')
        with self.assertRaisesRegex(s.SupervisorError,'SAME_TRUSTED_ROOT'):s.validate_domain(*rows)

    def test_distinct_review_and_exact_request(self):
        for key,value in [('executor_id','/root/review'),('decision','approved')]:
            rows=list(domain());rows[2][key]=value
            with self.assertRaises(s.SupervisorError):s.validate_domain(*rows)
        rows=list(domain());rows[2]['result']['bridge_request']=ref('other')
        with self.assertRaisesRegex(s.SupervisorError,'ACTION_BINDING'):s.validate_domain(*rows)

    def test_missing_extra_scope_refused(self):
        rows=list(domain());rows[0]['filesystem_scopes']=rows[1].request['filesystem_scopes']
        with self.assertRaisesRegex(s.SupervisorError,'EXACT_FS_SCOPES'):s.validate_domain(*rows)

    def test_bad_nonce_and_expiry(self):
        rows=list(domain());rows[0]['nonce']='z'*32
        with self.assertRaisesRegex(s.SupervisorError,'NONCE'):s.validate_domain(*rows)
        rows=list(domain());rows[-1]=rows[0]['expires_at_ns']
        with self.assertRaisesRegex(s.SupervisorError,'EXPIRY'):s.validate_domain(*rows)

    def test_bounded_timeout_and_output(self):
        for key,value in [('timeout_seconds',101),('timeout_seconds',True),('stdio_bound',1048577),('child_result_bound',True)]:
            rows=list(domain());rows[0][key]=value
            with self.assertRaises(s.SupervisorError):s.validate_domain(*rows)

    def test_normal_argv_no_forgery(self):
        request,plan,*_=domain();paths=s.own_paths(request['nonce'])
        outer=dict(paths=paths,bridge_plan=SimpleNamespace(source_inputs=dict(python=dict(path='PINNED-CONTROLLED-PYTHON'))))
        argv=s.child_argv(outer,envelope_reference=ref('envelope'))
        self.assertIs(type(argv),tuple);self.assertEqual(argv[:5],('PINNED-CONTROLLED-PYTHON','-I','-B','-X','utf8'))
        for path in (s.W/'supervisor.py',s.W/'child_entry.py'):
            tree=ast.parse(path.read_text(encoding='utf8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.Attribute) and isinstance(node.ctx,ast.Store):
                    self.assertNotIn(node.attr,('argv','orig_argv','__code__','__qualname__'))

    def test_null_ingress_precedes_native_child_launch(self):
        tree=ast.parse((s.W/'supervisor.py').read_text(encoding='utf8'))
        f=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='admission')
        self.assertIn('b.preflight(request[\'bridge_request\'])',ast.unparse(f))
        self.assertNotIn('launch', [n.attr for n in ast.walk(f) if isinstance(n,ast.Attribute)])

    def test_actual_admission_propagates_bridge_ingress_refusal_before_further_effects(self):
        request=domain()[0];base=dict(kind='CONTROLLED_FREEZE',python_hashes={'capture_bridge.py':s.digest(b'CONTROLLED')})
        inputs=dict(bridge_review=ref('review'),bridge_base_freeze=ref('base'),bridge_acceptance_records=[],
                    bridge_terminal_verification=ref('terminal'))
        review=dict(decision='approved',exit_status=0,executor_id='/root/admission',
                    result=dict(source_freeze=ref('base'),exact_python_hashes=base['python_hashes']))
        terminal=dict(response=dict(receipts_valid=True,terminal_success=True,
            states={name:'SUCCEEDED' for name in ('discover','plan','implement','review','validate','integrate')}))
        records={'bridge-request':{},'outer':request,'review':review,'base':base,'bridge':base,'terminal':terminal}
        original=s.SupervisorError('CONTROLLED_MISSING_ORIGINAL_ROOT_INGRESS_NO_EFFECTS')
        bridge=SimpleNamespace(preflight=lambda _:(_ for _ in ()).throw(original))
        def reread(value):return records[value['repository_relative_path'].split('/')[-1]]
        with patch.object(s,'read_ref',side_effect=reread),patch.object(s,'read',return_value=b'CONTROLLED'),\
             patch.object(s,'strict',return_value=inputs),patch.object(s,'verify_supervisor_freeze'),\
             patch.object(s,'load_exact',return_value=bridge),\
             patch.object(s,'verify_base_python',side_effect=AssertionError('must not proceed after ingress refusal')):
            with self.assertRaises(s.SupervisorError) as caught:s.admission(ref('outer'))
        self.assertIs(caught.exception,original)

    def test_owner_ready_published_only_after_complete_write(self):
        events=[];paths=s.own_paths('a'*32)
        def write(path,value):events.append(('complete-write',path,value))
        def link(source,target):
            self.assertEqual(events[0][0],'complete-write');events.append(('link-ready',source,target))
        s.publish_owner(paths,{'pid':7},write=write,link=link)
        self.assertEqual([x[0] for x in events],['complete-write','link-ready'])
        self.assertEqual(events[1][2],paths['owner_ready'])

    def test_owner_ready_collision_is_not_overwritten_or_retried(self):
        events=[]
        def link(*args):events.append('link');raise FileExistsError('CONTROLLED existing ready')
        with self.assertRaises(FileExistsError):
            s.publish_owner(s.own_paths('a'*32),{'pid':7},write=lambda *a:events.append('write'),link=link)
        self.assertEqual(events,['write','link'])


class BoundedOutput(unittest.TestCase):
    def test_exact_binary_bound(self):
        target=io.BytesIO();writer=CappedBinary(target,3);self.assertEqual(writer.write(b'abc'),3)
        with self.assertRaises(OutputBoundError):writer.write(b'd')
        self.assertEqual(target.getvalue(),b'abc');self.assertTrue(writer.exceeded)

    def test_partial_write_capped_before_error(self):
        target=io.BytesIO();writer=CappedBinary(target,3)
        with self.assertRaises(OutputBoundError):writer.write(b'abcdef')
        self.assertEqual(target.getvalue(),b'abc');self.assertEqual(writer.count,3)

    def test_utf8_is_bounded_in_bytes(self):
        target=io.BytesIO();binary=CappedBinary(target,4);text=CappedText(binary)
        self.assertEqual(text.write('\u00e9\u00e9'),2)
        with self.assertRaises(OutputBoundError):text.write('x')
        self.assertEqual(len(target.getvalue()),4)

    def test_binary_type_and_short_write_refused(self):
        writer=CappedBinary(io.BytesIO(),3)
        with self.assertRaises(TypeError):writer.write('x')
        writer=CappedBinary(SimpleNamespace(write=lambda raw:0),3)
        with self.assertRaisesRegex(OSError,'SHORT_OUTPUT'):writer.write(b'a')

    def test_short_write_is_sticky_and_never_retried(self):
        calls=[];data=bytearray()
        def short(raw):calls.append(raw);data.extend(raw[:1]);return 1
        writer=CappedBinary(SimpleNamespace(write=short),3)
        with self.assertRaisesRegex(OSError,'SHORT_OUTPUT'):writer.write(b'abc')
        with self.assertRaisesRegex(OutputBoundError,'NO_RETRY'):writer.write(b'abc')
        self.assertTrue(writer.uncertain);self.assertEqual(len(calls),1);self.assertEqual(len(data),1)
        self.assertEqual(writer.reserved,3)

    def test_raise_after_partial_write_is_sticky(self):
        calls=[];data=bytearray();original=OSError('CONTROLLED partial write unknown')
        def partial(raw):calls.append(raw);data.extend(raw[:1]);raise original
        writer=CappedBinary(SimpleNamespace(write=partial),3)
        with self.assertRaises(OSError) as caught:writer.write(b'abc')
        self.assertIs(caught.exception,original)
        with self.assertRaises(OutputBoundError):writer.write(b'abc')
        with self.assertRaises(OutputBoundError):writer.flush()
        self.assertTrue(writer.uncertain);self.assertEqual(len(calls),1);self.assertEqual(len(data),1)

    def test_two_joined_writers_cannot_exceed_three_bytes(self):
        target=io.BytesIO();writer=CappedBinary(target,3);barrier=threading.Barrier(3);errors=[]
        def write(raw):
            barrier.wait(timeout=3)
            try:writer.write(raw)
            except BaseException as error:errors.append(error)
        threads=[threading.Thread(target=write,args=(raw,)) for raw in (b'abc',b'xyz')]
        for thread in threads:thread.start()
        barrier.wait(timeout=3)
        for thread in threads:thread.join(timeout=3);self.assertFalse(thread.is_alive())
        self.assertEqual(len(target.getvalue()),3);self.assertEqual(writer.count,3)
        self.assertEqual(writer.reserved,3);self.assertEqual(len(errors),1)
        self.assertIsInstance(errors[0],OutputBoundError)


REDIRECTOR=dict(path='T:/CONTROLLED/e3/python.exe',sha256='a'*64,bytes=100)
BASE=dict(path='C:/CONTROLLED/base/python.exe',sha256='b'*64,bytes=200)
LAUNCH=(REDIRECTOR['path'],'-I','-B','-X','utf8','CONTROLLED-child.py')


def hello(pid=12):
    return dict(pid=pid,argv=[BASE['path'],*LAUNCH[1:]],sys_executable=REDIRECTOR['path'],
                base_executable=BASE['path'])


class IdentityPort:
    """Explicit synthetic handles; never implements any native lookup."""
    def __init__(self,ids=(11,12)):
        self.ids=ids;self.rows=[];self.calls=[];self.root_creation=100;self.member_answers={}
        self.observations={pid:dict(pid=pid,creation_time=100+pid,
            image_path=(REDIRECTOR if pid==11 else BASE)['path'],
            image_sha256=(REDIRECTOR if pid==11 else BASE)['sha256']) for pid in ids}
        self.exits={pid:dict(pid=pid,creation_time=100+pid,exit_status=0) for pid in ids}
        self.observe_errors={};self.close_errors={};self.open_error=None;self.alive_value=True
    def members(self):self.calls.append(('members',));return self.ids
    def open_member(self,pid):
        self.calls.append(('open',pid));row=dict(pid=pid,handle=pid,state='OWNED');self.rows.append(row)
        if self.open_error:
            row['state']='OPEN_UNCERTAIN';raise self.open_error
        return row
    def member(self,row):
        pid=row['pid'];self.calls.append(('member',pid));answers=self.member_answers.get(pid,[True])
        return answers.pop(0) if len(answers)>1 else answers[0]
    def observe(self,row):
        pid=row['pid'];self.calls.append(('observe',pid))
        if pid in self.observe_errors:raise self.observe_errors[pid]
        return deepcopy(self.observations[pid])
    def alive(self,row):self.calls.append(('alive',row['pid']));return self.alive_value
    def exited(self,row):self.calls.append(('exit',row['pid']));return deepcopy(self.exits[row['pid']])
    def close_once(self,row):
        if row['state']!='OWNED':raise AssertionError('CONTROLLED unknown handle was retried')
        self.calls.append(('close',row['pid']));row['state']='CLOSE_IN_FLIGHT'
        if row['pid'] in self.close_errors:
            row['state']='CLOSE_UNCERTAIN';raise self.close_errors[row['pid']]
        row['state']='CLOSED';row['handle']=None


class OwnedInterpreter(unittest.TestCase):
    def qualify(self,port=None,value=None):
        port=port or IdentityPort();selection=identity.Selection(port)
        result=selection.qualify(value or hello(),LAUNCH,REDIRECTOR,BASE)
        return port,selection,result

    def test_complete_unique_member_retained_and_physical_exit_closed_once(self):
        port,selection,result=self.qualify()
        self.assertEqual(result['pid'],12);self.assertEqual(result['rights'],0x101000)
        self.assertEqual(result['reported_argv'][0],BASE['path']);self.assertEqual(result['launch_argv'][0],REDIRECTOR['path'])
        self.assertEqual(port.rows[0]['state'],'CLOSED');self.assertEqual(port.rows[1]['state'],'OWNED')
        receipt=selection.retire_once();self.assertTrue(receipt['physical_interpreter_exit'])
        self.assertEqual(receipt['retirement']['creation_time'],112)
        self.assertEqual(port.calls.count(('close',12)),1);self.assertEqual(port.calls.count(('close',11)),1)
        with self.assertRaisesRegex(identity.IdentityError,'NO_RETRY'):selection.retire_once()

    def test_list_header_ids_and_native_pointer_sized_layout(self):
        raw=struct.pack('<IIQQ',2,2,11,12)
        self.assertEqual(identity.parse_members(raw,len(raw)),(11,12))
        self.assertEqual(identity.parse_members(raw+b'\0'*16,len(raw)),(11,12))

    def test_short_truncated_duplicate_overflow_lists_refused(self):
        rows=[(b'x',1),(struct.pack('<IIQ',2,1,11),16),(struct.pack('<IIQQ',2,2,11,11),24),
              (struct.pack('<IIQ',1,1,0),16),(struct.pack('<IIQ',1,1,0x100000000),16),
              (struct.pack('<II',65,65)+b'\0'*520,528),(struct.pack('<IIQ',1,1,11),15)]
        for raw,returned in rows:
            with self.subTest(returned=returned,bytes=len(raw)):
                with self.assertRaises(identity.IdentityError):identity.parse_members(raw,returned)

    def test_unlisted_pid_refused_without_open(self):
        port=IdentityPort();selection=identity.Selection(port)
        with self.assertRaisesRegex(identity.IdentityError,'NOT_ENUMERATED'):
            selection.qualify(hello(99),LAUNCH,REDIRECTOR,BASE)
        self.assertEqual(port.rows,[])

    def test_membership_precedes_all_metadata_and_false_closes_handle(self):
        port=IdentityPort();port.member_answers[11]=[False];selection=identity.Selection(port)
        with self.assertRaisesRegex(identity.IdentityError,'NONMEMBER'):
            selection.qualify(hello(),LAUNCH,REDIRECTOR,BASE)
        self.assertNotIn(('observe',11),port.calls);self.assertEqual(port.rows[0]['state'],'CLOSED')
        self.assertFalse(selection.retire_once()['physical_interpreter_exit'])

    def test_membership_loss_after_observation_refused(self):
        port=IdentityPort();port.member_answers[12]=[True,False];selection=identity.Selection(port)
        with self.assertRaisesRegex(identity.IdentityError,'LEFT_HELD_JOB'):
            selection.qualify(hello(),LAUNCH,REDIRECTOR,BASE)
        self.assertEqual(port.rows[1]['state'],'CLOSED')

    def test_pid_reuse_creation_hash_path_and_boolean_observation_refused(self):
        for key,value in [('pid',99),('creation_time',99),('creation_time',True),
                          ('image_sha256','c'*64),('image_path','C:/CONTROLLED/unexpected.exe')]:
            port=IdentityPort();port.observations[12][key]=value;selection=identity.Selection(port)
            with self.subTest(key=key):
                with self.assertRaises(identity.IdentityError):selection.qualify(hello(),LAUNCH,REDIRECTOR,BASE)
                self.assertTrue(selection.retire_once()['all_query_handles_closed'])

    def test_original_redirector_hash_verified_separately(self):
        port=IdentityPort();port.observations[11]['image_sha256']='c'*64
        with self.assertRaisesRegex(identity.IdentityError,'REDIRECTOR_IMAGE_BYTES'):
            self.qualify(port)

    def test_reported_argv_executable_or_base_cannot_be_substituted(self):
        for key,value in [('pid',True),('argv',list(LAUNCH)),('sys_executable',BASE['path']),
                          ('base_executable',REDIRECTOR['path'])]:
            item=hello();item[key]=value;port=IdentityPort();selection=identity.Selection(port)
            with self.subTest(key=key):
                with self.assertRaises(identity.IdentityError):selection.qualify(item,LAUNCH,REDIRECTOR,BASE)
                self.assertEqual(port.calls,[])

    def test_ambiguous_base_interpreters_closed_without_release(self):
        port=IdentityPort((11,12,13));selection=identity.Selection(port)
        with self.assertRaisesRegex(identity.IdentityError,'AMBIGUOUS'):
            selection.qualify(hello(),LAUNCH,REDIRECTOR,BASE)
        self.assertTrue(all(row['state']=='CLOSED' for row in port.rows));self.assertIsNone(selection.selected)

    def test_selection_failure_is_not_retried(self):
        port=IdentityPort();selection=identity.Selection(port)
        with self.assertRaises(identity.IdentityError):selection.qualify(hello(99),LAUNCH,REDIRECTOR,BASE)
        with self.assertRaisesRegex(identity.IdentityError,'ONE_SELECTION'):
            selection.qualify(hello(),LAUNCH,REDIRECTOR,BASE)
        self.assertEqual(port.calls,[('members',)])

    def test_metadata_short_read_preserves_error_and_closes(self):
        port=IdentityPort();original=OSError('CONTROLLED short image/time read');port.observe_errors[12]=original
        selection=identity.Selection(port)
        with self.assertRaises(OSError) as caught:selection.qualify(hello(),LAUNCH,REDIRECTOR,BASE)
        self.assertIs(caught.exception,original);self.assertTrue(selection.retire_once()['all_query_handles_closed'])

    def test_metadata_error_not_replaced_by_uncertain_close(self):
        port=IdentityPort();original=OSError('CONTROLLED image query failed');cleanup=OSError('CONTROLLED close unknown')
        port.observe_errors[12]=original;port.close_errors[12]=cleanup;selection=identity.Selection(port)
        with self.assertRaises(OSError) as caught:selection.qualify(hello(),LAUNCH,REDIRECTOR,BASE)
        self.assertIs(caught.exception,original);self.assertIs(original.owned_interpreter_cleanup_error,cleanup)
        with self.assertRaisesRegex(identity.IdentityError,'CUSTODY_UNCERTAIN'):selection.retire_once()
        self.assertEqual(port.calls.count(('close',12)),1);self.assertEqual(selection.snapshot()['query_custody'][1]['state'],'CLOSE_UNCERTAIN')

    def test_unknown_open_preserved_never_adopted_or_retried(self):
        port=IdentityPort();original=OSError('CONTROLLED open interrupted');port.open_error=original
        selection=identity.Selection(port)
        with self.assertRaises(OSError) as caught:selection.qualify(hello(),LAUNCH,REDIRECTOR,BASE)
        self.assertIs(caught.exception,original)
        with self.assertRaisesRegex(identity.IdentityError,'CUSTODY_UNCERTAIN'):selection.retire_once()
        self.assertFalse(any(call[0]=='close' for call in port.calls))

    def test_failed_selection_closes_previously_retained_match_without_profile_release(self):
        port=IdentityPort((11,12,13));original=OSError('CONTROLLED later member observation failed')
        port.observe_errors[13]=original;selection=identity.Selection(port)
        with self.assertRaises(OSError) as caught:selection.qualify(hello(),LAUNCH,REDIRECTOR,BASE)
        self.assertIs(caught.exception,original);self.assertIsNone(selection.selected)
        self.assertEqual(port.rows[1]['state'],'OWNED')
        result=selection.retire_once();self.assertTrue(result['all_query_handles_closed'])
        self.assertFalse(result['physical_interpreter_exit']);self.assertEqual(port.calls.count(('close',12)),1)

    def test_exit_failure_preserved_with_separate_query_close_uncertainty(self):
        port,selection,_=self.qualify();original=TimeoutError('CONTROLLED exit observation unknown')
        cleanup=OSError('CONTROLLED retained query close unknown');port.close_errors[12]=cleanup
        def pending(row):raise original
        port.exited=pending
        with self.assertRaises(TimeoutError) as caught:selection.retire_once()
        self.assertIs(caught.exception,original);self.assertEqual(original.owned_interpreter_cleanup_errors,(cleanup,))
        self.assertEqual(selection.snapshot()['query_custody'][1]['state'],'CLOSE_UNCERTAIN')
        self.assertEqual(port.calls.count(('close',12)),1)

    def test_retained_handle_exit_pid_or_creation_change_cannot_pass(self):
        for key,value in [('pid',99),('creation_time',999)]:
            port,selection,_=self.qualify();port.exits[12][key]=value
            with self.subTest(key=key):
                with self.assertRaisesRegex(identity.IdentityError,'EXIT_IDENTITY_CHANGED'):selection.retire_once()
                self.assertTrue(all(row['state']=='CLOSED' for row in port.rows))

    def test_physical_exit_pending_preserves_failure_and_closes_known_handle(self):
        port,selection,_=self.qualify();original=TimeoutError('CONTROLLED physical exit still pending')
        def pending(row):raise original
        port.exited=pending
        with self.assertRaises(TimeoutError) as caught:selection.retire_once()
        self.assertIs(caught.exception,original);self.assertIs(original.owned_interpreter_custody,selection)
        self.assertTrue(all(row['state']=='CLOSED' for row in port.rows))

    def test_already_exited_candidate_refused(self):
        port=IdentityPort();port.alive_value=False
        with self.assertRaisesRegex(identity.IdentityError,'ALREADY_EXITED'):self.qualify(port)

    def test_native_adapter_ast_uses_only_explicit_job_and_enumerated_query_rights(self):
        tree=ast.parse((s.W/'owned_interpreter.py').read_text(encoding='utf8'))
        klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='NativePort')
        calls=[n for n in ast.walk(klass) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
        opens=[n for n in calls if n.func.attr=='OpenProcess'];self.assertEqual(len(opens),1)
        self.assertEqual(ast.unparse(opens[0].args[0]),'QUERY_SYNCHRONIZE')
        self.assertEqual(ast.literal_eval(opens[0].args[1]),False)
        membership=[n for n in calls if n.func.attr=='IsProcessInJob'];self.assertEqual(len(membership),1)
        self.assertEqual(ast.unparse(membership[0].args[1]),'self.job')
        forbidden={'TerminateProcess','WriteProcessMemory','ReadProcessMemory','DebugActiveProcess','CreateProcessW'}
        self.assertFalse(forbidden.intersection(n.func.attr for n in calls))

    def data_native_port(self,*,short=False,hash_error=None,close_error=None,creation_changes=False):
        # Execute the adapter's source against explicit Python data functions.
        # NativePort.__init__, DLLs and native function pointers are never used.
        port=identity.NativePort.__new__(identity.NativePort);port.rows=[];port.expected_pins=[BASE]
        times=iter([112,999] if creation_changes else [112,112]);port.creation=lambda row:next(times)
        def image_query(handle,flags,name,length):
            name.value=BASE['path'];length._obj.value=len(name.value)-(1 if short else 0);return True
        def close(handle):
            if close_error:raise close_error
            return True
        physical=(7,8,9,0,BASE['bytes'],10,11)
        def hashed(api,handle):
            if hash_error:raise hash_error
            return BASE['sha256'],physical
        port.api=SimpleNamespace(GetProcessId=lambda handle:12,QueryFullProcessImageNameW=image_query,CloseHandle=close)
        port.jobs=SimpleNamespace(_open_image=lambda api,path:55,_file_identity=lambda api,handle:physical,_hash_image=hashed)
        return port,dict(pid=12,handle=12,state='OWNED')

    def test_native_observation_source_with_data_only_ports_pins_physical_image(self):
        port,row=self.data_native_port();observed=port.observe(row)
        self.assertEqual(observed['image_sha256'],BASE['sha256']);self.assertEqual(observed['pid'],12)
        self.assertEqual(port.rows[0]['state'],'CLOSED')

    def test_native_observation_source_short_image_read_refuses_before_image_open(self):
        port,row=self.data_native_port(short=True)
        with self.assertRaisesRegex(identity.IdentityError,'IMAGE_QUERY_SHORT'):port.observe(row)
        self.assertEqual(port.rows,[])

    def test_native_observation_hash_error_not_replaced_by_image_close_error(self):
        original=OSError('CONTROLLED native-port hash read short');cleanup=OSError('CONTROLLED image close unknown')
        port,row=self.data_native_port(hash_error=original,close_error=cleanup)
        with self.assertRaises(OSError) as caught:port.observe(row)
        self.assertIs(caught.exception,original);self.assertIs(original.owned_interpreter_image_cleanup_error,cleanup)
        self.assertEqual(port.rows[0]['state'],'CLOSE_UNCERTAIN')

    def test_native_observation_source_creation_change_refused(self):
        port,row=self.data_native_port(creation_changes=True)
        with self.assertRaisesRegex(identity.IdentityError,'CREATION_CHANGED_DURING_QUERY'):port.observe(row)
        self.assertEqual(port.rows[0]['state'],'CLOSED')

    def test_base_dependency_wrong_path_refuses_before_host_read(self):
        with self.assertRaisesRegex(s.SupervisorError,'EXACT_BASE_PYTHON_PATH'):
            s.verify_base_python(dict(path='C:/CONTROLLED/other.exe',bytes=100,sha256='a'*64))


if __name__=='__main__':unittest.main()
