"""Pure validation of the existing captured AC7 caller and live import bindings.

This module creates no fixture, native API, profile, process, DLL or authority.
It preserves existing imported objects. Compiled source code is compared rather
than executed; the only imports performed are declared pinned AC7 modules.
"""
from dataclasses import dataclass
from pathlib import Path
import ast
import builtins
import contextlib
import ctypes as C
from ctypes import wintypes as W
import importlib
import math
from importlib.machinery import SourceFileLoader, ModuleSpec
import operator
import sys
import threading
import types
import hashlib
from capture_core import require, CaptureError, retain

F=Path('T:/00-Active/Project-AI-CETA')
NAME='CETA.ProjectAICETA.IsolatedWorker.AC1.V1'
WORKER='3df03778e1e2f6f707d38b0869e04e262926f2d4c375f1d3d10562d3456443cc'


def source_bytes(path,pin):
    path=Path(path)
    require(path.is_absolute() and path.is_file(),'CALLER_SOURCE_REQUIRED')
    for part in (path,*path.parents):
        require(not part.lstat().st_file_attributes&0x400,'CALLER_REPARSE_REFUSED')
    before=path.stat();raw=path.read_bytes();after=path.stat()
    identity=lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns)
    require(identity(before)==identity(after) and hashlib.sha256(raw).hexdigest()==pin,
            'CALLER_SOURCE_BYTES_CHANGED:'+str(path))
    return raw


def code_digest(code):
    require(type(code) is types.CodeType,'CALLER_CODE_REQUIRED')
    # marshal encodes object-sharing/interning details that differ between a
    # valid .pyc import and a fresh compile. Fingerprint every semantic/location
    # code field recursively, without that serialization reference topology.
    def constant(value):
        if type(value) is types.CodeType:return ('code',record(value))
        if type(value) is tuple:return ('tuple',tuple(constant(item) for item in value))
        if type(value) is frozenset:return ('frozenset',tuple(sorted((constant(item) for item in value),key=repr)))
        require(type(value) in (type(None),bool,int,float,complex,str,bytes) or value is Ellipsis,
                'CALLER_CODE_CONSTANT_UNSUPPORTED')
        return (type(value).__name__,repr(value))
    def record(value):
        return (value.co_argcount,value.co_posonlyargcount,value.co_kwonlyargcount,value.co_nlocals,
            value.co_stacksize,value.co_flags,value.co_code,value.co_names,value.co_varnames,
            value.co_filename,value.co_name,value.co_qualname,value.co_firstlineno,value.co_linetable,
            value.co_exceptiontable,value.co_freevars,value.co_cellvars,tuple(constant(item) for item in value.co_consts))
    return hashlib.sha256(repr(record(code)).encode('utf8')).hexdigest()


def code_index(raw,filename):
    result={}
    def visit(code):
        result[code.co_qualname]=code
        for item in code.co_consts:
            if type(item) is types.CodeType:visit(item)
    visit(compile(raw,filename,'exec',dont_inherit=True,optimize=0))
    return result


def function_matches(value,expected,namespace):
    require(type(value) is types.FunctionType and value.__globals__ is namespace,
            'CALLER_FUNCTION_GLOBALS_CHANGED')
    require(value.__code__==expected and code_digest(value.__code__)==code_digest(expected),
            'CALLER_LIVE_CODE_CHANGED:'+expected.co_qualname)


def unwrap(value):
    return value.__func__ if type(value) in (classmethod,staticmethod) else value


