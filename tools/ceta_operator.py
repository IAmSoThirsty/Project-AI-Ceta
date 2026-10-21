"""Launch native CETA tasks in an explicit disposable development profile."""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ceta.application.operator import OperatorSession
from ceta.application.task_operator import TaskOperatorSession
from ceta.application.lifecycle import (
    LauncherShutdownCustody, ShutdownCoordinator, ShutdownIncomplete,
)
from ceta.composition.owned_service import OwnedService
from ceta.contracts.wire import ContractError, RecordCodec, strict_loads


def _run_owned_operation(service, prepare, *, custody=None):
    """Run one owned UI lifetime and preserve the real owner on failure.

    ``custody`` is a restart fence only.  It must be marked before the ambiguous
    ``start()`` boundary and cannot stand in for the retained in-memory owner.
    The outer ``main`` process is responsible for retaining that owner until
    actual terminal observation when this function exports ``ShutdownIncomplete``.
    """
    binding = None
    if custody is not None:
        binding_factory = getattr(custody, "_coordinator_binding", None)
        if binding_factory is not None:
            binding = binding_factory()
    shutdown = ShutdownCoordinator(service, custody_binding=binding)
    primary = None
    try:
        run = prepare(shutdown)
        if custody is not None:
            custody.mark_start_requested()
        service.start()
        if custody is not None:
            custody.mark_start_returned()
        return run()
    except BaseException as error:
        primary = error
        raise
    finally:
        try:
            observed = shutdown.drain()
            if observed.workers_stopped:
                if custody is not None:
                    # The actual coordinator observation, not a successful
                    # request, is the only terminal record accepted here.
                    custody.mark_termination_observed(shutdown.terminal_settlement())
            else:
                raise ShutdownIncomplete(observed, shutdown.pending_owner)
        except BaseException as cleanup:
            incomplete = (cleanup if isinstance(cleanup, ShutdownIncomplete)
                          else ShutdownIncomplete(shutdown.observation,
                                                  shutdown.pending_owner,
                                                  cleanup_error=cleanup))
            if custody is not None:
                try:
                    # A PENDING record is not a handoff acknowledgement.  It
                    # only denies replacement work after an abnormal exit.
                    custody.mark_unresolved(incomplete.observation)
                except BaseException as custody_error:
                    incomplete.durable_custody_error = custody_error
            if primary is None:
                # Keep the actual cleanup BaseException (including an
                # interruption) primary; the typed owner remains attached.
                shutdown.retain_failure(cleanup, incomplete)
                raise
            # Preserve the original failure. Cleanup failure is separately
            # visible and must not be relabelled as a successful process exit.
            shutdown.retain_failure(primary, incomplete)


def _run_owned_ui(service, setup_ui, *, custody=None):
    """Preserve the existing UI setup/start/cleanup contract."""
    def prepare(shutdown):
        application, window = setup_ui(shutdown)
        window.show()
        return application.exec
    return _run_owned_operation(service, prepare, custody=custody)


def _run_owned_diagnostics(service, codec, envelope, *, custody=None, emit=True):
    """One explicit finite observation with the same retained shutdown owner."""
    def prepare(shutdown):
        session = OperatorSession(service, codec)
        shutdown.capture_session(session)
        def run():
            deadline = time.monotonic() + 15.0
            for _ in range(1501):
                observed = service.poll()
                if observed["state"] == "READY":
                    break
                if observed["state"] != "STARTING" or time.monotonic() >= deadline:
                    return 2, {"startup": "UNAVAILABLE", "operation": "NOT_EXECUTED",
                               "code": "DIAGNOSTICS_STARTUP_UNAVAILABLE"}
                time.sleep(0.01)
            else:
                return 2, {"startup": "UNAVAILABLE", "operation": "NOT_EXECUTED",
                           "code": "DIAGNOSTICS_STARTUP_DEADLINE"}
            try:
                result = session.resource_diagnostics(envelope)
            except ContractError as error:
                data = BaseException.__dict__["__dict__"].__get__(error)
                if "journal_custody" in data or "diagnostics_journal_custody" in data:
                    raise
                code = error.code.split(":", 1)[0]
                return 2, {"startup": "READY", "operation": "UNAVAILABLE",
                           "code": code if code.isidentifier() else "DIAGNOSTICS_UNAVAILABLE"}
            return (0 if result["state"] == "COMPLETE_PROCESS_USAGE" else 2), {
                "startup": "READY", "operation": result["state"], "diagnostics": result}
        return run
    try:
        code, report = _run_owned_operation(service, prepare, custody=custody)
    except ContractError as error:
        data = BaseException.__dict__["__dict__"].__get__(error)
        if (_attached_shutdown_incomplete(error) is not None
                or "journal_custody" in data or "diagnostics_journal_custody" in data):
            raise
        safe_code = error.code.split(":", 1)[0]
        code, report = 2, {"startup": "UNAVAILABLE", "operation": "NOT_EXECUTED",
                           "code": safe_code if safe_code.isidentifier() else "DIAGNOSTICS_STARTUP_UNAVAILABLE"}
    # Only successful owned shutdown can publish the final operation result.
    report["cleanup"] = "STOPPED"
    wire = json.dumps(report, separators=(",", ":"))
    if len(wire.encode("utf8")) > 32768:
        raise ContractError("DIAGNOSTICS_OUTPUT_BOUND")
    if emit:
        print(wire)
        return code
    return code, report


