"""Actual canonical SQLite preparation; native approval/current facts CONTROLLED.

No native process, profile, authentication, CPU Set or production activation.
Only the existing native observation and approval predicates are controlled;
the selected preparation predicate, kernel, same-CAS rows and real writer run.
"""
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
import threading
import unittest
import uuid
from unittest.mock import patch

from ceta.contracts.kernel_transactions import (PeerIdentity, basis_key, budget_key,
    control_wire, logical_key, read_budget, ZERO_BUDGET)
from ceta.contracts.owner_enrollment import enrollment_transcript_bytes
from ceta.contracts.store_transactions import STORE_PROFILE, StoreKey
from ceta.contracts.wire import ContractError, RecordCodec, canonical_bytes, strict_loads
from ceta.effects.native_cpu_binding import NativeCpuBinding
from ceta.identity import owner_session as module
from ceta.identity.native_clock import NativeSessionClock
from ceta.identity.native_code_binding import NativeCodeBinding, _RetainedBinding
from ceta.identity.native_owner_view import NativeOwnerView, NativeOwnerObservation, NativeStoreBinding
from ceta.identity.owners import WindowsIdentityOwners
from ceta.kernel.owner_authority import (_row, _wire, ceremony_key, enrollment_key,
    grant_key_for, owned_cpu_proposal)
from ceta.kernel.transactions import KernelTransactions
from ceta.store.journal import SqliteJournal
import test_owner_authority_transactions as data

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT/'.agents/fixtures/owner-preparation'
FACTS = []
raw = lambda error: BaseException.__dict__['__dict__'].__get__(error)


