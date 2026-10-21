"""Real pinned AC7 imports; controlled data contexts, no fixture/native launch.

The qualification driver's definitions are compiled from its actual pinned AST
without its top-level native file-reader calls. The original helper/support
module bytes are executed only to define their dormant functions and imports.
No run_native_probe/prepare_probe/effect/inspect/qualify method is invoked.
"""
from contextlib import contextmanager
from dataclasses import replace
from pathlib import Path
import ast
import builtins
import ctypes as C
from ctypes import wintypes as WT
import hashlib
import importlib.util
import json
import os
import struct
import sys
import threading
import types
import unittest
import uuid
from capture_core import CaptureError,Limits
import caller_boundary as boundary
import isolated_adapter as adapter
from loader_snaps import pe_codeview,pdb_codeview,match_codeview
from test_loader_snaps import pe_fixture,pdb_fixture

W=Path(__file__).resolve().parent
F=boundary.F
Q=F/'.agents/ac7-token-contract-20261020'
POLICY={
    'helper':dict(path=str(F/'.agents/runtime/ac1-20261014/native_fixture_support.py'),sha256='a7247426deee70890107b9d826c7cda9209015edd5f1192f93ee3bd1e5a4314f'),
    'support':dict(path=str(F/'.agents/runtime/ac3-20261014/ac3_support.py'),sha256='cb44b9f5d4cc50764b486181ad01c41bfee970e91af64338481134c42640096b'),
    'driver':dict(path=str(Q/'tools/qualify_isolated_worker.py'),sha256='79da07922e6a7f56cca0ae9d90a2498c3d6f28a58dcb6bd3144ab56a87b5bd84'),
    'reader':dict(path=str(F/'.agents/pr4-20261014/preserve_ceta_complete.py'),sha256='2ccbca31973ead308e1cdcc6676bbd7371cdec29a0f16178f3f55a4ab4130618')}


@contextmanager
def changed(target,name,value):
    namespace=vars(target)
    previous=namespace[name] if name in namespace else getattr(target,name)
    setattr(target,name,value)
    try:yield
    finally:setattr(target,name,previous)


def load_reader(name):
    path=POLICY['reader']['path'];boundary.source_bytes(path,POLICY['reader']['sha256'])
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module
    spec.loader.exec_module(module)
    return module


