"""Finding 5 evidence-binding predicates, IMPLEMENTED_NOT_QUALIFIED.

These are pure checks, not authenticated provenance, a permit issuer, a store,
or a verifier's acceptance decision. Composition must own the resolvers. All
resolver results remain unauthenticated inputs in this implementation. Runtime
admission is explicitly closed pending the actual trusted owners and integration.
"""
from dataclasses import dataclass
import re
from typing import Callable

from .events import EventContract, StreamPosition
from .read_sets import ReadSet, require_current_preparation
from .wire import ContractError, ParsedRecord, RecordCodec

_HASH = re.compile(r"sha256:[0-9a-f]{64}")
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")


@dataclass(frozen=True)
class ConsumptionEvidence:
    """Internal store-resolution input; construction does not prove durability."""

    consumed_permit_wire: bytes
    event_wire: bytes
    prior_position: StreamPosition


@dataclass(frozen=True)
class QualificationEvidence:
    """Internal verifier-resolution input, not another admitted wire record.

    The commitment freezes the exact qualification candidate, including scope,
    executable, configuration, fixture, policy, counts and claimed independence.
    Counts and bundle identities must come from separately resolved evidence.
    Neither these values nor their equality authenticates the provider or proves
    that the frozen threshold policy and independence obligations were satisfied.
    """

    qualification_commitment: str
    sample_count: int
    failure_count: int
    skip_count: int
    bundle_commitments: tuple[tuple[str, str], ...]
    independence_evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class PreparationEvidence:
    """Kernel-resolved dependencies and current state; no worker ownership."""

    proposal_commitment: str
    required_resource_ids: tuple[str, ...]
    current: ReadSet


