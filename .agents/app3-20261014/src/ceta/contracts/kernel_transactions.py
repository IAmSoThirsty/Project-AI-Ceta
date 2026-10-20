"""Internal CMP02 values and owner ports; construction is never authentication."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
from typing import Protocol

from .events import StreamPosition
from .history import HistoryPort
from .read_sets import ReadSet, ResourceRevision
from .store_transactions import AtomicStorePort, StoreCommit, StoreKey, MAX_GENERATION, identifier, commitment
from .temporal import ClockSample, Deadline
from .wire import ContractError, ParsedRecord, RecordCodec, MIN_INTEGER, MAX_INTEGER, canonical_bytes, strict_loads

KERNEL_PROFILE = "ceta-kernel-transactions-v1"
ALLOCATION_PROFILE = "ceta-allocation-liability-v1"
INTENT_PROFILE = "ceta-kernel-intent-v2"
BUDGET_FIELDS = ("wall_time_ms", "max_model_calls", "max_effects", "max_input_tokens",
                 "max_output_tokens", "max_bytes_read", "max_bytes_written")


def require(condition, code):
    if not condition:
        raise ContractError(code)


def object_value(wire, fields, profile=KERNEL_PROFILE):
    value = strict_loads(wire)
    require(type(value) is dict and set(value) == set(fields) | {"profile"}
            and value["profile"] == profile and canonical_bytes(value) == wire, "KERNEL_METADATA_INVALID")
    return value


def read_intent(wire):
    """Accept exact legacy intent-v1 or the explicitly selected intent-v2 shape."""
    value = strict_loads(wire)
    require(type(value) is dict, "KERNEL_METADATA_INVALID")
    fields = ("scope_id", "permit_id", "grant_key", "basis_wire", "cost", "deadline",
              "dependencies", "state", "consumption")
    profile = value.get("profile")
    if profile == INTENT_PROFILE:
        result = object_value(wire, fields + ("grant_commitment",), INTENT_PROFILE)
        commitment(result["grant_commitment"])
        return result
    return object_value(wire, fields)


def bound_generation(value):
    require(type(value) is int and 0 <= value <= MAX_GENERATION, "KERNEL_GENERATION_INVALID")
    return value


def digest(domain, value):
    return "sha256:" + hashlib.sha256(("CETA:kernel:" + domain + "\0").encode("ascii") + canonical_bytes(value)).hexdigest()


def logical_key(collection, scope_id, kind, logical_id):
    identifier(logical_id)
    return StoreKey(collection, scope_id, kind + ":" + hashlib.sha256(logical_id.encode("ascii")).hexdigest())


def basis_key(scope_id, proposal_id):
    return logical_key("projection", scope_id, "prepared", proposal_id)


def task_key(scope_id, task_id):
    return logical_key("projection", scope_id, "task", task_id)


def resource_key(scope_id, resource_id):
    return logical_key("projection", scope_id, "resource", resource_id)


def budget_key(grant_key):
    require(type(grant_key) is StoreKey and grant_key.collection == "grant", "KERNEL_GRANT_KEY_REQUIRED")
    return StoreKey("budget", grant_key.scope_id, grant_key.record_id)


def intent_key(scope_id, permit_id):
    return StoreKey("intent", scope_id, permit_id)


@dataclass(frozen=True)
class BudgetVector:
    """Development allocation units, not measured usage or billing semantics."""
    values: tuple[int, ...]

    def __post_init__(self):
        require(type(self.values) is tuple and len(self.values) == len(BUDGET_FIELDS)
                and all(type(v) is int and 0 <= v <= MAX_GENERATION for v in self.values), "KERNEL_BUDGET_INVALID")

    @classmethod
    def from_dict(cls, value):
        require(type(value) is dict and set(value) == set(BUDGET_FIELDS), "KERNEL_BUDGET_INVALID")
        return cls(tuple(value[name] for name in BUDGET_FIELDS))

    def as_dict(self):
        return dict(zip(BUDGET_FIELDS, self.values, strict=True))

    def add(self, other):
        require(type(other) is BudgetVector, "KERNEL_BUDGET_INVALID")
        return BudgetVector(tuple(a + b for a, b in zip(self.values, other.values, strict=True)))

    def subtract(self, other):
        require(type(other) is BudgetVector, "KERNEL_BUDGET_INVALID")
        return BudgetVector(tuple(a - b for a, b in zip(self.values, other.values, strict=True)))

    def contains(self, other):
        require(type(other) is BudgetVector, "KERNEL_BUDGET_INVALID")
        return all(a >= b for a, b in zip(self.values, other.values, strict=True))


ZERO_BUDGET = BudgetVector((0,) * len(BUDGET_FIELDS))


def budget_wire(scope_id, grant_id, limit, recovery, held=ZERO_BUDGET, charged=ZERO_BUDGET):
    identifier(scope_id); identifier(grant_id)
    require(all(type(v) is BudgetVector for v in (limit, recovery, held, charged)), "KERNEL_BUDGET_INVALID")
    require(limit.contains(recovery.add(held).add(charged)), "KERNEL_BUDGET_CONSERVATION_FAILED")
    return canonical_bytes({"profile": ALLOCATION_PROFILE, "scope_id": scope_id, "grant_id": grant_id,
                            "limit": limit.as_dict(), "recovery": recovery.as_dict(),
                            "held": held.as_dict(), "charged": charged.as_dict()})


def read_budget(wire, key):
    require(type(key) is StoreKey and key.collection == "budget", "KERNEL_BUDGET_KEY_REQUIRED")
    value = object_value(wire, ("scope_id", "grant_id", "limit", "recovery", "held", "charged"), ALLOCATION_PROFILE)
    require(value["scope_id"] == key.scope_id and value["grant_id"] == key.record_id, "KERNEL_BUDGET_KEY_MISMATCH")
    vectors = tuple(BudgetVector.from_dict(value[name]) for name in ("limit", "recovery", "held", "charged"))
    require(budget_wire(value["scope_id"], value["grant_id"], *vectors) == wire, "KERNEL_BUDGET_CONSERVATION_FAILED")
    return vectors


def control_wire(scope_id, authority_generation, fence_generation, policy_commitment, environment_commitment):
    identifier(scope_id); bound_generation(authority_generation); bound_generation(fence_generation)
    commitment(policy_commitment); commitment(environment_commitment)
    return canonical_bytes({"profile": KERNEL_PROFILE, "scope_id": scope_id, "authority_generation": authority_generation,
                            "fence_generation": fence_generation, "policy_commitment": policy_commitment,
                            "environment_commitment": environment_commitment})


def task_wire(scope_id, task_id, revision):
    identifier(scope_id); identifier(task_id); commitment(revision)
    return canonical_bytes({"profile": KERNEL_PROFILE, "scope_id": scope_id, "task_id": task_id, "revision": revision})


def resource_wire(scope_id, resource_id, revision):
    identifier(scope_id); identifier(resource_id); commitment(revision)
    return canonical_bytes({"profile": KERNEL_PROFILE, "scope_id": scope_id, "resource_id": resource_id, "revision": revision})


def encode_basis(proposal, grant_key, read_set, *, principal_id, actor_session, adapter_commitment,
                 registry_commitment, owner_input_commitment, candidate_commitment, task_revision,
                 review_refs, approval_evidence_ref):
    require(type(proposal) is ParsedRecord and proposal.record_type == "ActionProposal"
            and type(grant_key) is StoreKey and grant_key.collection == "grant" and type(read_set) is ReadSet,
            "KERNEL_PREPARED_BASIS_REQUIRED")
    for value in (principal_id, actor_session): identifier(value)
    if approval_evidence_ref is not None: identifier(approval_evidence_ref)
    require(not proposal.as_dict()["requires_human_approval"] or approval_evidence_ref is not None, "KERNEL_APPROVAL_REQUIRED")
    for value in (adapter_commitment, registry_commitment, owner_input_commitment, task_revision): commitment(value)
    if candidate_commitment is not None: commitment(candidate_commitment)
    require(type(review_refs) is tuple and len(review_refs) <= 128, "KERNEL_REVIEW_REFS_INVALID")
    for value in review_refs: identifier(value)
    require(len(set(review_refs)) == len(review_refs), "KERNEL_REVIEW_REFS_INVALID")
    require(proposal.as_dict()["scope_id"] == read_set.scope_id, "KERNEL_BASIS_SCOPE_MISMATCH")
    return canonical_bytes({"profile": KERNEL_PROFILE, "effect_state": "PREPARED", "proposal_wire": proposal.original_wire.decode("utf8"),
        "proposal_commitment": proposal.commitment, "grant_key": grant_key.as_dict(), "read_set": strict_loads(read_set.canonical_wire()),
        "principal_id": principal_id, "actor_session": actor_session, "adapter_commitment": adapter_commitment,
        "registry_commitment": registry_commitment, "owner_input_commitment": owner_input_commitment,
        "candidate_commitment": candidate_commitment, "task_revision": task_revision, "review_refs": list(review_refs),
        "approval_evidence_ref": approval_evidence_ref})


def read_basis(wire, codec):
    value = object_value(wire, ("effect_state", "proposal_wire", "proposal_commitment", "grant_key", "read_set", "principal_id",
        "actor_session", "adapter_commitment", "registry_commitment", "owner_input_commitment", "candidate_commitment",
        "task_revision", "review_refs", "approval_evidence_ref"))
    require(value["effect_state"] == "PREPARED" and type(value["proposal_wire"]) is str, "KERNEL_PREPARED_BASIS_REQUIRED")
    key = value["grant_key"]
    require(type(key) is dict and set(key) == {"collection", "scope_id", "record_id"}, "KERNEL_GRANT_KEY_REQUIRED")
    grant = StoreKey(**key)
    require(grant.collection == "grant", "KERNEL_GRANT_KEY_REQUIRED")
    r = value["read_set"]
    require(type(r) is dict and set(r) == {"contract_type", "contract_version", "read_set_profile", "canonicalization_profile",
            "scope_id", "authority_generation", "fence_generation", "policy_commitment", "environment_commitment", "resources"}
            and type(r["resources"]) is list, "KERNEL_READ_SET_INVALID")
    resources = []
    for resource in r["resources"]:
        require(type(resource) is dict and set(resource) == {"resource_id", "revision"}, "KERNEL_READ_SET_INVALID")
        resources.append(ResourceRevision(**resource))
    read_set = ReadSet(r["scope_id"], r["authority_generation"], r["fence_generation"], r["policy_commitment"], r["environment_commitment"], tuple(resources))
    require(strict_loads(read_set.canonical_wire()) == r, "KERNEL_READ_SET_PROFILE_MISMATCH")
    require(type(codec) is RecordCodec and type(value["review_refs"]) is list, "KERNEL_PREPARED_BASIS_REQUIRED")
    proposal = codec.decode(value["proposal_wire"].encode("utf8"))
    require(proposal.commitment == value["proposal_commitment"], "KERNEL_PROPOSAL_BINDING_MISMATCH")
    require(encode_basis(proposal, grant, read_set, principal_id=value["principal_id"], actor_session=value["actor_session"],
        adapter_commitment=value["adapter_commitment"], registry_commitment=value["registry_commitment"],
        owner_input_commitment=value["owner_input_commitment"], candidate_commitment=value["candidate_commitment"],
        task_revision=value["task_revision"], review_refs=tuple(value["review_refs"]),
        approval_evidence_ref=value["approval_evidence_ref"]) == wire, "KERNEL_PREPARED_BASIS_REQUIRED")
    return value, grant, read_set


def deadline_wire(deadline):
    require(type(deadline) is Deadline, "DEADLINE_REQUIRED")
    return {name: getattr(deadline, name) for name in deadline.__dataclass_fields__}


def deadline_text(nanoseconds):
    require(type(nanoseconds) is int and MIN_INTEGER <= nanoseconds <= MAX_INTEGER, "INVALID_TEMPORAL_INTEGER")
    seconds, fraction = divmod(nanoseconds, 1_000_000_000)
    instant = datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)
    return instant.strftime("%Y-%m-%dT%H:%M:%S") + (("." + f"{fraction:09d}").rstrip("0") if fraction else "") + "Z"


@dataclass(frozen=True)
class PeerIdentity:
    principal_id: str
    session_id: str

    def __post_init__(self):
        identifier(self.principal_id); identifier(self.session_id)


class AuthorityOwners(Protocol):
    """Captured trusted-owner seams; no concrete OS authentication exists here.

    Prepared-basis verification must resolve the preceding preparation decision,
    policy/registry, evidence, and exact consent. Admission checks actual peer,
    protected handles and preconditions. Tests explicitly supply fixture owners.
    Worker data and these Python types do not authenticate any owner.

    Authentication must revalidate the exact captured context and process lifetime.
    Predicates may run initially, inside the writer transaction immediately before
    COMMIT, and after COMMIT. They verify current trusted facts using the identical
    original proposal/PREPARED permit/revocable grant and basis, returning None or
    a typed denial. Checks must be bounded, repeatable, side-effect-free and must
    not reenter kernel/store commands, consume approval, allocate authority, or
    wait for model/human/external work. Transaction-owned rows need not retain
    their pre-transition state after COMMIT; the kernel/store owns that CAS.
    Repeated sampling does not retain protected resources across an effect.
    """
    def authenticate(self, request_context: object) -> PeerIdentity: ...
    def require_prepared_basis(self, proposal: ParsedRecord, basis_wire: bytes, peer: PeerIdentity) -> None: ...
    def require_admission(self, permit: ParsedRecord, basis_wire: bytes, peer: PeerIdentity) -> None: ...
    def require_revocation(self, grant: ParsedRecord, peer: PeerIdentity, reason_ref: str) -> None: ...
    def clock(self) -> tuple[ClockSample, ClockSample]: ...


class KernelStorePort(AtomicStorePort, HistoryPort, Protocol):
    """One composed store provides both existing ports; no second writer."""


@dataclass(frozen=True)
class KernelResult:
    record_wire: bytes
    event_wire: bytes
    prior_position: StreamPosition
    commit: StoreCommit

    def __post_init__(self):
        require(type(self.record_wire) is bytes and type(self.event_wire) is bytes
                and type(self.prior_position) is StreamPosition and type(self.commit) is StoreCommit,
                "KERNEL_RESULT_INVALID")
