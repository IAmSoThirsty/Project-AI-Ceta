"""Process-local qualification observations; no GC suppression or assertion edits."""
import ctypes as C
from ctypes import wintypes as W
import functools,gc


def native_handle_count():
    kernel=C.WinDLL('kernel32',use_last_error=True,winmode=0x800)
    current=kernel.GetCurrentProcess;current.argtypes=[];current.restype=W.HANDLE
    count=kernel.GetProcessHandleCount;count.argtypes=[W.HANDLE,C.POINTER(W.DWORD)];count.restype=W.BOOL
    def observe():
        saved=C.get_last_error()
        try:
            value=W.DWORD()
            if not count(current(),C.byref(value)):raise OSError(C.get_last_error(),'GetProcessHandleCount(current)')
            return value.value
        finally:C.set_last_error(saved)
    return observe


class Observer:
    def __init__(self,count):
        self.count=count;self.gc_rows=[];self.test_rows=[];self.handle_rows=[]
        self.failed=False;self.current=None;self.api_sequence=0;self.restore=None
    def append(self,collection,value):
        try:collection.append(value)
        except BaseException:self.failed=True
    def callback(self,phase,info):
        saved=C.get_last_error()
        try:self.append(self.gc_rows,{'phase':phase,'test_id':self.current,'generation':info['generation'],
            'collected':info.get('collected'),'uncollectable':info.get('uncollectable'),'process_handles':self.count()})
        except BaseException:self.failed=True
        finally:C.set_last_error(saved)
    def before_test(self,test_id):
        self.current=test_id;before=self.count();collected=gc.collect();after=self.count()
        self.append(self.test_rows,{'test_id':test_id,'before_collect_handles':before,
            'collected_objects':collected,'after_collect_handles':after,'gc_enabled':gc.isenabled()})
    def install(self,api_class=None):
        gc.callbacks.append(self.callback)
        if api_class is None:return
        original=api_class.__init__;observer=self
        @functools.wraps(original)
        def initialize(api,*args,**kwargs):
            original(api,*args,**kwargs);observer.api_sequence+=1;identity=observer.api_sequence
            for operation in ('CreateFileW','CreateJobObjectW','CreateProcessW'):
                native=getattr(api,operation)
                def wrapped(*a,_native=native,_operation=operation,**k):
                    result=_native(*a,**k);saved=C.get_last_error()
                    try:observer.append(observer.handle_rows,{'api_sequence':identity,'operation':_operation,
                        'result':result,'last_error':saved,'test_id':observer.current})
                    except BaseException:observer.failed=True
                    finally:C.set_last_error(saved)
                    return result
                functools.update_wrapper(wrapped,native)
                for field in ('argtypes','restype'):
                    if hasattr(native,field):setattr(wrapped,field,getattr(native,field))
                setattr(api,operation,wrapped)
            close=api.close
            @functools.wraps(close)
            def closing(handle):
                try:result=close(handle)
                except BaseException:
                    saved=C.get_last_error()
                    try:observer.append(observer.handle_rows,{'api_sequence':identity,'operation':'close',
                        'handle':handle,'returned':False,'test_id':observer.current})
                    except BaseException:observer.failed=True
                    finally:C.set_last_error(saved)
                    raise
                saved=C.get_last_error()
                try:observer.append(observer.handle_rows,{'api_sequence':identity,'operation':'close',
                    'handle':handle,'returned':True,'test_id':observer.current})
                except BaseException:observer.failed=True
                finally:C.set_last_error(saved)
                return result
            api.close=closing
        api_class.__init__=initialize
        self.restore=lambda:setattr(api_class,'__init__',original)
    def uninstall(self):
        if self.restore is not None:self.restore();self.restore=None
        gc.callbacks.remove(self.callback)