def controlled_context():
    inputs=json.loads((F/'.agents/runtime/operational-resume-20261020/loader-capture-r3/work/INPUTS.json').read_bytes())
    inputs['caller_contract']=POLICY
    admitted=boundary.validate_ceta_modules(inputs)
    isolation=admitted['ceta.supervisor.isolated_worker'][0]
    jobs=admitted['ceta.supervisor.windows_jobs'][0];service=admitted['ceta.supervisor.service'][0]
    directory=W/'data-contexts'/uuid.uuid4().hex;directory.mkdir(parents=True,exist_ok=False)
    raw=boundary.source_bytes(POLICY['driver']['path'],POLICY['driver']['sha256'])
    tree=ast.parse(raw,POLICY['driver']['path'])
    constants={'F','R','Q','PY','NAME','SID','USER','MANIFEST','IMAGE','PROPOSAL','SOURCE_BASELINE',
               'SOURCE_BASELINE_SHA','DEPENDENCIES','CANDIDATE_BASELINE','digest','now','reader'}
    # Exact source AST/line numbers; omit only executable module-scope capture
    # preflights. No production integration is asserted by this data fixture.
    selected=[node for node in tree.body if isinstance(node,(ast.Import,ast.ImportFrom,ast.FunctionDef,ast.ClassDef))
        or isinstance(node,ast.Assign) and any(isinstance(t,ast.Name) and t.id in constants for t in node.targets)]
    spec=importlib.util.spec_from_file_location('ac6_single_attempt_preflight',POLICY['driver']['path'])
    driver=importlib.util.module_from_spec(spec);sys.modules[spec.name]=driver
    exec(compile(ast.Module(body=selected,type_ignores=[]),driver.__file__,'exec',dont_inherit=True),vars(driver))
    driver.module=isolation;driver.WindowsOwnedProcess=jobs.WindowsOwnedProcess
    driver.fs=load_reader('profile_r2_native_reader')
    support_raw=boundary.source_bytes(POLICY['support']['path'],POLICY['support']['sha256'])
    helper_raw=boundary.transform_helper(boundary.source_bytes(POLICY['helper']['path'],POLICY['helper']['sha256']))
    (directory/'ac3_support.py').write_bytes(support_raw)
    (directory/'native_fixture_support.py').write_bytes(helper_raw)
    support=types.ModuleType('profile_r2_captured_ac_support');support.__file__=str(directory/'ac3_support.py')
    sys.modules[support.__name__]=support
    exec(compile(support_raw,support.__file__,'exec',dont_inherit=True),vars(support))
    shim=types.ModuleType('ac_support')
    vars(shim).update({key:value for key,value in vars(support).items() if not key.startswith('_')})
    support.Q,support.R,support.D=Q,directory,directory
    # Extract the real nested owned_write_new code; instantiate its one data
    # closure without invoking prepare_probe (which has native path checks).
    codes=boundary.code_index(raw,driver.__file__)
    writer=types.FunctionType(codes['prepare_probe.<locals>.owned_write_new'],vars(driver),
        'owned_write_new',None,((lambda value:lambda:value)(directory).__closure__[0],))
    support.write_new=shim.write_new=writer
    shim.Q,shim.R,shim.D=Q,directory,directory;sys.modules[shim.__name__]=shim
    helper=types.ModuleType('profile_r2_captured_native_probe');helper.__file__=str(directory/'native_fixture_support.py')
    helper.check_launch_paths=driver.check_launch_paths;sys.modules[helper.__name__]=helper
    exec(compile(helper_raw,helper.__file__,'exec',dont_inherit=True),vars(helper))
    control=service._ControlApi.__new__(service._ControlApi)  # No native constructor.
    handles=[101,102,103,104,105,106,107]
    closer=boundary.ChildPipeClosure(control,(102,104,106),handles)
    context=boundary.PreparedCaller(helper,support,shim,driver,control,handles,closer,directory,threading.get_ident())
    fixture=directory/'native-fixtures'/('ac1-'+'0'*32)
    launch=dict(executable=str(fixture/'assets/isolated_worker.exe'),arguments=('probe',),cwd=str(fixture),
        scratch_root=str(fixture/'scratch'),expected_image_sha256=boundary.WORKER,appcontainer_name=boundary.NAME,
        inherited_handles=(),standard_handles=(102,104,106))
    release=dict(fixture_root=str(fixture),parent_output_handles=[103,105],
        prepared_launch={key:list(value) if type(value) is tuple else value for key,value in launch.items()},
        nonce='a'*32,caller_binding={},caller_native_control={},loader_snaps=False)
    _,snapshot=boundary.validate_prepared(context,inputs,release,launch,103,105,closer,match_release=False)
    release['caller_binding']=snapshot
    return context,inputs,release,launch,admitted


class CallerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.context,self.inputs,self.release,self.launch,self.admitted=controlled_context()

    def validate(self,**overrides):
        return boundary.validate_prepared(overrides.get('context',self.context),self.inputs,self.release,
            self.launch,103,105,overrides.get('callback',self.context.close_child_pipe_ends))

    def test_preloaded_real_pinned_imports_preserve_module_and_class_identity(self):
        before={key:module for key,(module,_) in self.admitted.items()}
        isolation,snapshot=self.validate()
        self.assertIs(isolation,self.admitted['ceta.supervisor.isolated_worker'][0])
        self.assertEqual(snapshot,self.release['caller_binding'])
        for key,module in before.items():self.assertIs(sys.modules[key],module)
        self.assertIs(self.context.helper.IsolatedWindowsWorker,isolation.IsolatedWindowsWorker)

    def test_actual_owned_caller_reaches_guarded_native_boundary_without_attempt(self):
        import owned_caller
        observed=[]
        def gated(control):
            observed.append(control)
            raise CaptureError('CONTROLLED_NATIVE_MEMBER_BOUNDARY')
        def no_consume(*a):self.fail('attempt consumed before caller/native control preflight')
        def no_provider(*a):self.fail('native provider loaded')
        with (changed(adapter,'admission',lambda *a:(self.release,Limits(),self.inputs,W/'native-attempts/capture-controlled')),
             changed(adapter,'native_control_members',gated),changed(adapter,'consume_attempt',no_consume),
             changed(adapter,'open_functions',no_provider)):
            with self.assertRaisesRegex(CaptureError,'CONTROLLED_NATIVE_MEMBER_BOUNDARY'):
                owned_caller.execute_prepared_capture(release_path=W/'NO-RELEASE',release_sha256='0'*64,
                    launch_arguments=self.launch,stdout_handle=103,stderr_handle=105,
                    close_child_pipe_ends=self.context.close_child_pipe_ends,caller_context=self.context)
        self.assertEqual(observed,[self.context.control]);self.assertFalse(adapter._active)

    def test_changed_file_origin_and_spec_are_refused(self):
        module=self.admitted['ceta.supervisor.isolated_worker'][0]
        for target,name,value in ((module,'__file__',str(W/'foreign.py')),(module.__spec__,'origin',str(W/'foreign.py')),
                                  (module.__loader__,'path',str(W/'foreign.py')),(module,'__package__','foreign')):
            with self.subTest(name=name),changed(target,name,value),self.assertRaises(CaptureError):self.validate()

    def test_unknown_foreign_module_and_sys_modules_alias_are_refused(self):
        module=self.admitted['ceta.supervisor.isolated_worker'][0]
        for key,value in (('ceta.unreviewed',types.ModuleType('ceta.unreviewed')),('unknown_ceta_alias',module)):
            sys.modules[key]=value
            try:
                with self.subTest(key=key),self.assertRaises(CaptureError):self.validate()
            finally:del sys.modules[key]

    def test_exact_path_with_changed_live_code_is_refused(self):
        module=self.admitted['ceta.supervisor.isolated_worker'][0]
        function=module.appcontainer_sid
        with changed(function,'__code__',(lambda name:'changed').__code__),self.assertRaisesRegex(CaptureError,'LIVE_CODE'):
            self.validate()

    def test_changed_class_base_method_descriptor_and_function_defaults_are_refused(self):
        jobs=self.admitted['ceta.supervisor.windows_jobs'][0]
        actual=vars(jobs.WindowsOwnedProcess)['launch']
        with changed(jobs.WindowsOwnedProcess,'launch',actual.__func__),self.assertRaisesRegex(CaptureError,'CLASSMETHOD'):
            self.validate()
        function=jobs.WindowsOwnedProcess.terminate
        with changed(function,'__defaults__',(0,)),self.assertRaisesRegex(CaptureError,'DEFAULTS'):
            self.validate()

    def test_changed_ctypes_field_list_is_refused_without_native_effect(self):
        jobs=self.admitted['ceta.supervisor.windows_jobs'][0]
        fields=jobs.PROCESS_INFORMATION._fields_;before=list(fields)
        fields[0]=('process',C.c_uint32)
        try:
            with self.assertRaisesRegex(CaptureError,'ABI_FIELDS'):self.validate()
        finally:fields[:]=before

    def test_helper_shim_reader_and_path_guard_aliases_are_refused(self):
        for target,name,value in ((self.context.helper,'IsolatedWindowsWorker',object()),
                                  (self.context.shim,'sha',lambda p:'wrong'),
                                  (self.context.helper,'check_launch_paths',lambda *a:None),
                                  (self.context.helper,'fs',object())):
            with self.subTest(name=name),changed(target,name,value),self.assertRaises(CaptureError):self.validate()

    def test_changed_live_launcher_constant_and_stdlib_alias_are_refused(self):
        isolation=self.admitted['ceta.supervisor.isolated_worker'][0]
        for target,name,value in ((isolation,'CHILD_PROCESS_RESTRICTED',0),(isolation,'Path',object()),
                (self.context.support.fs.open_source.__wrapped__,'__code__',(lambda *a:None).__code__)):
            with self.subTest(name=name),changed(target,name,value),self.assertRaises(CaptureError):self.validate()

    def test_unknown_custody_constructor_wrapper_is_refused(self):
        isolation=self.admitted['ceta.supervisor.isolated_worker'][0]
        with changed(isolation._IsolationAPI,'__init__',lambda *a:None),self.assertRaisesRegex(CaptureError,'CUSTODY_WRAPPER'):
            self.validate()

    def test_exact_source_constructor_wrappers_and_closure_owner_are_validated(self):
        isolation=self.admitted['ceta.supervisor.isolated_worker'][0];jobs=self.admitted['ceta.supervisor.windows_jobs'][0]
        driver=self.context.driver;run=driver._QualificationRun(self.context.directory,'0'*64)
        context=replace(self.context,qualification_run=run)
        codes=boundary.code_index(Path(driver.__file__).read_bytes(),driver.__file__)
        def cell(value):return (lambda:value).__closure__[0]
        def wrapper(name,original):
            code=codes['_QualificationRun.execute.<locals>.'+name]
            values={('original_api' if name=='api_init' else 'original_owner'):original,'self':run}
            return types.FunctionType(code,vars(driver),name,None,tuple(cell(values[key]) for key in code.co_freevars))
        with (changed(isolation._IsolationAPI,'__init__',wrapper('api_init',isolation._IsolationAPI.__init__)),
             changed(jobs.WindowsOwnedProcess,'__init__',wrapper('owner_init',jobs.WindowsOwnedProcess.__init__))):
            _,snapshot=boundary.validate_prepared(context,self.inputs,self.release,self.launch,103,105,
                context.close_child_pipe_ends,match_release=False)
            self.release['caller_binding']=snapshot;self.validate(context=context)
            with self.assertRaisesRegex(CaptureError,'CUSTODY_WRAPPER_CLOSURE'):
                self.validate(context=replace(context,qualification_run=driver._QualificationRun(context.directory,'1'*64)))

    def test_unapproved_callback_changed_handle_collections_and_release_binding_refused(self):
        with self.assertRaisesRegex(CaptureError,'PIPE_CALLBACK'):self.validate(callback=lambda:None)
        for mutate in ('duplicate','remove','add','release'):
            handles=self.context.owned_handles;before=list(handles);original=self.release['caller_binding']
            try:
                if mutate=='duplicate':handles.append(102)
                elif mutate=='remove':handles.remove(104)
                elif mutate=='add':handles.append(108)
                else:self.release['caller_binding']={}
                with self.subTest(mutate=mutate),self.assertRaises(CaptureError):self.validate()
            finally:handles[:]=before;self.release['caller_binding']=original

    def test_wrong_thread_rejected_before_imports_or_native_boundaries(self):
        with self.assertRaisesRegex(CaptureError,'CREATOR_THREAD'):
            self.validate(context=replace(self.context,creator_thread=self.context.creator_thread+1))

    def test_changed_live_callback_code_is_refused(self):
        function=boundary.ChildPipeClosure.__call__
        with changed(function,'__code__',(lambda self:None).__code__),self.assertRaisesRegex(CaptureError,'LIVE_CODE'):
            self.validate()

    def test_native_control_fixtures_cannot_be_accepted_as_production_bindings(self):
        with self.assertRaisesRegex(CaptureError,'NATIVE_CONTROL_MEMBERS'):
            boundary.native_control_members(self.context.control)

    def test_source_byte_pin_and_changed_control_method_are_refused(self):
        key='src/ceta/supervisor/isolated_worker.py';before=self.inputs['ac7_payload_hashes'][key]
        self.inputs['ac7_payload_hashes'][key]='0'*64
        try:
            with self.assertRaisesRegex(CaptureError,'SOURCE_BYTES_CHANGED'):self.validate()
        finally:self.inputs['ac7_payload_hashes'][key]=before
        self.context.control.close=lambda handle:None
        try:
            with self.assertRaisesRegex(CaptureError,'CONTROL_CLOSE'):self.validate()
        finally:del self.context.control.close

    def test_actual_adapter_rejects_unknown_callback_before_attempt_or_native_member_check(self):
        events=[]
        def forbidden(*a):events.append('unexpected');self.fail('effect boundary reached for invalid caller')
        with (changed(adapter,'admission',lambda *a:(self.release,Limits(),self.inputs,W/'unused-attempt')),
              changed(adapter,'consume_attempt',forbidden),changed(adapter,'open_functions',forbidden),
              changed(adapter,'native_control_members',forbidden)):
            with self.assertRaisesRegex(CaptureError,'PIPE_CALLBACK'):
                adapter.launch_isolated_capture(release_path=W/'NO-RELEASE',release_sha256='0'*64,
                    launch_arguments=self.launch,stdout_handle=103,stderr_handle=105,
                    close_child_pipe_ends=lambda:None,caller_context=self.context)
        self.assertEqual(events,[]);self.assertFalse(adapter._active)


