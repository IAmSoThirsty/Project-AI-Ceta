"""Internal resource-accounting profile; typed construction grants no authority.

The existing CMP02/CMP03 owners retain approval and transaction ownership.
These values deliberately do not provision a budget, authenticate an observer,
authorize a workload or certify cleanup. Their references must be resolved by
the captured trusted owner before mutation or positive result publication.
"""
from dataclasses import dataclass
from typing import Protocol

from .kernel_transactions import (PeerIdentity, bound_generation, commitment,
    deadline_wire, digest, identifier, logical_key, object_value, require)
from .resource_management import BudgetEnvelope, ReservationRequest, ResourceVector
from .store_transactions import StoreKey
from .temporal import Deadline
from .wire import ParsedRecord, canonical_bytes

RESOURCE_RESERVATION_PROFILE = "ceta-kernel-resource-reservations-v1"
VECTOR_FIELDS = tuple(ResourceVector.__dataclass_fields__)
ZERO_RESOURCES = ResourceVector(0, 0, 0, 0)


def vector_value(vector: ResourceVector) -> dict:
    require(type(vector) is ResourceVector, "RESOURCE_VECTOR_REQUIRED")
    vector.__post_init__()
    return {name: getattr(vector, name) for name in VECTOR_FIELDS}


def read_vector(value: dict) -> ResourceVector:
    require(type(value) is dict and set(value) == set(VECTOR_FIELDS), "RESOURCE_VECTOR_INVALID")
    return ResourceVector(**value)


def request_value(request: ReservationRequest) -> dict:
    require(type(request) is ReservationRequest, "RESOURCE_RESERVATION_REQUEST_REQUIRED")
    request.__post_init__()
    value = {name: getattr(request, name) for name in ReservationRequest.__dataclass_fields__}
    value["requirements"] = vector_value(request.requirements)
    bound_generation(request.expected_generation)
    return value


def read_request(value: dict) -> ReservationRequest:
    require(type(value) is dict and set(value) == set(ReservationRequest.__dataclass_fields__),
            "RESOURCE_RESERVATION_REQUEST_INVALID")
    result = ReservationRequest(**dict(value, requirements=read_vector(value["requirements"])))
    require(request_value(result) == value, "RESOURCE_RESERVATION_REQUEST_INVALID")
    return result


def resource_budget_key(scope_id: str, budget_id: str) -> StoreKey:
    """Separate logical key in the existing budget collection, with no new store."""
    return logical_key("budget", scope_id, "resource-budget", budget_id)


def resource_lease_key(scope_id: str, request_id: str) -> StoreKey:
    """Request identity is unique within its canonical scope, across budgets."""
    return logical_key("reservation", scope_id, "resource-lease", request_id)


@dataclass(frozen=True)
class ResourceBudgetBinding:
    scope_id: str
    task_id: str
    principal_id: str
    session_id: str
    proposal_commitment: str
    basis_commitment: str
    grant_key: StoreKey
    grant_commitment: str
    authority_generation: int
    fence_generation: int
    policy_commitment: str
    environment_commitment: str
    deadline: Deadline

    def __post_init__(self) -> None:
        for value in (self.scope_id, self.task_id, self.principal_id, self.session_id):
            identifier(value)
        for value in (self.proposal_commitment, self.basis_commitment, self.grant_commitment,
                      self.policy_commitment, self.environment_commitment):
            commitment(value)
        require(type(self.grant_key) is StoreKey and self.grant_key.collection == "grant",
                "KERNEL_GRANT_KEY_REQUIRED")
        bound_generation(self.authority_generation); bound_generation(self.fence_generation)
        require(type(self.deadline) is Deadline, "DEADLINE_REQUIRED")
        self.deadline.__post_init__()

    def as_dict(self) -> dict:
        self.__post_init__()
        value = {name: getattr(self, name) for name in self.__dataclass_fields__}
        value.update(grant_key=self.grant_key.as_dict(), deadline=deadline_wire(self.deadline))
        return value

    @classmethod
    def from_dict(cls, value: dict) -> "ResourceBudgetBinding":
        require(type(value) is dict and set(value) == set(cls.__dataclass_fields__),
                "RESOURCE_BUDGET_BINDING_INVALID")
        require(type(value["grant_key"]) is dict and set(value["grant_key"]) == {"collection", "scope_id", "record_id"},
                "KERNEL_GRANT_KEY_REQUIRED")
        require(type(value["deadline"]) is dict and set(value["deadline"]) == set(Deadline.__dataclass_fields__),
                "DEADLINE_REQUIRED")
        result = cls(**dict(value, grant_key=StoreKey(**value["grant_key"]), deadline=Deadline(**value["deadline"])))
        require(result.as_dict() == value, "RESOURCE_BUDGET_BINDING_INVALID")
        return result


def resource_budget_wire(binding: ResourceBudgetBinding, envelope: BudgetEnvelope) -> bytes:
    """Serialize owner input; this function supplies no positive approval proof."""
    require(type(binding) is ResourceBudgetBinding and type(envelope) is BudgetEnvelope,
            "RESOURCE_BUDGET_RECORD_REQUIRED")
    binding.__post_init__(); envelope.__post_init__(); bound_generation(envelope.generation)
    value = {name: getattr(envelope, name) for name in envelope.__dataclass_fields__}
    for name in ("limit", "control_reserve", "measured_use", "reserved_use"):
        value[name] = vector_value(value[name])
    return canonical_bytes({"profile": RESOURCE_RESERVATION_PROFILE, "binding": binding.as_dict(), "budget": value})


