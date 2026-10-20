"""Concrete, explicitly selected native owners for the manual CPU profile.

Selections are trusted-process inputs. No selection is loaded from CLI fields,
environment discovery, a receipt, or an untrusted configuration file. This owner
does not create an AppContainer profile or change host/filesystem policy.
"""
from dataclasses import dataclass
from pathlib import Path
import threading

from ceta.composition.native_cpu_runtime import NativeCpuConfiguration, NativeCpuRuntime
from ceta.composition.real_effect_service import ManualEffectLimits, ManualRealEffectSession
from ceta.contracts.kernel_transactions import commitment, identifier, require
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.contracts.wire import ContractError, RecordCodec
from ceta.effects.native_cpu_binding import NativeCpuBinding
from ceta.effects.native_observer import NativeCpuEffectObserver, observer_code_commitment
from ceta.identity.native_clock import NativeSessionClock
from ceta.identity.native_code_binding import CodePin, NativeCodeBinding
from ceta.identity.windows_pipe import WindowsPeerRegistry
from ceta.store.journal import SqliteJournal
from ceta.store.outcome_capacity import OutcomeCapacityBudget, OutcomeCapacityRuntime
from ceta.supervisor.isolated_worker import IsolatedWindowsWorker, IsolatedLaunchError


@dataclass(frozen=True)
class ManualRuntimeSelection:
    """Reviewed deployment inputs supplied only by the trusted composition root.

    The canonical owner must supply its actual durable epoch; this value does not
    create or advance an epoch. Code pins identify the complete selected surface.
    Constructing this record establishes no native or profile qualification.
    """
    private_root: Path
    scratch_root: Path
    installation_scope_id: str
    scope_id: str
    durable_epoch: int
    code_pins: tuple[CodePin, ...]
    policy_commitment: str
    adapter_commitment: str
    helper_name: str
    helper_source_name: str
    worker_name: str
    observer_name: str
    observer_source_name: str
    capacity_helper_name: str
    appcontainer_name: str
    capacity_budget: OutcomeCapacityBudget
    limits: ManualEffectLimits
    create: bool = False
    work_duration_ms: int = 30000

    def __post_init__(self):
        require(type(self.private_root) is type(Path()) and self.private_root.is_absolute()
            and type(self.scratch_root) is type(Path()) and self.scratch_root.is_absolute()
            and self.private_root != self.scratch_root, 'MANUAL_PROFILE_ABSOLUTE_ROOTS_REQUIRED')
        identifier(self.installation_scope_id)
        identifier(self.scope_id)
        require(self.installation_scope_id != self.scope_id,
            'MANUAL_PROFILE_DISTINCT_SCOPES_REQUIRED')
        require(type(self.durable_epoch) is int and 0 <= self.durable_epoch <= 2**63 - 1,
            'MANUAL_PROFILE_CANONICAL_EPOCH_REQUIRED')
        require(type(self.code_pins) is tuple and self.code_pins
            and all(type(pin) is CodePin for pin in self.code_pins),
            'MANUAL_PROFILE_REVIEWED_MANIFEST_REQUIRED')
        for pin in self.code_pins:
            pin.__post_init__()
        commitment(self.policy_commitment)
        commitment(self.adapter_commitment)
        names = (self.helper_name, self.helper_source_name, self.worker_name,
            self.observer_name, self.observer_source_name, self.capacity_helper_name)
        require(all(type(n) is str and 0 < len(n) <= 512 for n in names)
            and len(set(names)) == len(names), 'MANUAL_PROFILE_MANIFEST_NAMES_REQUIRED')
        for group, name in (('environment', self.helper_name), ('source', self.helper_source_name),
            ('environment', self.worker_name), ('environment', self.observer_name),
            ('source', self.observer_source_name), ('environment', self.capacity_helper_name)):
            require(sum(pin.group == group and pin.logical_name == name
                for pin in self.code_pins) == 1, 'MANUAL_PROFILE_NAMED_PIN_REQUIRED')
        require(type(self.appcontainer_name) is str
            and self.appcontainer_name.startswith('CETA.')
            and 6 <= len(self.appcontainer_name) <= 64
            and all(c.isascii() and (c.isalnum() or c in '._-') for c in self.appcontainer_name),
            'MANUAL_PROFILE_CONTAINER_SELECTION_REQUIRED')
        require(type(self.capacity_budget) is OutcomeCapacityBudget
            and type(self.limits) is ManualEffectLimits and type(self.create) is bool,
            'MANUAL_PROFILE_TYPED_CONFIGURATION_REQUIRED')
        self.capacity_budget.__post_init__()
        self.limits.__post_init__()
        require(type(self.work_duration_ms) is int and 1 <= self.work_duration_ms <= 30000,
            'MANUAL_PROFILE_WORK_DURATION_BOUND')


