"""Real canonical SQLite connections with explicitly controlled close responses.

The proxy's known native disposition is separate from the journal's uncertainty.
No mocked positive authority or claim of a native SQLite close defect is made.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys,unittest,uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from ceta.contracts.wire import ContractError,RecordCodec,strict_loads
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.store import journal as product
from ceta.store.sqlite_runtime import load_sqlite,runtime_identity

NATIVE_CONNECTION_RECEIPTS=[]
SCOPE=('project:constructor-fixture',)
raw_dict=lambda error:BaseException.__dict__['__dict__'].__get__(error)
traceback_of=lambda error:BaseException.__dict__['__traceback__'].__get__(error)

def original_raise(error,holder):
    try:raise error
    except BaseException:
        if holder.original_traceback is None:
            holder.original_traceback=traceback_of(error)
        raise


class ConnectionProxy:
    def __init__(self,real,*,setup_primary=None,close_actions=()):
        self.real=real;self.setup_primary=setup_primary;self.close_actions=list(close_actions)
        self.close_calls=0;self.native_close_calls=0;self.native_known_closed=False
        self.fixture_recovery_calls=0;self.original_traceback=None
        if real.execute('SELECT 1').fetchone()!=(1,):raise AssertionError('real SQLite fixture unavailable')
    def __getattr__(self,name):return getattr(self.real,name)
    def setconfig(self,*args):
        if self.setup_primary is not None:
            primary=self.setup_primary;self.setup_primary=None;original_raise(primary,self)
        return self.real.setconfig(*args)
    def close(self):
        self.close_calls+=1
        action=self.close_actions.pop(0) if self.close_actions else ('normal',None)
        kind,value=action
        if kind=='before':original_raise(value,self)
        self.real.close();self.native_close_calls+=1;self.native_known_closed=True
        if kind=='after':original_raise(value,self)
        if kind=='return':return value
        return None
    def recover_fixture(self):
        # The test knows exactly whether its controlled response called native
        # close. Product code receives no such oracle or inferred permission.
        if not self.native_known_closed:
            self.real.close();self.native_close_calls+=1;self.native_known_closed=True
            self.fixture_recovery_calls+=1
        try:self.real.execute('SELECT 1')
        except Exception as error:
            if not isinstance(error,load_sqlite().ProgrammingError):raise
        else:raise AssertionError('fixture native connection remained open')


class SQLiteFactory:
    def __init__(self,sqlite,plans,*,connect_primary=None,fail_connect=0):
        self.sqlite=sqlite;self.plans=list(plans);self.connections=[]
        self.connect_primary=connect_primary;self.fail_connect=fail_connect;self.connect_calls=0
    def __getattr__(self,name):return getattr(self.sqlite,name)
    def connect(self,*args,**kwargs):
        self.connect_calls+=1
        if self.connect_calls==self.fail_connect:raise self.connect_primary
        real=self.sqlite.connect(*args,**kwargs)
        plan=self.plans.pop(0) if self.plans else {}
        proxy=ConnectionProxy(real,**plan);self.connections.append(proxy);return proxy


class JournalConstructorCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sqlite=load_sqlite();cls.native_identity=runtime_identity()
        cls.codec=RecordCodec(strict_loads((ROOT/'contracts/schemas/records.schema.json').read_bytes()))
    def setUp(self):self.factories=[];self.returned=[];self.roots=[]
    def root(self,*,existing=True,profile='ceta-sqlite-journal-v1'):
        path=ROOT/'.agents/fixtures/journal-constructor'/uuid.uuid4().hex
        path.mkdir(parents=True,exist_ok=False);self.roots.append(path)
        if existing:
            seed=product.SqliteJournal(path,self.codec,SCOPE,create=True,profile=profile)
            seed.close()
        return path
    def factory(self,plans=(),**kwargs):
        result=SQLiteFactory(self.sqlite,plans,**kwargs);self.factories.append(result);return result
    def construct(self,factory,*,root=None,**kwargs):
        root=self.root() if root is None else root
        caught=None;returned=None
        try:
            with patch.object(product,'load_sqlite',lambda:factory):
                returned=product.SqliteJournal(root,self.codec,SCOPE,**kwargs)
        except BaseException as error:caught=error
        if returned is not None:self.returned.append(returned)
        return caught,returned
    def tearDown(self):
        for owner in self.returned:owner.close()
        receipts=[]
        for factory in self.factories:
            for connection in factory.connections:
                connection.recover_fixture()
                receipts.append({'close_calls':connection.close_calls,'native_close_calls':connection.native_close_calls,
                    'fixture_recovery_calls':connection.fixture_recovery_calls,
                    'native_known_closed':connection.native_known_closed})
        NATIVE_CONNECTION_RECEIPTS.append({'test_id':self.id(),'fixture_roots':[str(v) for v in self.roots],
            'connections':receipts,'all_fixture_native_connections_closed':all(v['native_known_closed'] for v in receipts),
            'qualification':'Real project SQLite connections; controlled Python response faults. Product uncertainty is not overwritten by the test recovery oracle.'})
    def custody(self,error,factory,state,closed):
        data=raw_dict(error);owner=data['journal_custody']
        self.assertIs(data['journal_connection'],factory.connections[-1] if factory.connections else None)
        self.assertIs(owner._connection,data['journal_connection'])
        self.assertEqual(data['journal_cleanup_state'],state);self.assertEqual(owner._constructor_close_state,state)
        self.assertIs(owner._closed,closed);self.assertTrue(owner._constructor_failed)
        try:owner.validate()
        except ContractError as denied:self.assertEqual(denied.code,'JOURNAL_CONSTRUCTION_FAILED')
        else:self.fail('failed constructor owner permitted journal use')
        return owner
    def assert_original_traceback(self,error,connection):
        current=traceback_of(error);found=False
        while current is not None:
            found|=current is connection.original_traceback;current=current.tb_next
        self.assertTrue(found,'original primary traceback tail was lost')

    def test_cleanup_failure_preserves_exact_primary_and_native_fixture_recovery(self):
        for control in (KeyboardInterrupt,SystemExit,MemoryError):
            for when in ('before','after'):
                with self.subTest(control=control.__name__,when=when):
                    primary=control('controlled constructor primary');secondary=OSError('controlled close response')
                    factory=self.factory([{'setup_primary':primary,'close_actions':[(when,secondary)]}])
                    caught,_=self.construct(factory)
                    self.assertIs(caught,primary);self.assertEqual(factory.connections[0].close_calls,1)
                    owner=self.custody(caught,factory,'UNCERTAIN',False)
                    self.assertIs(raw_dict(caught)['journal_cleanup_error'],secondary)
                    self.assert_original_traceback(caught,factory.connections[0])
                    try:owner.close()
                    except ContractError as denied:self.assertEqual(denied.code,'JOURNAL_CONSTRUCTOR_CLOSE_UNCERTAIN')
                    else:self.fail('uncertain constructor close was replayed')
                    self.assertEqual(factory.connections[0].close_calls,1)

    def test_readonly_switch_close_is_never_implicitly_replayed(self):
        for when in ('before','after'):
            with self.subTest(when=when):
                primary=KeyboardInterrupt('switch close');secondary=OSError('second close must never run')
                factory=self.factory([{'close_actions':[(when,primary),('before',secondary)]}])
                caught,_=self.construct(factory)
                self.assertIs(caught,primary);self.assertEqual(factory.connect_calls,1)
                self.assertEqual(factory.connections[0].close_calls,1)
                self.custody(caught,factory,'UNCERTAIN',False)
                self.assert_original_traceback(caught,factory.connections[0])

    def test_successful_cleanup_marks_known_closed_without_replacing_control(self):
        for control in (KeyboardInterrupt,SystemExit,MemoryError):
            with self.subTest(control=control.__name__):
                primary=control('setup');factory=self.factory([{'setup_primary':primary}])
                caught,_=self.construct(factory)
                self.assertIs(caught,primary);owner=self.custody(caught,factory,'CLOSED',True)
                self.assertIsNone(raw_dict(caught)['journal_cleanup_error'])
                self.assert_original_traceback(caught,factory.connections[0]);owner.close()
                self.assertEqual(factory.connections[0].close_calls,1)

    def test_initial_connect_failure_has_absent_connection_and_known_closed_owner(self):
        primary=KeyboardInterrupt('connect before connection exists')
        factory=self.factory(connect_primary=primary,fail_connect=1)
        caught,_=self.construct(factory)
        self.assertIs(caught,primary);self.assertEqual(factory.connections,[])
        self.custody(caught,factory,'ABSENT',True)

    def test_writer_connect_failure_does_not_reclose_known_closed_inspection(self):
        primary=SystemExit('writer connect');factory=self.factory([{}],connect_primary=primary,fail_connect=2)
        caught,_=self.construct(factory)
        self.assertIs(caught,primary);self.assertEqual(factory.connect_calls,2)
        self.assertEqual(factory.connections[0].close_calls,1)
        self.custody(caught,factory,'CLOSED',True)

    def test_writer_setup_failure_retains_exact_new_connection(self):
        primary=KeyboardInterrupt('writer config');secondary=OSError('writer close refusal')
        factory=self.factory([{}, {'setup_primary':primary,'close_actions':[('before',secondary)]}])
        caught,_=self.construct(factory)
        self.assertIs(caught,primary);self.assertEqual(len(factory.connections),2)
        self.assertTrue(factory.connections[0].native_known_closed)
        self.assertEqual(factory.connections[0].close_calls,1)
        self.custody(caught,factory,'UNCERTAIN',False)
        self.assertIs(raw_dict(caught)['journal_cleanup_error'],secondary)

    def test_malformed_cleanup_response_stays_uncertain_and_keeps_primary(self):
        for value in (False,True,0,'closed'):
            with self.subTest(return_type=type(value).__name__,value=value):
                primary=KeyboardInterrupt('setup');factory=self.factory([
                    {'setup_primary':primary,'close_actions':[('return',value)]}])
                caught,_=self.construct(factory)
                self.assertIs(caught,primary);self.custody(caught,factory,'UNCERTAIN',False)
                self.assertEqual(raw_dict(caught)['journal_cleanup_error'].code,'JOURNAL_CLOSE_RESULT_INVALID')
                self.assertEqual(factory.connections[0].close_calls,1)
                self.assertTrue(factory.connections[0].native_known_closed)

    def test_malformed_switch_close_response_never_opens_writer(self):
        for value in (False,True,0,'closed'):
            with self.subTest(return_type=type(value).__name__,value=value):
                factory=self.factory([{'close_actions':[('return',value)]}])
                caught,_=self.construct(factory)
                self.assertIsInstance(caught,ContractError);self.assertEqual(caught.code,'JOURNAL_CLOSE_RESULT_INVALID')
                self.assertEqual(factory.connect_calls,1);self.custody(caught,factory,'UNCERTAIN',False)

    def test_hostile_diagnostic_setters_and_note_getters_are_not_invoked(self):
        hits=[]
        class Primary(KeyboardInterrupt):
            def __setattr__(self,name,value):hits.append(name);raise OSError('diagnostic setter refused')
            @property
            def add_note(self):hits.append('add_note');raise OSError('diagnostic note refused')
        primary=Primary('original');secondary=OSError('cleanup')
        factory=self.factory([{'setup_primary':primary,'close_actions':[('before',secondary)]}])
        caught,_=self.construct(factory)
        self.assertIs(caught,primary);self.custody(caught,factory,'UNCERTAIN',False)
        self.assertIs(raw_dict(caught)['journal_cleanup_error'],secondary);self.assertEqual(hits,[])

    def test_parallel_explicit_close_cannot_replay_uncertain_constructor_close(self):
        primary=KeyboardInterrupt('setup');factory=self.factory([
            {'setup_primary':primary,'close_actions':[('after',OSError('response lost'))]}])
        caught,_=self.construct(factory);self.assertIs(caught,primary)
        owner=self.custody(caught,factory,'UNCERTAIN',False)
        def attempt(_):
            try:owner.close()
            except ContractError as denied:return denied.code
            return 'unexpected success'
        with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(attempt,range(16)))
        self.assertEqual(results,['JOURNAL_CONSTRUCTOR_CLOSE_UNCERTAIN']*16)
        self.assertEqual(factory.connections[0].close_calls,1)

    def test_create_and_reopen_preserve_both_canonical_profiles(self):
        for profile in ('ceta-sqlite-journal-v1',STORE_PROFILE):
            with self.subTest(profile=profile):
                root=self.root(existing=False);factory=self.factory()
                error,owner=self.construct(factory,root=root,create=True,profile=profile)
                self.assertIsNone(error);self.assertFalse(owner._constructor_failed);self.assertFalse(owner._closed)
                owner.validate();owner.close()
                error,reopened=self.construct(factory,root=root,profile=profile)
                self.assertIsNone(error);reopened.validate();reopened.close()

    def test_readonly_constructor_has_one_connection_and_retains_readonly_denial(self):
        factory=self.factory();error,owner=self.construct(factory,read_only=True)
        self.assertIsNone(error);self.assertEqual(factory.connect_calls,1)
        owner.validate();self.assertTrue(owner.storage_identity()['read_only']);owner.close()
        self.assertEqual(factory.connections[0].close_calls,1)

    def test_real_default_close_response_is_exact_none(self):
        root=self.root();connection=self.sqlite.connect((root/'history.sqlite3').as_uri()+'?mode=ro',uri=True)
        self.assertIsNone(connection.close())


if __name__=='__main__':unittest.main(verbosity=2)