def data_value(node,namespace,local=None):
    """Bounded data expressions used by pinned defaults/ctypes field layouts.

    No call expression, descriptor, comprehension iterator supplied by a caller,
    or general eval is admitted. ctypes array multiplication constructs a type,
    never a native provider or an instance.
    """
    local=local or {}
    if isinstance(node,ast.Constant):return node.value
    if isinstance(node,ast.Name):
        if node.id not in local and node.id not in namespace and node.id in ('object','str','bytes','int','float','bool','Exception','RuntimeError','ValueError','TypeError'):
            return vars(builtins)[node.id]
        require(node.id in local or node.id in namespace,'CALLER_DATA_NAME_UNKNOWN:'+node.id)
        return local[node.id] if node.id in local else namespace[node.id]
    if isinstance(node,ast.Attribute):
        owner=data_value(node.value,namespace,local)
        require(type(owner) is types.ModuleType or isinstance(owner,type),'CALLER_DATA_ATTRIBUTE_UNSAFE')
        require(node.attr in vars(owner),'CALLER_DATA_ATTRIBUTE_UNKNOWN')
        return vars(owner)[node.attr]
    if isinstance(node,(ast.Tuple,ast.List)):
        values=[data_value(item,namespace,local) for item in node.elts]
        return tuple(values) if isinstance(node,ast.Tuple) else values
    if isinstance(node,ast.Dict):
        return {data_value(key,namespace,local):data_value(value,namespace,local) for key,value in zip(node.keys,node.values,strict=True)}
    if isinstance(node,ast.UnaryOp) and isinstance(node.op,(ast.USub,ast.UAdd)):
        value=data_value(node.operand,namespace,local)
        require(type(value) in (int,float),'CALLER_DATA_UNARY_UNSAFE')
        return -value if isinstance(node.op,ast.USub) else value
    if isinstance(node,ast.BinOp):
        left,right=data_value(node.left,namespace,local),data_value(node.right,namespace,local)
        if isinstance(node.op,ast.Div) and type(left) is type(F) and type(right) is str:return left/right
        if type(left) is int and type(right) is int:
            operation={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Pow:operator.pow,
                ast.LShift:operator.lshift,ast.RShift:operator.rshift,ast.BitOr:operator.or_,ast.BitAnd:operator.and_}.get(type(node.op))
            require(operation is not None and abs(left)<(1<<64) and abs(right)<(1<<64)
                    and (not isinstance(node.op,(ast.LShift,ast.RShift,ast.Pow)) or 0<=right<=64), 'CALLER_DATA_INTEGER_BOUND')
            return operation(left,right)
        if isinstance(node.op,ast.Add) and type(left) is list and type(right) is list:return left+right
        if isinstance(node.op,ast.Mult) and isinstance(left,type) and issubclass(left,(C.Structure,C.Union,C._SimpleCData,C.Array)):
            require(type(right) is int and 0<right<=1024,'CALLER_CTYPE_ARRAY_BOUND')
            return left*right
    if isinstance(node,ast.ListComp) and len(node.generators)==1:
        generator=node.generators[0]
        require(isinstance(generator.target,ast.Name) and not generator.ifs and not generator.is_async,'CALLER_DATA_COMPREHENSION_UNSAFE')
        values=data_value(generator.iter,namespace,local)
        require(type(values) in (tuple,list) and len(values)<=128,'CALLER_DATA_COMPREHENSION_BOUND')
        return [data_value(node.elt,namespace,dict(local,**{generator.target.id:value})) for value in values]
    raise CaptureError('CALLER_UNSUPPORTED_DATA_EXPRESSION:'+ast.dump(node))


def declarative(node):
    return (isinstance(node,(ast.Constant,ast.Name,ast.Attribute))
        and not any(isinstance(value,ast.Call) for value in ast.walk(node))) or (
        isinstance(node,(ast.Tuple,ast.List,ast.Dict,ast.UnaryOp,ast.BinOp))
        and all(not isinstance(value,(ast.Call,ast.Lambda,ast.ListComp,ast.SetComp,ast.DictComp,ast.GeneratorExp)) for value in ast.walk(node)))


def default_data_equal(actual,expected,*,trusted=()):
    """Compare bounded exact builtin data without consulting supplied hooks.

    Opaque source-referenced objects are compared only by identity. Normalize
    both sides before equality; the final records contain only exact builtin
    types. Dicts are read with dict.items and compared without hashing or
    looking up caller-provided keys. Even identical containers are traversed,
    so identity cannot hide cycles or unbounded contents.
    """
    require(type(trusted) is tuple and len(trusted)<=256,'CALLER_DEFAULTS_TRUST_BOUND')
    remaining=[2048]
    def normalize(value,depth,active):
        remaining[0]-=1
        require(depth<=16 and remaining[0]>=0,'CALLER_DEFAULTS_COMPLEXITY_BOUND')
        kind=type(value)
        if kind is type(None):return ('none',)
        if kind is bool:return ('bool',value)
        if kind is int:
            require(int.bit_length(value)<=4096,'CALLER_DEFAULTS_INTEGER_BOUND')
            return ('int',value)
        if kind is float:
            require(math.isfinite(value),'CALLER_DEFAULTS_NONFINITE')
            return ('float',float.hex(value))
        if kind is complex:
            require(math.isfinite(value.real) and math.isfinite(value.imag),'CALLER_DEFAULTS_NONFINITE')
            return ('complex',float.hex(value.real),float.hex(value.imag))
        if kind is str:
            require(str.__len__(value)<=65536,'CALLER_DEFAULTS_SCALAR_BOUND')
            require(len(str.encode(value,'utf8','surrogatepass'))<=65536,'CALLER_DEFAULTS_SCALAR_BOUND')
            return ('str',value)
        if kind is bytes:
            require(bytes.__len__(value)<=65536,'CALLER_DEFAULTS_SCALAR_BOUND')
            return ('bytes',value)
        if kind is tuple or kind is list or kind is dict:
            marker=id(value)
            require(marker not in active,'CALLER_DEFAULTS_CYCLE')
            length=tuple.__len__(value) if kind is tuple else list.__len__(value) if kind is list else dict.__len__(value)
            require(length<=256,'CALLER_DEFAULTS_CONTAINER_BOUND')
            active.add(marker)
            try:
                if kind is dict:
                    pairs=[(normalize(key,depth+1,active),normalize(item,depth+1,active)) for key,item in dict.items(value)]
                    return ('dict',tuple(sorted(pairs)))
                values=tuple(normalize(item,depth+1,active) for item in (tuple.__iter__(value) if kind is tuple else list.__iter__(value)))
                return ('tuple' if kind is tuple else 'list',values)
            finally:active.remove(marker)
        for reference in trusted:
            if value is reference:return ('identity',id(value))
        raise CaptureError('CALLER_DEFAULTS_UNSUPPORTED_VALUE')
    return normalize(actual,0,set())==normalize(expected,0,set())


