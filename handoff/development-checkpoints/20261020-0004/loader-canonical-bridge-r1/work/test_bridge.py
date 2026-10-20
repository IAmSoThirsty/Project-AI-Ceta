"""Guarded DATA controls; synthetic approvals are never execution evidence."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import ast
import json
import unittest

import capture_bridge as b
import native_port as n


def ref(name, pin='a' * 64):
    return dict(repository_relative_path='test-controlled-only/' + name, sha256=pin)


def records():
    now = 1000_000_000_000
    request = dict(schema_version=1, kind=b.KIND, repository=str(b.F), executor='/root', nonce='a' * 32,
        issued_at_ns=now - 1, expires_at_ns=now + 600_000_000_000,
        bridge_freeze=ref('bridge'), loader_freeze=ref('loader', 'b' * 64),
        symbol_supplement=ref('symbols', 'c' * 64), symbol_review=ref('symbol-review'),
        source_review=ref('source-review'), action_review=ref('action-review'), owner_grant=ref('owner'),
        lease=dict(control_root='.agents/runtime/CONTROLLED-ONLY', run_id='data-control', node_id='implement',
                   executor_id='/root', input_hash='d' * 64, claimed_at='CONTROLLED-NOT-ACTUAL', workspace=str(b.W)),
        limits=dict(seconds=15.0, events=1024, debug_bytes=1048576, per_debug_string=16384, stdio_bytes=1048576),
        filesystem_scopes=b.required_scopes('a' * 32))
    grant = dict(kind='CETA_CANONICAL_LOADER_BRIDGE_OWNER_GRANT_V1', source='actual_current_human_reply',
        protected_effects_authorized=True, automatic_retry=False, bind_fresh_runtime_ids=True,
        request_binding={k:v for k,v in request.items() if k != 'owner_grant'}, effects=list(b.EFFECTS),
        human_message_reference=ref('CONTROLLED-NOT-ACTUAL-HUMAN'), verbatim_human_reply='CONTROLLED DATA ONLY',
        old_approval_reused=False, profile_name='CETA.ProjectAICETA.IsolatedWorker.AC1.V1')
    human = dict(kind='CETA_ACTUAL_HUMAN_MESSAGE_V1', source='actual_current_human_reply',
                 text='CONTROLLED DATA ONLY', message_id='CONTROLLED-NOT-ACTUAL', recorded_at='CONTROLLED')
    action = dict(decision='approve', exit_status=0, executor_id='/root', result=dict(
        bridge_freeze=request['bridge_freeze'], loader_freeze=request['loader_freeze'],
        source_review=request['source_review'], symbol_review=request['symbol_review'],
        loader_snaps_input_reference=request['symbol_supplement'], scope='ONE_FRESH_CANONICAL_FIXTURE_OWNED_CAPTURE'))
    source = dict(schema_version=1, decision='approved', exit_status=0, executor_id='/root/admission',
                  result=dict(freeze=dict(request['loader_freeze'], path='CONTROLLED')))
    symbols = dict(schema_version=1, decision='approved', exit_status=0, executor_id='/root',
                   result=dict(artifact=request['symbol_supplement']))
    return request, grant, human, action, source, symbols, now


class Authorization(unittest.TestCase):
    def reject(self, records_, text):
        with self.assertRaisesRegex(b.BridgeError, text):
            b.validate_authorizations(*records_)

    def test_controlled_complete_data_contract(self):
        rows = records()
        binding = b.validate_authorizations(*rows)
        self.assertNotIn('owner_grant', binding)
        self.assertEqual(binding['nonce'], 'a' * 32)

    def test_absent_human_grant(self):
        rows = list(records()); rows[1] = {}
        self.reject(rows, 'FRESH_EXPLICIT_HUMAN_GRANT')

    def test_expired(self):
        rows = list(records()); rows[-1] = rows[0]['expires_at_ns']
        self.reject(rows, 'EXPIRED')

    def test_insufficient_cleanup_time(self):
        rows = list(records()); rows[-1] = rows[0]['expires_at_ns'] - 149_000_000_000
        self.reject(rows, 'INSUFFICIENT_LIFETIME')

    def test_unbounded_expiry(self):
        rows = list(records()); rows[0]['expires_at_ns'] += 1800_000_000_000
        self.reject(rows, 'EXPIRED_OR_INSUFFICIENT')

    def test_bool_timestamp_is_not_integer(self):
        rows = list(records()); rows[0]['issued_at_ns'] = True
        self.reject(rows, 'EXPIRED_OR_INSUFFICIENT')

    def test_mutated_nonce(self):
        rows = list(records()); rows[0]['nonce'] = 'z' * 32
        self.reject(rows, 'NONCE_INVALID')

    def test_old_approval_refused(self):
        rows = list(records()); rows[1]['old_approval_reused'] = True
        self.reject(rows, 'OLD_GRANT_REFUSED')

    def test_dynamic_ids_need_explicit_delegation(self):
        rows = list(records()); rows[1]['bind_fresh_runtime_ids'] = False
        self.reject(rows, 'FRESH_EXPLICIT_HUMAN_GRANT')

    def test_new_effect_is_not_authorized(self):
        rows = list(records()); rows[1]['effects'].append('attach_existing_process')
        self.reject(rows, 'EFFECT_OR_INPUT_MISMATCH')

    def test_foreign_repository(self):
        rows = list(records()); rows[0]['repository'] = 'T:/some-other-repository'
        self.reject(rows, 'REPOSITORY_OR_EXECUTOR')

    def test_human_text_not_reinterpreted(self):
        rows = list(records()); rows[2]['text'] += ' CHANGED'
        self.reject(rows, 'HUMAN_PROVENANCE')

    def test_missing_human_identifier(self):
        rows = list(records()); del rows[2]['message_id']
        self.reject(rows, 'HUMAN_PROVENANCE')

    def test_wrong_profile(self):
        rows = list(records()); rows[1]['profile_name'] = 'a-live-profile'
        self.reject(rows, 'PROFILE_OR_OLD')

    def test_self_review_rejected(self):
        rows = list(records()); rows[3]['executor_id'] = '/root/review'
        self.reject(rows, 'ACTION_REVIEW_REQUIRED')

    def test_loader_author_cannot_self_review(self):
        rows = list(records()); rows[4]['executor_id'] = '/root/implement'
        self.reject(rows, 'INDEPENDENT_REVIEW')

    def test_wrong_exact_source_hash(self):
        rows = list(records()); rows[4]['result'] = dict(freeze=ref('other', 'd' * 64))
        self.reject(rows, 'REVIEW_BINDING_MISMATCH')

    def test_v1_cannot_replace_approved_v2_reference(self):
        rows = list(records()); rows[5]['result'] = dict(artifact=ref('historical-v1', 'f' * 64))
        self.reject(rows, 'REVIEW_BINDING_MISMATCH')

    def test_extra_request_field_rejected(self):
        rows = list(records()); rows[0]['allow_fallback'] = True
        self.reject(rows, 'REQUEST_FIELDS')

    def test_limits_and_exact_scopes(self):
        for key, value in [('seconds', 31), ('events', True), ('stdio_bytes', 4194305)]:
            rows = list(records()); rows[0]['limits'][key] = value
            self.reject(rows, 'CAPTURE_')
        rows = list(records()); rows[0]['filesystem_scopes'].append('00-Active/Other/**')
        self.reject(rows, 'EXACT_FS_SCOPE')

    def test_r5_action_code_and_inputs_exact_before_effects(self):
        inputs=dict(loader_code_manifest=ref('code'),loader_inputs=ref('inputs'))
        action=dict(result=dict(code_manifest=inputs['loader_code_manifest'],inputs=inputs['loader_inputs']))
        b.validate_action_loader_inputs(action,inputs)
        for field in ('code_manifest','inputs'):
            changed=deepcopy(action);del changed['result'][field]
            with self.assertRaisesRegex(b.BridgeError,'R5_ACTION_REVIEW_CHANGED'):
                b.validate_action_loader_inputs(changed,inputs)
            changed=deepcopy(action);changed['result'][field]=ref('wrong','f'*64)
            with self.assertRaisesRegex(b.BridgeError,'R5_ACTION_REVIEW_CHANGED'):
                b.validate_action_loader_inputs(changed,inputs)


class PureBindings(unittest.TestCase):
    def test_json_duplicate_and_nonfinite(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}'):
            with self.assertRaises(b.BridgeError): b.strict_json(raw)

    def test_json_deep_or_huge_input(self):
        with self.assertRaises(b.BridgeError): b.strict_json(b'[' * 50 + b'0' + b']' * 50)
        with self.assertRaises(b.BridgeError): b.strict_json(b' ' * (b.MAX_JSON + 1))

    def test_reference_paths_reject_escape(self):
        for name in ('../outside', '/absolute', 'C:/outside', 'a\\b', 'a//b', 'a/./b', 'a/../b'):
            with self.assertRaises(b.BridgeError): b.reference_path(dict(repository_relative_path=name, sha256='a' * 64))

    def test_exact_nonce_scopes_are_separate(self):
        names = b.required_scopes('a' * 32)
        self.assertEqual(len(names), 4)
        self.assertTrue(any('/loader-capture-r5/work/bridge-release-' in p for p in names))
        self.assertTrue(any('/native-attempts/capture-' in p for p in names))
        self.assertTrue(any('/ac7-token-contract-20261020/loader-bridge-' in p for p in names))

    def test_scope_prefix_boundary(self):
        self.assertTrue(b.scope_covers('a/b/**', 'a/b/c/**'))
        self.assertFalse(b.scope_covers('a/b/**', 'a/b-other/**'))
        self.assertFalse(b.scope_covers('a/b', 'a/b/**'))

    def test_live_lease_data_contract(self):
        request, *_ = records()
        lease = request['lease']
        lease['control_root'] = b.W.relative_to(b.F).as_posix()
        claim = {key:lease[key] for key in ('executor_id','input_hash','claimed_at','workspace')}
        scopes = b.required_scopes(request['nonce'])
        claim['effective_write_scope'] = scopes
        data = {'claims.json':dict(implement=claim),
                'state.json':dict(nodes=dict(implement=dict(state='RUNNING', claim=claim))),
                'graph.json':dict(graph=dict(nodes=dict(implement=dict(access='write_scoped',write_scope=scopes))))}
        result = b.validate_lease(lease, request['nonce'], read_json=lambda p:data[p.name])
        self.assertEqual(result['checked_scopes'], scopes)
        data['state.json']['nodes']['implement']['state']='SUCCEEDED'
        with self.assertRaisesRegex(b.BridgeError, 'NOT_RUNNING'):
            b.validate_lease(lease, request['nonce'], read_json=lambda p:data[p.name])

    def test_stale_or_incomplete_lease(self):
        request, *_ = records(); lease=request['lease']
        lease['control_root']=b.W.relative_to(b.F).as_posix()
        claim = {key:lease[key] for key in ('executor_id','input_hash','claimed_at','workspace')}
        claim['effective_write_scope']=b.required_scopes(request['nonce'])[:-1]
        data={'claims.json':dict(implement=claim),
              'state.json':dict(nodes=dict(implement=dict(state='RUNNING', claim=claim))),
              'graph.json':dict(graph=dict(nodes=dict(implement=dict(access='write_scoped',write_scope=claim['effective_write_scope']))))}
        with self.assertRaisesRegex(b.BridgeError,'NOT_LEASED'):
            b.validate_lease(lease,request['nonce'],read_json=lambda p:data[p.name])
        claim['input_hash']='f'*64
        with self.assertRaisesRegex(b.BridgeError,'LEASE_MISMATCH'):
            b.validate_lease(lease,request['nonce'],read_json=lambda p:data[p.name])

    def test_release_derivation_keeps_original_human_reference(self):
        request, grant, *_ = records()
        plan = SimpleNamespace(request=request, grant=grant, inputs=dict(loader_code_manifest=ref('code'),
            loader_inputs=ref('inputs')), source_inputs=dict(worker=dict(sha256='e' * 64)), request_reference=ref('request'))
        launch = dict(arguments=('probe', 'allowed'), standard_handles=(1, 2, 3))
        release, owner = b.derive_release(plan, fixture=b.F/'.agents/runtime/test/native-fixtures/ac1-data',
            launch=launch, parents=(4, 5), binding=dict(actual_object_id=123), native_control={}, owner_reference=ref('bound'))
        self.assertEqual(owner['original_human_grant'], request['owner_grant'])
        self.assertEqual(owner['original_human_message'], grant['human_message_reference'])
        self.assertNotIn('human_reply', owner)
        self.assertIn('not a new human reply', owner['derivation'])
        self.assertEqual(release['prepared_launch']['arguments'], ['probe', 'allowed'])
        for key in ('allow_profile_creation','allow_profile_deletion','allow_existing_process_attach','automatic_retry'):
            self.assertIs(release[key], False)

    def test_closed_ordinary_owner_is_never_polled(self):
        class Closed:
            lifetime_closed=True;pid=17;creation_time=19
            def poll(self): raise AssertionError('closed handle must not be polled')
        self.assertTrue(n.retire_ordinary(Closed())['lifetime_closed'])

    def test_no_native_module_load_on_import(self):
        import sys
        self.assertNotIn('ac6_single_attempt_preflight', sys.modules)
        self.assertNotIn('isolated_adapter', sys.modules)
        self.assertNotIn('win32_debug', sys.modules)

    def test_preloaded_driver_file_label_does_not_admit_it(self):
        import sys,types
        name='CONTROLLED_PRELOADED_DRIVER'
        module=types.ModuleType(name);module.__file__=str(Path(n.__file__))
        sys.modules[name]=module
        try:
            with self.assertRaisesRegex(b.BridgeError,'ALREADY_LOADED'):
                n.load_exact(name,Path(n.__file__),b.file_sha(n.__file__)['sha256'])
        finally:del sys.modules[name]

    def test_native_port_cannot_be_called_before_admission(self):
        request,grant,*_=records()
        port=n.NativePort(SimpleNamespace(paths=b.scope_paths(request['nonce']),request=request,grant=grant))
        with self.assertRaisesRegex(b.BridgeError,'NOT_ADMITTED'):port.live()

    def test_self_described_human_record_has_no_trusted_ingress(self):
        request,grant,human,*_=records()
        with self.assertRaisesRegex(b.BridgeError,'TRUSTED_ROOT_INGRESS_REQUIRED'):
            b.validate_trusted_ingress(None,request,grant,human,{}, {})

    def test_absent_root_anchor_is_actual_preflight_refusal(self):
        with self.assertRaisesRegex(b.BridgeError,'ROOT_INGRESS_NOT_BOUND_NO_EFFECTS'):
            b.trusted_anchor(dict(trusted_owner_ingress_reference=None))
        tree=ast.parse(Path(b.__file__).read_text(encoding='utf8'))
        function=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='preflight')
        anchor_line=next(node.lineno for node in ast.walk(function) if isinstance(node,ast.Call)
            and isinstance(node.func,ast.Name) and node.func.id=='trusted_anchor')
        grant_line=next(node.lineno for node in function.body if isinstance(node,ast.Assign)
            and any(isinstance(target,ast.Name) and target.id=='grant' for target in node.targets))
        self.assertLess(anchor_line,grant_line)

    def test_exact_controlled_ingress_binding(self):
        request,grant,human,*_=records()
        question=dict(kind='CETA_ACTUAL_HUMAN_QUESTION_V1',text='CONTROLLED QUESTION ONLY',message_id='CONTROLLED-QUESTION')
        human['in_reply_to']=question['message_id'];grant['question_reference']=ref('CONTROLLED-QUESTION')
        hashes={'capture_bridge.py':'1'*64,'native_port.py':'2'*64}
        anchor=dict(kind='CETA_ROOT_RECORDED_ACTION_INGRESS_V1',recorded_by='/root',source='actual_current_human_reply',
            human_message_reference=grant['human_message_reference'],nonce=request['nonce'],message_id=human['message_id'],
            repository=str(b.F),code_hashes=hashes,loader_freeze=request['loader_freeze'],
            symbol_supplement=request['symbol_supplement'],effects=list(b.EFFECTS),
            filesystem_scopes=request['filesystem_scopes'],maximum_expires_at_ns=request['expires_at_ns'],
            question_reference=grant['question_reference'],question_message_id=question['message_id'],
            question_text_sha256=b.digest(question['text'].encode('utf8')),
            text_sha256=b.digest(human['text'].encode('utf8')))
        b.validate_trusted_ingress(anchor,request,grant,human,question,hashes)
        anchor['nonce']='b'*32
        with self.assertRaisesRegex(b.BridgeError,'INGRESS_BINDING_MISMATCH'):
            b.validate_trusted_ingress(anchor,request,grant,human,question,hashes)

    def test_production_path_uses_actual_canonical_functions(self):
        raw = Path(n.__file__).read_text(encoding='utf-8'); tree = ast.parse(raw)
        calls = [ast.unparse(node.func) for node in ast.walk(tree) if isinstance(node, ast.Call)]
        for name in ('self.driver.prepare_probe', 'helper.prepare_fixture',
                     'self.boundary.PreparedCaller', 'self.boundary.ChildPipeClosure',
                     'self.owned.execute_prepared_capture', 'self.driver.assert_isolation'):
            self.assertIn(name, calls)
        self.assertNotIn('patch.object', calls)
        self.assertNotIn('self.driver._QualificationRun', calls)
        self.assertNotIn('__code__', [node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
                                   and isinstance(node.ctx, ast.Store)])


class PersistedEvidence(unittest.TestCase):
    def fixture(self):
        request, grant, *_ = records()
        paths = b.scope_paths(request['nonce'])
        plan = SimpleNamespace(request=request, grant=grant, paths=paths,
            source_inputs=dict(worker=dict(sha256='e' * 64)))
        raw = b'CONTROLLED STDOUT'
        result = dict(identity=dict(pid=1, creation_time=2, image_sha256='e' * 64),
            stdout_sha256=b.digest(raw), stderr_sha256=b.digest(b''), stdout_bytes=len(raw), stderr_bytes=0)
        retirement = dict(pid=1, creation_time=2, lifetime_closed=True, debug_exit_continued=True,
            native_pending=dict(exit_continued=True, event_state='IDLE', file_handle=None,
                                file_state='NONE', possible_file_handle_after_unknown_wait_return=None))
        release = b'CONTROLLED RELEASE'
        attempt = dict(nonce=request['nonce'], release_path=str(paths['release']),
                       release_sha256=b.digest(release), automatic_retry=False)
        data = {'RESULT.json':b.canonical(result), 'RETIREMENT.json':b.canonical(retirement),
                'stdout.bin':raw,'stderr.bin':b'', 'ATTEMPT.json':b.canonical(attempt),
                paths['release'].name:release}
        return plan, data

    def read(self, data):
        return lambda path, **kw: data[Path(path).name]

    def assert_rejected(self, key, mutate, reason):
        plan, data = self.fixture()
        value = b.strict_json(data[key]); mutate(value); data[key] = b.canonical(value)
        with self.assertRaisesRegex(b.BridgeError, reason):
            b.persisted_capture(plan, read=self.read(data))

    def test_wrong_nonce(self):
        self.assert_rejected('ATTEMPT.json', lambda x:x.update(nonce='b'*32), 'ATTEMPT_BINDING')

    def test_complete_controlled_readback_preserves_bytes(self):
        plan,data=self.fixture()
        out=b.persisted_capture(plan,read=self.read(data),make_reference=lambda p:ref(p.name,b.digest(data[p.name])))
        self.assertEqual(out['stdout'],data['stdout.bin'])
        self.assertTrue(out['retirement']['lifetime_closed'])
        self.assertEqual(len(out['references']),3)

    def test_missing_actual_retirement_is_not_success(self):
        plan,data=self.fixture();del data['RETIREMENT.json']
        with self.assertRaises(KeyError): b.persisted_capture(plan,read=self.read(data))

    def test_wrong_capture_identity(self):
        self.assert_rejected('RESULT.json', lambda x:x['identity'].update(image_sha256='d'*64), 'CAPTURE_IDENTITY')

    def test_wrong_retirement_identity(self):
        self.assert_rejected('RETIREMENT.json', lambda x:x.update(pid=99), 'RETIREMENT_UNPROVEN')

    def test_uncertain_retirement(self):
        self.assert_rejected('RETIREMENT.json', lambda x:x.update(lifetime_closed=False), 'RETIREMENT_UNPROVEN')

    def test_pending_debug_event(self):
        self.assert_rejected('RETIREMENT.json', lambda x:x['native_pending'].update(event_state='WAIT_IN_FLIGHT'),
                             'NATIVE_CUSTODY_PENDING')

    def test_stdio_hash_change(self):
        self.assert_rejected('RESULT.json', lambda x:x.update(stdout_sha256='f'*64), 'STDIO_CHANGED')

    def test_release_change(self):
        self.assert_rejected('ATTEMPT.json', lambda x:x.update(release_sha256='f'*64), 'RELEASE_CHANGED')


class CustodyControls(unittest.TestCase):
    def port(self):
        request, grant, *_ = records()
        plan=SimpleNamespace(paths=b.scope_paths(request['nonce']), request=request, grant=grant)
        port=n.NativePort(plan)
        port.record=lambda name,value:None
        calls=[]
        port.control=SimpleNamespace(close=lambda handle:calls.append(handle))
        port.handles=[11,12,13]
        return port,calls

    def test_known_handles_closed_once(self):
        port,calls=self.port();port.cleanup_once()
        self.assertEqual(calls,[11,12,13]);self.assertTrue(port.retired)
        with self.assertRaisesRegex(b.BridgeError,'ALREADY_ATTEMPTED'):
            port.cleanup_once()
        self.assertEqual(calls,[11,12,13])

    def test_uncertain_child_close_retains_numeric_handles(self):
        port,calls=self.port();port.closure=SimpleNamespace(state='CLOSE_IN_FLIGHT')
        port.cleanup_once()
        self.assertFalse(port.retired);self.assertEqual(calls,[])
        self.assertEqual(port.handles,[11,12,13]);self.assertFalse(port.delete_called)

    def test_capture_without_proven_retirement_retains_pipes(self):
        port,calls=self.port();port.capture_called=True
        port.cleanup_once()
        self.assertFalse(port.retired);self.assertEqual(calls,[])

    def test_interrupted_allocation_is_not_replayed(self):
        port,calls=self.port();port.handle_in_flight='CreatePipe'
        port.cleanup_once()
        self.assertTrue(port.unknown);self.assertFalse(port.retired);self.assertEqual(calls,[])

    def test_close_then_raise_is_not_retried(self):
        port,calls=self.port()
        def close(handle):
            calls.append(handle)
            if handle==11:raise RuntimeError('CONTROLLED close return uncertain')
        port.control.close=close;port.cleanup_once()
        self.assertEqual(calls.count(11),1);self.assertIn(11,port.handles)
        self.assertTrue(port.unknown);self.assertFalse(port.retired)
        with self.assertRaises(b.BridgeError):port.cleanup_once()
        self.assertEqual(calls.count(11),1)

    def test_child_handles_already_removed_are_never_closed_twice(self):
        port,calls=self.port();port.closure=SimpleNamespace(state='CLOSED',children=(21,22,23))
        port.cleanup_once()
        self.assertEqual(calls,[11,12,13]);self.assertFalse(any(x in calls for x in (21,22,23)))

    def test_listener_close_requires_descriptor_observation(self):
        port,calls=self.port();port.listener=SimpleNamespace(close=lambda:None,fileno=lambda:7)
        port.cleanup_once()
        self.assertFalse(port.retired)
        self.assertTrue(any(x['stage']=='listener_close' for x in port.failures))
        self.assertFalse(any(x['kind']=='ordinary_loopback_listener' for x in port.cleanup))

    def test_listener_closed_descriptor_recorded(self):
        port,calls=self.port();port.listener=SimpleNamespace(close=lambda:None,fileno=lambda:-1)
        port.cleanup_once()
        row=next(x for x in port.cleanup if x['kind']=='ordinary_loopback_listener')
        self.assertEqual(row['descriptor_after_close'],-1);self.assertTrue(port.retired)


class ZCanonicalConstructors(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import importlib,sys
        sys.path.insert(0,str(b.R5))
        cls.boundary=importlib.import_module('caller_boundary')
        cls.inputs=b.strict_json(b.read_bytes(b.R5/'INPUTS.json'))

    def test_actual_unwrapped_source_before_driver(self):
        import sys
        admitted=n.validate_unwrapped_canonical(self.boundary,self.inputs)
        self.assertIn('ceta.supervisor.isolated_worker',admitted)
        self.assertIn('ceta.supervisor.windows_jobs',admitted)
        self.assertNotIn('ac6_single_attempt_preflight',sys.modules)

    def mutation(self,module_name,class_name):
        import sys
        n.validate_unwrapped_canonical(self.boundary,self.inputs)
        cls=getattr(sys.modules[module_name],class_name)
        original=cls.__init__;called=[]
        def forbidden_constructor(*args,**kwargs):
            called.append(True);raise AssertionError('CONTROLLED constructor must never execute')
        cls.__init__=forbidden_constructor
        try:
            with self.assertRaisesRegex(sys.modules['capture_core'].CaptureError,'CALLER_'):
                n.validate_unwrapped_canonical(self.boundary,self.inputs)
        finally:cls.__init__=original
        self.assertEqual(called,[])
        self.assertNotIn('ac6_single_attempt_preflight',sys.modules)
        n.validate_unwrapped_canonical(self.boundary,self.inputs)

    def test_mutated_isolation_constructor_rejected_before_driver(self):
        self.mutation('ceta.supervisor.isolated_worker','_IsolationAPI')

    def test_mutated_owned_process_constructor_rejected_before_driver(self):
        self.mutation('ceta.supervisor.windows_jobs','WindowsOwnedProcess')


if __name__ == '__main__':
    unittest.main()
