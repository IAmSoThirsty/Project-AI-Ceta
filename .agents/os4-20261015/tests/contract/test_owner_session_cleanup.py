"""Actual owner methods with controlled sessions and no native allocations."""
from contextlib import contextmanager
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from ceta.identity import owner_session as module

MESSAGE='Native enrollment-session custody remains available for explicit retirement.'
raw=lambda error:BaseException.__dict__['__dict__'].__get__(error)

class OwnerSessionCleanupTests(unittest.TestCase):
    def primary(self):
        hits=[]
        class Storage(dict):
            def update(self,*args,**kwargs):hits.append('update');raise OSError('dictionary override')
            def __getitem__(self,key):hits.append('getitem');raise OSError('dictionary override')
            def __setitem__(self,key,value):hits.append('setitem');raise OSError('dictionary override')
            def __contains__(self,key):hits.append('contains');raise OSError('dictionary override')
        primary=KeyboardInterrupt('original')
        BaseException.__dict__['__dict__'].__set__(primary,Storage())
        return primary,hits
    def owner(self,cleanup):
        calls=[]
        class Session:
            _enrollment=False
            def close(self):calls.append('close');raise cleanup
        owner=object.__new__(module.NativeCpuOwnerSession)
        owner._effect=SimpleNamespace(active=True);owner._effect_lease=owner._effect_proof=None
        owner._approval=SimpleNamespace(_active=Session())
        return owner,calls
    @contextmanager
    def dispatch(self,owner):
        @contextmanager
        def controlled_base(self,context):yield self
        with patch.object(module.NativeOwnerSession,'native_context',controlled_base):
            with owner.native_context(object()):yield owner
    def caught(self,action):
        try:action()
        except BaseException as error:return error
        self.fail('expected original exception')
    def body(self,owner,primary):
        with self.dispatch(owner):raise primary

    def test_exact_helper_preserves_primary_despite_dictionary_override(self):
        primary,hits=self.primary();owner,_=self.owner(OSError('cleanup'))
        module._expose(primary,owner)
        self.assertIs(dict.__getitem__(raw(primary),'native_owner_session'),owner)
        self.assertEqual(hits,[])

    def test_exact_context_preserves_primary_despite_dictionary_override(self):
        primary,hits=self.primary();cleanup=OSError('close');owner,calls=self.owner(cleanup)
        self.assertIs(self.caught(lambda:self.body(owner,primary)),primary)
        self.assertIs(dict.__getitem__(raw(primary),'native_owner_session_cleanup_error'),cleanup)
        self.assertEqual(hits,[]);self.assertEqual(calls,['close'])
        self.assertIsNone(owner._effect);self.assertIsNone(owner._effect_proof)

    def test_exact_context_retains_primary_and_session_cleanup_secondary(self):
        primary=KeyboardInterrupt('body');cleanup=SystemExit('close');owner,calls=self.owner(cleanup)
        self.assertIs(self.caught(lambda:self.body(owner,primary)),primary)
        self.assertIs(raw(primary)['native_owner_session_cleanup_error'],cleanup)
        self.assertIs(raw(primary)['native_owner_session'],owner)
        self.assertIs(raw(primary)['close_cleanup'].__self__,owner);self.assertEqual(calls,['close'])

    def test_cleanup_only_failure_remains_exact_primary_with_custody(self):
        cleanup,hits=self.primary();owner,calls=self.owner(cleanup)
        def action():
            with self.dispatch(owner):pass
        self.assertIs(self.caught(action),cleanup)
        self.assertIs(dict.__getitem__(raw(cleanup),'native_owner_session'),owner)
        self.assertFalse(dict.__contains__(raw(cleanup),'native_owner_session_cleanup_error'))
        self.assertEqual(calls,['close']);self.assertEqual(hits,[])

    def test_unknown_note_container_is_preserved_without_callbacks(self):
        hits=[]
        class Notes(list):
            def __iter__(self):hits.append('iterate');raise OSError('notes')
            def append(self,value):hits.append('append');raise OSError('notes')
        primary=KeyboardInterrupt('body');notes=Notes(['old']);raw(primary)['__notes__']=notes
        owner,_=self.owner(OSError('close'));module._expose(primary,owner)
        self.assertIs(raw(primary)['__notes__'],notes);self.assertEqual(hits,[])

    def test_diagnostic_getters_setters_and_add_note_are_never_invoked(self):
        hits=[]
        class Primary(KeyboardInterrupt):
            @property
            def add_note(self):hits.append('note');raise OSError('note')
            @property
            def __notes__(self):hits.append('notes');raise OSError('notes')
            def __setattr__(self,name,value):hits.append('setter');raise OSError('setter')
        primary=Primary('body');owner,_=self.owner(OSError('close'))
        module._expose(primary,owner)
        self.assertEqual(raw(primary)['__notes__'],[MESSAGE]);self.assertEqual(hits,[])

    def test_inherited_close_preserves_primary_with_hostile_dictionary(self):
        primary,hits=self.primary();owner,_=self.owner(OSError('close'))
        def refuse():raise primary
        owner.request_stop=refuse
        self.assertIs(self.caught(owner.close),primary)
        self.assertIs(dict.__getitem__(raw(primary),'native_owner_session'),owner)
        self.assertEqual(hits,[])

    def test_existing_plain_notes_keep_values_and_append_established_text(self):
        primary=KeyboardInterrupt('body');notes=['earlier'];raw(primary)['__notes__']=notes
        owner,_=self.owner(OSError('close'));module._expose(primary,owner)
        self.assertIs(raw(primary)['__notes__'],notes)
        self.assertEqual(notes,['earlier',MESSAGE])