def _attached_shutdown_incomplete(error):
    """Read typed cleanup custody without trusting an exception subclass hook."""
    if isinstance(error, ShutdownIncomplete):
        return error
    try:
        values = BaseException.__dict__["__dict__"].__get__(error)
    except BaseException:
        return None
    incomplete = values.get("shutdown_incomplete")
    return incomplete if isinstance(incomplete, ShutdownIncomplete) else None


def _attach_custody_close_failure(primary, close_error):
    """Keep a final lock-release failure diagnostic without replacing primary.

    The launcher has already retained and settled the actual owned lifetime at
    this point.  A failure while releasing its *decision lock* is still useful
    diagnostic information, but Python's ``finally`` semantics must not let it
    replace the initiating application ``BaseException``.  Use the base
    exception dictionary so a hostile/custom ``__setattr__`` or ``add_note``
    implementation cannot become a second replacement path.
    """
    incomplete = _attached_shutdown_incomplete(primary)
    try:
        primary.add_note("LAUNCHER_CUSTODY_CLOSE_FAILED: " + type(close_error).__name__)
    except BaseException:
        pass
    # Export after the optional diagnostic hook.  A custom ``add_note`` may
    # erase or replace its own dictionary while returning successfully.
    try:
        BaseException.__dict__["__dict__"].__get__(primary)["launcher_custody_close_error"] = close_error
    except BaseException:
        pass
    if incomplete is not None:
        try:
            incomplete.launcher_custody_close_error = close_error
        except BaseException:
            pass


def _attempt_outer_custody_settlement(incomplete, custody, *, timeout_seconds=15.0):
    """Try one bounded retained-owner drain before an outer process may exit.

    ``False`` is deliberately not an error result.  It means this process still
    has the actual owner and must remain alive; a durable PENDING record alone
    cannot make the process exit safe.
    """
    owner = incomplete.pending_owner
    if owner is None:
        return False
    try:
        observed = owner.retry(timeout_seconds=timeout_seconds)
    except BaseException:
        try:
            custody.mark_unresolved(owner.observation)
        except BaseException:
            pass
        return False
    if observed.workers_stopped:
        try:
            custody.mark_termination_observed(owner.coordinator.terminal_settlement())
        except BaseException:
            # Descriptive STOPPED is not enough to cross the outer interpreter
            # boundary.  Keep the actual owner and PENDING restart fence until
            # the bound concrete-retirement/no-publication proof *and* durable
            # terminal transition both succeed.  A secondary persistence or
            # proof failure remains diagnostic without replacing the primary.
            try:
                custody.mark_unresolved(observed)
            except BaseException:
                pass
            return False
        return True
    try:
        custody.mark_unresolved(observed)
    except BaseException:
        pass
    return False


def _hold_outer_custody_until_settled(incomplete, custody):
    """Do not cross the interpreter boundary while the real owner is pending."""
    while True:
        try:
            if _attempt_outer_custody_settlement(incomplete, custody):
                return
        except BaseException:
            # A second interruption cannot be allowed to turn the already
            # retained owner into an outer-process abandonment.  The original
            # primary error remains pending for re-raise after settlement.
            pass
        try:
            # This is a retained-owner wait, not a replacement service or a
            # claim that the pending record itself can perform protected
            # custody.  A signal at this boundary must not become an implicit
            # authorization to cross the interpreter boundary.
            time.sleep(0.05)
        except BaseException:
            pass


def _hold_constructor_uncertainty():
    """Fail closed when construction never yielded an actual owner to observe."""
    while True:
        # The durable record makes a forced-process crash restart-safe.  It is
        # not evidence that no launch attempt can later publish, so ordinary
        # Python control flow may not exit through this condition.
        try:
            time.sleep(0.05)
        except BaseException:
            # No service/worker owner was returned by the constructor.  A
            # subsequent interruption provides neither a no-entry observation
            # nor a protected survivor acknowledgement.
            pass


