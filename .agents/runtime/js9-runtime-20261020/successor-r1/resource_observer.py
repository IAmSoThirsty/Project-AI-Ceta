"""Transparent observations of exact newly returned resources; no API results changed."""
from pathlib import Path
import errno
import functools
import os


def attach(primary,owner,secondary=None):
    values=BaseException.__dict__['__dict__'].__get__(primary)
    dict.update(values,review_observation_owner=owner,review_observation_cleanup_error=secondary,
        review_observation_retirement_attempted=True,review_observation_automatic_retry=False)


def record_or_retire(registry,row,owner,close):
    """Failure before handing a newly returned owner to its caller closes once."""
    try:list.append(registry,row)
    except BaseException as primary:
        secondary=None
        try:close()
        except BaseException as error:secondary=error
        attach(primary,owner,secondary)
        raise


class Observer:
    def __init__(self,sqlite):
        self.sqlite=sqlite;self.connections=[];self.streams=[];self.descriptors=[];self.native=[]
        self.original_connect=sqlite.connect;self.original_open=Path.open
        self.original_os_open=os.open;self.original_os_close=os.close;self.installed=False

    def connect(self,*args,**kwargs):
        owner=self.original_connect(*args,**kwargs)
        try:
            row=self._connection_row(owner,args,kwargs)
            list.append(self.connections,row)
        except BaseException as primary:
            secondary=None
            try:owner.close()
            except BaseException as error:secondary=error
            attach(primary,owner,secondary)
            raise
        return owner

    @staticmethod
    def _connection_row(owner,args,kwargs):
        argument=args[0] if args else dict.get(kwargs,'database')
        return {'owner':owner,'object_id':id(owner),'database_argument':argument,
            'database':argument if type(argument) is str else None}

    def opened(self,path,*args,**kwargs):
        owner=self.original_open(path,*args,**kwargs)
        try:
            fd=owner.fileno();info=os.fstat(fd)
            row={'owner':owner,'object_id':id(owner),'descriptor':fd,'path':str(path),
                'device':info.st_dev,'inode':info.st_ino}
        except BaseException as primary:
            secondary=None
            try:owner.close()
            except BaseException as error:secondary=error
            attach(primary,owner,secondary);raise
        record_or_retire(self.streams,row,owner,lambda:owner.close())
        return owner

    def os_opened(self,path,flags,*args,**kwargs):
        fd=self.original_os_open(path,flags,*args,**kwargs)
        try:
            info=os.fstat(fd)
            row={'descriptor':fd,'path':str(path),'device':info.st_dev,'inode':info.st_ino,'closed':False}
        except BaseException as primary:
            secondary=None
            try:self.original_os_close(fd)
            except BaseException as error:secondary=error
            attach(primary,fd,secondary);raise
        record_or_retire(self.descriptors,row,fd,lambda:self.original_os_close(fd))
        return fd

    def os_closed(self,fd):
        self.original_os_close(fd)
        for row in self.descriptors:
            if row['descriptor']==fd and row['closed'] is False:row['closed']=True

    def install(self):
        assert not self.installed
        observer=self
        @functools.wraps(self.original_connect)
        def connect(*args,**kwargs):return observer.connect(*args,**kwargs)
        @functools.wraps(self.original_open)
        def opened(path,*args,**kwargs):return observer.opened(path,*args,**kwargs)
        self.sqlite.connect=connect;Path.open=opened;os.open=self.os_opened;os.close=self.os_closed
        self.installed=True

    def uninstall(self):
        if self.installed:
            self.sqlite.connect=self.original_connect;Path.open=self.original_open
            os.open=self.original_os_open;os.close=self.original_os_close;self.installed=False

    def observe_case(self,test):
        # All values come from this exact test's retained actual service owners.
        # No numeric PID lookup, reopening or mutation occurs here.
        import sys
        service_type=sys.modules['ceta.composition.owned_service'].OwnedService
        process_type=sys.modules['ceta.supervisor.windows_jobs'].WindowsOwnedProcess
        selected_native=test.id().startswith('test_shutdown_lifecycle.NativeShutdownTests.')
        services=[service for service in getattr(test,'services',()) if type(service) is service_type]
        if selected_native and len(services)!=1:raise RuntimeError('EXPECTED_NATIVE_SERVICE_CAPTURE_MISSING')
        captured=0
        for service in services:
            if type(service) is not service_type:continue
            for slot in ('_client','_service'):
                channel=getattr(service,slot,None)
                if channel is None:continue
                process=channel.process
                if process is None:continue
                assert type(process) is process_type
                closed={'process':process._process is None,'thread':process._thread is None,
                    'job':process._job is None,'startup_handles':not process._cleanup_handles,
                    'channel_input':channel._input is None,'channel_output':channel._output is None,
                    'channel_error':channel._error is None,'channel_child_handles':not channel._child_handles,
                    'channel_launch_custody':channel._launch_error is None}
                self.native.append({'test_id':test.id(),'slot':slot,'object_id':id(process),
                    'pid':process.pid,'creation_time':process.creation_time,'image_sha256':process.image_sha256,
                    'closed_native_designations':closed,'retired':all(closed.values()) and process.lifetime_closed})
                captured+=1
        if selected_native and captured!=2:raise RuntimeError('EXPECTED_TWO_NATIVE_CHANNEL_CAPTURES_MISSING')

    def finish(self):
        assert not self.installed
        connections=[];streams=[];remaining=[]
        for row in self.connections:
            owner=row['owner'];closed=False;observation=None
            try:owner.execute('SELECT 1')
            except self.sqlite.ProgrammingError as error:
                observation=str(error);closed=observation=='Cannot operate on a closed database.'
            except BaseException as error:observation=type(error).__name__
            value={key:value for key,value in row.items() if key not in ('owner','database_argument')}
            value.update(physical_closed_probe=closed,probe_observation=observation)
            connections.append(value)
            if not closed:remaining.append({'kind':'sqlite','object_id':row['object_id'],'database':row['database']})
        for row in self.streams:
            owner=row['owner'];closed=owner.closed
            try:owner.fileno();fileno_denied=False
            except ValueError:fileno_denied=True
            value={key:value for key,value in row.items() if key!='owner'}
            value.update(closed=closed,fileno_denied=fileno_denied);streams.append(value)
            if not (closed and fileno_denied):remaining.append({'kind':'stream','object_id':row['object_id'],'path':row['path']})
        for row in self.descriptors:
            if not row['closed']:remaining.append({'kind':'descriptor',**row})
        for row in self.native:
            if not row['retired']:remaining.append({'kind':'native-owner','test_id':row['test_id'],'pid':row['pid'],'creation_time':row['creation_time']})
        return {'sqlite':connections,'streams':streams,'os_descriptors':self.descriptors,'native_owners':self.native,
            'remaining_resources':remaining,'owned_resources_closed':not remaining,
            'no_logical_journal_closed_flags_used':True,'no_native_process_API_wrappers':True,
            'clock_registration_calls':0,'physical_probe_limits':'Only exact captured fixture-returned objects; no historical/native numeric adoption.'}
