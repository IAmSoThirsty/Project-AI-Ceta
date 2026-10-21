"""In-process integration point for the existing AC7 fixture's owned pipes.

The canonical caller provisions its fixture/profile and constructs its exact
launch mapping and handles. This function introduces no replacement launcher,
PID selection, fixture service, profile creation or handle-opening path.
"""
from isolated_adapter import launch_isolated_capture
from capture_core import retain, require


def execute_prepared_capture(*, release_path, release_sha256, launch_arguments,
                             stdout_handle, stderr_handle, close_child_pipe_ends,caller_context=None):
    """One capture and explicit retirement on the creator thread.

    close_child_pipe_ends is the canonical caller's already-owned pipe closure,
    called once after successful launch, before any collector pump. The caller
    retains parent read ends until return or unresolved-custody handoff. The
    function never retries an uncertain native operation or discards an owner.
    """
    require(callable(close_child_pipe_ends), 'CAPTURE_CANONICAL_PIPE_CLOSURE_REQUIRED')
    session = launch_isolated_capture(release_path=release_path, release_sha256=release_sha256,
        launch_arguments=launch_arguments, stdout_handle=stdout_handle, stderr_handle=stderr_handle,
        caller_context=caller_context,close_child_pipe_ends=close_child_pipe_ends)
    primary = None
    report = None
    try:
        close_child_pipe_ends()
        report = session.collect()
    except BaseException as error:
        primary = error
        retain(error, capture=session, owner=session.owner)
        if not session.persist_started:
            try:
                session.persist(error)
            except BaseException as secondary:
                retain(error, capture=session, owner=session.owner, secondary=secondary)
        raise
    finally:
        try:
            retirement = session.retire()
        except BaseException as secondary:
            if primary is None:
                retain(secondary, capture=session, owner=session.owner)
                raise
            retain(primary, capture=session, owner=session.owner, secondary=secondary)
    return dict(capture=report, retirement=retirement, native_qualification=False,
                startup_failure_causality='Only explicit captured diagnostics may narrow UNKNOWN')


if __name__ == '__main__':
    raise SystemExit('No standalone native launcher. Invoke execute_prepared_capture in the '
                     'exact reviewed AC7 fixture process after separate action-specific owner approval.')