def read_resource_budget(wire: bytes, key: StoreKey) -> tuple[ResourceBudgetBinding, BudgetEnvelope]:
    value = object_value(wire, ("binding", "budget"), RESOURCE_RESERVATION_PROFILE)
    binding = ResourceBudgetBinding.from_dict(value["binding"])
    budget = value["budget"]
    require(type(budget) is dict and set(budget) == set(BudgetEnvelope.__dataclass_fields__), "RESOURCE_BUDGET_RECORD_INVALID")
    fields = dict(budget)
    for name in ("limit", "control_reserve", "measured_use", "reserved_use"):
        fields[name] = read_vector(fields[name])
    envelope = BudgetEnvelope(**fields)
    require(type(key) is StoreKey and resource_budget_key(binding.scope_id, envelope.budget_id) == key,
            "RESOURCE_BUDGET_KEY_MISMATCH")
    require(resource_budget_wire(binding, envelope) == wire, "RESOURCE_BUDGET_RECORD_INVALID")
    return binding, envelope


@dataclass(frozen=True)
class ResourceLease:
    """Durable accounting observation; HELD does not authorize an external effect."""
    binding: ResourceBudgetBinding
    request: ReservationRequest
    reservation_ref: str
    state: str
    allocated_generation: int | None
    terminal_generation: int | None
    reason_ref: str | None

    def __post_init__(self) -> None:
        require(type(self.binding) is ResourceBudgetBinding, "RESOURCE_BUDGET_BINDING_INVALID")
        self.binding.__post_init__(); request_value(self.request)
        require(self.reservation_ref == resource_lease_key(self.binding.scope_id, self.request.request_id).record_id,
                "RESOURCE_LEASE_KEY_MISMATCH")
        require(type(self.state) is str and self.state in {"HELD", "RELEASED", "CANCELLED"},
                "RESOURCE_LEASE_STATE_INVALID")
        if self.allocated_generation is not None:
            bound_generation(self.allocated_generation)
            require(self.allocated_generation > self.request.expected_generation, "RESOURCE_LEASE_GENERATION_INVALID")
        if self.state == "HELD":
            require(self.allocated_generation is not None and self.terminal_generation is None and self.reason_ref is None,
                    "RESOURCE_LEASE_STATE_INVALID")
        else:
            bound_generation(self.terminal_generation); identifier(self.reason_ref)
            require(self.terminal_generation >= (self.allocated_generation or 0), "RESOURCE_LEASE_GENERATION_INVALID")
            require(self.state == "CANCELLED" or self.allocated_generation is not None, "RESOURCE_LEASE_STATE_INVALID")

    @property
    def canonical_wire(self) -> bytes:
        self.__post_init__()
        return canonical_bytes({"profile": RESOURCE_RESERVATION_PROFILE, "binding": self.binding.as_dict(),
            "request": request_value(self.request), "reservation_ref": self.reservation_ref, "state": self.state,
            "allocated_generation": self.allocated_generation, "terminal_generation": self.terminal_generation,
            "reason_ref": self.reason_ref})

    @classmethod
    def from_wire(cls, wire: bytes, key: StoreKey) -> "ResourceLease":
        value = object_value(wire, tuple(cls.__dataclass_fields__), RESOURCE_RESERVATION_PROFILE)
        result = cls(**{name: value[name] for name in cls.__dataclass_fields__ if name not in {"binding", "request"}},
                     binding=ResourceBudgetBinding.from_dict(value["binding"]), request=read_request(value["request"]))
        require(type(key) is StoreKey and resource_lease_key(result.binding.scope_id, result.request.request_id) == key,
                "RESOURCE_LEASE_KEY_MISMATCH")
        require(result.canonical_wire == wire, "RESOURCE_LEASE_RECORD_INVALID")
        return result


class ResourceReservationCapabilities(Protocol):
    """Additional predicates on the SAME captured AuthorityOwners object.

    The reservation predicate resolves exact current allocation approval and
    the request's observation/clock domain. The cleanup predicate verifies that
    the held resources are no longer in use, including uncertain native effects.
    Neither a caller reason nor a digest certifies approval or cleanup.

    Both predicates must be bounded, repeatable and side-effect-free, return
    None or raise a typed denial, and NEVER reenter the kernel/store or wait for
    external work. They run inside the existing SQLite commit guard as well as
    before positive publication. Elapsed checks can reject an overlong return;
    arbitrary synchronous Python callbacks cannot be preempted by this port.
    No concrete native implementation or budget provisioning is supplied here.
    """
    def require_resource_reservation(self, proposal: ParsedRecord, basis_wire: bytes,
                                     budget_wire: bytes, request: ReservationRequest, peer: PeerIdentity) -> None: ...

    def require_resource_cleanup(self, proposal: ParsedRecord, lease_wire: bytes, peer: PeerIdentity) -> None: ...
