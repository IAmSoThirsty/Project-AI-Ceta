"""Real canonical SQLite with labelled post-construction response/getter faults."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sys
import unittest
import uuid
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from ceta.contracts.events import StreamPosition
from ceta.contracts.store_transactions import STORE_PROFILE,StoreKey
from ceta.contracts.wire import ContractError
from ceta.store import journal as product
from test_history import codec,entry
from test_journal_constructor_cleanup import ConnectionProxy,SQLiteFactory,original_raise,raw_dict,traceback_of

SCOPE='project:fixture'
NATIVE_RECEIPTS=[]


class PostProxy(ConnectionProxy):
    def __init__(self,real,**kwargs):
        super().__init__(real,**kwargs)
        self.getter_error=None;self.getter_value=None;self.use_getter_value=False
        self.sql_actions={};self.sql_calls=[];self.getter_calls=0
    @property
    def in_transaction(self):
        self.getter_calls+=1
        if self.getter_error is not None:original_raise(self.getter_error,self)
        return self.getter_value if self.use_getter_value else self.real.in_transaction
    def execute(self,sql,*args):
        self.sql_calls.append(sql)
        action=self.sql_actions.pop(sql,None)
        if action is not None and action[0]=='before':original_raise(action[1],self)
        result=self.real.execute(sql,*args)
        if action is not None:
            if action[0]=='after':original_raise(action[1],self)
            if action[0]=='return':return action[1]
        return result


class PostConstructionCleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.codec=codec()
    def setUp(self):self.resources=[]
    def opened(self,*,profile='ceta-sqlite-journal-v1',close_actions=()):
        root=ROOT/'.agents/fixtures/journal-postconstruct'/uuid.uuid4().hex
        root.mkdir(parents=True,exist_ok=False)
        owner=product.SqliteJournal(root,self.codec,(SCOPE,),create=True,profile=profile)
        proxy=PostProxy(owner._connection,close_actions=close_actions)
        owner._connection=proxy
        if owner._state is not None:owner._state.connection=proxy
        self.resources.append((root,owner,proxy))
        return owner,proxy
    def tearDown(self):
        rows=[]
        for root,owner,proxy in self.resources:
            # Only this fixture knows whether a controlled native call ran.
            # Never replay owner.close() or overwrite its uncertainty record.
            proxy.recover_fixture()
            rows.append({'root':str(root),'close_calls':proxy.close_calls,'native_close_calls':proxy.native_close_calls,
                'fixture_recovery_calls':proxy.fixture_recovery_calls,'native_known_closed':proxy.native_known_closed,
                'transaction_statements':list(proxy.sql_calls),'product_closed':owner._closed,
                'product_close_state':getattr(owner,'_connection_close_state','ABSENT_IN_BASELINE'),
                'product_transaction_state':getattr(owner,'_transaction_cleanup_state','ABSENT_IN_BASELINE')})
        NATIVE_RECEIPTS.append({'test_id':self.id(),'resources':rows,'all_exact_native_connections_closed':all(row['native_known_closed'] for row in rows),
            'qualification':'Actual project SQLite connections, explicitly controlled Python response/getter faults. Not evidence of a native SQLite leak or live authority.'})
    def caught(self,action):
        try:action()
        except BaseException as error:return error
        self.fail('expected exact controlled primary')
    def assert_traceback(self,error,proxy):
        current=traceback_of(error)
        while current is not None:
            if current is proxy.original_traceback:return
            current=current.tb_next
        self.fail('original primary traceback tail lost')
    def assert_owner(self,error,owner,proxy):
        self.assertIs(raw_dict(error)['journal_custody'],owner)
        self.assertIs(raw_dict(error)['journal_connection'],proxy)
    def broken_verification(self,owner,proxy,primary):
        def verify(*args,**kwargs):original_raise(primary,proxy)
        owner._verify=verify
    def operation(self,owner,name):
        point=StreamPosition(SCOPE,0,None)
        values={'validate':lambda:owner.validate(),'append':lambda:owner.append(point,(entry(self.codec,point,'post-append'),)),
            'commit':lambda:owner.commit((point,),(entry(self.codec,point,'post-commit'),)),
            'snapshot':lambda:owner.snapshot((StoreKey('queue',SCOPE,'queue:post'),)),
            'store_position':lambda:owner.store_position(),'replay':lambda:owner.replay(SCOPE),
            'projection':lambda:owner.projection(SCOPE)}
        return values[name]

    def hostile_dictionary_primary(self):
        hits=[]
        def refuse(name):hits.append(name);raise OSError('controlled exception dictionary callback')
        class Storage(dict):
            def update(self,*args,**kwargs):refuse('update')
            def get(self,*args):refuse('get')
            def __getitem__(self,key):refuse('getitem')
            def __setitem__(self,key,value):refuse('setitem')
            def __contains__(self,key):refuse('contains')
        primary=KeyboardInterrupt('hostile exception dictionary')
        BaseException.__dict__['__dict__'].__set__(primary,Storage())
        return primary,hits

    def test_close_failure_never_replays_and_retains_exact_custody(self):
        for kind in (KeyboardInterrupt,SystemExit):
            for when in ('before','after'):
                with self.subTest(primary=kind.__name__,when=when):
                    primary=kind('controlled close primary')
                    owner,proxy=self.opened(close_actions=[(when,primary)])
                    caught=self.caught(owner.close);self.assertIs(caught,primary)
                    second=self.caught(owner.close)
                    self.assertEqual(proxy.close_calls,1,'uncertain native close was replayed')
                    self.assertIsInstance(second,ContractError);self.assertEqual(second.code,'JOURNAL_CLOSE_UNCERTAIN')
                    self.assertFalse(owner._closed);self.assert_owner(caught,owner,proxy)
                    self.assertEqual(raw_dict(caught)['journal_close_state'],'UNCERTAIN');self.assert_traceback(caught,proxy)

    def test_validation_getter_failure_never_replaces_original_primary(self):
        for kind in (KeyboardInterrupt,SystemExit):
            with self.subTest(primary=kind.__name__):
                owner,proxy=self.opened();primary=kind('verification');secondary=OSError('transaction getter')
                self.broken_verification(owner,proxy,primary);proxy.getter_error=secondary
                caught=self.caught(owner.validate);self.assertIs(caught,primary);self.assert_owner(caught,owner,proxy)
                self.assertIs(raw_dict(caught)['journal_rollback_error'],secondary)
                self.assertEqual(raw_dict(caught)['journal_transaction_state'],'UNCERTAIN')
                self.assert_traceback(caught,proxy);self.assertNotIn('ROLLBACK',proxy.sql_calls)

    def test_rollback_response_loss_poison_preserves_one_legitimate_close(self):
        owner,proxy=self.opened();primary=KeyboardInterrupt('verification');secondary=OSError('after native rollback')
        self.broken_verification(owner,proxy,primary);proxy.sql_actions['ROLLBACK']=('after',secondary)
        caught=self.caught(owner.validate);self.assertIs(caught,primary)
        self.assertFalse(proxy.real.in_transaction);self.assertEqual(proxy.sql_calls.count('ROLLBACK'),1)
        self.assertIs(raw_dict(caught)['journal_rollback_error'],secondary)
        denied=self.caught(owner.validate);self.assertEqual(denied.code,'JOURNAL_TRANSACTION_CLEANUP_UNCERTAIN')
        owner.close();owner.close();self.assertTrue(owner._closed);self.assertEqual(proxy.close_calls,1)
        self.assertEqual(owner._transaction_cleanup_state,'UNCERTAIN')

    def test_successful_close_remains_exact_none_and_idempotent(self):
        for profile in ('ceta-sqlite-journal-v1',STORE_PROFILE):
            with self.subTest(profile=profile):
                owner,proxy=self.opened(profile=profile)
                self.assertIsNone(owner.close());self.assertIsNone(owner.close())
                self.assertEqual(proxy.close_calls,1);self.assertTrue(owner._closed)
                self.assertEqual(owner._connection_close_state,'CLOSED')

    def test_malformed_close_response_stays_uncertain_without_replay(self):
        for value in (False,True,0,'closed'):
            with self.subTest(response=value):
                owner,proxy=self.opened(close_actions=[('return',value)])
                caught=self.caught(owner.close);self.assertEqual(caught.code,'JOURNAL_CLOSE_RESULT_INVALID')
                self.assertFalse(owner._closed);self.assertTrue(proxy.native_known_closed)
                self.assert_owner(caught,owner,proxy)
                denied=self.caught(owner.close);self.assertEqual(denied.code,'JOURNAL_CLOSE_UNCERTAIN')
                self.assertEqual(proxy.close_calls,1)

    def test_close_method_lookup_failure_is_single_attempt_uncertainty(self):
        owner,proxy=self.opened();primary=KeyboardInterrupt('controlled close getter')
        class LookupProxy(PostProxy):
            @property
            def close(self):original_raise(primary,self)
        replacement=LookupProxy(proxy.real);owner._connection=replacement
        self.resources[-1]=(self.resources[-1][0],owner,replacement)
        caught=self.caught(owner.close);self.assertIs(caught,primary);self.assert_owner(caught,owner,replacement)
        self.assertEqual(self.caught(owner.close).code,'JOURNAL_CLOSE_UNCERTAIN')
        self.assertFalse(owner._closed);self.assertEqual(replacement.close_calls,0)

    def test_all_seven_transaction_paths_preserve_getter_secondary_and_custody(self):
        for name in ('validate','append','commit','snapshot','store_position','replay','projection'):
            with self.subTest(operation=name):
                owner,proxy=self.opened(profile=STORE_PROFILE if name in ('commit','snapshot','store_position') else 'ceta-sqlite-journal-v1')
                primary=KeyboardInterrupt(name);secondary=OSError('controlled getter')
                self.broken_verification(owner,proxy,primary);proxy.getter_error=secondary
                caught=self.caught(self.operation(owner,name));self.assertIs(caught,primary)
                self.assert_owner(caught,owner,proxy);self.assertIs(raw_dict(caught)['journal_rollback_error'],secondary)
                self.assertEqual(owner._transaction_cleanup_state,'UNCERTAIN');self.assert_traceback(caught,proxy)
                self.assertFalse(owner._closed);owner.close();self.assertEqual(proxy.close_calls,1)

    def test_rollback_refusal_before_native_preserves_primary_and_does_not_retry(self):
        owner,proxy=self.opened();primary=SystemExit('verify');secondary=KeyboardInterrupt('rollback before native')
        self.broken_verification(owner,proxy,primary);proxy.sql_actions['ROLLBACK']=('before',secondary)
        caught=self.caught(owner.validate);self.assertIs(caught,primary);self.assertTrue(proxy.real.in_transaction)
        self.assertIs(raw_dict(caught)['journal_rollback_error'],secondary)
        for action in (owner.validate,lambda:owner.replay(SCOPE),owner.storage_identity):
            self.assertEqual(self.caught(action).code,'JOURNAL_TRANSACTION_CLEANUP_UNCERTAIN')
        self.assertEqual(proxy.sql_calls.count('ROLLBACK'),1);owner.close()

    def test_successful_rollback_keeps_journal_usable_and_primary_exact(self):
        owner,proxy=self.opened();original=owner._verify;primary=KeyboardInterrupt('verify')
        self.broken_verification(owner,proxy,primary)
        caught=self.caught(owner.validate);self.assertIs(caught,primary)
        self.assertIsNone(raw_dict(caught)['journal_rollback_error']);self.assertEqual(owner._transaction_cleanup_state,'READY')
        self.assertFalse(proxy.real.in_transaction);owner._verify=original
        point=owner.position(SCOPE);owner.append(point,(entry(self.codec,point,'after-rollback'),))
        self.assertEqual(owner.position(SCOPE).next_sequence,1);owner.close()

    def test_malformed_in_transaction_values_do_not_confer_recovery(self):
        for value in (0,1,None,'no',object()):
            with self.subTest(value_type=type(value).__name__):
                owner,proxy=self.opened();primary=KeyboardInterrupt('verify')
                self.broken_verification(owner,proxy,primary);proxy.use_getter_value=True;proxy.getter_value=value
                caught=self.caught(owner.validate);self.assertIs(caught,primary)
                self.assertEqual(raw_dict(caught)['journal_rollback_error'].code,'JOURNAL_TRANSACTION_STATE_INVALID')
                self.assertNotIn('ROLLBACK',proxy.sql_calls);self.assertEqual(owner._transaction_cleanup_state,'UNCERTAIN')
                owner.close()

    def test_rollback_return_or_postcheck_failure_remains_uncertain(self):
        for value in (None,False,True,0):
            with self.subTest(response=value):
                owner,proxy=self.opened();primary=SystemExit('verify')
                self.broken_verification(owner,proxy,primary);proxy.sql_actions['ROLLBACK']=('return',value)
                caught=self.caught(owner.validate);self.assertIs(caught,primary)
                self.assertEqual(raw_dict(caught)['journal_rollback_error'].code,'JOURNAL_ROLLBACK_RESULT_INVALID')
                self.assertFalse(proxy.real.in_transaction);self.assertEqual(owner._transaction_cleanup_state,'UNCERTAIN')
                owner.close()

    def test_rollback_postcheck_getter_failure_keeps_native_disposition_distinct(self):
        owner,proxy=self.opened();primary=KeyboardInterrupt('verify');secondary=OSError('after rollback observation')
        self.broken_verification(owner,proxy,primary);real_execute=proxy.execute
        def execute(sql,*args):
            result=real_execute(sql,*args)
            if sql=='ROLLBACK':proxy.getter_error=secondary
            return result
        proxy.execute=execute
        caught=self.caught(owner.validate);self.assertIs(caught,primary)
        self.assertFalse(proxy.real.in_transaction);self.assertIs(raw_dict(caught)['journal_rollback_error'],secondary)
        self.assertEqual(owner._transaction_cleanup_state,'UNCERTAIN');owner.close()

    def test_begin_response_loss_is_caught_and_rolled_back_once(self):
        owner,proxy=self.opened();primary=KeyboardInterrupt('after native BEGIN')
        proxy.sql_actions['BEGIN']=('after',primary)
        caught=self.caught(owner.validate);self.assertIs(caught,primary);self.assert_owner(caught,owner,proxy)
        self.assertEqual(proxy.sql_calls.count('ROLLBACK'),1);self.assertFalse(proxy.real.in_transaction)
        self.assertEqual(owner._transaction_cleanup_state,'READY');owner.validate();owner.close()

    def test_begin_refusal_with_no_native_transaction_does_not_issue_rollback(self):
        owner,proxy=self.opened();primary=SystemExit('before native BEGIN')
        proxy.sql_actions['BEGIN']=('before',primary)
        caught=self.caught(owner.validate);self.assertIs(caught,primary)
        self.assertNotIn('ROLLBACK',proxy.sql_calls);self.assertFalse(proxy.real.in_transaction)
        self.assertEqual(owner._transaction_cleanup_state,'READY');owner.validate();owner.close()

    def test_commit_response_loss_never_replays_commit_and_reconciles_actual_history(self):
        owner,proxy=self.opened();point=owner.position(SCOPE);primary=KeyboardInterrupt('after native COMMIT')
        proxy.sql_actions['COMMIT']=('after',primary)
        caught=self.caught(lambda:owner.append(point,(entry(self.codec,point,'committed-response-loss'),)))
        self.assertIs(caught,primary);self.assertEqual(owner._transaction_cleanup_state,'READY')
        self.assertNotIn('ROLLBACK',proxy.sql_calls);self.assertEqual(owner.position(SCOPE).next_sequence,1)
        self.assertEqual(len(owner.replay(SCOPE)),1);owner.close()

    def test_concurrent_close_invokes_native_exactly_once_after_refusal(self):
        primary=KeyboardInterrupt('controlled refusal');owner,proxy=self.opened(close_actions=[('before',primary)])
        def attempt(_):return self.caught(owner.close)
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(attempt,range(24)))
        self.assertEqual(sum(error is primary for error in results),1)
        self.assertEqual(sum(isinstance(error,ContractError) and error.code=='JOURNAL_CLOSE_UNCERTAIN' for error in results),23)
        self.assertEqual(proxy.close_calls,1);self.assertFalse(owner._closed)

    def test_hostile_primary_diagnostic_setters_are_not_called(self):
        hits=[]
        class Primary(KeyboardInterrupt):
            def __setattr__(self,name,value):hits.append(name);raise OSError('setter')
            @property
            def add_note(self):hits.append('add_note');raise OSError('note')
        owner,proxy=self.opened();primary=Primary('verify');secondary=SystemExit('rollback')
        self.broken_verification(owner,proxy,primary);proxy.sql_actions['ROLLBACK']=('before',secondary)
        caught=self.caught(owner.validate);self.assertIs(caught,primary);self.assert_owner(caught,owner,proxy)
        self.assertIs(raw_dict(caught)['journal_rollback_error'],secondary);self.assertEqual(hits,[]);owner.close()

    def test_transaction_uncertainty_and_close_uncertainty_remain_separate(self):
        owner,proxy=self.opened(close_actions=[('after',SystemExit('close response'))])
        primary=KeyboardInterrupt('verify');secondary=OSError('transaction getter')
        self.broken_verification(owner,proxy,primary);proxy.getter_error=secondary
        self.assertIs(self.caught(owner.validate),primary)
        close_primary=self.caught(owner.close);self.assertIsInstance(close_primary,SystemExit)
        self.assertIs(raw_dict(primary)['journal_rollback_error'],secondary)
        self.assertIs(raw_dict(close_primary)['journal_rollback_error'],secondary)
        self.assertEqual(owner._transaction_cleanup_state,'UNCERTAIN');self.assertEqual(owner._connection_close_state,'UNCERTAIN')
        self.assertEqual(self.caught(owner.close).code,'JOURNAL_CLOSE_UNCERTAIN');self.assertEqual(proxy.close_calls,1)

    def test_reopen_after_explicit_retirement_recovers_without_effect_replay(self):
        owner,proxy=self.opened();primary=KeyboardInterrupt('verify');secondary=OSError('rollback refusal')
        self.broken_verification(owner,proxy,primary);proxy.sql_actions['ROLLBACK']=('before',secondary)
        self.assertIs(self.caught(owner.validate),primary);owner.close()
        reopened=product.SqliteJournal(owner.path.parent,self.codec,(SCOPE,))
        try:self.assertEqual(reopened.position(SCOPE).next_sequence,0);self.assertEqual(reopened.replay(SCOPE),())
        finally:reopened.close()

    def test_projection_diagnostic_uses_only_trusted_exception_storage(self):
        hits=[]
        class Primary(KeyboardInterrupt):
            def __setattr__(self,name,value):hits.append(name);raise OSError('setter')
            @property
            def add_note(self):hits.append('add_note');raise OSError('note')
            @property
            def __notes__(self):hits.append('__notes__');raise OSError('notes getter')
        owner,proxy=self.opened();primary=Primary('projection');secondary=OSError('rollback')
        self.broken_verification(owner,proxy,primary);proxy.sql_actions['ROLLBACK']=('before',secondary)
        caught=self.caught(lambda:owner.projection(SCOPE));self.assertIs(caught,primary)
        self.assertIn('JOURNAL_PROJECTION_ROLLBACK_UNOBSERVED',raw_dict(caught)['__notes__'])
        self.assertIs(raw_dict(caught)['journal_rollback_error'],secondary);self.assertEqual(hits,[]);owner.close()

    def test_projection_unknown_note_container_is_preserved_without_callbacks(self):
        hits=[]
        class HostileNotes(list):
            def append(self,value):hits.append('append');raise OSError('append')
            def __iter__(self):hits.append('iterate');raise OSError('iterate')
        owner,proxy=self.opened();primary=KeyboardInterrupt('projection');secondary=OSError('rollback')
        notes=HostileNotes(['original']);raw_dict(primary)['__notes__']=notes
        self.broken_verification(owner,proxy,primary);proxy.sql_actions['ROLLBACK']=('before',secondary)
        caught=self.caught(lambda:owner.projection(SCOPE));self.assertIs(caught,primary)
        self.assertIs(raw_dict(caught)['__notes__'],notes);self.assertEqual(hits,[])
        self.assertIs(raw_dict(caught)['journal_rollback_error'],secondary);owner.close()

    def test_close_retention_bypasses_hostile_dictionary_methods(self):
        primary,hits=self.hostile_dictionary_primary()
        owner,proxy=self.opened(close_actions=[('before',primary)])
        self.assertIs(self.caught(owner.close),primary)
        self.assertIs(dict.__getitem__(raw_dict(primary),'journal_custody'),owner)
        self.assertEqual(hits,[]);self.assertEqual(proxy.close_calls,1)

    def test_rollback_retention_bypasses_hostile_dictionary_methods(self):
        primary,hits=self.hostile_dictionary_primary();owner,proxy=self.opened();secondary=OSError('rollback')
        self.broken_verification(owner,proxy,primary);proxy.sql_actions['ROLLBACK']=('before',secondary)
        self.assertIs(self.caught(owner.validate),primary)
        self.assertIs(dict.__getitem__(raw_dict(primary),'journal_rollback_error'),secondary)
        self.assertEqual(hits,[]);owner.close()

    def test_projection_note_bypasses_hostile_dictionary_methods(self):
        primary,hits=self.hostile_dictionary_primary();owner,proxy=self.opened();secondary=OSError('rollback')
        self.broken_verification(owner,proxy,primary);proxy.sql_actions['ROLLBACK']=('before',secondary)
        self.assertIs(self.caught(lambda:owner.projection(SCOPE)),primary)
        self.assertIn('JOURNAL_PROJECTION_ROLLBACK_UNOBSERVED',dict.__getitem__(raw_dict(primary),'__notes__'))
        self.assertEqual(hits,[]);owner.close()

    def test_constructor_retention_keeps_JC1_contract_with_hostile_dictionary(self):
        primary,hits=self.hostile_dictionary_primary();secondary=OSError('constructor close refusal')
        sqlite=product.load_sqlite();factory=SQLiteFactory(sqlite,[{'setup_primary':primary,'close_actions':[('before',secondary)]}])
        root=ROOT/'.agents/fixtures/journal-postconstruct'/uuid.uuid4().hex;root.mkdir(parents=True,exist_ok=False)
        try:
            with patch.object(product,'load_sqlite',lambda:factory):
                caught=self.caught(lambda:product.SqliteJournal(root,self.codec,(SCOPE,),create=True))
            self.assertIs(caught,primary)
            self.assertIs(dict.__getitem__(raw_dict(primary),'journal_cleanup_error'),secondary)
            self.assertIs(dict.__getitem__(raw_dict(primary),'journal_connection'),factory.connections[0])
            self.assertEqual(factory.connections[0].close_calls,1);self.assertEqual(hits,[])
        finally:
            for connection in factory.connections:connection.recover_fixture()
            NATIVE_RECEIPTS.append({'test_id':self.id(),'resources':[{'root':str(root),'native_known_closed':c.native_known_closed,
                'close_calls':c.close_calls,'native_close_calls':c.native_close_calls,'fixture_recovery_calls':c.fixture_recovery_calls} for c in factory.connections],
                'all_exact_native_connections_closed':all(c.native_known_closed for c in factory.connections),
                'qualification':'Real constructor connection with controlled diagnostic dictionary/close faults; no native leak claim.'})


if __name__=='__main__':unittest.main(verbosity=2)
