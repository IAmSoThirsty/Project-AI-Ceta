"""Bounded internal production records shared by the r6 component ports.

These values preserve exact bindings and independent execution/observation
states. They do not authenticate their producer or add a public IPC record to
the existing twenty-record codec. Trusted owners resolve their commitments.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib

from .kernel_transactions import BudgetVector
from .read_sets import ReadSet, ResourceRevision
from .store_transactions import MAX_GENERATION, commitment as _commitment, identifier
from .temporal import ClockSample, Deadline
from .wire import ContractError, canonical_bytes, strict_loads

PROFILE = "ceta-production-internal-records-v1"
MAX_REFERENCES = 4096


def _require(value, code):
    if value is not True:
        raise ContractError(code)


def _counter(value):
    _require(type(value) is int and 0 <= value <= MAX_GENERATION,
             "RUNTIME_COUNTER_INVALID")


def _capture(value, kind):
    _require(type(value) is kind, "RUNTIME_RECORD_TYPE_REQUIRED")
    try:
        return kind(**{field.name: getattr(value, field.name) for field in fields(kind)})
    except (AttributeError, TypeError) as error:
        raise ContractError("RUNTIME_RECORD_INCOMPLETE") from error


def _read_set(value):
    _require(type(value) is ReadSet, "RUNTIME_READ_SET_REQUIRED")
    try:
        resources = value.resources
        _require(type(resources) is tuple and 1 <= len(resources) <= MAX_REFERENCES,
                 "RUNTIME_RESOURCE_SET_INVALID")
        return ReadSet(value.scope_id, value.authority_generation, value.fence_generation,
                       value.policy_commitment, value.environment_commitment,
                       tuple(_capture(row, ResourceRevision) for row in resources))
    except (AttributeError, TypeError) as error:
        raise ContractError("RUNTIME_READ_SET_INVALID") from error


def _references(values, *, required=False):
    _require(type(values) is tuple and int(required) <= len(values) <= MAX_REFERENCES,
             "RUNTIME_REFERENCES_INVALID")
    for value in values:
        _commitment(value)
    _require(len(set(values)) == len(values), "RUNTIME_REFERENCES_DUPLICATE")
    return tuple(values)


def _names(values):
    _require(type(values) is tuple and 1 <= len(values) <= 256,
             "RUNTIME_OPERATION_SET_INVALID")
    for value in values:
        identifier(value)
    _require(len(set(values)) == len(values), "RUNTIME_OPERATION_SET_DUPLICATE")
    return tuple(values)


def _plain(value):
    if type(value) in _RECORD_TYPES:
        captured = _capture(value, type(value))
        return {field.name: _plain(getattr(captured, field.name)) for field in fields(captured)}
    if type(value) is ReadSet:
        return strict_loads(_read_set(value).canonical_wire())
    if type(value) in (ClockSample, Deadline):
        captured = _capture(value, type(value))
        return {field.name: getattr(captured, field.name) for field in fields(captured)}
    if type(value) is BudgetVector:
        return _capture(value, BudgetVector).as_dict()
    if type(value) is tuple:
        return [_plain(item) for item in value]
    _require(value is None or type(value) in (str, int, bool), "RUNTIME_VALUE_INVALID")
    return value


class _InternalRecord:
    def canonical_wire(self):
        _require(type(self) in _RECORD_TYPES, "RUNTIME_RECORD_TYPE_REQUIRED")
        return canonical_bytes({"profile": PROFILE, "record_type": type(self).__name__,
                                "record_version": "1", "value": _plain(self)})

    def commitment(self):
        wire = self.canonical_wire()
        domain = ("CETA:" + PROFILE + ":" + type(self).__name__ + "\0").encode("ascii")
        return "sha256:" + hashlib.sha256(domain + wire).hexdigest()

    @classmethod
    def from_wire(cls, wire):
        _require(cls in _RECORD_TYPES, "RUNTIME_RECORD_TYPE_REQUIRED")
        document = strict_loads(wire)
        _require(type(document) is dict and set(document) ==
                 {"profile", "record_type", "record_version", "value"},
                 "RUNTIME_RECORD_SHAPE_INVALID")
        _require(document["profile"] == PROFILE and document["record_version"] == "1"
                 and document["record_type"] == cls.__name__, "RUNTIME_RECORD_VERSION_INVALID")
        result = _decode_value(cls, document["value"])
        _require(result.canonical_wire() == wire, "RUNTIME_RECORD_NONCANONICAL")
        return result


@dataclass(frozen=True, slots=True)
class RuntimeBasis(_InternalRecord):
    scope_id: str
    task_id: str
    principal_id: str
    actor_session_id: str
    task_revision: str
    objective_commitment: str
    candidate_commitment: str
    expected_store_revision: str | None
    read_set: ReadSet
    deadline: Deadline

    def __post_init__(self):
        for value in (self.scope_id, self.task_id, self.principal_id, self.actor_session_id):
            identifier(value)
        for value in (self.task_revision, self.objective_commitment, self.candidate_commitment):
            _commitment(value)
        if self.expected_store_revision is not None:
            _commitment(self.expected_store_revision)
        captured = _read_set(self.read_set)
        _require(captured.scope_id == self.scope_id, "RUNTIME_SCOPE_MISMATCH")
        object.__setattr__(self, "read_set", captured)
        object.__setattr__(self, "deadline", _capture(self.deadline, Deadline))


@dataclass(frozen=True, slots=True)
class AcceptanceIntent(_InternalRecord):
    intent_id: str
    basis: RuntimeBasis
    raw_input_commitment: str
    meaning_commitment: str
    proposal_commitment: str
    expected_draft_revision: int

    def __post_init__(self):
        identifier(self.intent_id)
        object.__setattr__(self, "basis", _capture(self.basis, RuntimeBasis))
        for value in (self.raw_input_commitment, self.meaning_commitment, self.proposal_commitment):
            _commitment(value)
        _counter(self.expected_draft_revision)


@dataclass(frozen=True, slots=True)
class ApprovalEvidence(_InternalRecord):
    evidence_id: str
    intent_commitment: str
    scope_id: str
    task_id: str
    principal_id: str
    actor_session_id: str
    display_commitment: str
    decision_reference: str
    decision_commitment: str
    decision: str
    observed_clock: ClockSample
    deadline: Deadline

    def __post_init__(self):
        for value in (self.evidence_id, self.scope_id, self.task_id, self.principal_id,
                      self.actor_session_id, self.decision_reference):
            identifier(value)
        for value in (self.intent_commitment, self.display_commitment, self.decision_commitment):
            _commitment(value)
        _require(type(self.decision) is str and self.decision in
                 {"APPROVED", "DENIED", "CANCELLED"}, "RUNTIME_APPROVAL_STATE_INVALID")
        clock = _capture(self.observed_clock, ClockSample)
        deadline = _capture(self.deadline, Deadline)
        _require((clock.boot_id, clock.durable_epoch, clock.resume_generation) ==
                 (deadline.boot_id, deadline.durable_epoch, deadline.resume_generation),
                 "RUNTIME_APPROVAL_EPOCH_MISMATCH")
        object.__setattr__(self, "observed_clock", clock)
        object.__setattr__(self, "deadline", deadline)

    def require_intent(self, intent, *, displayed_commitment):
        """Check exact captured data; the identity owner authenticates the decision."""
        evidence = _capture(self, ApprovalEvidence)
        accepted = _capture(intent, AcceptanceIntent)
        _commitment(displayed_commitment)
        _require(evidence.intent_commitment == accepted.commitment()
                 and evidence.display_commitment == displayed_commitment,
                 "RUNTIME_APPROVAL_BINDING_MISMATCH")
        for name in ("scope_id", "task_id", "principal_id", "actor_session_id"):
            _require(getattr(evidence, name) == getattr(accepted.basis, name),
                     "RUNTIME_APPROVAL_IDENTITY_MISMATCH")
        _require(evidence.deadline == accepted.basis.deadline,
                 "RUNTIME_APPROVAL_DEADLINE_MISMATCH")


@dataclass(frozen=True, slots=True)
class RuntimeAdmission(_InternalRecord):
    admission_id: str
    basis: RuntimeBasis
    permit_id: str
    consumed_permit_commitment: str
    prepared_request_commitment: str
    runtime_lease_id: str
    runtime_commitment: str
    worker_session_id: str
    reserved_budget: BudgetVector

    def __post_init__(self):
        for value in (self.admission_id, self.permit_id, self.runtime_lease_id, self.worker_session_id):
            identifier(value)
        object.__setattr__(self, "basis", _capture(self.basis, RuntimeBasis))
        for value in (self.consumed_permit_commitment, self.prepared_request_commitment,
                      self.runtime_commitment):
            _commitment(value)
        object.__setattr__(self, "reserved_budget", _capture(self.reserved_budget, BudgetVector))


@dataclass(frozen=True, slots=True)
class AdapterManifest(_InternalRecord):
    adapter_id: str
    adapter_version: str
    operation_ids: tuple[str, ...]
    operation_catalog_commitment: str
    schema_commitment: str
    executable_commitment: str
    configuration_commitment: str
    maximum_request_bytes: int
    maximum_response_bytes: int

    def __post_init__(self):
        identifier(self.adapter_id)
        identifier(self.adapter_version)
        object.__setattr__(self, "operation_ids", _names(self.operation_ids))
        for value in (self.operation_catalog_commitment, self.schema_commitment,
                      self.executable_commitment, self.configuration_commitment):
            _commitment(value)
        for value in (self.maximum_request_bytes, self.maximum_response_bytes):
            _require(type(value) is int and 1 <= value <= 1024 * 1024,
                     "RUNTIME_ADAPTER_WIRE_BOUND_INVALID")

    def require_operation(self, operation_id, *, catalog_commitment):
        manifest = _capture(self, AdapterManifest)
        identifier(operation_id)
        _commitment(catalog_commitment)
        _require(manifest.operation_catalog_commitment == catalog_commitment,
                 "RUNTIME_OPERATION_CATALOG_CHANGED")
        _require(operation_id in manifest.operation_ids, "RUNTIME_ADAPTER_OPERATION_UNDECLARED")


@dataclass(frozen=True, slots=True)
class ObservedOutcome(_InternalRecord):
    outcome_id: str
    admission_commitment: str
    execution_receipt_commitment: str | None
    observer_id: str
    observer_session_id: str
    execution_state: str
    effect_state: str
    observed_resource_commitments: tuple[str, ...]
    evidence_commitments: tuple[str, ...]
    actual_usage: BudgetVector | None

    def __post_init__(self):
        for value in (self.outcome_id, self.observer_id, self.observer_session_id):
            identifier(value)
        _commitment(self.admission_commitment)
        if self.execution_receipt_commitment is not None:
            _commitment(self.execution_receipt_commitment)
        _require(type(self.execution_state) is str and self.execution_state in
                 {"NOT_STARTED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED",
                  "TIMED_OUT", "INTERRUPTED", "INDETERMINATE"},
                 "RUNTIME_EXECUTION_STATE_INVALID")
        _require(type(self.effect_state) is str and self.effect_state in
                 {"NOT_OBSERVED", "NO_EFFECT", "EXPECTED_EFFECT", "UNEXPECTED_EFFECT",
                  "PARTIAL_EFFECT", "INDETERMINATE"}, "RUNTIME_EFFECT_STATE_INVALID")
        observed = self.effect_state not in {"NOT_OBSERVED", "INDETERMINATE"}
        object.__setattr__(self, "observed_resource_commitments",
                           _references(self.observed_resource_commitments, required=observed))
        object.__setattr__(self, "evidence_commitments",
                           _references(self.evidence_commitments, required=observed))
        if self.actual_usage is not None:
            object.__setattr__(self, "actual_usage", _capture(self.actual_usage, BudgetVector))

    def require_admission(self, admission):
        observation = _capture(self, ObservedOutcome)
        captured = _capture(admission, RuntimeAdmission)
        _require(observation.admission_commitment == captured.commitment(),
                 "RUNTIME_OUTCOME_ADMISSION_MISMATCH")


_RECORD_TYPES = (RuntimeBasis, AcceptanceIntent, ApprovalEvidence, RuntimeAdmission,
                 AdapterManifest, ObservedOutcome)


def _object(value, names):
    _require(type(value) is dict and set(value) == set(names), "RUNTIME_NESTED_SHAPE_INVALID")
    return dict(value)


def _decode_value(kind, value):
    document = _object(value, (field.name for field in fields(kind)))
    if kind is RuntimeBasis:
        read = _object(document["read_set"], ("contract_type", "contract_version", "read_set_profile",
            "canonicalization_profile", "scope_id", "authority_generation", "fence_generation",
            "policy_commitment", "environment_commitment", "resources"))
        rows = read["resources"]
        _require(type(rows) is list and 1 <= len(rows) <= MAX_REFERENCES,
                 "RUNTIME_RESOURCE_SET_INVALID")
        resources = tuple(ResourceRevision(**_object(row, ("resource_id", "revision"))) for row in rows)
        parsed = ReadSet(read["scope_id"], read["authority_generation"], read["fence_generation"],
                         read["policy_commitment"], read["environment_commitment"], resources)
        _require(strict_loads(parsed.canonical_wire()) == read, "RUNTIME_READ_SET_PROFILE_MISMATCH")
        document["read_set"] = parsed
    if "basis" in document:
        document["basis"] = _decode_value(RuntimeBasis, document["basis"])
    for name, target in (("deadline", Deadline), ("observed_clock", ClockSample)):
        if name in document:
            document[name] = target(**_object(document[name], (field.name for field in fields(target))))
    for name in ("reserved_budget", "actual_usage"):
        if name in document and document[name] is not None:
            document[name] = BudgetVector.from_dict(document[name])
    for name in ("operation_ids", "observed_resource_commitments", "evidence_commitments"):
        if name in document:
            _require(type(document[name]) is list, "RUNTIME_SEQUENCE_INVALID")
            document[name] = tuple(document[name])
    return kind(**document)
