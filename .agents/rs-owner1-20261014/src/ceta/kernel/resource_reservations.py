"""Resource accounting subordinate to the existing captured CMP02 owner.

The existing CMP03 store owns every write. This adapter provisions no budgets,
starts no workload and issues no authority. Missing resource-owner capabilities
deny; controlled owner fixtures do not establish live native authentication.
"""
from dataclasses import replace
import time
import uuid

from ceta.contracts.kernel_transactions import (basis_key, digest, read_basis, require)
from ceta.contracts.resource_management import (AdmissionState, ReservationRequest, ReservationResult)
from ceta.contracts.resource_reservations import (ResourceBudgetBinding, ResourceLease,
    read_resource_budget, request_value, resource_budget_key, resource_budget_wire, resource_lease_key)
from ceta.contracts.store_transactions import MAX_GENERATION
from ceta.contracts.temporal import require_deadline_current, utc_nanoseconds
from ceta.contracts.wire import ContractError


class KernelResourceReservations:
    """A ReservationPort bound by composition to one proposal and opaque context.

    Expected budget generations and all authority dependencies use the owner's
    existing one-snapshot/one-transaction CAS. Only confirmed conflict exceptions
    permit a read of the SAME request; no new allocation is automatically retried.
    Cleanup and recovery preserve terminal tombstones and do not redeem effects.
    """
    def __init__(self, kernel, proposal_wire: bytes, request_context: object, *,
                 maximum_observation_age_ns: int = 2_000_000_000,
                 maximum_owner_check_ns: int = 50_000_000):
        require(type(maximum_observation_age_ns) is int and 0 < maximum_observation_age_ns <= 60_000_000_000,
                "RESOURCE_OBSERVATION_AGE_BOUND_INVALID")
        require(type(maximum_owner_check_ns) is int and 0 < maximum_owner_check_ns <= 1_000_000_000,
                "RESOURCE_OWNER_CHECK_BOUND_INVALID")
        self._kernel = kernel
        self._proposal = kernel._decode(proposal_wire, "ActionProposal")
        self._context = request_context
        self._maximum_age_ns, self._maximum_check_ns = maximum_observation_age_ns, maximum_owner_check_ns

    def _timed(self, callback, *arguments):
        started = time.perf_counter_ns()
        try:
            result = callback(*arguments)
        except OSError as error:
            raise ContractError("RESOURCE_AUTHORITY_OWNER_UNAVAILABLE") from error
        elapsed = time.perf_counter_ns() - started
        require(0 <= elapsed <= self._maximum_check_ns, "RESOURCE_OWNER_CHECK_TOO_LONG")
        return result

    def _peer(self):
        return self._timed(self._kernel._peer, self._context)

    def _clock(self, progress=True):
        return self._timed(self._kernel._clock, progress)

    def _owner_check(self, name, *arguments):
        callback = getattr(self._kernel._owners, name, None)
        require(callable(callback), "RESOURCE_AUTHORITY_OWNER_UNAVAILABLE")
        result = self._timed(callback, *arguments)
        require(result is None, "KERNEL_OWNER_DECISION_INVALID")

    def _budget(self, cells, key):
        binding, budget = read_resource_budget(self._kernel._present(cells, key), key)
        require(budget.generation == cells[key].generation, "RESOURCE_BUDGET_GENERATION_MISMATCH")
        return binding, budget

    def _subject(self, binding, peer):
        p = self._proposal.as_dict()
        require(binding.scope_id == p["scope_id"] and binding.task_id == p["task_id"]
                and binding.proposal_commitment == self._proposal.commitment
                and (binding.principal_id, binding.session_id) == (peer.principal_id, peer.session_id),
                "RESOURCE_RESERVATION_SUBJECT_MISMATCH")

    def _current(self, budget_id, request_id=None):
        k, p = self._kernel, self._proposal.as_dict()
        peer = self._peer()
        basis = basis_key(p["scope_id"], p["record_id"])
        discovery = k._snapshot((basis,))
        basis_wire = k._present(discovery, basis)
        value, grant_key, prepared = read_basis(basis_wire, k._codec)
        self._owner_check("require_prepared_basis", self._proposal, basis_wire, peer)
        budget_key = resource_budget_key(p["scope_id"], budget_id)
        selected = k._selected(self._proposal, value, grant_key, prepared)
        lease_key = None if request_id is None else resource_lease_key(p["scope_id"], request_id)
        cells = k._snapshot(selected + (budget_key,) + (() if lease_key is None else (lease_key,)))
        require(cells[basis] == discovery[basis], "KERNEL_PREPARATION_CHANGED")
        _, _, _, grant = k._validate(self._proposal, basis_wire, peer, cells)
        binding, budget = self._budget(cells, budget_key)
        self._subject(binding, peer)
        expected = ResourceBudgetBinding(p["scope_id"], p["task_id"], peer.principal_id, peer.session_id,
            self._proposal.commitment, digest("resource-basis", value), grant_key, grant.commitment,
            prepared.authority_generation, prepared.fence_generation, prepared.policy_commitment,
            prepared.environment_commitment, binding.deadline)
        require(binding == expected, "RESOURCE_BUDGET_AUTHORITY_BINDING_MISMATCH")
        require(binding.deadline.expires_wall_ns <= utc_nanoseconds(grant.as_dict()["expires_at"]),
                "RESOURCE_BUDGET_DEADLINE_EXCEEDS_GRANT")
        return peer, basis_wire, cells, budget_key, lease_key, binding, budget, selected

    def _guard(self, peer, basis_wire, binding, budget_wire, request, grant_wire):
        k = self._kernel
        require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
        self._owner_check("require_prepared_basis", self._proposal, basis_wire, peer)
        self._owner_check("require_resource_reservation", self._proposal, basis_wire, budget_wire, request, peer)
        require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
        previous, sample = self._clock()
        require_deadline_current(binding.deadline, previous, sample)
        require(0 <= sample.monotonic_ns - request.observation_monotonic_ns <= self._maximum_age_ns,
                "RESOURCE_RESERVATION_OBSERVATION_STALE")
        require(sample.earliest_wall_ns >= utc_nanoseconds(k._decode(grant_wire, "StandingGrant").as_dict()["valid_from"]),
                "KERNEL_GRANT_NOT_YET_VALID")

    def _admitted(self, request, *, expected_selected=None):
        peer, basis, cells, bkey, lkey, binding, budget, selected = self._current(request.budget_id, request.request_id)
        if expected_selected is not None:
            require(all(cells[key] == expected_selected[key] for key in selected), "KERNEL_RELEVANT_STATE_CHANGED")
        lease = ResourceLease.from_wire(self._kernel._present(cells, lkey), lkey)
        require(lease.binding == binding and request_value(lease.request) == request_value(request),
                "RESOURCE_RESERVATION_REQUEST_CONFLICT")
        self._guard(peer, basis, binding, cells[bkey].value_wire, request, cells[binding.grant_key].value_wire)
        require(self._kernel._snapshot(tuple(cells)) == cells, "RESOURCE_RESERVATION_STATE_CHANGED")
        self._guard(peer, basis, binding, cells[bkey].value_wire, request, cells[binding.grant_key].value_wire)
        if lease.state != "HELD":
            return ReservationResult(AdmissionState.BLOCKED, None, None, ("RESOURCE_RESERVATION_TERMINAL",))
        require(lease.request.requirements.fits_within(budget.reserved_use), "RESOURCE_RESERVATION_ACCOUNTING_MISMATCH")
        return ReservationResult(AdmissionState.ADMITTED, lease.reservation_ref, lease.allocated_generation, ())

    def reserve(self, request: ReservationRequest) -> ReservationResult:
        request_value(request)
        peer, basis, cells, bkey, lkey, binding, budget, selected = self._current(request.budget_id, request.request_id)
        original_budget = cells[bkey].value_wire
        self._guard(peer, basis, binding, original_budget, request, cells[binding.grant_key].value_wire)
        if cells[lkey].value_wire is not None:
            return self._admitted(request)
        if request.expected_generation != budget.generation:
            return ReservationResult(AdmissionState.BLOCKED, None, None, ("RESOURCE_BUDGET_GENERATION_CHANGED",))
        if not request.requirements.fits_within(budget.allocatable):
            return ReservationResult(AdmissionState.BLOCKED, None, None, ("RESOURCE_BUDGET_EXHAUSTED",))
        require(budget.generation < MAX_GENERATION, "STORE_GENERATION_EXHAUSTED")
        updated = replace(budget, reserved_use=budget.reserved_use.add(request.requirements), generation=budget.generation + 1)
        lease = ResourceLease(binding, request, lkey.record_id, "HELD", updated.generation, None, None)
        _, sample = self._clock()
        def guard():
            self._guard(peer, basis, binding, original_budget, request, cells[binding.grant_key].value_wire)
        try:
            self._kernel._commit(self._proposal, "event:" + uuid.uuid4().hex, "kernel.resource.reserved", peer, sample, cells,
                {bkey: resource_budget_wire(binding, updated), lkey: lease.canonical_wire}, binding.policy_commitment, _guard=guard)
        except ContractError as error:
            if error.code not in {"JOURNAL_REVISION_CONFLICT", "STORE_REVISION_CONFLICT"}:
                raise
            # These exact store errors roll back before COMMIT. Inspect only the
            # identical identity; do not repeat allocation or an uncertain call.
            current = self._kernel._snapshot((lkey,))
            if current[lkey].value_wire is not None:
                return self._admitted(request)
            return ReservationResult(AdmissionState.BLOCKED, None, None, ("RESOURCE_BUDGET_GENERATION_CHANGED",))
        return self._admitted(request, expected_selected=cells)

    def budget(self, budget_id: str):
        """A coherent authorized envelope; it supplies no new reservation."""
        peer, basis, cells, bkey, _, binding, budget, _ = self._current(budget_id)
        require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
        self._owner_check("require_prepared_basis", self._proposal, basis, peer)
        require(self._kernel._snapshot(tuple(cells)) == cells, "RESOURCE_RESERVATION_STATE_CHANGED")
        require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
        previous, sample = self._clock()
        require_deadline_current(binding.deadline, previous, sample)
        require(sample.earliest_wall_ns >= utc_nanoseconds(self._kernel._decode(
            cells[binding.grant_key].value_wire, "StandingGrant").as_dict()["valid_from"]), "KERNEL_GRANT_NOT_YET_VALID")
        return budget

    def recover(self, request_id: str) -> ResourceLease:
        """Observe bound historical accounting, without reviving admission."""
        k, p = self._kernel, self._proposal.as_dict()
        peer = self._peer()
        key = resource_lease_key(p["scope_id"], request_id)
        cells = k._snapshot((key,))
        lease = ResourceLease.from_wire(k._present(cells, key), key)
        self._subject(lease.binding, peer)
        require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
        require(k._snapshot((key,)) == cells, "RESOURCE_RESERVATION_STATE_CHANGED")
        require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
        return lease

    def _terminal(self, request: ReservationRequest, reason_ref: str, state: str):
        """Durably fence an identity; held capacity requires actual owner cleanup."""
        from ceta.contracts.kernel_transactions import identifier
        request_value(request); identifier(reason_ref)
        k, p = self._kernel, self._proposal.as_dict()
        peer = self._peer()
        bkey = resource_budget_key(p["scope_id"], request.budget_id)
        lkey = resource_lease_key(p["scope_id"], request.request_id)
        cells = k._snapshot((bkey, lkey))
        binding, budget = self._budget(cells, bkey)
        self._subject(binding, peer)
        if cells[lkey].value_wire is None:
            require(state == "CANCELLED", "RESOURCE_RESERVATION_NOT_FOUND")
            # A caller-selected ID cannot fence another task's future request.
            # Pending cancellation resolves the same exact approved identity,
            # with its full current dependency CAS, before creating a tombstone.
            peer, basis, current, bkey, lkey, binding, budget, _ = self._current(request.budget_id, request.request_id)
            require(current[lkey].value_wire is None, "RESOURCE_RESERVATION_STATE_CHANGED")
            cells = current
            self._guard(peer, basis, binding, cells[bkey].value_wire, request, cells[binding.grant_key].value_wire)
            lease = ResourceLease(binding, request, lkey.record_id, state, None, budget.generation, reason_ref)
            values = {lkey: lease.canonical_wire}
            cleanup_wire = None
        else:
            current = ResourceLease.from_wire(cells[lkey].value_wire, lkey)
            require(current.binding == binding and request_value(current.request) == request_value(request),
                    "RESOURCE_RESERVATION_REQUEST_CONFLICT")
            if current.state != "HELD":
                require(current.state == state and current.reason_ref == reason_ref, "RESOURCE_RESERVATION_TERMINAL_CONFLICT")
                require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
                require(k._snapshot(tuple(cells)) == cells, "RESOURCE_RESERVATION_STATE_CHANGED")
                require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
                return current
            cleanup_wire = current.canonical_wire
            self._owner_check("require_resource_cleanup", self._proposal, cleanup_wire, peer)
            require(current.request.requirements.fits_within(budget.reserved_use), "RESOURCE_RESERVATION_ACCOUNTING_MISMATCH")
            require(budget.generation < MAX_GENERATION, "STORE_GENERATION_EXHAUSTED")
            updated = replace(budget, reserved_use=budget.reserved_use.subtract(current.request.requirements), generation=budget.generation + 1)
            lease = replace(current, state=state, terminal_generation=updated.generation, reason_ref=reason_ref)
            values = {bkey: resource_budget_wire(binding, updated), lkey: lease.canonical_wire}
        def guard():
            require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
            if cleanup_wire is not None:
                self._owner_check("require_resource_cleanup", self._proposal, cleanup_wire, peer)
            else:
                self._guard(peer, basis, binding, cells[bkey].value_wire, request, cells[binding.grant_key].value_wire)
            require(self._peer() == peer, "KERNEL_PEER_BINDING_MISMATCH")
        guard()
        _, sample = self._clock(progress=False)
        k._commit(self._proposal, "event:" + uuid.uuid4().hex, "kernel.resource." + state.lower(), peer, sample, cells,
                  values, binding.policy_commitment, _guard=guard)
        guard()
        recovered = self.recover(request.request_id)
        require(recovered == lease, "RESOURCE_RESERVATION_STATE_CHANGED")
        guard()
        return recovered

    def cancel(self, request: ReservationRequest, reason_ref: str) -> ResourceLease:
        return self._terminal(request, reason_ref, "CANCELLED")

    def release(self, request_id: str, reason_ref: str) -> ResourceLease:
        current = self.recover(request_id)
        return self._terminal(current.request, reason_ref, "RELEASED")
