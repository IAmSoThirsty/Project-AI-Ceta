"""Controlled instruction faults; execute only in an owned bounded test child.

Actual disposable canonical journals, controlled authority and nonnative
targets. Original six predicates are retained; source-line stimulus follows
the successor's protected map calls. No genuine/native-effect qualification.
"""
import ast
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

from ceta.contracts.wire import ContractError
from ceta.kernel.transactions import KernelTransactions
from ceta.kernel import cpu_execution as execution
import test_cpu_execution_admission as parent
import test_owner_authority_transactions as authority

INTERRUPTION_FACTS = []


def _method(name):
    tree = ast.parse(Path(execution.__file__).read_bytes())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == '_CpuExecutionCoordinator')
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name)


def _observe(owner):
    lock = execution._LIVENESS_LOCK
    locked = lock.locked()
    acquired = lock.acquire(False)
    if acquired: lock.release()
    a = execution._MUTATING_OWNERS.get(id(owner.owners))
    b = execution._MUTATING_STORES.get(id(owner.store))
    return dict(lock_locked_after=locked,nonblocking_lock_acquired=acquired,
        owner_count=0 if a is None else a[1],store_count=0 if b is None else b[1],
        local_count=owner.mutating,local_invocations=len(owner._mutations))


def _injected(call, method, line, primary, *, event='line', condition=None):
    code = method.__func__.__code__
    hits = []
    def trace(frame, kind, value):
        if frame.f_code is code and kind == event and (event != 'line' or frame.f_lineno == line) \
                and (condition is None or condition()):
            hits.append(dict(line=frame.f_lineno,event=kind,native_thread_id=threading.get_native_id()))
            raise primary
        return trace
    previous = sys.gettrace()
    escaped = None
    try:
        sys.settrace(trace)
        try: call()
        except BaseException as error: escaped = error
    finally: sys.settrace(previous)
    return escaped, hits


