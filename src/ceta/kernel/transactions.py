"""CMP02 development transaction owner, IMPLEMENTED_NOT_QUALIFIED.

The existing CMP03 store remains the sole writer. These mechanics run only
with explicitly composed owner implementations; the default composition denies.
No method dispatches an effect or opens runtime admission.
"""
import threading
import uuid

from ceta.contracts.evidence_admission import ConsumptionEvidence
from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.kernel_transactions import (AuthorityOwners, BudgetVector, KernelResult,
    KernelStorePort, PeerIdentity, KERNEL_PROFILE, basis_key, budget_key, control_wire,
    deadline_text, deadline_wire, digest, identifier, intent_key, logical_key, budget_wire, bound_generation,
    object_value, read_basis, read_budget, read_intent, INTENT_PROFILE, require, resource_key, resource_wire, task_key, task_wire)
from ceta.contracts.read_sets import ReadSet, ResourceRevision, require_current_preparation
from ceta.contracts.store_transactions import StoreChange, StoreExpectation, StoreKey, MAX_BATCH, commitment
from ceta.contracts.temporal import ClockSample, Deadline, issue_deadline, require_clock_progress, require_deadline_current, utc_nanoseconds
from ceta.contracts.wire import ContractError, PROFILE, ParsedRecord, RecordCodec, canonical_bytes, strict_loads
from .cpu_execution import _CpuExecutionCoordinator, _coordinated, _stopping


class _PreparationInvocation:
    """One private call's custody and canonical read set, never authority data."""
    def __init__(self, kernel, context):
        self.kernel, self.store, self.owner = kernel, kernel._store, kernel._owners
        self.context, self.thread, self.active = context, threading.get_ident(), True
        self.phase = 'ENTERING'
        self.enrollment_key = self.request = self.enrollment_wire = None
        self.designation = self.observed = self.started = self.last_tick = None
        self.proposal = self.basis_wire = self.peer = self.cells = None


def _preparation_failure(primary, invocation, secondary=None):
    data = BaseException.__dict__['__dict__'].__get__(primary)
    dict.update(data, native_preparation_invocation=invocation,
                native_preparation_owner=invocation.owner)
    if secondary is not None:
        errors = dict.get(data, 'native_preparation_cleanup_errors')
        if type(errors) is not tuple: errors = ()
        dict.__setitem__(data, 'native_preparation_cleanup_errors', errors+(secondary,))