def _retain(primary, profile, secondary=None):
    data = BaseException.__dict__['__dict__'].__get__(primary)
    dict.__setitem__(data, 'manual_real_effect_profile', profile)
    if secondary is not None:
        previous = dict.get(data, 'manual_real_effect_profile_cleanup_errors', ())
        dict.__setitem__(data, 'manual_real_effect_profile_cleanup_errors', previous + (secondary,))


class ManualRealEffectProfile:
    """Own the concrete runtime dependencies; native effects are explicit methods.

    Construction loads native clock/VFS owners and may create a selected journal.
    It must therefore be called only by an explicitly released trusted host, never
    merely because a command declares a profile. Worker launch is a separate step.
    """
    def __init__(self, selection, codec):
        require(type(selection) is ManualRuntimeSelection and type(codec) is RecordCodec,
            'MANUAL_PROFILE_TRUSTED_SELECTION_REQUIRED')
        selection.__post_init__()
        self.selection, self.limits = selection, selection.limits
        self.adapter_commitment = selection.adapter_commitment
        self._thread, self._state = threading.get_ident(), 'BUILDING'
        self.code = self.clock = self.observer = self.store = self.registry = self.runtime = None
        self.capacity = None
        self.worker = self._binding = None
        self._worker_launch_attempted = False
        self._worker_launch_error = None
        self._session = None
        self._initialized = []
        self._failed_constructor = None
        self._constructor_history = []
        try:
            # Publish each partial native owner before its fallible initializer.
            self._construct('code', NativeCodeBinding, selection.code_pins)
            self._construct('clock', NativeSessionClock, selection.durable_epoch)
            capacity = self._pin('environment', selection.capacity_helper_name)
            self._construct('capacity', OutcomeCapacityRuntime, capacity.path, capacity.sha256)
            observer = self._pin('environment', selection.observer_name)
            driver = self._pin('source', selection.observer_source_name)
            observed_code = observer_code_commitment(observer.sha256, driver.sha256)
            self._construct('observer', NativeCpuEffectObserver, observer.path,
                observer.sha256, observed_code, clock=self.clock)
            self._construct('registry', WindowsPeerRegistry)
            self._construct('store', SqliteJournal, selection.private_root, codec,
                (selection.installation_scope_id, selection.scope_id), create=selection.create,
                profile=STORE_PROFILE, outcome_runtime=self.capacity)
            configuration = NativeCpuConfiguration(self.clock, self.code, self.capacity,
                selection.capacity_budget, self.observer, selection.scope_id,
                selection.policy_commitment, selection.helper_name, selection.helper_source_name,
                selection.worker_name, selection.observer_name, selection.observer_source_name,
                selection.capacity_helper_name)
            self._construct('runtime', NativeCpuRuntime, self.store, codec,
                selection.installation_scope_id, self.registry, configuration)
            self._state = 'ACTIVE'
        except BaseException as primary:
            # Constructors already own their partial cleanup. Do not replay it.
            self._state = 'PENDING'
            _retain(primary, self)
            raise

    def _construct(self, name, kind, *args, **kwargs):
        owner = object.__new__(kind)
        setattr(self, name, owner)
        try:
            kind.__init__(owner, *args, **kwargs)
        except BaseException as primary:
            self._failed_constructor = (name, owner, primary)
            raise
        self._initialized.append(name)

    def retire_failed_constructor(self):
        """Explicit partial-owner retirement; never replay an initializer.

        Pre-API branches below are the concrete constructors' no-acquisition
        states. Unknown connection/API cleanup still refuses in those owners.
        Loaded DLLs follow the existing runtime's process lifetime; this does
        not unload libraries or report their handles retired.
        """
        require(threading.get_ident() == self._thread and self._state == 'PENDING'
            and self._failed_constructor is not None and self._session is None,
            'MANUAL_PROFILE_FAILED_CONSTRUCTOR_REQUIRED')
        name, owner, original = self._failed_constructor
        require(getattr(self, name) is owner and name not in self._initialized,
            'MANUAL_PROFILE_PARTIAL_OWNER_CHANGED')
        data = object.__getattribute__(owner, '__dict__')
        try:
            if name == 'code':
                # NativeCodeBinding publishes _api/_files/_ancestors together,
                # before its first _retain/open. API binding acquires no files.
                if '_api' in data:
                    NativeCodeBinding.close(owner)
                else:
                    require('_files' not in data and '_ancestors' not in data,
                        'MANUAL_PROFILE_PARTIAL_CODE_CUSTODY_UNKNOWN')
            elif name == 'clock':
                if '_registration' in data:
                    NativeSessionClock.close(owner)
                else:
                    require('_api' not in data and '_thread' not in data,
                        'MANUAL_PROFILE_PARTIAL_CLOCK_CUSTODY_UNKNOWN')
            elif name == 'runtime':
                NativeCpuRuntime.close(owner)
            elif name == 'store':
                if '_connection' in data:
                    SqliteJournal.close(owner)
                # The current initializer publishes this field before file
                # creation or SQLite connection acquisition.
            elif name == 'registry':
                if '_lock' in data:
                    WindowsPeerRegistry.close(owner)
                else:
                    require(not data.get('_entries'), 'MANUAL_PROFILE_PARTIAL_REGISTRY_PENDING')
                # Before _entries publication only export binding has occurred.
            elif name == 'observer':
                custody = dict.get(BaseException.__dict__['__dict__'].__get__(original),
                    'source_hash_custody')
                if custody is not None:
                    custody.close()
                    require(custody.closed, 'MANUAL_PROFILE_PARTIAL_SOURCE_PIN_PENDING')
                require('_custody' not in data or data['_custody'] is None,
                    'MANUAL_PROFILE_PARTIAL_OBSERVER_PENDING')
            elif name == 'capacity':
                require(self.store is None, 'MANUAL_PROFILE_PARTIAL_VFS_PENDING')
                # This initializer loads/binds the helper. VFS registration
                # starts only in SqliteJournal, which has not been called.
            else:
                raise ContractError('MANUAL_PROFILE_PARTIAL_CONSTRUCTOR_UNKNOWN')
            self._constructor_history.append(self._failed_constructor)
            setattr(self, name, None)
            self._failed_constructor = None
        except BaseException as cleanup:
            _retain(cleanup, self)
            _retain(original, self, cleanup)
            raise

    def _pin(self, group, name):
        entries = [p for p in self.selection.code_pins if p.group == group and p.logical_name == name]
        require(len(entries) == 1, 'MANUAL_PROFILE_NAMED_PIN_REQUIRED')
        return entries[0]

    def require_session(self, session):
        require(threading.get_ident() == self._thread and self._state in ('ACTIVE', 'PENDING')
            and self._session is session and session.profile is self
            and session.runtime is self.runtime, 'MANUAL_PROFILE_ORIGINAL_SESSION_REQUIRED')

    def command_session(self, original_context):
        require(threading.get_ident() == self._thread and self._state == 'ACTIVE'
            and self._session is None, 'MANUAL_PROFILE_SESSION_ALREADY_OWNED')
        # Authentication precedes all command-session publication and native work.
        self.registry.authenticate(original_context)
        session = ManualRealEffectSession(self, original_context)
        self._session = session
        return session

    def retire_session(self, session):
        self.require_session(session)
        require(session.closed, 'MANUAL_PROFILE_SESSION_RETIREMENT_UNPROVED')
        self._session = None

    def cpu_binding(self):
        require(threading.get_ident() == self._thread and self._state == 'ACTIVE'
            and self._session is not None, 'MANUAL_PROFILE_ORIGINAL_SESSION_REQUIRED')
        if not self._worker_launch_attempted:
            self._worker_launch_attempted = True
            pin = self._pin('environment', self.selection.worker_name)
            try:
                self.worker = IsolatedWindowsWorker.launch(pin.path,
                    ('cpu', str(self.selection.work_duration_ms)),
                    cwd=str(Path(pin.path).parent), scratch_root=str(self.selection.scratch_root),
                    expected_image_sha256=pin.sha256,
                    appcontainer_name=self.selection.appcontainer_name)
            except BaseException as primary:
                # A returned partial owner stays attached even if launch raised.
                self._worker_launch_error = primary
                data = BaseException.__dict__['__dict__'].__get__(primary)
                self.worker = dict.get(data, 'owned_process')
                _retain(primary, self)
                raise
        require(self._worker_launch_error is None and type(self.worker) is IsolatedWindowsWorker,
            'MANUAL_PROFILE_RESTRICTED_WORKER_UNAVAILABLE')
        if self._binding is None or self._binding._closed:
            self._binding = NativeCpuBinding(self.worker, self.clock,
                cancel_event=self.runtime._owner._stopped)
        return self._binding

    @property
    def closed(self):
        return self._state == 'CLOSED'

    def close(self):
        require(threading.get_ident() == self._thread, 'MANUAL_PROFILE_ORIGINAL_THREAD_REQUIRED')
        if self.closed:
            return
        self._state = 'PENDING'
        try:
            require(self._session is None, 'MANUAL_PROFILE_COMMAND_CUSTODY_PENDING')
            # Unknown partial constructor state needs its exact exposed recovery;
            # it cannot be guessed safe by calling an uninitialized close method.
            expected = ('code', 'clock', 'capacity', 'observer', 'registry', 'store', 'runtime')
            require(all(getattr(self, name) is None or name in self._initialized for name in expected),
                'MANUAL_PROFILE_PARTIAL_CONSTRUCTOR_CUSTODY_PENDING')
            if self.runtime is not None:
                self.runtime.close()
            if self._binding is not None:
                self._binding.close()
            if self.worker is not None and not self.worker.lifetime_closed:
                if self.worker.poll() is None:
                    self.worker.terminate(125)
                require(self.worker.wait(2) and self.worker.active_process_count() == 0,
                    'MANUAL_PROFILE_WORKER_RETIREMENT_UNOBSERVED')
                self.worker.close()
            if self._worker_launch_error is not None:
                error = self._worker_launch_error
                cleanup = dict.get(BaseException.__dict__['__dict__'].__get__(error), 'isolation_cleanup')
                if type(error) is IsolatedLaunchError:
                    IsolatedLaunchError.close_cleanup(error)
                elif type(cleanup) is IsolatedLaunchError:
                    IsolatedLaunchError.close_cleanup(cleanup)
                self._worker_launch_error = None
            if self.observer is not None:
                self.observer.close_cleanup()
            if self.store is not None:
                self.store.close()
            if self.registry is not None:
                self.registry.close()
            if self.clock is not None:
                self.clock.close()
            if self.code is not None:
                self.code.close()
            self._state = 'CLOSED'
        except BaseException as primary:
            _retain(primary, self)
            raise

    def __copy__(self):
        raise ContractError('MANUAL_PROFILE_COPY_FORBIDDEN')

    def __reduce_ex__(self, protocol):
        raise ContractError('MANUAL_PROFILE_SERIALIZATION_FORBIDDEN')