class RegistrationInterruptionTests(unittest.TestCase):
    fixture = parent.CpuExecutionAdmissionTests.fixture
    lease = parent.CpuExecutionAdmissionTests.lease
    status = parent.CpuExecutionAdmissionTests.status

    @classmethod
    def setUpClass(cls): parent.CpuExecutionAdmissionTests.setUpClass.__func__(cls)

    def idle(self, owner):
        row = _observe(owner)
        self.assertFalse(row['lock_locked_after'])
        self.assertTrue(row['nonblocking_lock_acquired'])
        self.assertEqual((row['owner_count'],row['store_count'],row['local_count'],row['local_invocations']),(0,0,0,0))

    def settle_own_fixture(self, owner):
        # Test-only known-row retirement after preserving failure facts. Never
        # adopt another fixture, replay a public method, or retry native exit.
        if execution._LIVENESS_LOCK.locked(): execution._LIVENESS_LOCK.release()
        self.assertTrue(execution._LIVENESS_LOCK.acquire(False))
        try:
            for table,identity in ((execution._MUTATING_OWNERS,owner.owners),(execution._MUTATING_STORES,owner.store)):
                row = table.get(id(identity))
                if row is not None:
                    self.assertIs(row[0],identity)
                    self.assertTrue(all(item.coordinator is owner for item in row[2]))
                    del table[id(identity)]
            owner._mutations.clear(); owner.mutating = 0
        finally: execution._LIVENESS_LOCK.release()

    def test_original_six_public_mutation_boundaries_release_lock_and_identity(self):
        method = _method('mutate')
        metadata = next(n for n in ast.walk(method) if isinstance(n,ast.With))
        calls = [n for n in metadata.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
            and isinstance(n.value.func,ast.Name) and n.value.func.id == '_add_mutation']
        local = next(n for n in metadata.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)
            and isinstance(n.value.func,ast.Attribute) and n.value.func.attr == 'add')
        callback = next(n for n in ast.walk(method) if isinstance(n,ast.Return))
        points = (('after-owner-registration',calls[1].lineno),
            ('after-both-before-local',local.lineno),('after-local-before-outer-finally',callback.lineno))
        for point,line in points:
            for control in (KeyboardInterrupt,SystemExit):
                with self.subTest(point=point,control=control.__name__):
                    f = self.fixture(); owner = f.kernel._cpu_execution
                    grant = f.cell(authority.grant_key_for(f.request)).value_wire
                    sql, peers = [], []
                    f.store._connection.set_trace_callback(lambda statement: sql.append(True))
                    original_peer = f.kernel._peer
                    def peer(context): peers.append(True); return original_peer(context)
                    primary = control('original six exact partial-registration boundary')
                    try:
                        with patch.object(f.kernel,'_peer',peer):
                            escaped,hits = _injected(lambda:f.kernel.revoke(grant,f.owners.context,'reason:owner-revoke'),
                                owner.mutate,line,primary)
                        facts = dict(point=point,control=control.__name__,source_line=line,injection_hit=hits,
                            exact_primary=escaped is primary,peer_callbacks=len(peers),SQL_statements_during_attempt=len(sql),
                            dispatch_calls=0,**_observe(owner))
                        INTERRUPTION_FACTS.append(facts)
                        self.assertIs(escaped,primary);self.assertEqual(len(hits),1)
                        self.assertEqual(peers,[]);self.assertEqual(sql,[]);self.idle(owner)
                    finally:
                        f.store._connection.set_trace_callback(None)
                        self.settle_own_fixture(owner)
                    self.assertEqual(self.status(f),'PREPARED')

    def test_nested_partial_publication_removes_only_exact_inner_invocation(self):
        f = self.fixture(); owner = f.kernel._cpu_execution; primary = KeyboardInterrupt('inner publication')
        original = execution._add_mutation; inner_tokens = []
        def add(table, identity, registration):
            original(table,identity,registration)
            if table is execution._MUTATING_STORES:
                inner_tokens.append(registration); raise primary
        def inner(kernel): self.fail('inner callback must not run')
        def outer(kernel):
            outer_tokens = execution._MUTATING_OWNERS[id(owner.owners)][2]
            with patch.object(execution,'_add_mutation',add):
                with self.assertRaises(KeyboardInterrupt) as raised: owner.mutate(inner,(),{})
            self.assertIs(raised.exception,primary)
            self.assertEqual(_observe(owner)['owner_count'],1);self.assertEqual(owner.mutating,1)
            self.assertEqual(execution._MUTATING_OWNERS[id(owner.owners)][2],outer_tokens)
            self.assertNotIn(inner_tokens[0],outer_tokens)
        owner.mutate(outer,(),{});self.idle(owner)

    def test_simultaneous_other_coordinator_token_survives_partial_failure(self):
        f = self.fixture(); a = f.kernel._cpu_execution
        b = KernelTransactions(f.store,f.codec,authority.INSTALLATION,f.owners)._cpu_execution
        entered, release = threading.Event(), threading.Event(); errors = []
        def paused(kernel): entered.set(); self.assertTrue(release.wait(3))
        def worker():
            try: a.mutate(paused,(),{})
            except BaseException as error: errors.append(error)
        thread = threading.Thread(target=worker,name='ka4-own-held-mutation');thread.start()
        try:
            self.assertTrue(entered.wait(2));original = execution._add_mutation;primary = SystemExit('other partial')
            def add(table, identity, registration):
                original(table,identity,registration)
                if table is execution._MUTATING_OWNERS: raise primary
            with patch.object(execution,'_add_mutation',add):
                with self.assertRaises(SystemExit) as raised:b.mutate(lambda kernel:None,(),{})
            self.assertIs(raised.exception,primary)
            self.assertEqual(_observe(a)['owner_count'],1);self.assertEqual(a.mutating,1);self.assertEqual(b.mutating,0)
        finally:release.set();thread.join(3)
        self.assertFalse(thread.is_alive());self.assertFalse(errors);self.idle(a);self.idle(b)

    def test_cleanup_secondary_keeps_primary_and_exact_invocation_without_hooks(self):
        f = self.fixture();owner=f.kernel._cpu_execution;hooks=[]
        class Data(dict):
            def refuse(self,*args,**kwargs):hooks.append('dictionary');raise OSError('hook')
            get=update=__getitem__=__setitem__=refuse
        class Primary(KeyboardInterrupt):
            def __setattr__(self,*args):hooks.append('setter');raise OSError('setter')
        primary=Primary('body');secondary=SystemExit('retirement')
        BaseException.__dict__['__dict__'].__set__(primary,Data())
        original=execution._attempt_remove
        def remove(table, identity, registration):
            return secondary if table is execution._MUTATING_OWNERS else original(table,identity,registration)
        def body(kernel):raise primary
        try:
            with patch.object(execution,'_attempt_remove',remove):
                try:owner.mutate(body,(),{})
                except BaseException as escaped:self.assertIs(escaped,primary)
                else:self.fail('primary suppressed')
            data=BaseException.__dict__['__dict__'].__get__(primary)
            registration=dict.__getitem__(data,'cpu_registration_custody')[-1]
            self.assertIs(dict.__getitem__(data,'cpu_registration_cleanup_failures')[0][0],secondary)
            self.assertIn(registration,execution._MUTATING_OWNERS[id(owner.owners)][2])
            self.assertEqual(registration.cleanup_failures,(secondary,));self.assertFalse(registration.retired)
            self.assertFalse(execution._LIVENESS_LOCK.locked());self.assertEqual(hooks,[])
        finally:self.settle_own_fixture(owner)

    def test_partial_claim_and_return_faults_preserve_primary_without_consumption(self):
        method=_method('claim_liveness');metadata=next(n for n in ast.walk(method) if isinstance(n,ast.With))
        assignments=[n for n in metadata.body if isinstance(n,ast.Assign)]
        store=next(n for n in assignments if isinstance(n.targets[0],ast.Subscript)
            and isinstance(n.targets[0].value,ast.Name) and n.targets[0].value.id=='_ACTIVE_STORES')
        active=next(n for n in assignments if isinstance(n.targets[0],ast.Attribute) and n.targets[0].attr=='active')
        for label,line,event in (('owner-only',store.lineno,'line'),('both-before-active',active.lineno,'line'),
                                ('claim-return',0,'return')):
            for control in (KeyboardInterrupt,SystemExit):
                with self.subTest(point=label,control=control.__name__):
                    f=self.fixture();owner=f.kernel._cpu_execution;lease=self.lease(f);primary=control(label)
                    escaped,hits=_injected(lease.__enter__,owner.claim_liveness,line,primary,event=event)
                    self.assertIs(escaped,primary);self.assertEqual(len(hits),1)
                    self.assertFalse(execution._LIVENESS_LOCK.locked());self.assertIsNone(owner.active)
                    self.assertNotIn(id(owner.owners),execution._ACTIVE_OWNERS)
                    self.assertNotIn(id(owner.store),execution._ACTIVE_STORES)
                    self.assertTrue(lease.inspection()['closed']);self.assertFalse(lease.inspection()['pending_cleanup'])
                    self.assertEqual(self.status(f),'PREPARED')

    def test_release_control_secondary_retains_original_primary_and_pending_lease(self):
        f=self.fixture();owner=f.kernel._cpu_execution;lease=self.lease(f)
        primary=KeyboardInterrupt('body');secondary=SystemExit('active partial retirement')
        method=_method('release_liveness');loop=next(n for n in ast.walk(method) if isinstance(n,ast.For))
        code=owner.release_liveness.__func__.__code__;hits=[];previous=sys.gettrace()
        def trace(frame,event,value):
            if frame.f_code is code and event=='line' and frame.f_lineno==loop.lineno \
                    and id(owner.owners) not in execution._ACTIVE_OWNERS \
                    and id(owner.store) in execution._ACTIVE_STORES:
                hits.append(True);raise secondary
            return trace
        escaped=None
        try:
            with lease:
                sys.settrace(trace)
                raise primary
        except BaseException as error:escaped=error
        finally:sys.settrace(previous)
        try:
            self.assertIs(escaped,primary);self.assertEqual(hits,[True])
            self.assertIs(primary.owned_cpu_execution,lease);self.assertIs(primary.owned_cpu_cleanup_failure,secondary)
            self.assertTrue(lease.inspection()['pending_cleanup']);self.assertFalse(lease.inspection()['closed'])
            self.assertFalse(execution._LIVENESS_LOCK.locked());self.assertFalse(f.owners.managers[-1].locked)
        finally:
            # Only known volatile metadata is settled. Native/retainer exit is
            # not replayed, and historical pending flags are not relabelled.
            owner.release_liveness(lease)

    def test_losing_release_never_removes_exact_winning_active_rows(self):
        f=self.fixture();owner=f.kernel._cpu_execution;loser=self.lease(f)
        with self.lease(f) as winner:
            before_owner=execution._ACTIVE_OWNERS[id(owner.owners)]
            before_store=execution._ACTIVE_STORES[id(owner.store)]
            owner.release_liveness(loser)
            self.assertIs(owner.active,winner)
            self.assertIs(execution._ACTIVE_OWNERS[id(owner.owners)],before_owner)
            self.assertIs(execution._ACTIVE_STORES[id(owner.store)],before_store)
        self.idle(owner)