class KernelTransactions:
    def __init__(self, store: KernelStorePort, codec: RecordCodec, installation_scope_id: str,
                 owners: AuthorityOwners | None = None):
        identifier(installation_scope_id)
        require(type(codec) is RecordCodec, "KERNEL_CODEC_REQUIRED")
        self._store, self._codec, self._installation, self._owners = store, codec, installation_scope_id, owners
        self._owned_cpu_outcome_current = getattr(owners, 'require_owned_cpu_outcome_current', None)
        self._cpu_execution = _CpuExecutionCoordinator(self)
        self._events = EventContract(codec)
        self._control = StoreKey("projection", installation_scope_id, "kernel-control")
        self._registry = StoreKey("projection", installation_scope_id, "kernel-registry")
        self._preparation_owner = self._preparation_invocation = None
        self._preparation_lock = threading.Lock()
        from ceta.identity.owner_session import NativeCpuOwnerSession
        self._preparation_check = None
        self._admission_check = None
        if type(owners) is NativeCpuOwnerSession:
            self._preparation_check = NativeCpuOwnerSession.require_prepared_basis.__get__(owners)
            self._admission_check = NativeCpuOwnerSession.require_admission.__get__(owners)
            self._preparation_owner = owners
            # Publish only after every initializer allocation and binding.
            NativeCpuOwnerSession._bind_preparation_kernel(owners, self)

    def _peer(self, context):
        require(self._owners is not None, "KERNEL_OWNERS_UNAVAILABLE")
        peer = self._owners.authenticate(context)
        require(type(peer) is PeerIdentity, "KERNEL_AUTHENTICATED_PEER_REQUIRED")
        return peer

    def _clock(self, progress=True):
        samples = self._owners.clock()
        require(type(samples) is tuple and len(samples) == 2 and all(type(s) is ClockSample for s in samples), "CLOCK_SAMPLE_REQUIRED")
        if progress:
            require_clock_progress(*samples)
        return samples

    def _decode(self, wire, name):
        record = self._codec.decode(wire)
        require(record.record_type == name, "KERNEL_" + name.upper() + "_REQUIRED")
        return record

    def _snapshot(self, keys):
        # One consistent snapshot, never a truncated dependency list or several
        # snapshots represented as one authority decision.
        unique = tuple(sorted(set(keys)))
        require(len(unique) <= MAX_BATCH, "KERNEL_DEPENDENCY_CAPACITY_EXCEEDED")
        cells = self._store.snapshot(unique)
        require(type(cells) is tuple and len(cells) == len(unique) and {c.key for c in cells} == set(unique), "KERNEL_SNAPSHOT_INVALID")
        return {c.key: c for c in cells}

    @staticmethod
    def _present(cells, key):
        cell = cells[key]
        require(cell.value_wire is not None, "KERNEL_REQUIRED_STATE_MISSING")
        return cell.value_wire

    @staticmethod
    def _expect(cell):
        return StoreExpectation(cell.key, cell.revision)

    def _selected(self, proposal, basis, grant_key, read_set):
        p = proposal.as_dict()
        require(p["scope_id"] != self._installation and grant_key.scope_id in {p["scope_id"], self._installation}, "KERNEL_SCOPE_BRIDGE_UNAVAILABLE")
        return (basis_key(p["scope_id"], p["record_id"]), grant_key, self._control, self._registry,
                task_key(p["scope_id"], p["task_id"])) + tuple(resource_key(p["scope_id"], r.resource_id) for r in read_set.resources)

    def _validate(self, proposal, basis_wire, peer, cells):
        basis, grant_key, prepared = read_basis(basis_wire, self._codec)
        p = proposal.as_dict()
        require(proposal.commitment == basis["proposal_commitment"], "KERNEL_PROPOSAL_BINDING_MISMATCH")
        require((peer.principal_id, peer.session_id) == (basis["principal_id"], basis["actor_session"]), "KERNEL_PEER_BINDING_MISMATCH")
        control = object_value(self._present(cells, self._control), ("scope_id", "authority_generation", "fence_generation", "policy_commitment", "environment_commitment"))
        require(control["scope_id"] == self._installation and control_wire(**control_without_profile(control)) == self._present(cells, self._control), "KERNEL_CONTROL_BINDING_MISMATCH")
        registry = object_value(self._present(cells, self._registry), ("scope_id", "commitment", "operations"))
        require(registry["scope_id"] == self._installation and registry["commitment"] == basis["registry_commitment"]
                and type(registry["operations"]) is list and 1 <= len(registry["operations"]) <= MAX_BATCH, "KERNEL_REGISTRY_BINDING_MISMATCH")
        seen = set()
        matched = False
        for operation in registry["operations"]:
            require(type(operation) is dict and set(operation) == {"adapter_id", "adapter_version", "adapter_commitment", "operation"}, "KERNEL_REGISTRY_INVALID")
            identifier(operation["adapter_id"])
            commitment(operation["adapter_commitment"])
            require(all(type(operation[k]) is str and 1 <= len(operation[k]) <= 4096 for k in ("adapter_version", "operation")), "KERNEL_REGISTRY_INVALID")
            identity = (operation["adapter_id"], operation["adapter_version"], operation["operation"])
            require(identity not in seen, "KERNEL_REGISTRY_INVALID")
            seen.add(identity)
            matched |= identity == (p["adapter_id"], p["adapter_version"], p["operation"]) and operation["adapter_commitment"] == basis["adapter_commitment"]
        require(matched, "KERNEL_OPERATION_UNREGISTERED")
        task = object_value(self._present(cells, task_key(p["scope_id"], p["task_id"])), ("scope_id", "task_id", "revision"))
        require(task_wire(p["scope_id"], p["task_id"], basis["task_revision"]) == canonical_bytes(task), "KERNEL_TASK_REVISION_CHANGED")
        resources = []
        for resource in prepared.resources:
            observed = object_value(self._present(cells, resource_key(p["scope_id"], resource.resource_id)), ("scope_id", "resource_id", "revision"))
            require(resource_wire(p["scope_id"], resource.resource_id, observed["revision"]) == canonical_bytes(observed), "KERNEL_RESOURCE_BINDING_MISMATCH")
            resources.append(ResourceRevision(resource.resource_id, observed["revision"]))
        current = ReadSet(p["scope_id"], control["authority_generation"], control["fence_generation"], control["policy_commitment"], control["environment_commitment"], tuple(resources))
        require_current_preparation(prepared, current, tuple(r.resource_id for r in prepared.resources))
        grant_record = self._decode(self._present(cells, grant_key), "StandingGrant")
        grant = grant_record.as_dict()
        require(grant["scope_id"] == grant_key.scope_id and grant["record_id"] == grant_key.record_id, "KERNEL_GRANT_BINDING_MISMATCH")
        require(grant["status"] == "ACTIVE", "KERNEL_GRANT_NOT_ACTIVE")
        require(grant["grantee_id"] == peer.principal_id and grant["purpose_ref"] == p["task_id"], "KERNEL_GRANT_PURPOSE_MISMATCH")
        require(grant["policy_commitment"] == current.policy_commitment and p["operation"] in grant["operation_classes"], "KERNEL_GRANT_OPERATION_DENIED")
        targets = set()
        prepared_resources = {r.resource_id: r.revision for r in prepared.resources}
        for target in p["resources"]:
            require(target["scope_id"] == p["scope_id"] and target["resource_id"] not in targets
                    and target["revision"] == prepared_resources.get(target["resource_id"]), "KERNEL_TARGET_BINDING_MISMATCH")
            targets.add(target["resource_id"])
            require(any(g["scope_id"] == target["scope_id"] and g["resource_id"] == target["resource_id"]
                        and g["access"] == target["access"] and (g["revision"] is None or g["revision"] == target["revision"])
                        for g in grant["resource_scope"]), "KERNEL_GRANT_RESOURCE_DENIED")
        return basis, grant_key, prepared, grant_record

    def _entry(self, point, record, event_id, event_type, peer, sample):
        event = {"record_type": "EventRecord", "schema_version": "1", "record_id": event_id,
            "scope_id": point.scope_id, "causation_ref": record.as_dict()["causation_ref"], "sequence": point.next_sequence,
            "event_type": event_type, "actor_id": peer.principal_id, "actor_session": peer.session_id,
            "recorded_at": deadline_text(sample.wall_time_ns), "previous_head": point.head,
            "payload_ref": record.record_id, "payload_commitment": record.commitment, "canonicalization_profile": PROFILE,
            "signer_key_ref": None, "signature_ref": None}
        wire = canonical_bytes(event)
        self._events.require_successor(wire, point)
        return JournalEntry(wire, record.canonical_wire)

    def _commit(self, record, event_id, event_type, peer, sample, cells, values, policy_commitment, *, _point=None, _guard=None):
        point = _point if _point is not None else self._store.position(record.as_dict()["scope_id"])
        row = self._entry(point, record, event_id, event_type, peer, sample)
        points, rows, event_by_scope = [point], [row], {point.scope_id: event_id}
        # An installation-owned budget requires a same-scope admitted payload,
        # even when the operation's permit stream is project-owned.
        for scope in sorted({k.scope_id for k in values} - {point.scope_id}):
            other_point = self._store.position(scope)
            other_id = "event:" + uuid.uuid4().hex
            decision = self._codec.decode(canonical_bytes({"record_type": "PolicyDecision", "schema_version": "1",
                "record_id": "decision:" + uuid.uuid4().hex, "scope_id": scope, "causation_ref": event_id,
                "request_ref": record.record_id, "policy_commitment": policy_commitment, "rule_refs": [],
                "evaluated_inputs_commitment": digest("allocation-change", [{"key": k.as_dict(), "value": strict_loads(v)} for k, v in sorted(values.items())]),
                "relevant_revision_refs": [], "outcome": "ALLOW", "reason_codes": ["DEVELOPMENT_ALLOCATION_PROFILE"],
                "obligation_refs": [], "revalidation_triggers": [], "authority_owner_id": "kernel:cmp02"}))
            points.append(other_point)
            rows.append(self._entry(other_point, decision, other_id, "kernel.development.allocation", peer, sample))
            event_by_scope[scope] = other_id
        result = self._store.commit(tuple(points), tuple(rows), checks=tuple(self._expect(c) for c in cells.values()),
            changes=tuple(StoreChange(self._expect(cells[k]), v, event_by_scope[k.scope_id]) for k, v in values.items()), guard=_guard)
        return KernelResult(record.canonical_wire, row.event_wire, point, result)

    @_coordinated
    def prepare(self, proposal_wire: bytes, request_context: object) -> KernelResult:
        owner = self._preparation_owner
        if owner is None:
            return self._prepare(proposal_wire, request_context)
        primary = invocation = None
        from ceta.identity.owner_session import NativeCpuOwnerSession
        try:
            with self._preparation_lock:
                require(owner is self._owners and self._preparation_invocation is None,
                        'OWNER_PREPARATION_REENTRANT')
                invocation = _PreparationInvocation(self, request_context)
                # Retirement coverage exists before the FIRST publication.
                # Metadata lock ends before authentication, SQL or observation.
                self._preparation_invocation = invocation
            NativeCpuOwnerSession._begin_preparation(owner, invocation)
            invocation.phase = 'READY'
            return self._prepare(proposal_wire, request_context, invocation)
        except BaseException as error:
            primary = error
            if invocation is not None: _preparation_failure(error, invocation)
            raise
        finally:
            if invocation is not None:
                invocation.active = False
                invocation.phase = 'RETIRING'
                try:
                    NativeCpuOwnerSession._end_preparation(owner, invocation)
                except BaseException as cleanup:
                    if primary is None:
                        invocation.phase = 'CLEANUP_PENDING'
                        _preparation_failure(cleanup, invocation)
                        raise
                    invocation.phase = 'CLEANUP_PENDING'
                    _preparation_failure(primary, invocation, cleanup)
                else:
                    invocation.phase = 'RETIRED'
                finally:
                    with self._preparation_lock:
                        if self._preparation_invocation is invocation:
                            self._preparation_invocation = None

    def _prepare(self, proposal_wire, request_context, _native=None):
        if _native is not None:
            require(type(_native) is _PreparationInvocation and _native.active
                and self._preparation_invocation is _native and _native.kernel is self
                and _native.context is request_context and _native.thread == threading.get_ident()
                and _native.phase == 'READY', 'OWNER_PREPARATION_INVOCATION_REENTRY')
            _native.phase = 'PREPARING'
        peer = self._peer(request_context)
        proposal = self._decode(proposal_wire, "ActionProposal")
        p = proposal.as_dict()
        key = basis_key(p["scope_id"], p["record_id"])
        extra = () if _native is None else (_native.enrollment_key,)
        discovery = self._snapshot((key,)+extra)
        basis_wire = self._present(discovery, key)
        basis, grant_key, prepared = read_basis(basis_wire, self._codec)
        check = self._owners.require_prepared_basis if self._preparation_check is None else self._preparation_check
        if _native is None:
            require(check(proposal, basis_wire, peer) is None, "KERNEL_OWNER_DECISION_INVALID")
        else:
            from .owner_authority import _row, ceremony_key
            from ceta.contracts.real_effect import CAP_OPERATION, decode_native_approval_transcript
            row = _row(self._present(discovery, _native.enrollment_key))
            field = 'cap_approval' if _native.request.operation == CAP_OPERATION else 'restore_approval'
            approval = row[field]
            require(type(approval) is dict and type(approval.get('transcript_wire')) is str,
                    'OWNER_PREPARATION_APPROVAL_REQUIRED')
            transcript = decode_native_approval_transcript(approval['transcript_wire'].encode('utf8'))
            extra += (logical_key('projection', self._installation, 'owner-effect', _native.request.request_id),
                ceremony_key(self._installation, 'challenge', transcript.challenge_id),
                ceremony_key(self._installation, 'nonce', transcript.ceremony_nonce))
        permit_id, reservation_id, event_id = (prefix + uuid.uuid4().hex for prefix in ("permit:", "reservation:", "event:"))
        permit_key = StoreKey("permit", p["scope_id"], permit_id)
        reservation_key = StoreKey("reservation", p["scope_id"], reservation_id)
        intent = intent_key(p["scope_id"], permit_id)
        issued = logical_key("projection", p["scope_id"], "issuance", p["record_id"])
        selected = self._selected(proposal, basis, grant_key, prepared)
        cells = self._snapshot(selected + extra + (budget_key(grant_key), permit_key, reservation_key, intent, issued))
        require(cells[key] == discovery[key], "KERNEL_PREPARATION_CHANGED")
        require(all(cells[k] == discovery[k] for k in discovery), "KERNEL_PREPARATION_CHANGED")
        require(cells[issued].generation == 0, "KERNEL_PROPOSAL_ALREADY_PREPARED")
        require(all(cells[k].generation == 0 for k in (permit_key, reservation_key, intent)), "KERNEL_ISSUANCE_COLLISION")
        basis, grant_key, prepared, grant_record = self._validate(proposal, basis_wire, peer, cells)
        if _native is not None:
            _native.proposal, _native.basis_wire, _native.peer = proposal, basis_wire, peer
            _native.cells = tuple(cells.values())
            require(check(proposal, basis_wire, peer) is None, "KERNEL_OWNER_DECISION_INVALID")
        grant = grant_record.as_dict()
        limit, recovery, held, charged = read_budget(self._present(cells, budget_key(grant_key)), budget_key(grant_key))
        require(limit == BudgetVector.from_dict(grant["budget"]), "KERNEL_BUDGET_LIMIT_MISMATCH")
        cost = BudgetVector.from_dict(p["budget"])
        require(cost.values[0] > 0 and cost.as_dict()["max_effects"] == 1, "KERNEL_OPERATION_BUDGET_UNSUPPORTED")
        require(limit.subtract(recovery.add(held).add(charged)).contains(cost), "KERNEL_BUDGET_EXHAUSTED")
        previous, sample = self._clock()
        require(sample.earliest_wall_ns >= utc_nanoseconds(grant["valid_from"]), "KERNEL_GRANT_NOT_YET_VALID")
        deadline = issue_deadline(grant["expires_at"], cost.values[0] * 1_000_000, previous, sample)
        dependencies = [{"key": k.as_dict(), "revision": cells[k].revision} for k in selected]
        governed = {"proposal": strict_loads(proposal.canonical_wire), "basis": strict_loads(basis_wire),
                    "grant_commitment": grant_record.commitment, "reservation_ref": reservation_id, "issuance_ref": event_id,
                    "deadline": deadline_wire(deadline), "dependencies": dependencies}
        permit = {"record_type": "OperationPermit", "schema_version": "1", "record_id": permit_id, "scope_id": p["scope_id"],
            "causation_ref": p["record_id"], "grant_ref": grant_key.record_id, "task_id": p["task_id"], "proposal_ref": p["record_id"],
            "adapter_id": p["adapter_id"], "adapter_commitment": basis["adapter_commitment"], "operation": p["operation"],
            "arguments_commitment": p["arguments_commitment"], "input_commitment": digest("operation-inputs", governed),
            "candidate_commitment": basis["candidate_commitment"], "resources": p["resources"], "policy_commitment": prepared.policy_commitment,
            "review_refs": basis["review_refs"], "approval_evidence_ref": basis["approval_evidence_ref"], "environment_commitment": prepared.environment_commitment,
            "authority_generation": prepared.authority_generation, "fence_generation": prepared.fence_generation,
            "nonce": "nonce:" + uuid.uuid4().hex, "expires_at": deadline_text(deadline.expires_wall_ns), "reservation_ref": reservation_id,
            "issuance_evidence_ref": event_id, "consume_event_ref": None, "status": "PREPARED"}
        record = self._codec.decode(canonical_bytes(permit))
        reservation = {"profile": KERNEL_PROFILE, "scope_id": p["scope_id"], "reservation_id": reservation_id,
            "permit_id": permit_id, "grant_key": grant_key.as_dict(), "cost": cost.as_dict(), "state": "HELD"}
        intention = {"profile": INTENT_PROFILE, "scope_id": p["scope_id"], "permit_id": permit_id, "grant_key": grant_key.as_dict(),
             "grant_commitment": grant_record.commitment,
            "basis_wire": basis_wire.decode("utf8"), "cost": cost.as_dict(), "deadline": deadline_wire(deadline),
            "dependencies": dependencies,
            "state": "INTENT_COMMITTED", "consumption": None}
        point = self._store.position(p["scope_id"])
        values = {permit_key: record.canonical_wire, reservation_key: canonical_bytes(reservation), intent: canonical_bytes(intention),
            issued: canonical_bytes({"profile": KERNEL_PROFILE, "scope_id": p["scope_id"], "proposal_id": p["record_id"], "permit_id": permit_id,
                                     "issuance_event_ref": event_id, "sequence": point.next_sequence, "previous_head": point.head}),
            budget_key(grant_key): budget_wire(grant_key.scope_id, grant_key.record_id, limit, recovery, held.add(cost), charged)}
        def guard():
            require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
            require(check(proposal, basis_wire, peer) is None, "KERNEL_OWNER_DECISION_INVALID")
            require_deadline_current(deadline, *self._clock())
            require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
            require_deadline_current(deadline, *self._clock())
            if _native is not None:
                # Last pure retained fence follows EVERY fallible peer/clock call.
                require(check(proposal, basis_wire, peer) is None, "KERNEL_OWNER_DECISION_INVALID")
        result = self._commit(record, event_id, "kernel.intent.committed", peer, sample, cells, values, prepared.policy_commitment, _point=point, _guard=guard)
        guard()
        return result

    @_coordinated
    def consume(self, permit_wire: bytes, request_context: object) -> KernelResult:
        peer = self._peer(request_context)
        native_check = self._admission_check
        check = native_check if native_check is not None else self._owners.require_admission
        supplied = self._decode(permit_wire, "OperationPermit")
        p = supplied.as_dict()
        permit_key = StoreKey("permit", p["scope_id"], p["record_id"])
        intent = intent_key(p["scope_id"], p["record_id"])
        discovery = self._snapshot((permit_key, intent))
        record = self._decode(self._present(discovery, permit_key), "OperationPermit")
        require(record.as_dict()["status"] == "PREPARED", "KERNEL_PERMIT_NOT_PREPARED")
        require(record.canonical_wire == supplied.canonical_wire, "KERNEL_PERMIT_BINDING_MISMATCH")
        intention = read_intent(self._present(discovery, intent))
        require(intention["scope_id"] == p["scope_id"] and intention["permit_id"] == p["record_id"]
                and intention["state"] == "INTENT_COMMITTED" and intention["consumption"] is None
                and type(intention["basis_wire"]) is str, "KERNEL_INTENT_BINDING_MISMATCH")
        basis_wire = intention["basis_wire"].encode("utf8")
        basis, grant_key, prepared = read_basis(basis_wire, self._codec)
        proposal = self._decode(basis["proposal_wire"].encode("utf8"), "ActionProposal")
        require(proposal.as_dict()["record_id"] == p["proposal_ref"] and proposal.as_dict()["scope_id"] == p["scope_id"]
                and grant_key.as_dict() == intention["grant_key"] and grant_key.record_id == p["grant_ref"], "KERNEL_INTENT_BINDING_MISMATCH")
        reservation_key = StoreKey("reservation", p["scope_id"], p["reservation_ref"])
        issued = logical_key("projection", p["scope_id"], "issuance", p["proposal_ref"])
        selected = self._selected(proposal, basis, grant_key, prepared)
        cells = self._snapshot(selected + (budget_key(grant_key), permit_key, reservation_key, intent, issued))
        require(all(cells[k] == discovery[k] for k in discovery), "KERNEL_PREPARATION_CHANGED")
        require(self._present(cells, basis_key(p["scope_id"], p["proposal_ref"])) == basis_wire, "KERNEL_PREPARATION_CHANGED")
        require(type(intention["dependencies"]) is list and len(intention["dependencies"]) == len(selected), "KERNEL_DEPENDENCIES_INVALID")
        dependencies = []
        for dependency in intention["dependencies"]:
            require(type(dependency) is dict and set(dependency) == {"key", "revision"}
                    and type(dependency["key"]) is dict and set(dependency["key"]) == {"collection", "scope_id", "record_id"}, "KERNEL_DEPENDENCIES_INVALID")
            dependencies.append(StoreExpectation(StoreKey(**dependency["key"]), dependency["revision"]))
        require(len({d.key for d in dependencies}) == len(selected) and {d.key for d in dependencies} == set(selected), "KERNEL_DEPENDENCIES_INVALID")
        require(all(cells[d.key].revision == d.revision for d in dependencies), "KERNEL_RELEVANT_STATE_CHANGED")
        _, _, _, grant_record = self._validate(proposal, basis_wire, peer, cells)
        governed = {"proposal": strict_loads(proposal.canonical_wire), "basis": strict_loads(basis_wire),
                    "grant_commitment": grant_record.commitment, "reservation_ref": p["reservation_ref"], "issuance_ref": p["issuance_evidence_ref"],
                    "deadline": intention["deadline"], "dependencies": intention["dependencies"]}
        require(p["input_commitment"] == digest("operation-inputs", governed), "KERNEL_INPUT_BINDING_MISMATCH")
        require(check(record, basis_wire, peer) is None, "KERNEL_OWNER_DECISION_INVALID")
        issued_value = object_value(self._present(cells, issued), ("scope_id", "proposal_id", "permit_id", "issuance_event_ref", "sequence", "previous_head"))
        require({k: v for k, v in issued_value.items() if k not in {"sequence", "previous_head"}} ==
                {"profile": KERNEL_PROFILE, "scope_id": p["scope_id"], "proposal_id": p["proposal_ref"],
                 "permit_id": p["record_id"], "issuance_event_ref": p["issuance_evidence_ref"]}, "KERNEL_ISSUANCE_BINDING_MISMATCH")
        issuance_prior = StreamPosition(p["scope_id"], issued_value["sequence"], issued_value["previous_head"])
        issuance = self._store.replay(p["scope_id"], issuance_prior.next_sequence, 1)
        require(len(issuance) == 1 and issuance[0].payload_wire == record.canonical_wire, "KERNEL_ISSUANCE_BINDING_MISMATCH")
        issued_event = self._events.require_successor(issuance[0].event_wire, issuance_prior)
        require(issued_event.record.record_id == p["issuance_evidence_ref"]
                and issued_event.record.as_dict()["event_type"] == "kernel.intent.committed", "KERNEL_ISSUANCE_BINDING_MISMATCH")
        self._events.require_payload(issuance[0].event_wire, issuance[0].payload_wire)
        reservation = object_value(self._present(cells, reservation_key), ("scope_id", "reservation_id", "permit_id", "grant_key", "cost", "state"))
        cost = BudgetVector.from_dict(intention["cost"])
        require(cost == BudgetVector.from_dict(proposal.as_dict()["budget"]), "KERNEL_RESERVATION_BINDING_MISMATCH")
        require(reservation == {"profile": KERNEL_PROFILE, "scope_id": p["scope_id"], "reservation_id": p["reservation_ref"],
            "permit_id": p["record_id"], "grant_key": grant_key.as_dict(), "cost": cost.as_dict(), "state": "HELD"}, "KERNEL_RESERVATION_BINDING_MISMATCH")
        limit, recovery, held, charged = read_budget(self._present(cells, budget_key(grant_key)), budget_key(grant_key))
        require(limit == BudgetVector.from_dict(self._decode(self._present(cells, grant_key), "StandingGrant").as_dict()["budget"])
                and held.contains(cost), "KERNEL_BUDGET_BINDING_MISMATCH")
        require(type(intention["deadline"]) is dict and set(intention["deadline"]) == set(Deadline.__dataclass_fields__), "DEADLINE_REQUIRED")
        deadline = Deadline(**intention["deadline"])
        require(p["expires_at"] == deadline_text(deadline.expires_wall_ns), "KERNEL_DEADLINE_BINDING_MISMATCH")
        previous, sample = self._clock()
        require_deadline_current(deadline, previous, sample)
        event_id = "event:" + uuid.uuid4().hex
        p.update(status="CONSUMED", consume_event_ref=event_id, causation_ref=event_id)
        consumed = self._codec.decode(canonical_bytes(p))
        point = self._store.position(p["scope_id"])
        intention.update(state="ADMISSION_REDEEMED", consumption={"sequence": point.next_sequence, "previous_head": point.head, "event_id": event_id})
        reservation["state"] = "CHARGED"
        values = {permit_key: consumed.canonical_wire, reservation_key: canonical_bytes(reservation), intent: canonical_bytes(intention),
                  budget_key(grant_key): budget_wire(grant_key.scope_id, grant_key.record_id, limit, recovery, held.subtract(cost), charged.add(cost))}
        def guard():
            require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
            require(check(record, basis_wire, peer) is None, "KERNEL_OWNER_DECISION_INVALID")
            require_deadline_current(deadline, *self._clock())
            require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
            require_deadline_current(deadline, *self._clock())
            if native_check is not None:
                # Concrete native custody must still hold after every fallible
                # peer/clock callback, including at pre/post-COMMIT guards.
                require(check(record, basis_wire, peer) is None, "KERNEL_OWNER_DECISION_INVALID")
        result = self._commit(consumed, event_id, "kernel.permit.consumed", peer, sample, cells, values, prepared.policy_commitment, _point=point, _guard=guard)
        # A final stale identity/authority/time check after durable COMMIT must not return a
        # usable command result. The permit remains burned; no refund/replay.
        guard()
        return result

    def _revoke_basis(self, grant_wire: bytes, request_context: object, reason_ref: str):
        peer = self._peer(request_context)
        identifier(reason_ref)
        supplied = self._decode(grant_wire, "StandingGrant")
        grant = supplied.as_dict()
        require(grant["scope_id"] == self._installation or grant["scope_id"].startswith("project:"), "KERNEL_SCOPE_BRIDGE_UNAVAILABLE")
        key = StoreKey("grant", grant["scope_id"], grant["record_id"])
        cells = self._snapshot((key, self._control))
        current = self._decode(self._present(cells, key), "StandingGrant")
        require(current.canonical_wire == supplied.canonical_wire, "KERNEL_GRANT_BINDING_MISMATCH")
        require(grant["status"] in {"ACTIVE", "EXHAUSTED"}, "KERNEL_GRANT_NOT_REVOCABLE")
        require(self._owners.require_revocation(current, peer, reason_ref) is None, "KERNEL_OWNER_DECISION_INVALID")
        grant["revocation_generation"] = bound_generation(grant["revocation_generation"] + 1)
        event_id = "event:" + uuid.uuid4().hex
        grant.update(status="REVOKED", causation_ref=reason_ref)
        record = self._codec.decode(canonical_bytes(grant))
        _, sample = self._clock(progress=False)
        def guard():
            require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
            require(self._owners.require_revocation(current, peer, reason_ref) is None, "KERNEL_OWNER_DECISION_INVALID")
            require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
        return peer, key, cells, current, grant, event_id, record, sample, guard

    @_stopping
    def revoke(self, grant_wire: bytes, request_context: object, reason_ref: str) -> KernelResult:
        peer, key, cells, current, grant, event_id, record, sample, guard = self._revoke_basis(grant_wire, request_context, reason_ref)
        result = self._commit(record, event_id, "kernel.grant.revoked", peer, sample, cells,
                              {key: record.canonical_wire}, grant["policy_commitment"], _guard=guard)
        guard()
        return result

    def resolve_consumption(self, permit: ParsedRecord) -> ConsumptionEvidence:
        """Trusted internal evidence callback; public ingress uses the peer-bound query."""
        return self._resolve_consumption(permit)

    def resolve_consumption_for_peer(self, permit_wire: bytes, request_context: object) -> ConsumptionEvidence:
        """Disclose coherent historical evidence only to its current bound subject."""
        peer = self._peer(request_context)
        permit = self._decode(permit_wire, "OperationPermit")
        result = self._resolve_consumption(permit, peer=peer)
        require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
        return result

    def _resolve_consumption(self, permit: ParsedRecord, *, peer: PeerIdentity | None = None) -> ConsumptionEvidence:
        require(type(permit) is ParsedRecord and permit.record_type == "OperationPermit", "KERNEL_OPERATIONPERMIT_REQUIRED")
        decoded = self._decode(permit.original_wire, "OperationPermit")
        require(decoded == permit, "KERNEL_PARSED_RECORD_BINDING_MISMATCH")
        p = permit.as_dict()
        cells = self._snapshot((StoreKey("permit", p["scope_id"], p["record_id"]), intent_key(p["scope_id"], p["record_id"])))
        consumed = self._decode(self._present(cells, StoreKey("permit", p["scope_id"], p["record_id"])), "OperationPermit")
        saved = consumed.as_dict()
        require(saved["status"] == "CONSUMED" and saved["consume_event_ref"] is not None, "CONSUMPTION_EVIDENCE_UNAVAILABLE")
        require(all(p[k] == saved[k] for k in p if k not in {"status", "causation_ref"}), "CONSUMED_PERMIT_BINDING_MISMATCH")
        intention = read_intent(self._present(cells, intent_key(p["scope_id"], p["record_id"])))
        index = intention["consumption"]
        require(intention["scope_id"] == p["scope_id"] and intention["permit_id"] == p["record_id"]
                and intention["state"] == "ADMISSION_REDEEMED" and type(index) is dict
                and set(index) == {"sequence", "previous_head", "event_id"} and index["event_id"] == saved["consume_event_ref"], "KERNEL_CONSUMPTION_INDEX_INVALID")
        if peer is not None:
            require(type(intention["basis_wire"]) is str, "KERNEL_INTENT_BINDING_MISMATCH")
            basis, grant_key, prepared = read_basis(intention["basis_wire"].encode("utf8"), self._codec)
            require((peer.principal_id, peer.session_id) == (basis["principal_id"], basis["actor_session"]),
                    "KERNEL_PEER_BINDING_MISMATCH")
            proposal = self._decode(basis["proposal_wire"].encode("utf8"), "ActionProposal").as_dict()
            require(proposal["record_id"] == p["proposal_ref"] and proposal["scope_id"] == p["scope_id"]
                    and prepared.scope_id == p["scope_id"] and grant_key.as_dict() == intention["grant_key"]
                    and grant_key.record_id == p["grant_ref"] and grant_key.scope_id in {p["scope_id"], self._installation},
                    "KERNEL_INTENT_BINDING_MISMATCH")
            require(saved["causation_ref"] == saved["consume_event_ref"], "KERNEL_CONSUMPTION_INDEX_INVALID")
        prior = StreamPosition(p["scope_id"], index["sequence"], index["previous_head"])
        rows = self._store.replay(p["scope_id"], prior.next_sequence, 1)
        require(len(rows) == 1, "CONSUMPTION_EVIDENCE_UNAVAILABLE")
        row = rows[0]
        event = self._events.require_successor(row.event_wire, prior)
        require(event.record.record_id == saved["consume_event_ref"] and event.record.as_dict()["event_type"] == "kernel.permit.consumed"
                and row.payload_wire == consumed.canonical_wire, "KERNEL_CONSUMPTION_INDEX_INVALID")
        self._events.require_payload(row.event_wire, row.payload_wire)
        if peer is not None:
            attribution = event.record.as_dict()
            require((attribution["actor_id"], attribution["actor_session"]) == (peer.principal_id, peer.session_id)
                    and attribution["causation_ref"] == saved["consume_event_ref"], "KERNEL_CONSUMPTION_INDEX_INVALID")
            require(self._snapshot(tuple(cells)) == cells, "KERNEL_RECOVERY_STATE_CHANGED")
        return ConsumptionEvidence(row.payload_wire, row.event_wire, prior)

    def recover_permit(self, permit_wire: bytes, request_context: object) -> ParsedRecord:
        """Read the captured store after a lost result, without repeating admission.

        The original PREPARED permit is a selector and an immutable binding, not
        permission to recover another principal's data. A current consumed record
        must still resolve to its durable consumption event. This observation
        establishes neither execution nor settlement and allocates no authority.
        """
        peer = self._peer(request_context)
        supplied = self._decode(permit_wire, "OperationPermit")
        current = self._recover_permit(supplied, peer)
        require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
        return current

    def _recover_permit(self, supplied: ParsedRecord, peer: PeerIdentity, *, cells=None) -> ParsedRecord:
        """Internal validator; never substitute a public request or its context."""
        p = supplied.as_dict()
        require(p["status"] in {"PREPARED", "CONSUMED"}, "KERNEL_RECOVERY_STATE_UNAVAILABLE")
        key = StoreKey("permit", p["scope_id"], p["record_id"])
        intent = intent_key(p["scope_id"], p["record_id"])
        cells = self._snapshot((key, intent)) if cells is None else cells
        current = self._decode(self._present(cells, key), "OperationPermit")
        saved = current.as_dict()
        intention = read_intent(self._present(cells, intent))
        require(intention["scope_id"] == p["scope_id"] and intention["permit_id"] == p["record_id"]
                and type(intention["basis_wire"]) is str, "KERNEL_INTENT_BINDING_MISMATCH")
        basis, grant_key, prepared = read_basis(intention["basis_wire"].encode("utf8"), self._codec)
        require((peer.principal_id, peer.session_id) == (basis["principal_id"], basis["actor_session"]),
                "KERNEL_PEER_BINDING_MISMATCH")
        proposal = self._decode(basis["proposal_wire"].encode("utf8"), "ActionProposal").as_dict()
        require(grant_key.as_dict() == intention["grant_key"] and grant_key.record_id == p["grant_ref"]
                and grant_key.scope_id in {p["scope_id"], self._installation} and prepared.scope_id == p["scope_id"]
                and proposal["record_id"] == p["proposal_ref"] and proposal["scope_id"] == p["scope_id"],
                "KERNEL_INTENT_BINDING_MISMATCH")
        require(all(p[k] == saved[k] for k in p if k not in {"status", "causation_ref", "consume_event_ref"}),
                "KERNEL_RECOVERY_PERMIT_BINDING_MISMATCH")
        if p["status"] == "PREPARED":
            require(p["consume_event_ref"] is None and p["causation_ref"] == p["proposal_ref"],
                    "KERNEL_RECOVERY_PERMIT_BINDING_MISMATCH")
        else:
            require(p["consume_event_ref"] is not None and p["consume_event_ref"] == saved["consume_event_ref"]
                    and p["causation_ref"] == p["consume_event_ref"], "KERNEL_RECOVERY_PERMIT_BINDING_MISMATCH")
        if saved["status"] == "PREPARED":
            require(current.canonical_wire == supplied.canonical_wire and intention["state"] == "INTENT_COMMITTED"
                    and intention["consumption"] is None, "KERNEL_INTENT_BINDING_MISMATCH")
        elif saved["status"] == "CONSUMED":
            require(saved["causation_ref"] == saved["consume_event_ref"], "KERNEL_RECOVERY_PERMIT_BINDING_MISMATCH")
            self._resolve_consumption(current, peer=peer)
        else:
            require(False, "KERNEL_RECOVERY_STATE_UNAVAILABLE")
        require(self._snapshot(tuple(cells)) == cells, "KERNEL_RECOVERY_STATE_CHANGED")
        return current

    def recover_preparation(self, proposal_wire: bytes, request_context: object) -> ParsedRecord:
        """Observe committed issuance by its exact original proposal, without retry.

        The original opaque context remains bound to the proposal request. The
        private permit validator takes a trusted historical payload, never a new
        public request/context. Intent-v2 retains the original grant commitment;
        legacy metadata cannot establish that missing input and denies this route.
        """
        peer = self._peer(request_context)
        proposal = self._decode(proposal_wire, "ActionProposal")
        p = proposal.as_dict()
        issued = logical_key("projection", p["scope_id"], "issuance", p["record_id"])
        discovery = self._snapshot((issued,))
        association = object_value(self._present(discovery, issued),
            ("scope_id", "proposal_id", "permit_id", "issuance_event_ref", "sequence", "previous_head"))
        require(association["scope_id"] == p["scope_id"] and association["proposal_id"] == p["record_id"],
                "KERNEL_ISSUANCE_BINDING_MISMATCH")
        key = StoreKey("permit", p["scope_id"], association["permit_id"])
        intent = intent_key(p["scope_id"], association["permit_id"])
        cells = self._snapshot((issued, key, intent))
        require(cells[issued] == discovery[issued], "KERNEL_RECOVERY_STATE_CHANGED")
        intention = read_intent(self._present(cells, intent))
        require(intention["scope_id"] == p["scope_id"] and intention["permit_id"] == key.record_id
                and type(intention["basis_wire"]) is str, "KERNEL_INTENT_BINDING_MISMATCH")
        basis_wire = intention["basis_wire"].encode("utf8")
        basis, grant_key, prepared = read_basis(basis_wire, self._codec)
        require((basis["principal_id"], basis["actor_session"]) == (peer.principal_id, peer.session_id),
                "KERNEL_PEER_BINDING_MISMATCH")
        require(basis["proposal_wire"].encode("utf8") == proposal.original_wire
                and basis["proposal_commitment"] == proposal.commitment, "KERNEL_PROPOSAL_BINDING_MISMATCH")
        require(intention["profile"] == INTENT_PROFILE, "KERNEL_RECOVERY_INPUT_EVIDENCE_UNAVAILABLE")
        require(BudgetVector.from_dict(intention["cost"]) == BudgetVector.from_dict(p["budget"]),
                "KERNEL_RESERVATION_BINDING_MISMATCH")
        prior = StreamPosition(p["scope_id"], association["sequence"], association["previous_head"])
        rows = self._store.replay(p["scope_id"], prior.next_sequence, 1)
        require(len(rows) == 1, "KERNEL_ISSUANCE_BINDING_MISMATCH")
        row = rows[0]
        issuance = self._decode(row.payload_wire, "OperationPermit")
        original = issuance.as_dict()
        event = self._events.require_successor(row.event_wire, prior).record.as_dict()
        self._events.require_payload(row.event_wire, row.payload_wire)
        require(original["record_id"] == key.record_id and original["scope_id"] == p["scope_id"]
                and original["proposal_ref"] == p["record_id"] and original["causation_ref"] == p["record_id"]
                and original["status"] == "PREPARED" and original["consume_event_ref"] is None
                and original["issuance_evidence_ref"] == association["issuance_event_ref"]
                and event["record_id"] == association["issuance_event_ref"]
                and event["event_type"] == "kernel.intent.committed" and event["causation_ref"] == p["record_id"]
                and (event["actor_id"], event["actor_session"]) == (peer.principal_id, peer.session_id),
                "KERNEL_ISSUANCE_BINDING_MISMATCH")
        require(all(original[name] == p[name] for name in
                    ("task_id", "adapter_id", "operation", "arguments_commitment", "resources")),
                "KERNEL_PROPOSAL_BINDING_MISMATCH")
        require(original["grant_ref"] == grant_key.record_id and grant_key.as_dict() == intention["grant_key"]
                and grant_key.scope_id in {p["scope_id"], self._installation} and prepared.scope_id == p["scope_id"],
                "KERNEL_INTENT_BINDING_MISMATCH")
        require(all(original[name] == basis[name] for name in
                    ("adapter_commitment", "candidate_commitment", "review_refs", "approval_evidence_ref"))
                and original["policy_commitment"] == prepared.policy_commitment
                and original["environment_commitment"] == prepared.environment_commitment
                and original["authority_generation"] == prepared.authority_generation
                and original["fence_generation"] == prepared.fence_generation, "KERNEL_INPUT_BINDING_MISMATCH")
        require(type(intention["deadline"]) is dict
                and set(intention["deadline"]) == set(Deadline.__dataclass_fields__), "DEADLINE_REQUIRED")
        deadline = Deadline(**intention["deadline"])
        require(original["expires_at"] == deadline_text(deadline.expires_wall_ns), "KERNEL_DEADLINE_BINDING_MISMATCH")
        governed = {"proposal": strict_loads(proposal.canonical_wire), "basis": strict_loads(basis_wire),
                    "grant_commitment": intention["grant_commitment"], "reservation_ref": original["reservation_ref"],
                    "issuance_ref": original["issuance_evidence_ref"], "deadline": intention["deadline"],
                    "dependencies": intention["dependencies"]}
        require(original["input_commitment"] == digest("operation-inputs", governed), "KERNEL_INPUT_BINDING_MISMATCH")
        current = self._recover_permit(issuance, peer, cells=cells)
        require(current.original_wire == self._present(cells, key), "KERNEL_RECOVERY_STATE_CHANGED")
        require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
        require(self._snapshot(tuple(cells)) == cells, "KERNEL_RECOVERY_STATE_CHANGED")
        require(self._peer(request_context) == peer, "KERNEL_PEER_BINDING_MISMATCH")
        return current

    def require_runtime_admission(self) -> None:
        raise ContractError("RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE")

    def resource_reservations(self, proposal_wire: bytes, request_context: object, *,
                              maximum_observation_age_ns: int = 2_000_000_000,
                              maximum_owner_check_ns: int = 50_000_000):
        """Compose accounting on this owner; no new authority or budget is created.

        The existing public ReservationPort request remains unchanged. Missing
        resource-specific capabilities on the same captured owners deny. Native
        provisioning, public IPC composition and effect admission remain open.
        """
        from .resource_reservations import KernelResourceReservations
        return KernelResourceReservations(self, proposal_wire, request_context,
            maximum_observation_age_ns=maximum_observation_age_ns,
            maximum_owner_check_ns=maximum_owner_check_ns)


    @_coordinated
    def begin_owner_enrollment(self, request_wire: bytes, request_context: object) -> KernelResult:
        from .owner_authority import KernelOwnerAuthority
        return KernelOwnerAuthority(self).begin(request_wire, request_context)

    @_coordinated
    def enroll_owner(self, request_wire: bytes, transcript_wire: bytes, native_proof: object,
                     request_context: object) -> KernelResult:
        from .owner_authority import KernelOwnerAuthority
        return KernelOwnerAuthority(self).enroll(request_wire, transcript_wire, native_proof, request_context)

    @_coordinated
    def approve_owned_cpu(self, enrollment_id: str, request_wire: bytes, transcript_wire: bytes,
                          native_proof: object, request_context: object) -> KernelResult:
        from .owner_authority import KernelOwnerAuthority
        return KernelOwnerAuthority(self).approve(enrollment_id, request_wire, transcript_wire, native_proof, request_context)

    @_stopping
    def stop_owner_authority(self, enrollment_id: str, request_context: object, reason_ref: str) -> KernelResult:
        from .owner_authority import KernelOwnerAuthority
        return KernelOwnerAuthority(self).stop(enrollment_id, request_context, reason_ref)

    @_stopping
    def revoke_owner_authority(self, enrollment_id: str, request_context: object, reason_ref: str) -> KernelResult:
        from .owner_authority import KernelOwnerAuthority
        return KernelOwnerAuthority(self).stop(enrollment_id, request_context, reason_ref, revoke=True)

    def recover_owner_enrollment(self, enrollment_id: str, request_context: object):
        from .owner_authority import KernelOwnerAuthority
        return KernelOwnerAuthority(self).recover(enrollment_id, request_context)

    @_coordinated
    def begin_owned_cpu_attempt(self, request_wire: bytes, permit_wire: bytes,
                                native_proof: object, request_context: object):
        from .effect_transactions import KernelEffectTransactions
        return KernelEffectTransactions(self).begin(request_wire, permit_wire, native_proof, request_context)

    @_coordinated
    def record_owned_cpu_outcome(self, request_wire: bytes, permit_wire: bytes,
                                 receipt_wire: bytes, observation_wire: bytes | None,
                                 native_proof: object, request_context: object):
        from .effect_transactions import KernelEffectTransactions
        return KernelEffectTransactions(self).record(request_wire, permit_wire, receipt_wire,
            observation_wire, native_proof, request_context)

    def recover_owned_cpu_outcome(self, request_wire: bytes, permit_wire: bytes,
                                  request_context: object):
        from .effect_transactions import KernelEffectTransactions
        return KernelEffectTransactions(self).recover(request_wire, permit_wire, request_context)

    def owned_cpu_execution(self, request_wire: bytes, prepared_permit_wire: bytes,
                            native_binding: object, capture: object, native_proof: object,
                            request_context: object):
        """Create a single-use retained admission on this exact kernel.

        No configured native/current-view/physical-capacity owner means denial.
        Default runtime admission remains closed. Context entry consumes and
        reserves the canonical attempt; WT4 receives only the final fence.
        """
        return self._cpu_execution.create(request_wire, prepared_permit_wire,
            native_binding, capture, native_proof, request_context)


def control_without_profile(value):
    return {key: item for key, item in value.items() if key != "profile"}
