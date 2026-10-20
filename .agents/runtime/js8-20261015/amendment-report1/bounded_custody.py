"""One fixed disposable runner owner; engineering custody, no runtime authority."""
import time


def failure(error):
    try:message=str(error)
    except BaseException:message='<exception text unavailable>'
    return {'type':type(error).__name__,'message':message}


def attach(primary,**values):
    # BaseException storage and unbound dict avoid user diagnostic dispatch.
    data=BaseException.__dict__['__dict__'].__get__(primary)
    dict.update(data,values)


def retire(owner):
    """One attempt on this exact returned job, never a PID lookup or retry."""
    if owner.lifetime_closed:
        if owner._cleanup_handles:raise RuntimeError('FULL_RUNNER_RESIDUAL_STARTUP_HANDLES')
        return
    if owner.poll() is None or owner.active_process_count():owner.terminate(126)
    if not owner.wait(5):raise RuntimeError('FULL_RUNNER_RETIRE_WAIT_PENDING')
    deadline=time.perf_counter()+5
    while owner.active_process_count():
        if time.perf_counter()>=deadline:raise RuntimeError('FULL_RUNNER_RETIRE_JOB_PENDING')
        time.sleep(.001)
    owner.close()


def run_owned(launch,emit,read_child,*,timeout):
    """Evidence failures cannot bypass retirement; uncertain cleanup is retained."""
    owner=primary=cleanup=None
    report={'timeout_seconds':timeout,'native_owner':None,'child_exit':None,
        'primary_error':None,'retirement_error':None,'construction_custody':None,
        'native_owner_after':None,'child_result':None,'automatic_cleanup_retry':False}
    try:
        owner=launch()
        report['native_owner']={'pid':owner.pid,'creation_time':owner.creation_time,
            'image_sha256':owner.image_sha256}
        emit(report['native_owner'])
        if not owner.wait(timeout):raise TimeoutError('EXACT_FULL_TEST_RUNNER_BOUND_EXPIRED')
        report['child_exit']=owner.poll()
        deadline=time.perf_counter()+3
        while owner.active_process_count():
            if time.perf_counter()>=deadline:raise RuntimeError('FULL_CHILD_LEFT_OWN_JOB_MEMBERS')
            time.sleep(.001)
    except BaseException as error:
        primary=error
    finally:
        if owner is not None:
            try:retire(owner)
            except BaseException as error:
                cleanup=error
                if primary is None:primary=error
            # No fallible observation or final evidence precedes retirement.
            try:
                report['native_owner_after']={'closed':owner.lifetime_closed,
                    'process_closed':owner._process is None,'thread_closed':owner._thread is None,
                    'job_closed':owner._job is None,'startup_handles_closed':not owner._cleanup_handles}
                if not all(report['native_owner_after'].values()):
                    raise RuntimeError('FULL_RUNNER_CUSTODY_UNRESOLVED')
            except BaseException as error:
                report['final_observation_error']=failure(error)
                if primary is None:primary=error
        elif primary is not None:
            # A failed canonical constructor owns any partial cleanup itself.
            # Its retained exact owner must not receive an automatic retry.
            data=BaseException.__dict__['__dict__'].__get__(primary)
            report['construction_custody']={'retained_exact_owner':dict.get(data,'owned_process') is not None,
                'automatic_cleanup_retry':False}
    try:report['child_result']=read_child()
    except BaseException as error:
        report['child_result_read_error']=failure(error)
        if primary is None:primary=error
    report['retirement_error']=failure(cleanup) if cleanup is not None else None
    report['primary_error']=failure(primary) if primary is not None else None
    if primary is not None:
        try:attach(primary,full_runner_owner=owner,full_runner_recovery=(lambda:retire(owner)) if owner is not None else None,
            full_runner_cleanup_error=cleanup,full_runner_report=report)
        except BaseException:
            # Diagnostic failure is never authority to repeat native cleanup.
            pass
        raise primary
    return report
