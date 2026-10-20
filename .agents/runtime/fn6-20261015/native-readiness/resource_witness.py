"""Observational qualification harness. It grants no product authority."""
import threading
import time


def storage(error):
    return BaseException.__dict__['__dict__'].__get__(error)


def retained_return(owner, register, emit, retire):
    """Custody covers registry insertion and logging, not only field reads."""
    try:
        register(owner)
        emit(owner)
        return owner
    except BaseException as primary:
        secondary = None
        try:
            retire(owner)
        except BaseException as failure:
            secondary = failure
        try:
            dict.update(storage(primary), exact_recorder_owner=owner,
                        recorder_cleanup_error=secondary, recorder_retry_performed=False)
        except BaseException:
            pass
        raise


class Witness:
    """Strong exact-object references and native return facts; no PID reopening."""
    def __init__(self, label=lambda: None):
        self.label = label
        self.calls, self.handles, self.owners = [], [], []
        self.journals, self.clocks, self.threads, self.fixtures = [], [], [], []
        self.registrations = []
        self.observation_errors = []
        self._lock = threading.Lock()
        self._sequence = 0

    def row(self, kind, **values):
        with self._lock:
            if self._sequence >= 100_000:
                raise RuntimeError('WITNESS_RECORD_BOUND')
            self._sequence += 1
            row = dict(sequence=self._sequence, kind=kind, test_id=self.label(), **values)
            list.append(self.calls, row)
            return row

    def acquire(self, api, value, kind, row, parent=None):
        value = int(value or 0)
        if value in (0, -1, 2**64 - 1):
            return None
        record = dict(allocation=row['sequence'], api_id=id(api), handle=value, kind=kind,
                      root=parent['root'] if parent else row['sequence'], closed_at=None)
        list.append(self.handles, record)
        return record

    def find(self, api, value):
        value = int(value or 0)
        return next((r for r in reversed(self.handles) if r['api_id'] == id(api)
                     and r['handle'] == value and r['closed_at'] is None), None)

    def closed(self, api, value, row):
        record = self.find(api, value)
        row['allocation'] = record['allocation'] if record else None
        if record is not None:
            record['closed_at'] = row['sequence']

    def install(self, windows, jobs, clock, journal, sqlite, custody, emit, fixture_fact, worker_gate):
        """Called only after the supervisor's reviewed release was consumed."""
        import ctypes as C
        from ctypes import wintypes as W
        original_api = windows._API.__init__
        original_launch = windows.WindowsOwnedProcess.launch.__func__
        original_fixture = jobs.WindowsJobTests.setUp
        original_journal = journal.SqliteJournal.__init__
        original_clock = clock.NativeSessionClock.__init__
        original_clock_api = clock._NativeClockAPI.__init__
        original_start, original_join = threading.Thread.start, threading.Thread.join
        witness = self

        def api_init(api):
            original_api(api)
            # Preserve C last-error around observation so the original caller
            # receives the exact native function's status/error pair.
            def bind(name, observer):
                raw = getattr(api, name)
                def called(*args):
                    entry = witness.row(name, api_id=id(api))
                    result = raw(*args)
                    error = C.get_last_error()
                    try:
                        observer(entry, args, result)
                    except BaseException as failure:
                        # A post-native observer is not allowed to prevent
                        # canonical launch/close from receiving its result.
                        # Retain the exact error; deny qualification later.
                        list.append(witness.observation_errors, failure)
                    finally:
                        C.set_last_error(error)
                    return result
                setattr(api, name, called)
            def created(kind):
                def observe(entry, args, result):
                    entry['result_handle'] = int(result or 0)
                    witness.acquire(api, result, kind, entry)
                return observe
            bind('CreateJobObjectW', created('job'))
            bind('CreateFileW', created('image_file'))
            def process(entry, args, result):
                entry.update(native_success=bool(result), executable=args[0],
                             inherit_handles=bool(args[4]), creation_flags=int(args[5]), cwd=args[7])
                if result:
                    info = C.cast(args[-1], C.POINTER(windows.PROCESS_INFORMATION)).contents
                    witness.acquire(api, info.process, 'process', entry)
                    # Two outputs from one native call must have distinct
                    # allocation IDs, despite a shared acquisition call.
                    thread_entry = witness.row('CreateProcessW.startup_thread', api_id=id(api))
                    witness.acquire(api, info.thread, 'startup_thread', thread_entry)
                    entry['pid'] = int(info.pid)
            bind('CreateProcessW', process)
            def duplicate(entry, args, result):
                entry['native_success'] = bool(result)
                if result:
                    parent = witness.find(api, args[1])
                    value = C.cast(args[3], C.POINTER(windows.HANDLE)).contents.value
                    entry['source_allocation'] = parent['allocation'] if parent else None
                    witness.acquire(api, value, 'duplicate', entry, parent)
            bind('DuplicateHandle', duplicate)
            def close(entry, args, result):
                entry.update(handle=int(args[0] or 0), native_success=bool(result))
                if result:
                    witness.closed(api, args[0], entry)
            bind('CloseHandle', close)
            def wait(entry, args, result):
                record = witness.find(api, args[0])
                entry.update(root=record['root'] if record else None, handle=int(args[0] or 0),
                             result=int(result), timeout_ms=int(args[1]))
            bind('WaitForSingleObject', wait)
            def exit_code(entry, args, result):
                record = witness.find(api, args[0])
                entry.update(root=record['root'] if record else None, native_success=bool(result),
                             exit_code=int(C.cast(args[1], C.POINTER(windows.DWORD)).contents.value) if result else None)
            bind('GetExitCodeProcess', exit_code)
            def process_times(entry, args, result):
                record = witness.find(api, args[0])
                entry.update(root=record['root'] if record else None, native_success=bool(result))
                if result:
                    created = C.cast(args[1], C.POINTER(W.FILETIME)).contents
                    entry['creation_time'] = int(created.dwHighDateTime << 32 | created.dwLowDateTime)
            bind('GetProcessTimes', process_times)
            def query(entry, args, result):
                record = witness.find(api, args[0])
                entry.update(allocation=record['allocation'] if record else None,
                             native_success=bool(result), information_class=int(args[1]))
                if result and args[1] == 1:
                    entry['active_processes'] = int(C.cast(args[2], C.POINTER(windows.ACCOUNTING)).contents.active_processes)
                if result and args[1] == 15:
                    policy = C.cast(args[2], C.POINTER(windows.CPU_RATE_CONTROL)).contents
                    entry.update(observed_control_flags=int(policy.control_flags), observed_value=int(policy.value))
            bind('QueryInformationJobObject', query)
            raw_set = api.SetInformationJobObject
            def set_information(*args):
                record = witness.find(api, args[0])
                if type(args[1]) is not int or args[1] not in (9, 15) or record is None or record['kind'] != 'job':
                    raise RuntimeError('UNDECLARED_NATIVE_SET')
                entry = witness.row('SetInformationJobObject', allocation=record['allocation'],
                                    information_class=args[1])
                if args[1] == 15:
                    policy = C.cast(args[2], C.POINTER(windows.CPU_RATE_CONTROL)).contents
                    entry.update(requested_control_flags=int(policy.control_flags), requested_value=int(policy.value))
                result = raw_set(*args)
                error = C.get_last_error()
                try:
                    entry['native_success'] = bool(result)
                except BaseException as failure:
                    list.append(self.observation_errors, failure)
                finally:
                    C.set_last_error(error)
                return result
            api.SetInformationJobObject = set_information

        def launch(cls, executable, arguments=(), **kwargs):
            worker_gate(executable, arguments, kwargs)
            owner = original_launch(cls, executable, arguments, **kwargs)
            # The canonical constructor has returned, so this local already
            # owns the exact process/job even if registration itself fails.
            def register(value):
                api = value._api
                record = dict(owner=value, api=api, initial_process=int(value._process),
                    initial_thread=None, initial_job=int(value._job), pid=value.pid,
                    image_sha256=value.image_sha256,
                    process_allocation=self.find(api, value._process),
                    job_allocation=self.find(api, value._job), test_id=self.label())
                list.append(self.owners, record)
                self.row('returned_exact_owner', object_id=id(value))
                if self.observation_errors:
                    raise self.observation_errors[0]
            return retained_return(owner, register, emit, custody.retire)

        def fixture_setup(fixture):
            original_fixture(fixture)
            list.append(self.fixtures, dict(object=fixture, path=str(fixture.directory),
                                           native_identity=fixture_fact(fixture.directory)))
            raw = fixture.api.CreateEventW
            def create_event(*args):
                entry = self.row('CreateEventW', api_id=id(fixture.api))
                value = raw(*args)
                error = C.get_last_error()
                try:
                    entry['name'] = args[3]
                    self.acquire(fixture.api, value, 'event', entry)
                except BaseException as failure:
                    list.append(self.observation_errors, failure)
                finally:
                    C.set_last_error(error)
                return value
            fixture.api.CreateEventW = create_event
            def denied(*args, **kwargs):
                raise RuntimeError('NO_PID_REOPEN_OR_UNDECLARED_CHANNEL')
            fixture.api.OpenProcess = denied
            fixture.api.CreatePipe = denied

        def journal_init(owner, *args, **kwargs):
            record = dict(owner=owner, connection=None, test_id=self.label())
            list.append(self.journals, record)
            try:
                return original_journal(owner, *args, **kwargs)
            finally:
                record['connection'] = getattr(owner, '_connection', None)

        def clock_init(owner, *args, **kwargs):
            list.append(self.clocks, dict(owner=owner, test_id=self.label()))
            return original_clock(owner, *args, **kwargs)

        def clock_api_init(api):
            original_clock_api(api)
            register, unregister = api.PowerRegisterSuspendResumeNotification, api.PowerUnregisterSuspendResumeNotification
            def register_observed(*args):
                entry = self.row('PowerRegisterSuspendResumeNotification', api_id=id(api))
                status = register(*args)
                error = C.get_last_error()
                try:
                    value = C.cast(args[2], C.POINTER(W.HANDLE)).contents.value
                    entry.update(status=int(status), handle=int(value or 0))
                    if value:
                        list.append(self.registrations, dict(api_id=id(api), handle=int(value),
                            registration_sequence=entry['sequence'], register_status=int(status), unregistered_at=None))
                except BaseException as failure:
                    list.append(self.observation_errors, failure)
                finally:
                    C.set_last_error(error)
                return status
            def unregister_observed(handle):
                entry = self.row('PowerUnregisterSuspendResumeNotification', api_id=id(api), handle=int(handle))
                status = unregister(handle)
                error = C.get_last_error()
                try:
                    entry['status'] = int(status)
                    record = next((r for r in reversed(self.registrations) if r['api_id'] == id(api)
                        and r['handle'] == int(handle) and r['unregistered_at'] is None), None)
                    entry['registration_sequence'] = record['registration_sequence'] if record else None
                    if status == 0 and record is not None:
                        record['unregistered_at'] = entry['sequence']
                except BaseException as failure:
                    list.append(self.observation_errors, failure)
                finally:
                    C.set_last_error(error)
                return status
            api.PowerRegisterSuspendResumeNotification = register_observed
            api.PowerUnregisterSuspendResumeNotification = unregister_observed

        def thread_start(thread, *args, **kwargs):
            record = dict(thread=thread, start_returned=False, joins=[], test_id=self.label())
            list.append(self.threads, record)
            result = original_start(thread, *args, **kwargs)
            record['start_returned'] = True
            return result

        def thread_join(thread, *args, **kwargs):
            result = original_join(thread, *args, **kwargs)
            record = next((r for r in self.threads if r['thread'] is thread), None)
            if record is not None:
                list.append(record['joins'], dict(timeout=args[0] if args else kwargs.get('timeout'),
                                                 returned=True, alive_after=thread.is_alive()))
            return result

        windows._API.__init__ = api_init
        windows.WindowsOwnedProcess.launch = classmethod(launch)
        jobs.WindowsJobTests.setUp = fixture_setup
        journal.SqliteJournal.__init__ = journal_init
        clock.NativeSessionClock.__init__ = clock_init
        clock._NativeClockAPI.__init__ = clock_api_init
        threading.Thread.start, threading.Thread.join = thread_start, thread_join
        self.sqlite = sqlite

    def result(self):
        owners = []
        for record in self.owners:
            owner, process, job = record['owner'], record['process_allocation'], record['job_allocation']
            exit_waits = [r for r in self.calls if r['kind'] == 'WaitForSingleObject'
                          and process is not None and r.get('root') == process['root'] and r.get('result') == 0]
            exit_codes = [r for r in self.calls if r['kind'] == 'GetExitCodeProcess'
                          and process is not None and r.get('root') == process['root']
                          and r.get('native_success') and r.get('exit_code') != 259]
            empty = [r for r in self.calls if r['kind'] == 'QueryInformationJobObject'
                     and job is not None and r.get('allocation') == job['allocation']
                     and r.get('native_success') and r.get('active_processes') == 0]
            creation = [r for r in self.calls if r['kind'] == 'GetProcessTimes' and process is not None
                        and r.get('root') == process['root'] and r.get('native_success')
                        and r.get('creation_time') == owner.creation_time]
            native_closed = process is not None and job is not None and process['closed_at'] is not None and job['closed_at'] is not None
            owners.append(dict(object_id=id(owner), test_id=record['test_id'], pid=record['pid'],
                creation_time=owner.creation_time, image_sha256=record['image_sha256'],
                process_handle=record['initial_process'], job_handle=record['initial_job'],
                startup_thread_handle=record['initial_thread'], native_exit_wait_sequences=[r['sequence'] for r in exit_waits],
                actual_retained_creation_sequences=[r['sequence'] for r in creation],
                native_exit_codes=[r['exit_code'] for r in exit_codes], native_empty_job_sequences=[r['sequence'] for r in empty],
                process_close_sequence=process['closed_at'] if process else None,
                job_close_sequence=job['closed_at'] if job else None,
                exact_native_retirement=bool(native_closed and exit_waits and exit_codes and empty and creation),
                logical_closed=owner.lifetime_closed,
                residual_startup_handles=list(owner._cleanup_handles)))
        journals = []
        for record in self.journals:
            owner, connection = record['owner'], record['connection']
            closed = False
            if connection is not None:
                try:
                    connection.in_transaction
                except self.sqlite.ProgrammingError:
                    closed = True
                except BaseException as failure:
                    list.append(self.observation_errors, failure)
            journals.append(dict(object_id=id(owner), connection_object_id=id(connection) if connection else None,
                                 path=str(getattr(owner, 'path', 'UNAVAILABLE')), test_id=record['test_id'],
                                 exact_connection_closed_getter=closed, logical_closed=getattr(owner, '_closed', False)))
        clocks = []
        for record in self.clocks:
            owner = record['owner']
            row = dict(object_id=id(owner), test_id=record['test_id'], state='UNAVAILABLE')
            try:
                thread = getattr(owner, '_thread', None)
                row.update(api_id=id(getattr(owner, '_api', None)),
                    registration_current=getattr(owner, '_registration', None),
                    callbacks_active=getattr(owner, '_callbacks', None), state=owner.status().state,
                    sampler_object_id=id(thread) if thread is not None else None,
                    sampler_alive=thread.is_alive() if thread is not None else False,
                    sampler_native_id=thread.native_id if thread is not None else None)
                status = owner.status()
                row.update(boot_guid=getattr(status, 'boot_guid', None),
                           durable_epoch=getattr(status, 'durable_epoch', None),
                           resume_generation=getattr(status, 'resume_generation', None))
            except BaseException as failure:
                list.append(self.observation_errors, failure)
                row['observation_error_type'] = type(failure).__name__
            clocks.append(row)
        for row in clocks:
            registrations = [r for r in self.registrations if r['api_id'] == row.get('api_id')]
            row['native_registration_and_unregister_observed'] = (len(registrations) == 1
                and registrations[0]['register_status'] == 0 and registrations[0]['unregistered_at'] is not None)
            row['native_registration_sequence'] = registrations[0]['registration_sequence'] if len(registrations) == 1 else None
            row['native_unregister_sequence'] = registrations[0]['unregistered_at'] if len(registrations) == 1 else None
        threads = [dict(object_id=id(r['thread']), native_id=r['thread'].native_id, name=r['thread'].name,
                        test_id=r['test_id'], started=r['start_returned'], alive=r['thread'].is_alive(),
                        joins=r['joins']) for r in self.threads]
        open_handles = [r for r in self.handles if r['closed_at'] is None]
        remaining_registrations = [r for r in self.registrations if r['unregistered_at'] is None]
        fixtures = [{k: v for k, v in r.items() if k != 'object'} for r in self.fixtures]
        closed = bool(owners and all(r['exact_native_retirement'] and r['logical_closed']
                                     and not r['residual_startup_handles'] for r in owners)
            and journals and all(r['exact_connection_closed_getter'] and r['logical_closed'] for r in journals)
            and clocks and all(r['state'] == 'CLOSED' and r['registration_current'] is None
                              and not r['sampler_alive'] and r['callbacks_active'] == 0
                              and r['native_registration_and_unregister_observed'] for r in clocks)
            and all(not r['alive'] and r['joins'] and not r['joins'][-1]['alive_after'] for r in threads)
            and not open_handles and not remaining_registrations and not self.observation_errors)
        return dict(owners=owners, journals=journals, clocks=clocks, threads=threads,
                    handles=self.handles, registrations=self.registrations, fixture_directories=fixtures,
                    native_calls=self.calls, remaining_handles=open_handles,
                    remaining_registrations=remaining_registrations, owned_resources_closed=closed,
                    exact_observation_errors_retained=len(self.observation_errors),
                    observation_error_types=[type(e).__name__ for e in self.observation_errors],
                    historical_or_numeric_pid_reopening=False,
                    child_internal_event_handles='Fixed child finally blocks; child exit/empty job observed, not individually instrumented')
