"""Actual native enrollment ownership; no Windows Hello is requested here."""
from dataclasses import replace
import hashlib
from pathlib import Path
import threading
import time
import unittest
from unittest.mock import patch
import uuid

from ceta.contracts.owner_enrollment import enrollment_transcript_bytes
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.contracts.temporal import Deadline
from ceta.contracts.wire import ContractError, strict_loads
from ceta.identity import owner_session as module
from ceta.identity.native_clock import NativeSessionClock
from ceta.identity.native_code_binding import CodePin, NativeCodeBinding
from ceta.identity.native_owner_view import NativeOwnerView, NativeStoreBinding
from ceta.kernel.owner_authority import enrollment_key
from ceta.kernel.transactions import KernelTransactions
from ceta.store.journal import SqliteJournal
import test_owner_enrollment as data
import test_windows_pipe as pipe_tests
from test_kernel_transactions import INSTALLATION, PROJECT, POLICY, SCOPES

ROOT = Path(__file__).resolve().parents[2]
HELPER = HELPER_SHA = HELPER_SOURCE = HELPER_SOURCE_SHA = WORKER = WORKER_SHA = FIXTURES = None
NATIVE_RECEIPTS = []


class NativeOwnerSessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pipe_tests.WindowsPipeTests.setUpClass()

    def setUp(self):
        self.fixture = pipe_tests.WindowsPipeTests('test_registered_os_peer_reaches_handler_and_context_expires_after_dispatch')
        self.fixture.setUp()
        self.directory = Path(FIXTURES) / uuid.uuid4().hex
        self.directory.mkdir()
        self.store = self.clock = self.binding = self.code = self.owner = None
        self.sessions = []
        self.measured_pairs = []
        self.addCleanup(self.retire)
        self.store = SqliteJournal(self.directory, self.fixture.codec, SCOPES, create=True, profile=STORE_PROFILE)
        self.binding = NativeStoreBinding(self.directory)
        self.clock = NativeSessionClock(7)
        self.view = NativeOwnerView(self.fixture.registry, self.clock, self.binding)
        source = ROOT/'src/ceta/identity/owner_session.py'
        self.code = NativeCodeBinding((
            CodePin('source', 'identity/owner_session.py', str(source), hashlib.sha256(source.read_bytes()).hexdigest()),
            CodePin('source', 'native/owner_approval.cpp', str(HELPER_SOURCE), HELPER_SOURCE_SHA),
            CodePin('environment', 'native/owner_approval.exe', str(HELPER), HELPER_SHA),
            CodePin('environment', 'native/isolated_worker.exe', str(WORKER), WORKER_SHA)))
        self.owner = self.construct()
        self.kernel = KernelTransactions(self.store, self.fixture.codec, INSTALLATION, self.owner)

    def construct(self, **changes):
        arguments = dict(installation_id=INSTALLATION, scope_id=PROJECT, policy_commitment=POLICY,
            helper_name='native/owner_approval.exe', helper_source_name='native/owner_approval.cpp',
            worker_name='native/isolated_worker.exe', temporary_root=self.directory)
        arguments.update(changes)
        return module.NativeOwnerSession(self.view,self.clock,self.code,**arguments)

    def prepare(self, context):
        prepared = self.owner.approval_owner.prepare_enrollment(timeout_ms=5000)
        self.sessions.append(prepared)
        observed = self.view.observe(context)
        current = observed.current_clock
        deadline = Deadline(current.boot_id,current.durable_epoch,current.resume_generation,current.monotonic_ns,
            current.monotonic_ns+30_000_000_000,current.earliest_wall_ns,current.latest_wall_ns+30_000_000_000)
        binding = prepared.enrollment_binding
        request = data.request(installation_id=INSTALLATION,scope_id=PROJECT,
            principal_id=observed.peer.principal_id,actor_session=observed.peer.session_id,
            challenge_id=binding.challenge_id,ceremony_nonce=binding.ceremony_nonce,
            helper_identity=binding.helper.identity,ui_identity=binding.ui_identity,
            helper_commitment=binding.helper_commitment,ui_commitment=binding.ui_commitment,
            private_root=observed.private_root,database=observed.database,owner_facts=observed.owner_facts,
            clock_session_nonce=current.boot_id.rsplit(':',1)[1],deadline=deadline,
            policy_commitment=POLICY,source_commitment=self.code.source_commitment,
            environment_commitment=self.code.environment_commitment,worker_image_commitment='sha256:'+WORKER_SHA)
        self.measured_pairs.append({'helper':binding.helper.as_dict(),'owner':observed.owner_facts.as_dict()})
        return prepared,request

    def call(self, body):
        def handler(message, context):
            self.fixture.registry.require_message(context,message)
            with self.owner.native_context(context):
                return body(context)
        self.fixture.handler = handler
        success,result,answer = self.fixture.send(self.fixture.client(),self.fixture.message(),timeout=5.0)
        if not success: raise result
        self.assertEqual(answer,{'sent':True,'returned_none':True})
        return result

    def retire(self):
        failures=[]
        for session in self.sessions:
            try:
                if not session._closed:
                    session.cancel()
                    # A prepared helper has no request to parse/poll. Retire
                    # its actual owned process without creating an auth body.
                    session.process.wait(5)
                    deadline=time.perf_counter()+5
                    while session.process.active_process_count() and time.perf_counter()<deadline: time.sleep(.005)
                    session.close()
                self.assertTrue(session._closed and session.process.lifetime_closed)
                self.assertFalse(session.pending_native_cleanup)
            except BaseException as error:failures.append(error)
        for value in (self.owner,self.code,self.binding,self.clock,self.store):
            if value is not None:
                try:value.close()
                except BaseException as error:failures.append(error)
        try:self.fixture.tearDown()
        except BaseException as error:failures.append(error)
        row={'test_id':self.id(),'directory':str(self.directory),
            'sessions':[dict(pid=s.process.pid,creation_time=s.process.creation_time,
                closed=s._closed,lifetime_closed=s.process.lifetime_closed,
                native_facts=s.native_facts,gate_may_open=s._gate_may_open,
                authentication_invoked=None if s._result is None else s._result.authentication_invoked) for s in self.sessions],
            'owner_closed':self.owner is None or self.owner.closed,
            'code_closed':self.code is None or self.code.closed,
            'store_binding_closed':self.binding is None or self.binding.closed,
            'clock_closed':self.clock is None or self.clock.status().state=='CLOSED',
            'journal_closed':self.store is None or self.store._closed,
            'client_lifetimes':[dict(pid=c.process.pid,creation_time=c.selected_creation,exit_code=c.process.poll(),
                streams_closed=all(s is None or s.closed for s in (c.process.stdin,c.process.stdout,c.process.stderr)))
                for c in self.fixture.clients], 'cleanup_errors':[repr(e) for e in failures],
            'genuine_authentication_requested':False}
        row['actual_native_principal_pairs']=self.measured_pairs
        NATIVE_RECEIPTS.append(row)
        if failures:raise failures[0]

    def test_original_native_peer_designates_frozen_body_and_releases_dispatch(self):
        captured=[]
        def body(context):
            captured.append(context);prepared,request=self.prepare(context)
            frozen=self.owner.designate_enrollment(request,prepared,context)
            expected=self.owner.owner_enrollment_expected(context)
            self.assertEqual(expected,request);self.assertIsNot(expected,request)
            self.assertIsNot(frozen,request)
            self.assertEqual(expected.owner_facts.process_identity.pid,self.fixture.clients[-1].process.pid)
            self.assertFalse(prepared._gate_may_open)
            return frozen.input_commitment
        self.assertEqual(self.call(body),self.owner._expected.input_commitment)
        with self.assertRaisesRegex(ContractError,'ORIGINAL_DISPATCH_REQUIRED'):
            self.owner.owner_enrollment_expected(captured[0])

    def test_canonical_challenge_commits_on_actual_store_without_issuing_grant(self):
        def body(context):
            prepared,request=self.prepare(context);self.owner.designate_enrollment(request,prepared,context)
            result=self.kernel.begin_owner_enrollment(request.canonical_wire,context)
            self.assertEqual(self.fixture.codec.decode(result.record_wire).as_dict()['outcome'],'SEEK_AUTHORITY')
            value=self.store.snapshot((enrollment_key(INSTALLATION,request.request_id),))[0]
            row=strict_loads(value.value_wire)
            self.assertEqual(row['state'],'CHALLENGE');self.assertIsNone(row['grant_key'])
            self.assertFalse(prepared._gate_may_open)
            return self.store.position(INSTALLATION).next_sequence
        self.assertEqual(self.call(body),1)

    def test_hidden_native_display_is_not_a_verified_ceremony(self):
        def body(context):
            session,request=self.prepare(context);self.owner.designate_enrollment(request,session,context)
            result=session.inspect_enrollment(request).wait(10)
            self.assertEqual(result.status,'DISPLAY_BOUND_UNSHOWN')
            self.assertFalse(result.authentication_invoked or result.reported_verified)
            with self.assertRaisesRegex(ContractError,'GENUINE_CEREMONY_REQUIRED'):
                self.owner.retain_verified_enrollment(session,context)
            return result.display_exact
        self.assertTrue(self.call(body))

    def test_controlled_transcript_and_boolean_cannot_enroll_after_real_challenge(self):
        def body(context):
            session,request=self.prepare(context);self.owner.designate_enrollment(request,session,context)
            self.kernel.begin_owner_enrollment(request.canonical_wire,context)
            previous,current=self.clock.clock()
            proof=data.transcript(request,observed_clock=current)
            before=self.store.position(INSTALLATION)
            for supplied in (True,False,object(),proof,{'approved':True}):
                with self.subTest(proof_type=type(supplied).__name__),self.assertRaisesRegex(ContractError,'NATIVE_WITNESS_REQUIRED'):
                    self.kernel.enroll_owner(request.canonical_wire,enrollment_transcript_bytes(proof),supplied,context)
                self.assertEqual(self.store.position(INSTALLATION),before)
            self.assertFalse(session._gate_may_open)
        self.call(body)

    def test_retained_native_ceremony_anchor_survives_later_observations(self):
        from ceta.contracts.owner_enrollment import require_enrollment_transcript_binding
        def body(context):
            session,request=self.prepare(context);self.owner.designate_enrollment(request,session,context)
            anchor=self.owner._anchor
            _,reported=self.clock.clock()
            proof=data.transcript(request,observed_clock=reported)
            for _ in range(3):
                self.view.observe(context)
                previous,current=self.owner.clock()
                self.assertIs(previous,anchor)
                self.assertLessEqual(previous.monotonic_ns,reported.monotonic_ns)
                self.assertLessEqual(reported.monotonic_ns,current.monotonic_ns)
                # DATA_ONLY timing/codec assertion. No native witness is made.
                require_enrollment_transcript_binding(request,request,proof,previous,current)
            self.assertIsNone(self.owner._proof)
        self.call(body)

    def test_every_trusted_configuration_change_denies_designation(self):
        def body(context):
            session,request=self.prepare(context)
            for name in ('installation_id','scope_id','policy_commitment','source_commitment','environment_commitment','worker_image_commitment'):
                value='different:identity' if name.endswith('_id') else 'sha256:'+'f'*64
                with self.subTest(field=name),self.assertRaises(ContractError):
                    self.owner.designate_enrollment(replace(request,**{name:value}),session,context)
                self.assertIsNone(self.owner._expected)
            self.assertFalse(session._gate_may_open)
        self.call(body)

    def test_prepared_helper_nonce_ui_and_build_binding_changes_are_denied(self):
        def body(context):
            session,request=self.prepare(context)
            changes=({'challenge_id':'challenge:other'},{'ceremony_nonce':'f'*32},
                {'helper_identity':replace(request.helper_identity,pid=request.helper_identity.pid+1)},
                {'ui_identity':replace(request.ui_identity,pid=request.ui_identity.pid+1)},
                {'helper_commitment':'sha256:'+'f'*64},{'ui_commitment':'sha256:'+'f'*64})
            for changed in changes:
                with self.subTest(changed=tuple(changed)),self.assertRaisesRegex(ContractError,'PREPARATION_MISMATCH'):
                    self.owner.designate_enrollment(replace(request,**changed),session,context)
            self.assertFalse(session._gate_may_open)
        self.call(body)

    def test_root_database_or_native_owner_change_denies_before_designation(self):
        def body(context):
            session,request=self.prepare(context)
            for changed in ({'private_root':replace(request.private_root,file_id_hex='0'*32)},
                {'database':replace(request.database,file_id_hex='0'*32)},
                {'owner_facts':replace(request.owner_facts,modified_id_hex='f'*16)}):
                with self.subTest(changed=tuple(changed)),self.assertRaisesRegex(ContractError,'NATIVE_BINDING_CHANGED'):
                    self.owner.designate_enrollment(replace(request,**changed),session,context)
        self.call(body)

    def test_actual_filtered_flag_is_distinct_from_zero_restricted_sids(self):
        def body(context):
            session,request=self.prepare(context);helper=session.enrollment_binding.helper
            self.assertEqual(helper.restricted,bool(request.owner_facts.has_restrictions))
            self.assertEqual(helper.restricted_sid_count,len(request.owner_facts.restricted_sids))
            self.assertEqual(helper.restricted_sid_count,0)
            module._require_principal(helper,request.owner_facts)
            self.owner.designate_enrollment(request,session,context)
        self.call(body)

    def test_actual_native_lease_is_checked_before_intercepted_gate_without_prompt(self):
        def body(context):
            session,request=self.prepare(context);self.owner.designate_enrollment(request,session,context)
            primary=KeyboardInterrupt('CONTROLLED_GATE_REFUSED_BEFORE_NATIVE_SET')
            real=session._api.SetEvent;calls=[]
            def refuse_gate(handle):
                if handle==session._handles.get('gate'):
                    calls.append(handle)
                    self.assertIs(session._lease,self.owner._enrollment_lease)
                    self.assertIs(session._bound_context,context)
                    raise primary
                return real(handle)
            with patch.object(session._api,'SetEvent',refuse_gate):
                with self.assertRaises(KeyboardInterrupt) as caught:
                    session.begin_enrollment(request,original_context=context)
            self.assertIs(caught.exception,primary);self.assertEqual(len(calls),1)
            self.assertIs(primary.owned_session,session)
            self.assertTrue(session._closed);self.assertIsNone(self.owner._enrollment_lease)
            self.assertIsNone(self.owner._proof)
            self.assertFalse(session.native_facts.get('body_bound',False))
        self.call(body)

    def test_stop_during_actual_native_lease_check_cannot_open_the_gate(self):
        def body(context):
            session,request=self.prepare(context);self.owner.designate_enrollment(request,session,context)
            real_observe=self.owner._require_native;real_set=session._api.SetEvent;gate_calls=[]
            def stop_after_native(*args,**kwargs):
                observed=real_observe(*args,**kwargs);self.owner.request_stop();return observed
            def guard(handle):
                if handle==session._handles.get('gate'):
                    gate_calls.append(handle);raise AssertionError('AUTH_GATE_MUST_REMAIN_CLOSED')
                return real_set(handle)
            with patch.object(self.owner,'_require_native',stop_after_native),patch.object(session._api,'SetEvent',guard):
                with self.assertRaises(ContractError):session.begin_enrollment(request,original_context=context)
            self.assertEqual(gate_calls,[]);self.assertFalse(session._gate_may_open)
            self.assertIsNone(self.owner._proof)
        self.call(body)

    def test_owner_token_class_helper_logon_and_restriction_mismatches_are_rejected(self):
        def body(context):
            session,request=self.prepare(context);helper=session.enrollment_binding.helper;owner=request.owner_facts
            changed_helper=(replace(helper,user_sid='S-1-5-21-1-2-3-9999'),
                replace(helper,logon_sid='S-1-5-5-1-2'),replace(helper,terminal_session=helper.terminal_session+1),
                replace(helper,authentication_id=(1,0)),replace(helper,integrity_sid='S-1-16-12288'),
                replace(helper,integrity_attributes=helper.integrity_attributes ^ 1),
                replace(helper,elevation_type=2),replace(helper,restricted=not helper.restricted),
                replace(helper,restricted_sid_count=1),replace(helper,ui_access=1))
            for value in changed_helper:
                with self.subTest(helper=value.as_dict()),self.assertRaisesRegex(ContractError,'PRINCIPAL_MISMATCH'):
                    module._require_principal(value,owner)
            for changed in ({'token_type':2},{'impersonation_level':2},{'ui_access':1},
                {'integrity_sid':'S-1-16-12288'},{'elevation_type':2},
                {'has_restrictions':1,'restricted_sids':('S-1-5-12',)}):
                value=replace(owner,**changed)
                with self.subTest(owner=changed),self.assertRaisesRegex(ContractError,'PRINCIPAL_MISMATCH'):
                    module._require_principal(helper,value)
        self.call(body)

    def test_fabricated_and_foreign_thread_contexts_have_no_native_dispatch(self):
        with self.assertRaises(ContractError):
            with self.owner.native_context(object()):self.fail('fabricated context entered')
        def body(context):
            errors=[]
            def foreign():
                try:self.owner.owner_enrollment_expected(context)
                except ContractError as error:errors.append(error.code)
            thread=threading.Thread(target=foreign);thread.start();thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(errors,['OWNER_SESSION_ORIGINAL_DISPATCH_REQUIRED'])
        self.call(body)

    def test_duplicate_dispatch_and_second_designation_are_denied(self):
        def body(context):
            with self.assertRaisesRegex(ContractError,'DISPATCH_ALREADY_HELD'):
                with self.owner.native_context(context):self.fail('nested context accepted')
            session,request=self.prepare(context);self.owner.designate_enrollment(request,session,context)
            with self.assertRaisesRegex(ContractError,'DESIGNATION_DENIED'):
                self.owner.designate_enrollment(request,session,context)
        self.call(body)

    def test_stop_before_designation_keeps_native_gate_closed(self):
        def body(context):
            session,request=self.prepare(context);self.owner.request_stop()
            with self.assertRaisesRegex(ContractError,'DESIGNATION_DENIED'):
                self.owner.designate_enrollment(request,session,context)
            self.assertFalse(session._gate_may_open)
        self.call(body)

    def test_stop_after_designation_denies_challenge_without_sql_commit(self):
        def body(context):
            session,request=self.prepare(context);self.owner.designate_enrollment(request,session,context)
            self.owner.request_stop();before=self.store.position(INSTALLATION)
            with self.assertRaisesRegex(ContractError,'STOPPED'):
                self.kernel.begin_owner_enrollment(request.canonical_wire,context)
            self.assertEqual(before,self.store.position(INSTALLATION))
            self.assertFalse(session._gate_may_open)
        self.call(body)

    def test_stop_publishes_while_another_thread_owns_dispatch_lock(self):
        entered,release=threading.Event(),threading.Event()
        def hold():
            with self.owner._lock:entered.set();release.wait(3)
        thread=threading.Thread(target=hold);thread.start()
        try:
            self.assertTrue(entered.wait(3));started=time.perf_counter_ns();self.owner.request_stop()
            self.assertLess(time.perf_counter_ns()-started,250_000_000)
            self.assertTrue(self.owner._stopped.is_set())
        finally:release.set();thread.join(3)
        self.assertFalse(thread.is_alive())

    def test_close_busy_keeps_owner_available_and_does_not_close_borrowed_resources(self):
        entered,release=threading.Event(),threading.Event()
        def hold():
            with self.owner._lock:entered.set();release.wait(3)
        thread=threading.Thread(target=hold);thread.start()
        try:
            self.assertTrue(entered.wait(3))
            with self.assertRaisesRegex(ContractError,'BUSY'):self.owner.close()
            self.assertFalse(self.owner.closed or self.code.closed or self.binding.closed)
        finally:release.set();thread.join(3)
        self.owner.close();self.assertTrue(self.owner.closed)
        self.assertFalse(self.code.closed or self.binding.closed)

    def test_close_failure_preserves_refusing_control_exception_and_owner_custody(self):
        class Primary(KeyboardInterrupt):
            def __setattr__(self,name,value):raise RuntimeError('refused diagnostic storage')
            @property
            def add_note(self):raise RuntimeError('refused diagnostic lookup')
        primary=Primary('original session-close interruption')
        with patch.object(self.owner.approval_owner,'cancel_current',side_effect=primary):
            with self.assertRaises(Primary) as caught:self.owner.close()
        self.assertIs(caught.exception,primary)
        saved=BaseException.__dict__['__dict__'].__get__(primary)
        self.assertIs(saved['native_owner_session'],self.owner)
        saved['close_cleanup']();self.assertTrue(self.owner.closed)

    def test_closing_code_owner_invalidates_retained_final_fence(self):
        def body(context):
            with self.assertRaisesRegex(ContractError,'LEASE_ACTIVE'):self.code.close()
            with self.assertRaisesRegex(ContractError,'LEASE_INVALID'):
                self.owner.owner_enrollment_expected(context)
        self.call(body)

    def test_live_store_closure_invalidates_dispatch(self):
        def body(context):
            self.binding.close()
            with self.assertRaisesRegex(ContractError,'STORE_CLOSED'):
                self.owner.owner_enrollment_expected(context)
        self.call(body)

    def test_missing_manifest_role_denies_without_launching_helper(self):
        for role in ('helper_name','helper_source_name','worker_name'):
            with self.subTest(role=role),self.assertRaisesRegex(ContractError,'MANIFEST_BINDING_MISSING'):
                self.construct(**{role:'absent.exe'})
        self.assertIsNone(self.owner.approval_owner._active)

    def test_helper_scratch_must_be_the_measured_private_root(self):
        other=self.directory/'other-scratch';other.mkdir()
        with self.assertRaisesRegex(ContractError,'TEMPORARY_ROOT_BINDING_MISMATCH'):
            self.construct(temporary_root=other)
        self.assertIsNone(self.owner.approval_owner._active)

    def test_fabricated_native_owners_and_mismatched_clock_are_rejected(self):
        values=dict(installation_id=INSTALLATION,scope_id=PROJECT,policy_commitment=POLICY,
            helper_name='helper',helper_source_name='source',worker_name='worker',temporary_root=self.directory)
        for arguments in ((object(),self.clock,self.code),(self.view,object(),self.code),(self.view,self.clock,object())):
            with self.subTest(types=tuple(type(a).__name__ for a in arguments)),self.assertRaisesRegex(ContractError,'NATIVE_OWNERS_REQUIRED'):
                module.NativeOwnerSession(*arguments,**values)

    def test_effect_authority_preparation_and_admission_stay_closed(self):
        for method,args,code in ((self.owner.require_prepared_basis,(None,None,None),'TRUSTED_PREPARATION_OWNER_UNAVAILABLE'),
                (self.owner.require_admission,(None,None,None),'PROTECTED_RESOURCE_OWNER_UNAVAILABLE'),
                (self.owner.require_revocation,(None,None,None),'TRUSTED_REVOCATION_OWNER_UNAVAILABLE')):
            with self.subTest(method=method.__name__),self.assertRaisesRegex(ContractError,code):method(*args)
        for phase in ('APPROVE_CAP','APPROVE_RESTORE','UNKNOWN'):
            with self.subTest(phase=phase),self.assertRaisesRegex(ContractError,'EFFECT_OWNER_NOT_COMPOSED'):
                self.owner.require_owner_authority_current(phase,None,None,None,None,None,object())


if __name__=='__main__':unittest.main()