def validate_defaults(function,node,namespace):
    expected=tuple(data_value(value,namespace) for value in node.args.defaults) or None
    kw={argument.arg:data_value(value,namespace) for argument,value in zip(node.args.kwonlyargs,node.args.kw_defaults,strict=True) if value is not None} or None
    expressions=[*node.args.defaults,*[value for value in node.args.kw_defaults if value is not None]]
    trusted=tuple(data_value(item,namespace) for expression in expressions for item in ast.walk(expression)
        if isinstance(item,(ast.Name,ast.Attribute)))
    require(default_data_equal(function.__defaults__,expected,trusted=trusted)
            and default_data_equal(function.__kwdefaults__,kw,trusted=trusted),
            'CALLER_FUNCTION_DEFAULTS_CHANGED:'+node.name)


def validate_structure(cls,node,namespace):
    if not issubclass(cls,(C.Structure,C.Union)):return
    expected=None
    for entry in node.body:
        if isinstance(entry,ast.Assign) and any(isinstance(target,ast.Name) and target.id=='_fields_' for target in entry.targets):
            expected=data_value(entry.value,namespace)
    require(expected is not None and cls._fields_==expected,'CALLER_ABI_FIELDS_CHANGED:'+node.name)
    # Reconstruct only a data layout, not an API. Compare native field offsets
    # and complete size/alignment; a forged _fields_ list cannot hide the old
    # ctypes layout that was actually created by its metaclass.
    shadow=type('_Checked'+node.name,(C.Structure if issubclass(cls,C.Structure) else C.Union,),{'_fields_':expected})
    require(C.sizeof(cls)==C.sizeof(shadow) and C.alignment(cls)==C.alignment(shadow)
            and all(getattr(cls,row[0]).offset==getattr(shadow,row[0]).offset
                    and getattr(cls,row[0]).size==getattr(shadow,row[0]).size for row in expected),
            'CALLER_ABI_LAYOUT_CHANGED:'+node.name)