class ClosureTests(unittest.TestCase):
    def test_exact_close_then_remove_order_and_single_attempt(self):
        handles=[1,2,3,4];seen=[]
        class Control:
            def close(self,handle):seen.append((handle,list(handles)))
        closure=boundary.ChildPipeClosure(Control(),(1,2,3),handles);closure()
        self.assertEqual(seen,[(1,[1,2,3,4]),(2,[2,3,4]),(3,[3,4])]);self.assertEqual(handles,[4])
        with self.assertRaisesRegex(CaptureError,'NO_REPLAY'):closure()

    def test_uncertain_child_close_retains_same_collection_and_never_retries(self):
        handles=[1,2,3];seen=[]
        class Control:
            def close(self,handle):seen.append(handle);raise KeyboardInterrupt('controlled lost close return')
        closure=boundary.ChildPipeClosure(Control(),(1,2),handles)
        with self.assertRaises(KeyboardInterrupt) as caught:closure()
        self.assertIs(caught.exception.loader_child_pipe_custody,closure)
        self.assertEqual((closure.state,closure.current,handles),('CLOSE_IN_FLIGHT',1,[1,2,3]))
        with self.assertRaisesRegex(CaptureError,'NO_REPLAY'):closure()
        self.assertEqual(seen,[1])


def native_control_data():
    """Noncalled typed wrappers around inert addresses, never a DLL/callback.

    CreateEventW's types come from the actual pinned canonical helper AST.
    These data pointers have no native provenance and are not an integration
    or owner-approved production control. No wrapper is invoked by these tests.
    """
    inputs=json.loads((F/'.agents/runtime/operational-resume-20261020/loader-capture-r3/work/INPUTS.json').read_bytes())
    admitted=boundary.validate_ceta_modules(inputs)
    service=admitted['ceta.supervisor.service'][0]
    control=service._ControlApi.__new__(service._ControlApi)
    H,D,B,p=C.c_void_p,C.c_uint32,C.c_int32,C.POINTER
    declarations=dict(CreatePipe=([p(H),p(H),p(service._Attributes),D],B),
        SetHandleInformation=([H,D,D],B),PeekNamedPipe=([H,H,D,p(D),p(D),p(D)],B),
        ReadFile=([H,H,D,p(D),H],B),WriteFile=([H,H,D,p(D),H],B),CloseHandle=([H],B))
    helper=boundary.source_bytes(POLICY['helper']['path'],POLICY['helper']['sha256'])
    function=next(node for node in ast.parse(helper).body if isinstance(node,ast.FunctionDef) and node.name=='run_native_probe')
    arguments=next(node.value for node in function.body if isinstance(node,ast.Assign)
        and any(ast.unparse(target)=='control.CreateEventW.argtypes' for target in node.targets))
    result=next(node.value for node in function.body if isinstance(node,ast.Assign)
        and any(ast.unparse(target)=='control.CreateEventW.restype' for target in node.targets))
    namespace=dict(C=C,W=WT,HANDLE=H)
    declarations['CreateEventW']=(boundary.data_value(arguments,namespace),boundary.data_value(result,namespace))
    for index,(name,(argtypes,restype)) in enumerate(declarations.items(),1):
        pointer=C.WINFUNCTYPE(restype,*argtypes,use_last_error=True)(0x10000000+index*0x1000)
        pointer.__name__=name;pointer.argtypes=argtypes;pointer.restype=restype
        setattr(control,name,pointer)
    return control


