"""Relevant-state comparisons for preparation, with no authority issuance.

The kernel/registry must determine the complete resource dependency list, and
the trusted state owner must supply the actual current values. Neither is
authenticated here. The broker must still recheck protected resource handles
and consume authority atomically at its admission boundary.
"""
from dataclasses import dataclass
import hashlib
import re

from .wire import ContractError, PROFILE, canonical_bytes

READ_SET_PROFILE = "ceta-relevant-state-v1"
MAX_RESOURCES = 4096
MAX_GENERATION = 2**53 - 1
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")
_HASH = re.compile(r"sha256:[0-9a-f]{64}")


def _identifier(value: str) -> None:
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ContractError("INVALID_READ_SET_IDENTIFIER")


def _commitment(value: str) -> None:
    if type(value) is not str or not _HASH.fullmatch(value):
        raise ContractError("INVALID_REVISION_COMMITMENT")


@dataclass(frozen=True)
class ResourceRevision:
    resource_id: str
    revision: str

    def __post_init__(self) -> None:
        _identifier(self.resource_id)
        _commitment(self.revision)


@dataclass(frozen=True)
class ReadSet:
    scope_id: str
    authority_generation: int
    fence_generation: int
    policy_commitment: str
    environment_commitment: str
    resources: tuple[ResourceRevision, ...]

    def __post_init__(self) -> None:
        _identifier(self.scope_id)
        for generation in (self.authority_generation, self.fence_generation):
            if type(generation) is not int or not 0 <= generation <= MAX_GENERATION:
                raise ContractError("INVALID_REVISION_GENERATION")
        _commitment(self.policy_commitment)
        _commitment(self.environment_commitment)
        if (type(self.resources) is not tuple or not 1 <= len(self.resources) <= MAX_RESOURCES
                or any(type(resource) is not ResourceRevision for resource in self.resources)):
            raise ContractError("INVALID_READ_SET_RESOURCES")
        identifiers = [resource.resource_id for resource in self.resources]
        if len(set(identifiers)) != len(identifiers):
            raise ContractError("DUPLICATE_RESOURCE_REVISION")

    def canonical_wire(self) -> bytes:
        """Internal metadata identity; not a 21st admitted wire record type."""
        return canonical_bytes({
            "contract_type": "RelevantReadSet", "contract_version": "1",
            "read_set_profile": READ_SET_PROFILE, "canonicalization_profile": PROFILE,
            "scope_id": self.scope_id, "authority_generation": self.authority_generation,
            "fence_generation": self.fence_generation, "policy_commitment": self.policy_commitment,
            "environment_commitment": self.environment_commitment,
            "resources": [{"resource_id": r.resource_id, "revision": r.revision}
                          for r in sorted(self.resources, key=lambda r: r.resource_id)],
        })

    def commitment(self) -> str:
        domain = ("CETA:read-set:" + READ_SET_PROFILE + "\0").encode("ascii")
        return "sha256:" + hashlib.sha256(domain + self.canonical_wire()).hexdigest()


def require_current_preparation(expected: ReadSet, current: ReadSet,
                                required_resource_ids: tuple[str, ...]) -> None:
    """Reject stale/incomplete preparation under injected trusted dependencies.

    The caller must obtain required_resource_ids from the kernel's operation
    registry and actual target resolution, not from a model-authored read set.
    Current snapshots can include unrelated resources. Global journal position
    and telemetry counters are intentionally absent from this contract.
    """
    if type(expected) is not ReadSet or type(current) is not ReadSet:
        raise ContractError("READ_SET_REQUIRED")
    if type(required_resource_ids) is not tuple or not 1 <= len(required_resource_ids) <= MAX_RESOURCES:
        raise ContractError("INVALID_REQUIRED_RESOURCES")
    for resource_id in required_resource_ids:
        _identifier(resource_id)
    if len(set(required_resource_ids)) != len(required_resource_ids):
        raise ContractError("DUPLICATE_REQUIRED_RESOURCE")
    prepared = {r.resource_id: r.revision for r in expected.resources}
    if set(prepared) != set(required_resource_ids):
        raise ContractError("READ_SET_DEPENDENCY_MISMATCH")
    if expected.scope_id != current.scope_id:
        raise ContractError("READ_SET_SCOPE_MISMATCH")
    for field, code in (
        ("authority_generation", "AUTHORITY_GENERATION_CHANGED"),
        ("fence_generation", "FENCE_GENERATION_CHANGED"),
        ("policy_commitment", "POLICY_REVISION_CHANGED"),
        ("environment_commitment", "ENVIRONMENT_REVISION_CHANGED"),
    ):
        if getattr(expected, field) != getattr(current, field):
            raise ContractError(code)
    observed = {r.resource_id: r.revision for r in current.resources}
    for resource_id, revision in prepared.items():
        if resource_id not in observed:
            raise ContractError("CURRENT_RESOURCE_REVISION_MISSING")
        if observed[resource_id] != revision:
            raise ContractError("RESOURCE_REVISION_CHANGED")
