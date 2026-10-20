"""Bounded CPU dispatch, original observation, and canonical outcome recording."""
from ceta.contracts.kernel_transactions import require
from ceta.identity.native_cpu_outcome import NativeCpuOutcomeProvenance
from ceta.identity.native_owner_view import NativeOwnerView
from ceta.kernel.cpu_execution import _RetainedCpuExecution

_DISPATCH = _RetainedCpuExecution.dispatch
_RECORD = _RetainedCpuExecution.record_outcome


def _retain(primary, lease, capture=None, outcome=None, secondary=None):
    # Diagnostic hooks cannot replace an interrupt, effect failure or custody.
    data = BaseException.__dict__['__dict__'].__get__(primary)
    data.update(owned_cpu_execution=lease, cpu_outcome_capture=capture, cpu_recorded_outcome=outcome)
    if secondary is not None:
        previous = dict.get(data, 'cpu_outcome_secondary_errors', ())
        if type(previous) is not tuple: previous = ()
        data['cpu_outcome_secondary_errors'] = previous + (secondary,)


class NativeCpuOutcomeAdapter:
    """Use the existing lease; never dispatch directly through UI or native Set."""
    def __init__(self, view):
        require(type(view) is NativeOwnerView and type(getattr(view, '_cpu_outcome', None)) is NativeCpuOutcomeProvenance,
                'CPU_OUTCOME_ADAPTER_COMPOSITION_REQUIRED')
        self._view, self._producer = view, view._cpu_outcome

    def _selected(self):
        require(self._view._cpu_outcome is self._producer and self._producer._view is self._view,
                'CPU_OUTCOME_ADAPTER_CHANGED')

    def reconcile(self, lease):
        """Advance observation only; preserve the original receipt and never redispatch."""
        self._selected()
        capture = self._producer.collect(lease)
        outcome, primary = None, capture.observation_error
        try:
            outcome = _RECORD(lease, capture.receipt_wire, capture.observation_wire, capture.proof)
        except BaseException as secondary:
            _retain(primary if primary is not None else secondary, lease, capture, outcome, secondary)
            if primary is None: raise
        if primary is not None:
            _retain(primary, lease, capture, outcome)
            raise primary
        return outcome

    def execute(self, lease):
        """One admitted dispatch, followed by observation and existing kernel write."""
        self._selected()
        self._producer.require_ready(lease)
        try:
            _DISPATCH(lease)
        except BaseException as primary:
            outcome = None
            if lease._dispatch:
                try: outcome = self.reconcile(lease)
                except BaseException as secondary: _retain(primary, lease, secondary=secondary)
            _retain(primary, lease, outcome=outcome)
            raise
        return self.reconcile(lease)