class EventControlGuardTests(unittest.TestCase):
    def test_actual_canonical_seven_members_pass_real_guard_without_native_invocation(self):
        control=native_control_data();result=boundary.native_control_members(control)
        self.assertEqual(set(result),{'CreatePipe','SetHandleInformation','PeekNamedPipe','ReadFile','WriteFile','CloseHandle','CreateEventW'})
        self.assertEqual(control.CreateEventW.argtypes,[C.c_void_p,WT.BOOL,WT.BOOL,WT.LPCWSTR])
        self.assertIs(control.CreateEventW.restype,C.c_void_p)
        self.assertEqual(result['CreateEventW'],dict(object_id=id(control.CreateEventW),address=0x10007000))

    def test_every_missing_canonical_member_is_refused(self):
        control=native_control_data()
        for name in tuple(vars(control)):
            value=getattr(control,name);delattr(control,name)
            try:
                with self.subTest(name=name),self.assertRaisesRegex(CaptureError,'NATIVE_CONTROL_MEMBERS'):
                    boundary.native_control_members(control)
            finally:setattr(control,name,value)

    def test_unknown_extra_native_member_remains_refused(self):
        control=native_control_data();control.UnreviewedExtra=control.CreateEventW
        with self.assertRaisesRegex(CaptureError,'NATIVE_CONTROL_MEMBERS'):boundary.native_control_members(control)

    def test_event_wrong_argument_return_name_and_calling_flags_are_refused(self):
        for name,value in (('argtypes',[C.c_void_p,C.c_uint64,WT.BOOL,WT.LPCWSTR]),
                           ('restype',C.c_uint32),('__name__','OtherEvent'),('_flags_',0)):
            control=native_control_data()
            with self.subTest(name=name),changed(control.CreateEventW,name,value),self.assertRaisesRegex(CaptureError,'NATIVE_CONTROL_ABI'):
                boundary.native_control_members(control)

    def test_actual_adapter_passes_seven_member_guard_to_stopped_attempt_boundary(self):
        context,inputs,release,launch,_=controlled_context()
        control=native_control_data()
        closer=boundary.ChildPipeClosure(control,launch['standard_handles'],context.owned_handles)
        context=replace(context,control=control,close_child_pipe_ends=closer)
        _,release['caller_binding']=boundary.validate_prepared(context,inputs,release,launch,103,105,closer,match_release=False)
        release['caller_native_control']=boundary.native_control_members(control)
        observed=[];before_active=adapter._active
        def stop(*arguments):observed.append(arguments);raise CaptureError('CONTROLLED_ATTEMPT_BOUNDARY_NO_NATIVE_EFFECT')
        def no_provider(*arguments):self.fail('native provider reached')
        try:
            with (changed(adapter,'admission',lambda *a:(release,Limits(),inputs,W/'no-attempt')),
                  changed(adapter,'consume_attempt',stop),changed(adapter,'open_functions',no_provider)):
                with self.assertRaisesRegex(CaptureError,'CONTROLLED_ATTEMPT_BOUNDARY'):
                    adapter.launch_isolated_capture(release_path=W/'NO-RELEASE',release_sha256='0'*64,
                        launch_arguments=launch,stdout_handle=103,stderr_handle=105,
                        caller_context=context,close_child_pipe_ends=closer)
        finally:adapter._active=before_active  # Restore only this controlled no-effect fixture's flag.
        self.assertEqual(len(observed),1)