def validate_definitions(module,raw,*,overrides=None,functions=None):
    """Check every directly declared function/method against pinned bytecode."""
    overrides=overrides or {}
    namespace=vars(module);filename=module.__file__;codes=code_index(raw,filename)
    tree=ast.parse(raw,filename)
    for node in tree.body:
        if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
            if node.name not in overrides and (functions is None or node.name in functions):
                function=namespace.get(node.name)
                if [ast.unparse(value) for value in node.decorator_list]==['contextmanager']:
                    wrapped=getattr(function,'__wrapped__',None)
                    require(type(wrapped) is types.FunctionType and type(function) is types.FunctionType,
                            'CALLER_CONTEXT_WRAPPER_CHANGED')
                    reference=contextlib.contextmanager(wrapped)
                    function_matches(function,reference.__code__,vars(contextlib))
                    require(function.__closure__ is not None and len(function.__closure__)==1
                            and function.__closure__[0].cell_contents is wrapped,'CALLER_CONTEXT_WRAPPER_CLOSURE_CHANGED')
                    function=wrapped
                function_matches(function,codes[node.name],namespace)
                validate_defaults(function,node,namespace)
        elif isinstance(node,ast.ClassDef):
            if functions is not None:continue
            cls=namespace.get(node.name)
            require(isinstance(cls,type) and cls.__module__==module.__name__
                    and cls.__qualname__==node.name,'CALLER_CLASS_BINDING_CHANGED:'+node.name)
            require(cls.__bases__==tuple(data_value(base,namespace) for base in node.bases) if node.bases else cls.__bases__==(object,),
                    'CALLER_CLASS_BASES_CHANGED:'+node.name)
            validate_structure(cls,node,namespace)
            for member in node.body:
                if isinstance(member,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    key=node.name+'.'+member.name
                    if key in overrides:continue
                    actual=vars(cls).get(member.name)
                    if type(actual) is property:
                        candidates=(actual.fget,actual.fset,actual.fdel)
                        matches=[value for value in candidates if type(value) is types.FunctionType and value.__code__==codes[key]]
                        require(len(matches)==1,'CALLER_PROPERTY_CHANGED:'+key)
                        function_matches(matches[0],codes[key],namespace);validate_defaults(matches[0],member,namespace)
                    else:
                        decorators=[ast.unparse(value) for value in member.decorator_list]
                        if 'classmethod' in decorators:require(type(actual) is classmethod,'CALLER_CLASSMETHOD_CHANGED')
                        elif 'staticmethod' in decorators:require(type(actual) is staticmethod,'CALLER_STATICMETHOD_CHANGED')
                        else:require(type(actual) is types.FunctionType,'CALLER_METHOD_DESCRIPTOR_CHANGED')
                        function=unwrap(actual);function_matches(function,codes[key],namespace)
                        validate_defaults(function,member,namespace)
    # Imports from CETA are identity bindings, including relative aliases used
    # by the canonical launcher, control API and resource observation contracts.
    for node in tree.body:
        if isinstance(node,ast.ImportFrom):
            imported=node.module or ''
            if node.level:imported=importlib.util.resolve_name('.'*node.level+imported,module.__package__)
            if imported and imported!='__future__':
                target=sys.modules.get(imported)
                require(type(target) is types.ModuleType,'CALLER_IMPORTED_MODULE_MISSING:'+imported)
                for alias in node.names:
                    if alias.name!='*':
                        require(namespace.get(alias.asname or alias.name) is vars(target).get(alias.name),
                                'CALLER_IMPORTED_ALIAS_CHANGED:'+alias.name)
        elif isinstance(node,ast.Import):
            for alias in node.names:
                name=alias.asname or alias.name.split('.')[0]
                expected=sys.modules.get(alias.name if alias.asname else alias.name.split('.')[0])
                require(expected is not None and namespace.get(name) is expected,'CALLER_STDLIB_ALIAS_CHANGED:'+name)
        elif functions is None and isinstance(node,ast.Assign) and declarative(node.value):
            if all(isinstance(target,ast.Name) and target.id in overrides for target in node.targets):continue
            expected=data_value(node.value,namespace)
            for target in node.targets:
                if isinstance(target,ast.Name) and target.id not in overrides:
                    actual=namespace.get(target.id)
                    require(type(actual) is type(expected) and actual==expected,'CALLER_MODULE_DATA_CHANGED:'+target.id)
    if module.__name__=='ceta.supervisor.windows_jobs':
        require(namespace['INVALID_HANDLE']==(1<<64)-1,'CALLER_INVALID_HANDLE_CONSTANT_CHANGED')
    return codes


def module_path(name):
    return 'src/'+name.replace('.','/')+'.py'


def validate_ceta_modules(inputs,*,allow_imports=True):
    root=Path(inputs['ac7_candidate']);src=root/'src';pins=inputs['ac7_payload_hashes']
    snapshot={name:module for name,module in tuple(sys.modules.items()) if name=='ceta' or name.startswith('ceta.')}
    def inspect():
        result={}
        for key,module in tuple(sys.modules.items()):
            if type(module) is types.ModuleType and (module.__name__=='ceta' or module.__name__.startswith('ceta.')):
                require(key==module.__name__,'CALLER_CETA_MODULE_ALIAS_REFUSED')
            if not (key=='ceta' or key.startswith('ceta.')):continue
            require(type(module) is types.ModuleType and module.__name__==key,'CALLER_REAL_SOURCE_MODULE_REQUIRED')
            relative=module_path(key)
            package=False
            if relative not in pins:
                relative='src/'+key.replace('.','/')+'/__init__.py';package=True
            require(relative in pins,'CALLER_UNEXPECTED_CETA_MODULE:'+key)
            path=root/relative;spec=module.__spec__;loader=module.__loader__
            require(type(module.__file__) is str and Path(module.__file__).resolve()==path.resolve(),
                    'CALLER_MODULE_ORIGIN_CHANGED:'+key)
            require(type(spec) is ModuleSpec and spec.name==key and spec.origin==module.__file__
                    and spec.has_location and type(loader) is SourceFileLoader and spec.loader is loader
                    and loader.name==key and Path(loader.path).resolve()==path.resolve()
                    and set(vars(loader))=={'name','path'},'CALLER_MODULE_SPEC_CHANGED:'+key)
            expected_package=key if package else key.rpartition('.')[0]
            require(module.__package__==expected_package,'CALLER_PACKAGE_CHANGED:'+key)
            if package:
                expected=[str(path.parent)]
                require(type(module.__path__) is list and module.__path__==expected
                        and type(spec.submodule_search_locations) is list
                        and spec.submodule_search_locations==expected,'CALLER_PACKAGE_PATH_CHANGED:'+key)
            else:require(spec.submodule_search_locations is None,'CALLER_SOURCE_SPEC_PACKAGE_CHANGED')
            require(namespace_builtins(module),'CALLER_BUILTINS_BINDING_CHANGED')
            raw=source_bytes(path,pins[relative]);result[key]=(module,raw)
            parent=key.rpartition('.')[0]
            if parent in sys.modules:
                require(vars(sys.modules[parent]).get(key.rpartition('.')[2]) is module,
                        'CALLER_PARENT_MODULE_ALIAS_CHANGED:'+key)
        return result
    admitted=inspect()
    if allow_imports:
        if str(src) not in sys.path:sys.path.insert(0,str(src))
        for name in ('ceta.supervisor.isolated_worker','ceta.supervisor.windows_jobs','ceta.supervisor.service'):
            importlib.import_module(name)
        admitted=inspect()
    for name,module in snapshot.items():require(sys.modules.get(name) is module,'CALLER_EXISTING_IMPORT_REPLACED')
    # Constructor custody wrappers are validated separately against the exact
    # pinned qualification driver closure. No general monkeypatch exception.
    for name,(module,raw) in admitted.items():
        overrides={}
        if name=='ceta.supervisor.isolated_worker':overrides={'_IsolationAPI.__init__':True}
        elif name=='ceta.supervisor.windows_jobs':overrides={'WindowsOwnedProcess.__init__':True}
        validate_definitions(module,raw,overrides=overrides)
    return admitted


def namespace_builtins(module):
    return vars(module).get('__builtins__') is builtins.__dict__


def transform_helper(raw):
    """Exact existing AC7 prepare_probe transform; no helper code is executed."""
    body=raw.decode('utf8').replace('\r\n','\n')
    changes=[("    name = 'CETA.AC1.' + uuid.uuid4().hex\n",'    name = '+repr(NAME)+'\n'),
        ('    fs.write_new(image, fs.read_bytes(original))\n',
         '    fs.write_new(image, fs.read_bytes(original))\n    assert sha(image) == '+repr(WORKER)+'\n'),
        ('    control, api = _ControlApi(), _IsolationAPI()\n',
         '    check_launch_paths(fixture, image)\n    control, api = _ControlApi(), _IsolationAPI()\n'),
        ('        worker = IsolatedWindowsWorker.launch(',
         "        target_alive_before = trusted.poll() is None\n        assert target_alive_before, 'owned target exited before worker'\n        worker = IsolatedWindowsWorker.launch("),
        ("        assert worker.wait(10), 'probe did not exit'\n",
         "        assert worker.wait(10), 'probe did not exit'\n        target_alive_after = trusted.poll() is None\n        assert target_alive_after, 'owned target exited during worker'\n"),
        ("'creation_time': trusted.creation_time, 'integrity': integrity},",
         "'creation_time': trusted.creation_time, 'integrity': integrity, 'alive_before_worker': target_alive_before, 'alive_after_worker': target_alive_after},")]
    for before,after in changes:
        require(body.count(before)==1,'CALLER_DECLARED_HELPER_TRANSFORM_CHANGED')
        body=body.replace(before,after)
    require(body.count('expected_image_sha256=sha(image)')==2,'CALLER_IMAGE_TRANSFORM_CHANGED')
    return body.replace('expected_image_sha256=sha(image)','expected_image_sha256='+repr(WORKER)).encode('utf8')


class ChildPipeClosure:
    """Exact canonical close/remove ordering, with an explicit unknown state."""
    def __init__(self,control,children,owned_handles):
        self.control=control;self.children=children;self.owned_handles=owned_handles
        self.creator_thread=threading.get_ident();self.state='NOT_ATTEMPTED';self.current=None
        self.closed=[]
    def __call__(self):
        require(threading.get_ident()==self.creator_thread,'CALLER_CREATOR_THREAD_REQUIRED')
        require(self.state=='NOT_ATTEMPTED','CALLER_PIPE_CLOSURE_NO_REPLAY')
        try:
            for handle in self.children:
                require(self.owned_handles.count(handle)==1,'CALLER_PIPE_OWNERSHIP_CHANGED')
                self.current=handle;self.state='CLOSE_IN_FLIGHT'
                self.control.close(handle)
                self.state='CLOSE_RETURNED'
                self.owned_handles.remove(handle)
                self.closed.append(handle)
            self.current=None;self.state='CLOSED'
        except BaseException as error:
            data=BaseException.__dict__['__dict__'].__get__(error)
            dict.__setitem__(data,'loader_child_pipe_custody',self)
            raise


@dataclass(frozen=True,slots=True)
class PreparedCaller:
    helper:types.ModuleType
    support:types.ModuleType
    shim:types.ModuleType
    driver:types.ModuleType
    control:object
    owned_handles:list
    close_child_pipe_ends:ChildPipeClosure
    directory:Path
    creator_thread:int
    qualification_run:object=None


def validate_wrappers(ctx,admitted,driver_codes):
    isolation=admitted['ceta.supervisor.isolated_worker'][0]
    jobs=admitted['ceta.supervisor.windows_jobs'][0]
    wrappers=[]
    for module,cls_name,key,closure_name in ((isolation,'_IsolationAPI','api_init','original_api'),
                                            (jobs,'WindowsOwnedProcess','owner_init','original_owner')):
        cls=vars(module)[cls_name];function=vars(cls)['__init__']
        expected=code_index(admitted[module.__name__][1],module.__file__)[cls_name+'.__init__']
        if type(function) is types.FunctionType and function.__code__==expected:
            function_matches(function,expected,vars(module));wrappers.append('original');continue
        require(ctx.qualification_run is not None,'CALLER_UNAPPROVED_CUSTODY_WRAPPER')
        function_matches(function,driver_codes['_QualificationRun.execute.<locals>.'+key],vars(ctx.driver))
        cells=dict(zip(function.__code__.co_freevars,(cell.cell_contents for cell in function.__closure__ or ()),strict=True))
        require(set(cells)=={closure_name,'self'} and cells['self'] is ctx.qualification_run,
                'CALLER_CUSTODY_WRAPPER_CLOSURE_CHANGED')
        function_matches(cells[closure_name],expected,vars(module))
        run_type=vars(ctx.driver).get('_QualificationRun')
        require(type(ctx.qualification_run) is run_type and ctx.qualification_run.directory==ctx.directory,
                'CALLER_QUALIFICATION_OWNER_CHANGED')
        for field,kind in (('apis',isolation._IsolationAPI),('owners',jobs.WindowsOwnedProcess)):
            values=getattr(ctx.qualification_run,field)
            require(type(values) is list and len(values)<=128 and all(isinstance(value,kind) for value in values),
                    'CALLER_CUSTODY_COLLECTION_CHANGED')
        wrappers.append(code_digest(function.__code__))
    return wrappers


def validate_reader(module,policy,name):
    raw=source_bytes(policy['path'],policy['sha256'])
    require(type(module) is types.ModuleType and module.__name__==name and sys.modules.get(name) is module
            and Path(module.__file__)==Path(policy['path']) and type(module.__spec__) is ModuleSpec
            and module.__spec__.name==name and module.__spec__.origin==module.__file__
            and type(module.__loader__) is SourceFileLoader and module.__spec__.loader is module.__loader__
            and module.__loader__.name==name and Path(module.__loader__.path)==Path(module.__file__)
            and set(vars(module.__loader__))=={'name','path'} and namespace_builtins(module),
            'CALLER_READER_SOURCE_BINDING_CHANGED')
    validate_definitions(module,raw,functions={'require','io_path','lstat','exists','reparse','safe_components',
        'read_bytes','open_source','file_identity','hash_file','write_new'})


def native_control_members(control):
    """Validate exact existing _ControlApi function-pointer ABI, no call/load.

    Native pointers can only be obtained by the previously approved caller's
    constructor. This does not construct one or infer handle liveness from its
    integer. Runtime GetHandleInformation/type checks follow after admission.
    """
    H=C.c_void_p;D=C.c_uint32;B=C.c_int32;p=C.POINTER
    service=sys.modules['ceta.supervisor.service']
    declarations=dict(CreatePipe=([p(H),p(H),p(service._Attributes),D],B),
        SetHandleInformation=([H,D,D],B),PeekNamedPipe=([H,H,D,p(D),p(D),p(D)],B),
        ReadFile=([H,H,D,p(D),H],B),WriteFile=([H,H,D,p(D),H],B),CloseHandle=([H],B),
        CreateEventW=([C.c_void_p,W.BOOL,W.BOOL,W.LPCWSTR],H))
    require(set(vars(control))==set(declarations),'CALLER_NATIVE_CONTROL_MEMBERS_CHANGED')
    result={}
    for name,(arguments,restype) in declarations.items():
        value=vars(control)[name]
        require(isinstance(value,C._CFuncPtr) and value.__name__==name
                and value.argtypes==arguments and value.restype is restype
                and value._flags_==C._FUNCFLAG_USE_LASTERROR,
                'CALLER_NATIVE_CONTROL_ABI_CHANGED:'+name)
        # Casting an existing pointer is a data conversion, no lookup or call.
        address=C.cast(value,C.c_void_p).value
        require(type(address) is int and address>0,'CALLER_NATIVE_CONTROL_ADDRESS_MISSING')
        result[name]=dict(object_id=id(value),address=address)
    return result


def validate_prepared(ctx,inputs,release,launch_arguments,stdout_handle,stderr_handle,callback,*,match_release=True):
    """All named binding checks are pure and precede attempt/native admission."""
    require(type(ctx) is PreparedCaller,'CALLER_EXACT_PREPARED_CONTEXT_REQUIRED')
    require(ctx.creator_thread==threading.get_ident(),'CALLER_CREATOR_THREAD_REQUIRED')
    require(type(callback) is ChildPipeClosure and callback is ctx.close_child_pipe_ends,'CALLER_UNAPPROVED_PIPE_CALLBACK')
    own_codes=code_index(Path(__file__).read_bytes(),__file__)
    for method in ('__init__','__call__'):
        function_matches(vars(ChildPipeClosure)[method],own_codes['ChildPipeClosure.'+method],globals())
    require(callback.control is ctx.control and callback.owned_handles is ctx.owned_handles
            and callback.creator_thread==ctx.creator_thread and callback.state=='NOT_ATTEMPTED'
            and callback.closed==[] and callback.current is None,'CALLER_PIPE_CUSTODY_CHANGED')
    children=launch_arguments.get('standard_handles');parents=(stdout_handle,stderr_handle)
    require(type(children) is tuple and len(children)==3 and len(set(children))==3
            and all(type(handle) is int and 0<handle<(1<<64)-1 for handle in children+parents),
            'CALLER_EXACT_HANDLES_REQUIRED')
    require(len(set(children+parents))==5 and tuple(callback.children)==children
            and type(ctx.owned_handles) is list and len(set(ctx.owned_handles))==len(ctx.owned_handles)
            and all(type(handle) is int and 0<handle<(1<<64)-1 for handle in ctx.owned_handles)
            and 5<=len(ctx.owned_handles)<=16 and all(ctx.owned_handles.count(handle)==1 for handle in children+parents),
            'CALLER_HANDLE_OWNERSHIP_CHANGED')
    require(launch_arguments.get('inherited_handles')==() and list(parents)==release['parent_output_handles'],
            'CALLER_HANDLE_RELEASE_CHANGED')
    root=Path(inputs['ac7_candidate']);directory=Path(ctx.directory);fixture=Path(release['fixture_root'])
    require(directory.resolve().is_relative_to(F/'.agents/runtime') and fixture.parent.name=='native-fixtures'
            and fixture.parent.parent.resolve()==directory.resolve(),'CALLER_PREPARED_DIRECTORY_CHANGED')
    policy=inputs['caller_contract'];admitted=validate_ceta_modules(inputs)
    isolation=admitted['ceta.supervisor.isolated_worker'][0];jobs=admitted['ceta.supervisor.windows_jobs'][0]
    service=admitted['ceta.supervisor.service'][0]
    require(type(ctx.control) is service._ControlApi,'CALLER_CONTROL_OWNER_CHANGED')
    require(type(ctx.control.close) is types.MethodType and ctx.control.close.__func__ is service._ControlApi.close,
            'CALLER_CONTROL_CLOSE_CHANGED')
    modules=(ctx.helper,ctx.support,ctx.shim,ctx.driver)
    require(all(type(module) is types.ModuleType and sys.modules.get(module.__name__) is module for module in modules),
            'CALLER_CAPTURED_MODULE_IDENTITY_CHANGED')
    require(ctx.helper.__name__=='profile_r2_captured_native_probe'
            and ctx.support.__name__=='profile_r2_captured_ac_support' and ctx.shim.__name__=='ac_support',
            'CALLER_CAPTURED_MODULE_NAMES_CHANGED')
    helper_raw=source_bytes(policy['helper']['path'],policy['helper']['sha256'])
    helper_expected=transform_helper(helper_raw)
    require(Path(ctx.helper.__file__)==directory/'native_fixture_support.py'
            and source_bytes(ctx.helper.__file__,hashlib.sha256(helper_expected).hexdigest())==helper_expected,
            'CALLER_HELPER_TRANSFORM_CHANGED')
    support_raw=source_bytes(policy['support']['path'],policy['support']['sha256'])
    require(Path(ctx.support.__file__)==directory/'ac3_support.py'
            and source_bytes(ctx.support.__file__,policy['support']['sha256'])==support_raw,
            'CALLER_SUPPORT_COPY_CHANGED')
    for module,raw in ((ctx.helper,helper_expected),(ctx.support,support_raw)):
        require(module.__spec__ is None and module.__loader__ is None,'CALLER_CAPTURED_MODULE_SPEC_CHANGED')
        require(namespace_builtins(module),'CALLER_BUILTINS_BINDING_CHANGED')
        validate_definitions(module,raw,overrides={'write_new':True,'Q':True,'R':True,'D':True})
    require(ctx.shim.__spec__ is None and ctx.shim.__loader__ is None,'CALLER_SHIM_SPEC_CHANGED')
    driver_raw=source_bytes(policy['driver']['path'],policy['driver']['sha256'])
    require(Path(ctx.driver.__file__)==Path(policy['driver']['path']) and namespace_builtins(ctx.driver),
            'CALLER_DRIVER_ORIGIN_CHANGED')
    driver_spec=ctx.driver.__spec__;driver_loader=ctx.driver.__loader__
    if ctx.driver.__name__=='__main__':
        require(driver_spec is None,'CALLER_DRIVER_SCRIPT_SPEC_CHANGED')
    else:
        require(ctx.driver.__name__=='ac6_single_attempt_preflight' and type(driver_spec) is ModuleSpec
                and driver_spec.name==ctx.driver.__name__ and driver_spec.origin==ctx.driver.__file__
                and type(driver_loader) is SourceFileLoader and driver_spec.loader is driver_loader
                and driver_loader.name==ctx.driver.__name__ and driver_loader.path==ctx.driver.__file__,
                'CALLER_DRIVER_SOURCE_SPEC_CHANGED')
    driver_codes=validate_definitions(ctx.driver,driver_raw)
    require(ctx.driver.module is isolation and ctx.driver.WindowsOwnedProcess is jobs.WindowsOwnedProcess
            and ctx.driver.Q==root and ctx.driver.F==F,'CALLER_DRIVER_ALIAS_CHANGED')
    wrappers=validate_wrappers(ctx,admitted,driver_codes)
    expected_aliases=dict(IsolatedWindowsWorker=isolation.IsolatedWindowsWorker,_IsolationAPI=isolation._IsolationAPI,
        SID_AND_ATTRIBUTES=isolation.SID_AND_ATTRIBUTES,appcontainer_sid=isolation.appcontainer_sid,
        WindowsOwnedProcess=jobs.WindowsOwnedProcess,HANDLE=jobs.HANDLE,DWORD=jobs.DWORD,
        _ControlApi=service._ControlApi,_Attributes=service._Attributes)
    for name,value in expected_aliases.items():require(vars(ctx.helper).get(name) is value,'CALLER_HELPER_ALIAS_CHANGED:'+name)
    for module in (ctx.helper,ctx.support,ctx.shim):
        require(module.F==F and module.P==F and module.Q==root and module.R==directory and module.D==directory,
                'CALLER_SUPPORT_ROOT_CHANGED')
    for name,value in vars(ctx.support).items():
        if not name.startswith('_'):
            require(vars(ctx.shim).get(name) is value,'CALLER_SHIM_ALIAS_CHANGED:'+name)
            require(vars(ctx.helper).get(name) is value or name in expected_aliases,
                    'CALLER_HELPER_SUPPORT_ALIAS_CHANGED:'+name)
    # The exact owned_write_new closure in prepare_probe captures only directory
    # and retains the driver's existing require/save globals.
    write=ctx.support.write_new
    function_matches(write,driver_codes['prepare_probe.<locals>.owned_write_new'],vars(ctx.driver))
    cells=dict(zip(write.__code__.co_freevars,(cell.cell_contents for cell in write.__closure__ or ()),strict=True))
    require(cells=={'directory':directory},'CALLER_EVIDENCE_WRITER_CLOSURE_CHANGED')
    require(ctx.helper.check_launch_paths is ctx.driver.check_launch_paths,'CALLER_PATH_GUARD_ALIAS_CHANGED')
    require(ctx.helper.fs is ctx.support.fs and ctx.shim.fs is ctx.support.fs,'CALLER_READER_ALIAS_CHANGED')
    validate_reader(ctx.support.fs,policy['reader'],'ac2_qualified_native_reader')
    validate_reader(ctx.driver.fs,policy['reader'],'profile_r2_native_reader')
    snapshot=dict(creator_thread=ctx.creator_thread,directory=str(directory),module_ids={module.__name__:id(module) for module in modules},
        ceta_module_ids={name:id(module) for name,(module,_) in admitted.items()},
        children=list(children),parents=list(parents),owned_handles=list(ctx.owned_handles),control_id=id(ctx.control),
        control_close_id=id(ctx.control.close.__func__),control_members={name:id(value) for name,value in vars(ctx.control).items()},
        callback_id=id(callback),callback_code=code_digest(type(callback).__call__.__code__),wrappers=wrappers,
        isolation_class_id=id(isolation.IsolatedWindowsWorker),api_class_id=id(isolation._IsolationAPI),
        owner_class_id=id(jobs.WindowsOwnedProcess))
    if match_release:require(snapshot==release.get('caller_binding'),'CALLER_RELEASE_BINDING_CHANGED')
    return isolation,snapshot