class Fixture:
    """Canonical positive decisions depend on CONTROLLED native fixture ports."""
    def __init__(self, schema):
        self.root=Path(FIXTURES)/uuid.uuid4().hex;self.root.mkdir(parents=True)
        self.codec=RecordCodec(schema);self.fault=None;self.calls=[];self.native_calls=[]
        self.store=SqliteJournal(self.root,self.codec,(data.INSTALLATION,data.PROJECT),
            create=True,profile=STORE_PROFILE,before_commit=self.inject)
        self.enrollment=data.enrollment_request();self.request=data.effect_request(self.enrollment)
        self.control=data.ControlledOwners(self.enrollment);self.context=self.control.context
        owner=object.__new__(module.NativeCpuOwnerSession)
        self.owner=owner
        owner._preparation_kernel=owner._preparation_invocation=None
        owner._installation=data.INSTALLATION;owner._scope=data.PROJECT;owner._policy=data.H
        owner._closed=False;owner._stopped=threading.Event();owner._lock=threading.RLock()
        owner._effect_busy=owner._effect_retaining=False;owner._effect_serial=1
        owner._effect_lease=owner._effect_proof=owner._proof=owner._enrollment_lease=None
        owner._expected=self.enrollment;owner._anchor=None;owner._worker_commitment=data.H
        owner._approval=SimpleNamespace(_active=None,cancel_current=lambda:None)
        owner.authenticate=self.control.authenticate
        owner.clock=self.control.clock
        owner.owner_enrollment_expected=self.control.owner_enrollment_expected
        owner.require_owner_authority_current=self.control.require_owner_authority_current
        self.native_store=object.__new__(NativeStoreBinding)
        self.native_store._database_path=self.store.path;self.native_store._closed=False
        self.native_store._root_path=self.root
        self.clock=object.__new__(NativeSessionClock)
        self.clock._state='ACTIVE';self.clock._reason=None;self.clock._registration=object()
        self.clock._session='controlled-clock-session';self.clock._epoch=7;self.clock._resume=0
        code=object.__new__(NativeCodeBinding);code.source_commitment=code.environment_commitment=data.H
        code._closed=False;code._closing=threading.Event()
        self.code_lease=_RetainedBinding(code);code._lease=self.code_lease
        owner._code=code;owner._native_clock=self.clock
        self.view=object.__new__(NativeOwnerView)
        self.view._clock=self.clock;self.view._store=self.native_store;self.view._registry=object()
        self.view.observe=self.observe;owner._view=self.view
        owner._dispatch=(self.context,threading.get_ident(),self.code_lease)
        target=SimpleNamespace(resource_identity=self.request.process_identity,_closed=False,
            _termination_requested=False,_exit_code=None,_cpu_lifetime_unavailable=False,
            _process=object(),_job=object(),_pid=self.request.process_identity.pid,
            _creation_time=self.request.process_identity.creation_time,_image_sha256='a'*64,
            _cpu_job_digest=data.H,_cpu_version=self.request.expected_limit.version,
            _cpu_policy=self.request.expected_limit.limit)
        binding=object.__new__(NativeCpuBinding);binding._target=target;binding._clock=self.clock
        binding._closed=False;binding._cancelled=threading.Event();binding._external_cancel=None
        binding._reason=None;binding._lifetime=binding._target_fields();binding._session=self.clock._session
        binding._last_clock=data.clock();capture=object();self.binding=binding;self.capture=capture
        binding._current=SimpleNamespace(public=capture,measurement=SimpleNamespace(original=self.request.expected_limit))
        def controlled_current(value,request):
            self.native_calls.append('binding-current')
            if value is not capture or request.canonical_wire!=self.request.canonical_wire:
                raise ContractError('CONTROLLED_NATIVE_CAPTURE_CHANGED')
        binding.require_current=controlled_current
        owner._effect=module._EffectDesignation(self.request.canonical_wire,binding,capture,self.context,1)
        self.kernel=KernelTransactions(self.store,self.codec,data.INSTALLATION,owner)
        self.kernel.begin_owner_enrollment(self.enrollment.canonical_wire,self.context)
        transcript=data.enrollment_transcript(self.enrollment)
        proof=self.control.proof('ENROLL',None,transcript)
        self.kernel.enroll_owner(self.enrollment.canonical_wire,enrollment_transcript_bytes(transcript),proof,self.context)
        transcript=data.effect_transcript(self.enrollment,self.request)
        proof=self.control.proof('APPROVE_CAP',self.request,transcript)
        self.kernel.approve_owned_cpu(self.enrollment.request_id,self.request.canonical_wire,
            transcript.canonical_wire,proof,self.context)
        self.proposal=owned_cpu_proposal(self.codec,self.request)
        self.native_calls.clear();self.control.calls.clear()

    def observe(self, context):
        peer=self.control.authenticate(context);self.native_calls.append('owner-observe')
        return NativeOwnerObservation(peer,self.enrollment.owner_facts,self.enrollment.private_root,
            self.enrollment.database,*self.control.samples,0)

    def inject(self):
        if self.fault is not None:self.fault()

    def cell(self,key):return self.store.snapshot((key,))[0]

    def row(self):return _row(self.cell(enrollment_key(data.INSTALLATION,self.enrollment.request_id)).value_wire)

    def mutate(self,key,wire):
        """Adversarial controlled canonical write, never direct fixture seeding."""
        cell=self.cell(key);event='event:'+uuid.uuid4().hex
        first=self.codec.decode(self.store.replay(data.INSTALLATION,0,1)[0].payload_wire).as_dict()
        first.update(record_id='decision:'+uuid.uuid4().hex,reason_codes=['CONTROLLED_OS5_FAULT'])
        self.kernel._commit(self.codec.decode(canonical_bytes(first)),event,'kernel.fixture.os5',
            self.control.peer,data.clock(),{key:cell},{key:wire},data.H)

    def prepare(self):return self.kernel.prepare(self.proposal.canonical_wire,self.context)

    def close(self):
        self.store.close()
        FACTS.append(dict(root=str(self.root),closed=self.store._closed,
            transaction_open=self.store._connection is not None and not self.store._closed,
            kernel_invocation=getattr(self.kernel,'_preparation_invocation',None) is not None,
            owner_invocation=self.owner._preparation_invocation is not None,
            native_observation_calls=list(self.native_calls),controlled_native_and_approval=True))


class NativeOwnerPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.schema=strict_loads((ROOT/'contracts/schemas/records.schema.json').read_bytes())

    def fixture(self):
        value=Fixture(self.schema);self.addCleanup(value.close);return value

    def retired(self,f):
        self.assertIsNone(f.kernel._preparation_invocation)
        self.assertIsNone(f.owner._preparation_invocation);self.assertFalse(f.owner._effect_busy)
        self.assertFalse(f.store._connection.in_transaction)

    def no_issuance(self,f):
        key=logical_key('projection',data.PROJECT,'issuance',f.request.proposal_id)
        self.assertEqual(f.cell(key).generation,0);self.retired(f)

    def test_real_canonical_approval_prepares_without_parallel_basis_cache(self):
        f=self.fixture();result=f.prepare();permit=f.codec.decode(result.record_wire).as_dict()
        self.assertEqual(permit['status'],'PREPARED');self.assertEqual(permit['proposal_ref'],f.request.proposal_id)
        self.assertNotIn('prepared',vars(f.owner));self.assertEqual(f.native_calls,['owner-observe','binding-current'])
        _,_,held,charged=read_budget(f.cell(budget_key(grant_key_for(f.enrollment))).value_wire,budget_key(grant_key_for(f.enrollment)))
        self.assertEqual(held,f.request.operation_budget);self.assertEqual(charged,ZERO_BUDGET)
        self.retired(f)

    def test_writer_guard_has_no_native_observation_or_sql_reentry(self):
        f=self.fixture();inside=[]
        f.fault=lambda:inside.append((f.store._connection.in_transaction,tuple(f.native_calls)))
        f.prepare();self.assertEqual(inside,[(True,('owner-observe','binding-current'))]);self.retired(f)

    def test_default_owners_and_all_effect_admission_ports_stay_closed(self):
        f=self.fixture();default=WindowsIdentityOwners(object())
        with self.assertRaisesRegex(ContractError,'TRUSTED_PREPARATION_OWNER_UNAVAILABLE'):
            default.require_prepared_basis(f.proposal,b'{}',f.control.peer)
        result=f.prepare()
        for method,args in ((f.owner.require_admission,(None,None,f.control.peer)),
            (f.owner.require_revocation,(None,f.control.peer,'reason:stop')),(f.kernel.require_runtime_admission,())):
            with self.assertRaises(ContractError):method(*args)
        with self.assertRaisesRegex(ContractError,'PROTECTED_RESOURCE_OWNER_UNAVAILABLE'):
            f.kernel.consume(result.record_wire,f.context)
        self.retired(f)

    def test_equal_proposal_and_basis_cannot_call_owner_outside_kernel_invocation(self):
        f=self.fixture();basis=f.cell(basis_key(data.PROJECT,f.request.proposal_id)).value_wire
        with self.assertRaisesRegex(ContractError,'INVOCATION_REQUIRED'):
            f.owner.require_prepared_basis(f.proposal,basis,f.control.peer)
        self.no_issuance(f)

    def test_a_second_kernel_cannot_bind_the_same_native_session(self):
        f=self.fixture()
        with self.assertRaisesRegex(ContractError,'KERNEL_BINDING'):
            KernelTransactions(f.store,f.codec,data.INSTALLATION,f.owner)
        self.assertIs(f.owner._preparation_kernel,f.kernel);self.no_issuance(f)

    def test_fake_or_subclass_store_is_not_a_production_preparation_writer(self):
        f=self.fixture();original=f.kernel._store
        for other in (SimpleNamespace(),object.__new__(type('FakeJournal',(SqliteJournal,),{}))):
            f.kernel._store=other
            with self.assertRaises(ContractError):f.prepare()
            f.kernel._store=original;self.no_issuance(f)

    def test_wrong_store_identity_is_denied_before_read_or_commit(self):
        f=self.fixture();old=f.native_store._database_path
        f.native_store._database_path=old.with_name('different.sqlite3')
        with self.assertRaisesRegex(ContractError,'STORE_CHANGED'):f.prepare()
        f.native_store._database_path=old;self.no_issuance(f)

    def test_instance_snapshot_success_cannot_replace_canonical_store(self):
        f=self.fixture();f.store.snapshot=lambda keys:()
        with self.assertRaises((AttributeError,ContractError)):f.prepare()
        del f.store.snapshot;self.no_issuance(f)

    def test_original_context_is_required_and_failure_retires_only_own_invocation(self):
        f=self.fixture()
        with self.assertRaises(ContractError):f.kernel.prepare(f.proposal.canonical_wire,object())
        self.no_issuance(f);self.assertIs(f.owner._dispatch[0],f.context)

    def test_foreign_thread_cannot_prepare_on_a_live_original_dispatch(self):
        f=self.fixture();errors=[]
        def foreign():
            try:f.prepare()
            except BaseException as error:errors.append(error)
        worker=threading.Thread(target=foreign);worker.start();worker.join(5)
        self.assertFalse(worker.is_alive());self.assertEqual(len(errors),1)
        self.assertIsInstance(errors[0],ContractError);self.no_issuance(f)

    def test_peer_change_denies_before_any_issuance(self):
        f=self.fixture();f.control.peer=PeerIdentity('owner:other',f.control.peer.session_id)
        with self.assertRaises(ContractError):f.prepare()
        self.no_issuance(f)

    def test_request_change_does_not_reuse_equal_approved_basis(self):
        f=self.fixture();f.owner._effect.wire=replace(f.request,request_id='request:other').canonical_wire
        with self.assertRaises(ContractError):f.prepare()
        self.no_issuance(f)

    def test_source_environment_and_policy_configuration_changes_deny(self):
        for field in ('source_commitment','environment_commitment'):
            f=self.fixture();setattr(f.owner._code,field,data.H2)
            with self.subTest(field=field),self.assertRaises(ContractError):f.prepare()
            self.no_issuance(f)
        f=self.fixture();f.owner._policy=data.H2
        with self.assertRaises(ContractError):f.prepare()
        self.no_issuance(f)

    def test_generation_and_registry_changes_are_not_accepted_as_current(self):
        for key,change in (('generation',{'authority_generation':2}),('policy',{'policy_commitment':data.H2})):
            f=self.fixture();cell=f.cell(f.kernel._control);value=strict_loads(cell.value_wire);value.update(change)
            f.mutate(f.kernel._control,canonical_bytes(value))
            with self.subTest(key=key),self.assertRaises(ContractError):f.prepare()
            self.no_issuance(f)
        f=self.fixture();value=strict_loads(f.cell(f.kernel._registry).value_wire);value['commitment']=data.H2
        f.mutate(f.kernel._registry,canonical_bytes(value))
        with self.assertRaises(ContractError):f.prepare()
        self.no_issuance(f)

    def test_changed_approval_proposal_request_or_decision_is_denied(self):
        for field,value in (('request_wire','{}'),('proposal_wire','{}'),('decision_event_ref','event:foreign')):
            f=self.fixture();row=f.row();row['cap_approval'][field]=value
            f.mutate(enrollment_key(data.INSTALLATION,f.enrollment.request_id),_wire(row))
            with self.subTest(field=field),self.assertRaises(ContractError):f.prepare()
            self.no_issuance(f)

    def test_missing_approval_or_changed_enrollment_cannot_create_authority(self):
        for field,value in (('cap_approval',None),('state','STOPPED'),('request_wire','{}')):
            f=self.fixture();row=f.row();row[field]=value
            f.mutate(enrollment_key(data.INSTALLATION,f.enrollment.request_id),_wire(row))
            with self.subTest(field=field),self.assertRaises(ContractError):f.prepare()
            self.no_issuance(f)

    def test_request_index_and_consumed_ceremony_are_bound(self):
        for kind in ('request','challenge','nonce'):
            f=self.fixture();transcript=data.effect_transcript(f.enrollment,f.request)
            key=(logical_key('projection',data.INSTALLATION,'owner-effect',f.request.request_id) if kind=='request'
                else ceremony_key(data.INSTALLATION,kind,transcript.challenge_id if kind=='challenge' else transcript.ceremony_nonce))
            value=strict_loads(f.cell(key).value_wire)
            value['decision_event_ref' if kind=='request' else 'event_ref']='event:foreign'
            f.mutate(key,canonical_bytes(value))
            with self.subTest(kind=kind),self.assertRaises(ContractError):f.prepare()
            self.no_issuance(f)

    def test_row_mutation_between_read_and_writer_is_cas_conflict(self):
        f=self.fixture();once=[]
        def change():
            if once:return
            once.append(True);f.control.on_clock=None
            key=enrollment_key(data.INSTALLATION,f.enrollment.request_id);row=f.row();row['stop_reason_ref']='reason:changed'
            f.mutate(key,_wire(row))
        f.control.on_clock=change
        with self.assertRaisesRegex(ContractError,'CONFLICT'):f.prepare()
        self.no_issuance(f)

    def test_stop_before_entry_and_during_native_observation_denies(self):
        f=self.fixture();f.owner.request_stop()
        with self.assertRaises(ContractError):f.prepare()
        self.no_issuance(f)
        f=self.fixture();observe=f.view.observe
        def stop(context):
            value=observe(context);f.owner.request_stop();return value
        f.view.observe=stop
        with self.assertRaises(ContractError):f.prepare()
        self.no_issuance(f)

    def test_last_clock_callback_stop_wins_before_journal_commit(self):
        f=self.fixture();ticks=[]
        def stopping():
            ticks.append(True)
            if len(ticks)==3:f.owner.request_stop()
        f.control.on_clock=stopping
        with self.assertRaises(ContractError):f.prepare()
        self.assertEqual(len(ticks),3);self.no_issuance(f)

    def test_postcommit_stop_retains_exact_canonical_issuance_and_held_budget(self):
        f=self.fixture();ticks=[]
        def stopping():
            ticks.append(True)
            if len(ticks)==4:f.owner.request_stop()
        f.control.on_clock=stopping
        with self.assertRaises(ContractError):f.prepare()
        key=logical_key('projection',data.PROJECT,'issuance',f.request.proposal_id)
        self.assertEqual(f.cell(key).generation,1)
        recovered=f.kernel.recover_preparation(f.proposal.canonical_wire,f.context)
        self.assertEqual(recovered.as_dict()['status'],'PREPARED')
        _,_,held,charged=read_budget(f.cell(budget_key(grant_key_for(f.enrollment))).value_wire,budget_key(grant_key_for(f.enrollment)))
        self.assertEqual(held,f.request.operation_budget);self.assertEqual(charged,ZERO_BUDGET);self.retired(f)

    def test_reentrant_prepare_cannot_replace_or_retire_winning_invocation(self):
        f=self.fixture();calls=[];observe=f.view.observe
        def nested(context):
            token=f.kernel._preparation_invocation
            with self.assertRaisesRegex(ContractError,'REENTRANT'):f.prepare()
            self.assertIs(f.kernel._preparation_invocation,token);calls.append(True)
            return observe(context)
        f.view.observe=nested;f.prepare();self.assertEqual(calls,[True]);self.retired(f)

    def test_foreign_competitor_cannot_remove_active_token(self):
        f=self.fixture();attempted=threading.Event();errors=[];observe=f.view.observe
        def competing():
            try:f.prepare()
            except BaseException as error:errors.append(error)
            finally:attempted.set()
        def nested(context):
            token=f.kernel._preparation_invocation
            worker=threading.Thread(target=competing);worker.start();self.assertTrue(attempted.wait(5));worker.join(5)
            self.assertFalse(worker.is_alive());self.assertIs(f.kernel._preparation_invocation,token)
            return observe(context)
        f.view.observe=nested;f.prepare();self.assertEqual(len(errors),1);self.assertIsInstance(errors[0],ContractError);self.retired(f)

    def test_repeated_preparation_cannot_allocate_a_second_permit(self):
        f=self.fixture();first=f.prepare();before=f.store.position(data.PROJECT)
        with self.assertRaisesRegex(ContractError,'ALREADY_PREPARED'):f.prepare()
        self.assertEqual(f.store.position(data.PROJECT),before)
        self.assertEqual(f.kernel.recover_preparation(f.proposal.canonical_wire,f.context).canonical_wire,first.record_wire)
        self.retired(f)

    def test_public_check_replacement_cannot_bypass_captured_selected_predicate(self):
        f=self.fixture();f.owner.require_prepared_basis=lambda *args:None
        row=f.row();row['cap_approval']=None
        f.mutate(enrollment_key(data.INSTALLATION,f.enrollment.request_id),_wire(row))
        with self.assertRaises(ContractError):f.prepare()
        self.no_issuance(f)

    def test_primary_control_identity_and_cleanup_secondary_survive_hostile_hooks(self):
        for base in (KeyboardInterrupt,SystemExit,MemoryError):
            f=self.fixture();hits=[]
            class Storage(dict):
                def update(self,*args,**kwargs):hits.append('update');raise OSError('trap')
                def __setitem__(self,*args):hits.append('setitem');raise OSError('trap')
            class Primary(base):
                def __setattr__(self,*args):hits.append('setter');raise OSError('trap')
                @property
                def add_note(self):hits.append('note');raise OSError('trap')
            primary=Primary('original');BaseException.__dict__['__dict__'].__set__(primary,Storage())
            cleanup=OSError('exit-secondary');original=module.NativeCpuOwnerSession._end_preparation
            def fail():raise primary
            def ending(owner,token):
                original(owner,token);raise cleanup
            f.view.observe=lambda context:fail()
            with patch.object(module.NativeCpuOwnerSession,'_end_preparation',ending):
                try:f.prepare()
                except BaseException as caught:self.assertIs(caught,primary)
                else:self.fail('missing primary')
            self.assertIs(dict.__getitem__(raw(primary),'native_preparation_owner'),f.owner)
            self.assertEqual(dict.__getitem__(raw(primary),'native_preparation_cleanup_errors'),(cleanup,))
            self.assertEqual(hits,[]);self.no_issuance(f)

    def test_cleanup_only_failure_preserves_committed_permit_and_exact_invocation(self):
        f=self.fixture();cleanup=SystemExit('exit');original=module.NativeCpuOwnerSession._end_preparation
        def ending(owner,token):original(owner,token);raise cleanup
        with patch.object(module.NativeCpuOwnerSession,'_end_preparation',ending):
            try:f.prepare()
            except BaseException as caught:self.assertIs(caught,cleanup)
            else:self.fail('missing cleanup')
        self.assertIs(raw(cleanup)['native_preparation_owner'],f.owner)
        self.assertFalse(raw(cleanup)['native_preparation_invocation'].active)
        self.assertEqual(f.cell(logical_key('projection',data.PROJECT,'issuance',f.request.proposal_id)).generation,1)
        self.retired(f)

    def test_unretired_exit_failure_exposes_exact_pending_owner_without_retry(self):
        f=self.fixture();cleanup=OSError('before-retire');calls=[]
        def ending(owner,token):calls.append(token);raise cleanup
        with patch.object(module.NativeCpuOwnerSession,'_end_preparation',ending):
            try:f.prepare()
            except BaseException as caught:self.assertIs(caught,cleanup)
            else:self.fail('missing cleanup')
        token=raw(cleanup)['native_preparation_invocation'];self.assertEqual(calls,[token])
        self.assertIs(f.owner._preparation_invocation,token);self.assertFalse(token.active)
        with self.assertRaises(ContractError):f.prepare()
        module.NativeCpuOwnerSession._end_preparation(f.owner,token);self.retired(f)

    def test_timer_rollback_and_deadline_equality_never_open_preparation(self):
        for ticks in ((100,99),(100,100+60_000_000_000)):
            f=self.fixture()
            with patch.object(module.time,'perf_counter_ns',side_effect=ticks):
                with self.assertRaises(ContractError):f.prepare()
            self.no_issuance(f)

    def test_changed_target_or_code_lease_during_writer_rolls_back(self):
        for mutation in (lambda f:setattr(f.binding._target,'_cpu_version',2),
                         lambda f:setattr(f.code_lease,'_active',False)):
            f=self.fixture();f.fault=lambda:mutation(f)
            with self.assertRaises(ContractError):f.prepare()
            self.no_issuance(f)

    def test_private_prepare_bypass_has_no_registered_selected_owner_witness(self):
        f=self.fixture()
        with self.assertRaisesRegex(ContractError,'INVOCATION_REQUIRED'):
            f.kernel._prepare(f.proposal.canonical_wire,f.context)
        self.no_issuance(f)

    def test_interruption_at_kernel_publication_retires_exact_token(self):
        for kind in (KeyboardInterrupt,SystemExit):
            f=self.fixture();primary=kind('publication');seen=[]
            def setting(kernel,name,value):
                object.__setattr__(kernel,name,value)
                if kernel is f.kernel and name=='_preparation_invocation' and value is not None and not seen:
                    seen.append(value);raise primary
            with patch.object(KernelTransactions,'__setattr__',setting,create=True):
                try:f.prepare()
                except BaseException as caught:self.assertIs(caught,primary)
                else:self.fail('publication interruption missing')
            self.assertEqual(len(seen),1);self.no_issuance(f)
            self.assertFalse(seen[0].active)
            self.assertIs(raw(primary)['native_preparation_invocation'],seen[0])

    def test_interruption_at_owner_begin_partial_mutations_retires_exact_token(self):
        for kind in (KeyboardInterrupt,SystemExit):
            for field in ('_preparation_invocation','_effect_busy'):
                f=self.fixture();primary=kind('owner-begin');seen=[]
                def setting(owner,name,value):
                    object.__setattr__(owner,name,value)
                    if owner is f.owner and name==field and value and not seen:
                        seen.append(f.kernel._preparation_invocation);raise primary
                with patch.object(module.NativeCpuOwnerSession,'__setattr__',setting,create=True):
                    try:f.prepare()
                    except BaseException as caught:self.assertIs(caught,primary)
                    else:self.fail('begin interruption missing')
                self.assertEqual(len(seen),1);self.no_issuance(f)
                self.assertFalse(seen[0].active)

    def test_last_stopwatch_read_cannot_hide_target_code_or_context_changes(self):
        for mutate in (lambda f:setattr(f.binding._target,'_cpu_version',2),
            lambda f:setattr(f.owner._code,'environment_commitment',data.H2),
            lambda f:setattr(f.owner,'_dispatch',(object(),threading.get_ident(),f.code_lease))):
            f=self.fixture();original=module.time.perf_counter_ns;calls=[]
            def ticking():
                value=original();calls.append(value)
                if len(calls)==2:mutate(f)
                return value
            with patch.object(module.time,'perf_counter_ns',ticking):
                with self.assertRaises(ContractError):f.prepare()
            self.no_issuance(f)

    def test_private_reentry_cannot_publish_a_permit_from_clock_callback(self):
        f=self.fixture();entered=[]
        def reenter():
            f.control.on_clock=None;token=f.kernel._preparation_invocation;entered.append(token)
            with self.assertRaisesRegex(ContractError,'PREPARATION_INVOCATION_REENTRY'):
                f.kernel._prepare(f.proposal.canonical_wire,f.context,token)
            self.assertIs(f.kernel._preparation_invocation,token)
        f.control.on_clock=reenter;result=f.prepare()
        self.assertEqual(len(entered),1);self.assertEqual(f.codec.decode(result.record_wire).as_dict()['status'],'PREPARED')
        self.retired(f)

    def test_existing_writer_callback_denies_before_native_observation_or_nested_sql(self):
        f=self.fixture();checked=[]
        def callback():
            f.fault=None
            with self.assertRaisesRegex(ContractError,'OWNER_PREPARATION_WRITER_REENTRY'):
                f.prepare()
            self.assertEqual(f.native_calls,[])
            self.assertIsNone(f.kernel._preparation_invocation)
            self.assertIsNone(f.owner._preparation_invocation)
            self.assertTrue(f.store._connection.in_transaction);checked.append(True)
        f.fault=callback
        f.mutate(f.kernel._control,f.cell(f.kernel._control).value_wire)
        self.assertEqual(checked,[True]);self.no_issuance(f)