class DefaultDataGuardTests(unittest.TestCase):
    def hostile(self,calls):
        class UnexpectedDefault:
            def __eq__(self,other):calls.append('eq');return True
            def __bool__(self):calls.append('bool');raise AssertionError('untrusted bool')
            def __iter__(self):calls.append('iter');raise AssertionError('untrusted iter')
            def __len__(self):calls.append('len');raise AssertionError('untrusted len')
            __hash__=object.__hash__
        return UnexpectedDefault()

    def test_full_real_cpu_window_positional_default_rejected_without_any_hook(self):
        context,inputs,release,launch,admitted=controlled_context();calls=[]
        method=admitted['ceta.supervisor.windows_jobs'][0].WindowsOwnedProcess._cpu_window
        before=method.__code__;self.assertEqual(method.__defaults__,(None,))
        with changed(method,'__defaults__',(self.hostile(calls),)):
            with self.assertRaisesRegex(CaptureError,'DEFAULTS'):
                boundary.validate_prepared(context,inputs,release,launch,103,105,context.close_child_pipe_ends)
        self.assertIs(method.__code__,before);self.assertEqual(calls,[])
        boundary.validate_prepared(context,inputs,release,launch,103,105,context.close_child_pipe_ends)

    def test_full_real_cpu_keyword_default_rejected_without_any_hook(self):
        context,inputs,release,launch,admitted=controlled_context();calls=[]
        method=admitted['ceta.supervisor.windows_jobs'][0].WindowsOwnedProcess.apply_cpu_rate_limit
        self.assertIs(method.__kwdefaults__['dispatch_fence'],None)
        mutated=dict(method.__kwdefaults__,dispatch_fence=self.hostile(calls))
        with changed(method,'__kwdefaults__',mutated),self.assertRaisesRegex(CaptureError,'DEFAULTS'):
            boundary.validate_prepared(context,inputs,release,launch,103,105,context.close_child_pipe_ends)
        self.assertEqual(calls,[])

    def test_supported_nested_builtin_data_and_keyword_order_remain_valid(self):
        left={'alpha':[None,True,1,2.0,3+4j,b'bytes',('x',)],'beta':{'item':'\ud800'}}
        right={'beta':{'item':'\ud800'},'alpha':[None,True,1,2.0,3+4j,b'bytes',('x',)]}
        self.assertTrue(boundary.default_data_equal(left,right))
        for actual,expected in ((True,1),(1,1.0),([1],(1,)),(b'x','x')):
            with self.subTest(kind=type(actual).__name__):self.assertFalse(boundary.default_data_equal(actual,expected))
        raw=b'def data(value=(1, [None], {"key": True}), *, option={"a": 1, "b": 2}):\n    return value\n'
        namespace={};exec(compile(raw,'controlled-default-data','exec'),namespace)
        node=ast.parse(raw).body[0];function=namespace['data']
        function.__kwdefaults__={'option':{'b':2,'a':1}}
        boundary.validate_defaults(function,node,namespace)

    def test_nested_hostile_values_and_mapping_keys_never_run_hooks(self):
        calls=[];evil=self.hostile(calls)
        for actual,expected in (([evil],[None]),({'key':evil},{'key':None}),({evil:1},{'key':1}),(({'key':[evil]},),({'key':[None]},))):
            with self.subTest(container=type(actual).__name__),self.assertRaisesRegex(CaptureError,'DEFAULTS'):
                boundary.default_data_equal(actual,expected)
        self.assertEqual(calls,[])

    def test_container_subclasses_and_hostile_metaclass_never_run_hooks(self):
        calls=[]
        class HookList(list):
            def __eq__(self,other):calls.append('eq');return True
            def __iter__(self):calls.append('iter');raise AssertionError('custom iteration')
            def __len__(self):calls.append('len');raise AssertionError('custom length')
        class HookDict(dict):
            def items(self):calls.append('items');raise AssertionError('custom items')
        class HookMeta(type):
            def __eq__(self,other):calls.append('type-eq');return True
        class HookObject(metaclass=HookMeta):pass
        for actual,expected in ((HookList(),[]),(HookDict(),{}),(HookObject(),None)):
            with self.subTest(kind=type(actual).__name__),self.assertRaisesRegex(CaptureError,'DEFAULTS'):
                boundary.default_data_equal(actual,expected)
        self.assertEqual(calls,[])

    def test_cycles_depth_node_container_and_scalar_limits_are_refused(self):
        cycle=[];cycle.append(cycle);mapping={};mapping['self']=mapping
        deep=None
        for _ in range(18):deep=[deep]
        for value in (cycle,mapping,deep,[0]*257,[[0]*256]*9,b'x'*65537,'x'*65537,1<<4097,float('nan')):
            with self.subTest(kind=type(value).__name__),self.assertRaisesRegex(CaptureError,'DEFAULTS'):
                boundary.default_data_equal(value,value)

    def test_source_referenced_objects_use_identity_without_hooks(self):
        calls=[];token=self.hostile(calls);other=self.hostile(calls)
        raw=b'def data(value=TOKEN, *, option=TOKEN):\n    return value\n'
        namespace={'TOKEN':token};exec(compile(raw,'controlled-default-reference','exec'),namespace)
        function=namespace['data'];node=ast.parse(raw).body[0]
        boundary.validate_defaults(function,node,namespace)
        with changed(function,'__defaults__',(other,)),self.assertRaisesRegex(CaptureError,'DEFAULTS'):
            boundary.validate_defaults(function,node,namespace)
        self.assertEqual(calls,[])

    def test_untrusted_opaque_identity_is_not_a_cycle_or_type_bypass(self):
        calls=[];token=self.hostile(calls)
        with self.assertRaisesRegex(CaptureError,'UNSUPPORTED'):boundary.default_data_equal(token,token)
        self.assertTrue(boundary.default_data_equal(token,token,trusted=(token,)))
        self.assertEqual(calls,[])