class EvidenceAdmissionChecks:
    """Check source-supported prerequisites without promoting them to authority.

    Resolver wiring belongs to the kernel/store/verifier composition, never to
    worker IPC. There is no caller-supplied required-resource list, authenticated
    boolean, trusted-role label, threshold override or allow flag on check calls.
    Tests may inject fixtures to exercise only these mechanical predicates.
    """

    def __init__(
        self, codec: RecordCodec, *,
        resolve_consumption: Callable[[ParsedRecord], ConsumptionEvidence] | None = None,
        resolve_qualification: Callable[[ParsedRecord], QualificationEvidence] | None = None,
        resolve_preparation: Callable[[ParsedRecord], PreparationEvidence] | None = None,
    ) -> None:
        self._codec = codec
        self._events = EventContract(codec)
        self._resolve_consumption = resolve_consumption
        self._resolve_qualification = resolve_qualification
        self._resolve_preparation = resolve_preparation

    def check_permit_evidence(self, permit_wire: bytes) -> None:
        """Reject a spent-state claim without a bound consumed snapshot/event.

        A pre-consumption record remains structurally legitimate. Passing this
        check neither redeems it nor establishes that any effect occurred.
        No event-type name is invented: the eventual authenticated store owner
        must resolve the actual consumption event under the adopted event model.
        """
        record = self._codec.decode(permit_wire)
        if record.record_type != "OperationPermit":
            raise ContractError("OPERATION_PERMIT_REQUIRED")
        permit = record.as_dict()
        needs_consumption = permit["status"] in {"CONSUMED", "SETTLED"}
        if permit["consume_event_ref"] is None:
            if needs_consumption:
                raise ContractError("CONSUMPTION_REFERENCE_REQUIRED")
            return
        if self._resolve_consumption is None:
            raise ContractError("CONSUMPTION_EVIDENCE_UNAVAILABLE")
        evidence = self._resolve_consumption(record)
        if type(evidence) is not ConsumptionEvidence:
            raise ContractError("CONSUMPTION_EVIDENCE_REQUIRED")
        event = self._events.require_successor(evidence.event_wire, evidence.prior_position)
        if event.record.record_id != permit["consume_event_ref"]:
            raise ContractError("CONSUMPTION_EVENT_REFERENCE_MISMATCH")
        payload = self._events.require_payload(evidence.event_wire, evidence.consumed_permit_wire)
        if payload.record_type != "OperationPermit":
            raise ContractError("CONSUMED_PERMIT_PAYLOAD_REQUIRED")
        consumed = payload.as_dict()
        if consumed["status"] != "CONSUMED":
            raise ContractError("CONSUMED_PERMIT_STATUS_REQUIRED")
        # Status and the later causal reference may change at settlement. Every
        # other supplied field, including record/nonce/task/grant/resource identity,
        # expiry, reservation, issuance and the consumption reference must agree.
        for field in permit:
            if field not in {"status", "causation_ref"} and permit[field] != consumed[field]:
                raise ContractError("CONSUMED_PERMIT_BINDING_MISMATCH", "$/" + field)

    def check_qualification_evidence(self, qualification_wire: bytes) -> None:
        """Check concrete evidence prerequisites, not the qualification verdict.

        No numerical quality threshold is selected here. Nonzero failures/skips
        remain visible and can satisfy this binding predicate; the real verifier
        must evaluate the exact frozen policy before acceptance.
        """
        record = self._codec.decode(qualification_wire)
        if record.record_type != "CapabilityQualification":
            raise ContractError("CAPABILITY_QUALIFICATION_REQUIRED")
        claim = record.as_dict()
        if claim["status"] != "QUALIFIED_WITHIN_SCOPE":
            raise ContractError("QUALIFICATION_CLAIM_REQUIRED")
        if claim["sample_count"] == 0:
            raise ContractError("QUALIFICATION_SAMPLES_REQUIRED")
        if claim["executable_commitment"] is None:
            raise ContractError("QUALIFICATION_EXECUTABLE_REQUIRED")
        references = claim["evidence_bundle_refs"]
        if not references or len(set(references)) != len(references):
            raise ContractError("QUALIFICATION_BUNDLES_REQUIRED")
        if self._resolve_qualification is None:
            raise ContractError("QUALIFICATION_EVIDENCE_UNAVAILABLE")
        evidence = self._resolve_qualification(record)
        if type(evidence) is not QualificationEvidence:
            raise ContractError("QUALIFICATION_EVIDENCE_REQUIRED")
        if evidence.qualification_commitment != record.commitment:
            raise ContractError("QUALIFICATION_BINDING_MISMATCH")
        for field in ("sample_count", "failure_count", "skip_count"):
            value = getattr(evidence, field)
            if type(value) is not int or value != claim[field]:
                raise ContractError("QUALIFICATION_COUNT_MISMATCH", "$/" + field)
        bundles = evidence.bundle_commitments
        if (type(bundles) is not tuple or not 1 <= len(bundles) <= 4096
                or any(type(pair) is not tuple or len(pair) != 2 for pair in bundles)):
            raise ContractError("QUALIFICATION_BUNDLE_BINDING_REQUIRED")
        for reference, commitment in bundles:
            if (type(reference) is not str or not _IDENTIFIER.fullmatch(reference)
                    or type(commitment) is not str or not _HASH.fullmatch(commitment)):
                raise ContractError("QUALIFICATION_BUNDLE_BINDING_REQUIRED")
        resolved_ids = [pair[0] for pair in bundles]
        if len(set(resolved_ids)) != len(resolved_ids) or set(resolved_ids) != set(references):
            raise ContractError("QUALIFICATION_BUNDLE_REFERENCE_MISMATCH")
        independent_refs = evidence.independence_evidence_refs
        if (type(independent_refs) is not tuple or not independent_refs
                or len(independent_refs) > 4096
                or any(type(ref) is not str for ref in independent_refs)
                or len(set(independent_refs)) != len(independent_refs)
                or not set(independent_refs) <= set(resolved_ids)):
            raise ContractError("QUALIFICATION_INDEPENDENCE_EVIDENCE_REQUIRED")

    def check_preparation_evidence(self, proposal_wire: bytes, expected: ReadSet) -> None:
        """Use dependencies from the captured owner resolver, not a worker tuple."""
        record = self._codec.decode(proposal_wire)
        if record.record_type != "ActionProposal":
            raise ContractError("ACTION_PROPOSAL_REQUIRED")
        if type(expected) is not ReadSet:
            raise ContractError("READ_SET_REQUIRED")
        if self._resolve_preparation is None:
            raise ContractError("PREPARATION_EVIDENCE_UNAVAILABLE")
        evidence = self._resolve_preparation(record)
        if type(evidence) is not PreparationEvidence:
            raise ContractError("PREPARATION_EVIDENCE_REQUIRED")
        if evidence.proposal_commitment != record.commitment:
            raise ContractError("PREPARATION_PROPOSAL_BINDING_MISMATCH")
        proposal = record.as_dict()
        if proposal["scope_id"] != expected.scope_id:
            raise ContractError("PREPARATION_PROPOSAL_SCOPE_MISMATCH")
        require_current_preparation(expected, evidence.current, evidence.required_resource_ids)
        revisions = {resource.resource_id: resource.revision for resource in expected.resources}
        seen = set()
        for resource in proposal["resources"]:
            if resource["resource_id"] in seen:
                raise ContractError("DUPLICATE_PROPOSAL_RESOURCE")
            seen.add(resource["resource_id"])
            if resource["scope_id"] != expected.scope_id:
                raise ContractError("PREPARATION_RESOURCE_SCOPE_MISMATCH")
            if (resource["resource_id"] not in revisions
                    or resource["revision"] != revisions[resource["resource_id"]]):
                raise ContractError("PREPARATION_RESOURCE_BINDING_MISMATCH")

    def require_runtime_admission(self) -> None:
        """Deny until actual authenticated/durable/qualification owners exist.

        There is deliberately no success branch or caller flag. This is an
        explicit unavailable boundary, not a simulated authentication provider.
        Implementing the real kernel/store/broker path requires a later source-
        bound change and integrated execution tests; these pure checks cannot
        be substituted for that path.
        """
        raise ContractError("RUNTIME_EVIDENCE_OWNERS_UNAVAILABLE")