def _validate_profile_root(root):
    """Match the composition's selected development-root boundary before writes."""
    root = Path(root)
    if (not root.is_absolute() or not root.is_dir()
            or not root.resolve(strict=True).is_relative_to(ROOT / ".agents/fixtures")):
        raise ValueError("SERVICE_DEVELOPMENT_ROOT_REQUIRED")
    for path in (root, *root.parents):
        if path.is_symlink() or getattr(path, "is_junction", lambda: False)():
            raise ValueError("SERVICE_ROOT_LINK_REJECTED")
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--inspector", action="store_true", help="Open the existing typed record inspector instead of task controls.")
    parser.add_argument("--diagnostics", action="store_true", help="Explicit finite installation process measurements; no GUI or background sampler.")
    parser.add_argument("--diagnostics-envelope", nargs=3, type=int, metavar=("LATENCY_MS", "CPU_MILLI", "MEMORY_BYTES"),
                        help="Required caller-declared, unqualified comparison limits for diagnostics.")
    args = parser.parse_args()
    if args.diagnostics and (args.inspector or args.diagnostics_envelope is None):
        parser.error("--diagnostics requires --diagnostics-envelope LATENCY_MS CPU_MILLI MEMORY_BYTES and excludes --inspector")
    if not args.diagnostics and args.diagnostics_envelope is not None:
        parser.error("--diagnostics-envelope requires --diagnostics")
    envelope = None
    if args.diagnostics:
        from ceta.resource.diagnostics import PerformanceEnvelope
        try:
            envelope = PerformanceEnvelope(*args.diagnostics_envelope)
        except ContractError:
            parser.error("diagnostic envelope values must be nonnegative integers")
    if args.profile is None:
        root = ROOT / ".agents/fixtures/operator-24" / uuid.uuid4().hex
        root.mkdir(parents=True, exist_ok=False)
        create = True
    else:
        root, create = args.profile, False
    # Import failures occur before a service is constructed, so no owned native
    # lifetime exists yet.  Once custody is reserved below, every setup failure
    # must flow through _run_owned_ui and its actual ShutdownCoordinator.
    if not args.diagnostics:
        from PySide6.QtWidgets import QApplication
        from ceta.desktop.operator_view import create_operator_window
        from ceta.desktop.task_view import TaskView
    root = _validate_profile_root(root)
    codec = RecordCodec(strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes()))
    custody = LauncherShutdownCustody(root)
    custody.reserve_launch()
    primary = None
    diagnostics_report = None
    try:
        try:
            service = OwnedService(root, codec, "installation:operator-development",
                                   ("installation:operator-development", "project:operator-development"), create=create)
        except BaseException:
            # A constructor exception gives no retained service/worker object
            # through which no-entry can be observed.  Preserve PENDING and do
            # not permit this interpreter to exit as though no owner existed.
            try:
                custody.mark_constructor_unresolved()
            except BaseException:
                pass
            _hold_constructor_uncertainty()
            raise  # pragma: no cover - the fail-closed hold never returns.
        def setup_ui(shutdown):
            application = QApplication(sys.argv[:1])
            if args.inspector:
                session = OperatorSession(service, codec)
                shutdown.capture_session(session)
                window = create_operator_window(session)
            else:
                session = TaskOperatorSession(service, "project:operator-development")
                shutdown.capture_session(session)
                window = TaskView(session)
            return application, window
        # Setup, showing the window, launch and event-loop failures all share the
        # same owner-aware shutdown path. Development profile selection is unchanged.
        try:
            if args.diagnostics:
                exit_status, diagnostics_report = _run_owned_diagnostics(service, codec, envelope, custody=custody, emit=False)
                return exit_status
            return _run_owned_ui(service, setup_ui, custody=custody)
        except BaseException as error:
            primary = error
            incomplete = _attached_shutdown_incomplete(error)
            if incomplete is not None:
                # There is no protected surviving supervisor/native broker in
                # this development composition.  Retain the actual owner here
                # until it observes terminal settlement, then re-raise the
                # exact original BaseException.
                _hold_outer_custody_until_settled(incomplete, custody)
            raise
    except BaseException as error:
        # Cover constructor/setup/hold failures too.  The final lock release
        # cannot be allowed to replace *any* exception leaving main(), not only
        # a failure from the owned UI lifetime.
        primary = error
        raise
    finally:
        try:
            custody.close()
        except BaseException as close_error:
            if primary is None:
                raise
            _attach_custody_close_failure(primary, close_error)
        else:
            if primary is None and diagnostics_report is not None:
                print(json.dumps(diagnostics_report, separators=(",", ":")))


if __name__ == "__main__":
    raise SystemExit(main())