class SymbolV2Tests(unittest.TestCase):
    def test_v1_supplement_remains_denied_and_v2_retains_both_ages(self):
        image,pdb=pe_codeview(pe_fixture()),pdb_codeview(pdb_fixture(age=19))
        supplement=dict(schema_version=2,kind='CETA_OWNED_LOADER_SYMBOL_INPUTS_V2',image_codeview=image,
            pdb_codeview=pdb,codeview_match=match_codeview(image,pdb))
        adapter.validate_symbol_identity(supplement,image,pdb)
        for values in ({'schema_version':1,'kind':'CETA_OWNED_LOADER_SYMBOL_INPUTS_V1'},
                       {'schema_version':True},{'pdb_codeview':dict(pdb,info_age=7)}):
            with self.subTest(values=values),self.assertRaises(CaptureError):
                adapter.validate_symbol_identity(dict(supplement,**values),image,pdb)
    def test_retained_official_image_and_pdb_preserve_distinct_observed_ages(self):
        root=F/'.agents/runtime/operational-resume-20261020/loader-symbol-inputs-r1/work'
        evidence=json.loads((root/'NTDLL-CODEVIEW.json').read_bytes())
        image=boundary.source_bytes(evidence['ntdll_pin']['path'],evidence['ntdll_pin']['sha256'])
        pdb=boundary.source_bytes(root/'symbols/ntdll.pdb','c93f4614aa6f40fe370d40eb7ee9589ca0eda170ef2d704b5d278da71c02c249')
        self.assertEqual(len(pdb),1912832)
        observed=match_codeview(pe_codeview(image),pdb_codeview(pdb))
        self.assertEqual((observed['guid_hex'],observed['image_age'],observed['info_age'],observed['dbi_age']),
            ('5bd431c0a10d6e8a74d06ed6ab2dd9e1',1,4,1))

    def test_info_age_can_exceed_image_age_only_with_exact_dbi_age(self):
        result=match_codeview(pe_codeview(pe_fixture()),pdb_codeview(pdb_fixture(age=19)))
        self.assertEqual((result['image_age'],result['info_age'],result['dbi_age']),(7,19,7))
        for raw in (pdb_fixture(age=6),pdb_fixture(dbi_age=8),pdb_fixture(guid=b'X'*16)):
            with self.subTest(raw=hashlib.sha256(raw).hexdigest()),self.assertRaisesRegex(CaptureError,'MISMATCH'):
                match_codeview(pe_codeview(pe_fixture()),pdb_codeview(raw))

    def test_missing_zero_bad_signature_version_machine_and_bounds_refused(self):
        for case in ('missing','zero','signature','version','machine','stream-bounds','negative-substream','oversize-substream'):
            raw=bytearray(pdb_fixture())
            if case=='missing':struct.pack_into('<I',raw,3*512+16,0xffffffff)
            elif case=='zero':struct.pack_into('<I',raw,5*512+8,0)
            elif case=='signature':struct.pack_into('<i',raw,5*512,0)
            elif case=='version':struct.pack_into('<I',raw,5*512+4,0)
            elif case=='machine':struct.pack_into('<H',raw,5*512+58,0x14c)
            elif case=='stream-bounds':struct.pack_into('<I',raw,3*512+24,99999)
            elif case=='negative-substream':struct.pack_into('<i',raw,5*512+24,-1)
            else:struct.pack_into('<i',raw,5*512+24,100000)
            with self.subTest(case=case),self.assertRaises(CaptureError):pdb_codeview(bytes(raw))


if __name__=='__main__':unittest.main(verbosity=2)
