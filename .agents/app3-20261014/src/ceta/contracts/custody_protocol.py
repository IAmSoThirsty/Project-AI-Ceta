"""Canonical public protected-operation bindings, without release authority.

Uses the existing ProtectedOperationRequest wire record. Stable object identity
is separate from a fresh request and is never treated as confidential entropy or
a content-key derivation. Resolved material is public metadata/proof/ciphertext,
not a key, share or plaintext buffer. Comparison does not authenticate its owner,
verify its cryptographic proof, establish quorum or grant an operation.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib

from .store_transactions import MAX_GENERATION, identifier, commitment
from .temporal import ClockSample, Deadline, utc_nanoseconds, require_deadline_current
from .wire import ContractError, RecordCodec, PROFILE, canonical_bytes, strict_loads


CUSTODY_BINDING_PROFILE = "ceta-protected-operation-binding-v1"
MAX_CUSTODY_MATERIAL_BYTES = 16 * 1024 * 1024
MAX_CUSTODY_READ_SET_BYTES = 64 * 1024 * 1024
MAX_REPLAY_IDENTIFIERS = 4096
_OBJECT_FIELDS = ("scope_id", "object_id", "object_version", "ciphertext_commitment", "object_key_lineage_ref")
_REFERENCE_FIELDS = ("object_key_lineage_ref", "requester_proof_ref", "capability_ref", "purpose_proof_ref",
    "traversal_proof_ref", "interpretation_proof_ref", "worker_measurement_ref", "authority_manifest_ref",
    "quorum_policy_ref", "revocation_state_ref")
_ROOT_FIELDS = ("object_version", "ciphertext_commitment", "policy_root", "codex_root",
    "prior_audit_head", "session_binding")
MATERIAL_FIELDS = tuple(sorted(set(_REFERENCE_FIELDS) | set(_ROOT_FIELDS)))
_REQUEST_FIELDS = frozenset({"record_type", "schema_version", "record_id", "scope_id", "causation_ref",
    "object_id", "object_version", "ciphertext_commitment", "object_key_lineage_ref", "requester_proof_ref",
    "consumer_id", "operation", "capability_ref", "purpose_proof_ref", "policy_root", "codex_root",
    "traversal_proof_ref", "interpretation_proof_ref", "worker_measurement_ref", "authority_manifest_ref",
    "quorum_policy_ref", "epoch", "revocation_state_ref", "nonce", "issued_at", "expires_at",
    "prior_audit_head", "session_binding", "permitted_output_class"})
_TRANSCRIPT_DOMAIN = ("CETA:protected-operation-transcript:" + PROFILE + ":v1\0").encode("ascii")
_OBJECT_DOMAIN = ("CETA:protected-object-binding:" + PROFILE + ":v1\0").encode("ascii")
_MATERIAL_DOMAIN = ("CETA:protected-material-binding:" + PROFILE + ":v1\0").encode("ascii")
_CONTEXT_DOMAIN = ("CETA:protected-operation-context:" + PROFILE + ":v1\0").encode("ascii")
_CONTRIBUTION_DOMAIN = ("CETA:protected-contribution-binding:" + PROFILE + ":v1\0").encode("ascii")
REQUIRED_OWNER_VERIFICATIONS = (
    "AUTHENTIC_CURRENT_REQUESTER_AND_APPROVED_CONSUMER",
    "CURRENT_OBJECT_CIPHERTEXT_AND_KEY_LINEAGE",
    "CURRENT_CAPABILITY_AND_OPERATION_AUTHORIZATION",
    "AUTHENTIC_PURPOSE_TRAVERSAL_AND_INTERPRETATION_PROOFS",
    "CURRENT_POLICY_CODEX_AUTHORITY_MANIFEST_AND_REVOCATION",
    "GENUINE_INDEPENDENT_AUTHORITY_DOMAIN_QUORUM",
    "REVIEWED_THRESHOLD_ENVELOPE_AND_PROOF_VERIFICATION",
    "MEASURED_WORKER_CONTINUITY_AND_PERMITTED_OUTPUT_PATH",
    "AUTHENTIC_TIME_EPOCH_AND_DURABLE_ATOMIC_REPLAY_ADMISSION",
    "CURRENT_TRUSTED_AUDIT_CHECKPOINT",
    "QUALIFIED_NATIVE_SECRET_LIFETIME_AND_OUTCOME_CUSTODY",
)


def _require(condition, code):
    if condition is not True:
        raise ContractError(code)


def _copy(value, kind):
    _require(type(value) is kind, "CUSTODY_VALUE_TYPE_REQUIRED")
    try:
        return kind(**{field.name: object.__getattribute__(value, field.name)
            for field in fields(kind) if field.init})
    except (AttributeError, TypeError) as error:
        raise ContractError("CUSTODY_VALUE_FIELDS_INCOMPLETE") from error


def _hash(domain, wire):
    return "sha256:" + hashlib.sha256(domain + wire).hexdigest()


def _text(value):
    _require(type(value) is str and 1 <= len(value) <= 4096, "CUSTODY_TEXT_BOUND")
    canonical_bytes(value)


def _counter(value):
    _require(type(value) is int and 0 <= value <= MAX_GENERATION, "CUSTODY_COUNTER_INVALID")


def _ids(value):
    _require(type(value) is tuple and len(value) <= MAX_REPLAY_IDENTIFIERS, "CUSTODY_REPLAY_SET_BOUND")
    for item in value:
        identifier(item)
    _require(len(set(value)) == len(value), "CUSTODY_REPLAY_IDENTIFIER_DUPLICATE")
    return tuple(sorted(value))


def _codec(value):
    _require(type(value) is RecordCodec, "CUSTODY_CODEC_REQUIRED")
    try:
        return RecordCodec(strict_loads(canonical_bytes(object.__getattribute__(value, "_schema"))))
    except (AttributeError, TypeError, ContractError) as error:
        raise ContractError("CUSTODY_CODEC_INVALID") from error


@dataclass(frozen=True, slots=True)
class ProtectedObjectBinding:
    scope_id: str
    object_id: str
    object_version: str
    ciphertext_commitment: str
    object_key_lineage_ref: str

    def __post_init__(self):
        identifier(self.scope_id); identifier(self.object_id); identifier(self.object_key_lineage_ref)
        commitment(self.object_version); commitment(self.ciphertext_commitment)

    def as_dict(self):
        captured = _copy(self, ProtectedObjectBinding)
        return {name: getattr(captured, name) for name in _OBJECT_FIELDS}

    def canonical_wire(self):
        return canonical_bytes({"profile": CUSTODY_BINDING_PROFILE, "stable_object": self.as_dict()})

    def preimage(self):
        return _OBJECT_DOMAIN + self.canonical_wire()

    def commitment(self):
        return "sha256:" + hashlib.sha256(self.preimage()).hexdigest()


@dataclass(frozen=True, slots=True)
class ProtectedRequestBinding:
    object_binding: ProtectedObjectBinding
    record_id: str
    causation_ref: str | None
    requester_proof_ref: str
    consumer_id: str
    operation: str
    capability_ref: str
    purpose_proof_ref: str
    policy_root: str
    codex_root: str
    traversal_proof_ref: str
    interpretation_proof_ref: str
    worker_measurement_ref: str
    authority_manifest_ref: str
    quorum_policy_ref: str
    epoch: int
    revocation_state_ref: str
    nonce: str
    issued_at: str
    expires_at: str
    prior_audit_head: str
    session_binding: str
    permitted_output_class: str

    def __post_init__(self):
        object.__setattr__(self, "object_binding", _copy(self.object_binding, ProtectedObjectBinding))
        for name in ("record_id", "requester_proof_ref", "consumer_id", "capability_ref", "purpose_proof_ref",
            "traversal_proof_ref", "interpretation_proof_ref", "worker_measurement_ref", "authority_manifest_ref",
            "quorum_policy_ref", "revocation_state_ref", "nonce"):
            identifier(getattr(self, name))
        if self.causation_ref is not None:
            identifier(self.causation_ref)
        for name in ("policy_root", "codex_root", "prior_audit_head", "session_binding"):
            commitment(getattr(self, name))
        _counter(self.epoch); _text(self.operation); _text(self.permitted_output_class)
        _require(utc_nanoseconds(self.issued_at) < utc_nanoseconds(self.expires_at), "CUSTODY_REQUEST_INTERVAL_INVALID")

    def as_record(self):
        captured = _copy(self, ProtectedRequestBinding)
        value = {"record_type": "ProtectedOperationRequest", "schema_version": "1",
            **captured.object_binding.as_dict()}
        value.update({field.name: getattr(captured, field.name)
            for field in fields(ProtectedRequestBinding) if field.name != "object_binding"})
        return value

    def canonical_wire(self):
        return canonical_bytes(self.as_record())

    @classmethod
    def from_record(cls, document):
        _require(cls is ProtectedRequestBinding, "CUSTODY_REQUEST_BINDING_TYPE_REQUIRED")
        _require(type(document) is dict and set(document) == _REQUEST_FIELDS, "CUSTODY_REQUEST_FIELDS")
        _require(type(document["record_type"]) is str and type(document["schema_version"]) is str
            and document["record_type"] == "ProtectedOperationRequest" and document["schema_version"] == "1",
            "CUSTODY_REQUEST_VERSION_UNSUPPORTED")
        object_binding = ProtectedObjectBinding(**{name: document[name] for name in _OBJECT_FIELDS})
        return cls(object_binding, **{field.name: document[field.name]
            for field in fields(cls) if field.name != "object_binding"})


@dataclass(frozen=True, slots=True)
class CustodyMaterialExpectation:
    field_name: str
    scope_id: str
    binding: str
    raw_sha256: str
    byte_length: int

    def __post_init__(self):
        _require(type(self.field_name) is str and self.field_name in MATERIAL_FIELDS, "CUSTODY_MATERIAL_FIELD_UNKNOWN")
        identifier(self.scope_id)
        (commitment if self.field_name in _ROOT_FIELDS else identifier)(self.binding)
        commitment(self.raw_sha256)
        _require(type(self.byte_length) is int and 1 <= self.byte_length <= MAX_CUSTODY_MATERIAL_BYTES,
            "CUSTODY_MATERIAL_BYTE_BOUND")

    def as_dict(self):
        captured = _copy(self, CustodyMaterialExpectation)
        return {field.name: getattr(captured, field.name) for field in fields(captured)}


@dataclass(frozen=True, slots=True)
class ResolvedCustodyMaterial:
    """Exact public proof/metadata/ciphertext bytes, without reference authority."""
    field_name: str
    scope_id: str
    binding: str
    raw_bytes: bytes

    def __post_init__(self):
        _require(type(self.raw_bytes) is bytes, "CUSTODY_MATERIAL_BYTES_REQUIRED")
        # Shape is shared with expectations, while digest is derived locally.
        self.expectation()

    def expectation(self):
        return CustodyMaterialExpectation(self.field_name, self.scope_id, self.binding,
            "sha256:" + hashlib.sha256(self.raw_bytes).hexdigest(), len(self.raw_bytes))


def _expectations(values, request):
    _require(type(values) is tuple and len(values) == len(MATERIAL_FIELDS), "CUSTODY_MATERIAL_SET_INCOMPLETE")
    copied = tuple(_copy(item, CustodyMaterialExpectation) for item in values)
    _require(len({item.field_name for item in copied}) == len(copied)
        and {item.field_name for item in copied} == set(MATERIAL_FIELDS), "CUSTODY_MATERIAL_FIELD_DUPLICATE_OR_MISSING")
    record = request.as_record()
    for item in copied:
        _require(item.scope_id == record["scope_id"] and item.binding == record[item.field_name],
            "CUSTODY_MATERIAL_REQUEST_BINDING_MISMATCH")
    _require(sum(item.byte_length for item in copied) <= MAX_CUSTODY_READ_SET_BYTES, "CUSTODY_READ_SET_BYTE_BOUND")
    return tuple(sorted(copied, key=lambda item: item.field_name))


@dataclass(frozen=True, slots=True)
class ProtectedOperationContext:
    """Complete expected owner input; its construction is not authentication.

    Authority epoch is compared in the request binding. It is deliberately not
    equated to the independently owned temporal durable epoch. Replay facts must
    come from the genuine current owner and be atomically consumed there.
    """
    expected_request: ProtectedRequestBinding
    material_expectations: tuple[CustodyMaterialExpectation, ...]
    previous_clock: ClockSample
    current_clock: ClockSample
    deadline: Deadline
    used_nonces: tuple[str, ...]
    used_request_ids: tuple[str, ...]

    def __post_init__(self):
        request = _copy(self.expected_request, ProtectedRequestBinding)
        object.__setattr__(self, "expected_request", request)
        object.__setattr__(self, "material_expectations", _expectations(self.material_expectations, request))
        for name, kind in (("previous_clock", ClockSample), ("current_clock", ClockSample), ("deadline", Deadline)):
            object.__setattr__(self, name, _copy(getattr(self, name), kind))
        object.__setattr__(self, "used_nonces", _ids(self.used_nonces))
        object.__setattr__(self, "used_request_ids", _ids(self.used_request_ids))

    def material_binding_wire(self):
        captured = _copy(self, ProtectedOperationContext)
        return canonical_bytes({"profile": CUSTODY_BINDING_PROFILE,
            "request": captured.expected_request.as_record(),
            "material_expectations": [item.as_dict() for item in captured.material_expectations]})

    def material_binding_commitment(self):
        # Clock observations can advance independently at each authority. The
        # exact request/expiry/epoch and immutable material remain one binding.
        return _hash(_MATERIAL_DOMAIN, self.material_binding_wire())

    def canonical_wire(self):
        captured = _copy(self, ProtectedOperationContext)
        return canonical_bytes({"profile": CUSTODY_BINDING_PROFILE,
            "request": captured.expected_request.as_record(),
            "material_expectations": [item.as_dict() for item in captured.material_expectations],
            "previous_clock": {field.name: getattr(captured.previous_clock, field.name) for field in fields(ClockSample)},
            "current_clock": {field.name: getattr(captured.current_clock, field.name) for field in fields(ClockSample)},
            "deadline": {field.name: getattr(captured.deadline, field.name) for field in fields(Deadline)},
            "used_nonces": list(captured.used_nonces), "used_request_ids": list(captured.used_request_ids)})

    def commitment(self):
        return _hash(_CONTEXT_DOMAIN, self.canonical_wire())


@dataclass(frozen=True, slots=True)
class ProtectedBindingVerification:
    """Successful data comparisons and outstanding actual-owner obligations."""
    transcript_commitment: str
    stable_object_commitment: str
    material_binding_commitment: str
    context_commitment: str
    required_verifications: tuple[str, ...] = REQUIRED_OWNER_VERIFICATIONS

    def __post_init__(self):
        for name in ("transcript_commitment", "stable_object_commitment", "material_binding_commitment", "context_commitment"):
            commitment(getattr(self, name))
        _require(type(self.required_verifications) is tuple
            and self.required_verifications == REQUIRED_OWNER_VERIFICATIONS, "CUSTODY_OWNER_OBLIGATIONS_MISSING")


@dataclass(frozen=True, slots=True)
class ProtectedContributionBinding:
    """Request/recipient/object/worker/epoch binding data, without secret shares."""
    transcript_commitment: str
    stable_object_commitment: str
    material_binding_commitment: str
    consumer_id: str
    worker_measurement_ref: str
    authority_manifest_ref: str
    quorum_policy_ref: str
    epoch: int
    nonce: str
    session_binding: str

    def __post_init__(self):
        for name in ("transcript_commitment", "stable_object_commitment", "material_binding_commitment", "session_binding"):
            commitment(getattr(self, name))
        for name in ("consumer_id", "worker_measurement_ref", "authority_manifest_ref", "quorum_policy_ref", "nonce"):
            identifier(getattr(self, name))
        _counter(self.epoch)

    def canonical_wire(self):
        captured = _copy(self, ProtectedContributionBinding)
        return canonical_bytes({"profile": CUSTODY_BINDING_PROFILE,
            "contribution_binding": {field.name: getattr(captured, field.name) for field in fields(captured)}})

    def preimage(self):
        return _CONTRIBUTION_DOMAIN + self.canonical_wire()

    def commitment(self):
        return "sha256:" + hashlib.sha256(self.preimage()).hexdigest()


@dataclass(frozen=True, slots=True)
class ProtectedExecutionBinding:
    """Explicit correlation supplied by the genuine dispatch owner, not inferred.

    capability_ref has no selected OperationPermit interpretation in schema v1.
    The actual owner supplies that mapping and the corresponding input/event.
    """
    transcript_commitment: str
    scope_id: str
    task_id: str
    operation_id: str
    permit_id: str
    executor_session: str
    input_commitment: str
    dispatch_event_ref: str
    receipt_id: str

    def __post_init__(self):
        commitment(self.transcript_commitment); commitment(self.input_commitment)
        for name in ("scope_id", "task_id", "operation_id", "permit_id", "executor_session", "dispatch_event_ref", "receipt_id"):
            identifier(getattr(self, name))


def _request_parts(wire):
    document = strict_loads(wire)
    binding = ProtectedRequestBinding.from_record(document)
    canonical = binding.canonical_wire()
    domain = ("CETA:record:" + PROFILE + ":ProtectedOperationRequest\0").encode("ascii")
    return binding, canonical, "sha256:" + hashlib.sha256(wire).hexdigest(), _hash(domain, canonical)


@dataclass(frozen=True, slots=True, init=False)
class CanonicalProtectedTranscript:
    binding: ProtectedRequestBinding
    original_wire: bytes
    canonical_wire: bytes
    original_sha256: str
    record_commitment: str

    def __init__(self, codec, request_wire):
        decoded = _codec(codec).decode(request_wire)
        _require(decoded.record_type == "ProtectedOperationRequest", "CUSTODY_PROTECTED_REQUEST_REQUIRED")
        binding, canonical, raw_hash, record_hash = _request_parts(request_wire)
        _require(decoded.canonical_wire == canonical and decoded.commitment == record_hash,
            "CUSTODY_RECORD_CODEC_BINDING_MISMATCH")
        for name, value in (("binding", binding), ("original_wire", request_wire), ("canonical_wire", canonical),
            ("original_sha256", raw_hash), ("record_commitment", record_hash)):
            object.__setattr__(self, name, value)

    @classmethod
    def from_wire(cls, codec, request_wire):
        return cls(codec, request_wire)

    @classmethod
    def from_binding(cls, codec, binding):
        return cls(codec, _copy(binding, ProtectedRequestBinding).canonical_wire())

    def _checked(self):
        _require(type(self) is CanonicalProtectedTranscript, "CUSTODY_TRANSCRIPT_TYPE_REQUIRED")
        try:
            binding, canonical, raw_hash, record_hash = _request_parts(self.original_wire)
            captured = _copy(self.binding, ProtectedRequestBinding)
            _require(captured == binding and type(self.canonical_wire) is bytes and self.canonical_wire == canonical
                and type(self.original_sha256) is str and self.original_sha256 == raw_hash
                and type(self.record_commitment) is str and self.record_commitment == record_hash,
                "CUSTODY_TRANSCRIPT_CHANGED")
            return binding
        except AttributeError as error:
            raise ContractError("CUSTODY_TRANSCRIPT_FIELDS_INCOMPLETE") from error

    def preimage(self):
        binding = self._checked()
        return _TRANSCRIPT_DOMAIN + binding.canonical_wire()

    def commitment(self):
        return "sha256:" + hashlib.sha256(self.preimage()).hexdigest()

    def to_wire(self, *, preserve_original=True):
        self._checked()
        _require(type(preserve_original) is bool, "CUSTODY_WIRE_SELECTION_INVALID")
        return self.original_wire if preserve_original else self.canonical_wire

    def require_same_object(self, previous):
        _require(type(previous) is CanonicalProtectedTranscript, "CUSTODY_TRANSCRIPT_TYPE_REQUIRED")
        current, old = self._checked(), previous._checked()
        _require(current.object_binding == old.object_binding, "CUSTODY_STABLE_OBJECT_CHANGED")
        return _copy(current.object_binding, ProtectedObjectBinding)

    def require_distinct_request(self, previous):
        self.require_same_object(previous)
        current, old = self._checked(), previous._checked()
        _require(current.record_id != old.record_id and current.nonce != old.nonce,
            "CUSTODY_FRESH_REQUEST_ID_OR_NONCE_REUSED")

    def verify_bindings(self, context, materials):
        """Require complete exact current supplied data, without an allow result."""
        binding = self._checked()
        expected = _copy(context, ProtectedOperationContext)
        _require(binding == expected.expected_request, "CUSTODY_CALLER_CONTEXT_REQUEST_MISMATCH")
        _require(type(materials) is tuple and len(materials) == len(MATERIAL_FIELDS), "CUSTODY_MATERIAL_SET_INCOMPLETE")
        copied = tuple(_copy(item, ResolvedCustodyMaterial) for item in materials)
        _require({item.field_name for item in copied} == set(MATERIAL_FIELDS)
            and len({item.field_name for item in copied}) == len(copied), "CUSTODY_MATERIAL_FIELD_DUPLICATE_OR_MISSING")
        actual = tuple(sorted((item.expectation() for item in copied), key=lambda item: item.field_name))
        _require(actual == expected.material_expectations, "CUSTODY_RESOLVED_MATERIAL_CHANGED_OR_SUBSTITUTED")
        _require(sum(len(item.raw_bytes) for item in copied) <= MAX_CUSTODY_READ_SET_BYTES, "CUSTODY_READ_SET_BYTE_BOUND")
        _require(binding.nonce not in expected.used_nonces and binding.record_id not in expected.used_request_ids,
            "CUSTODY_REPLAY_OBSERVED")
        require_deadline_current(expected.deadline, expected.previous_clock, expected.current_clock)
        issued, expires = utc_nanoseconds(binding.issued_at), utc_nanoseconds(binding.expires_at)
        _require(expected.current_clock.earliest_wall_ns >= issued
            and expected.current_clock.latest_wall_ns < expires, "CUSTODY_REQUEST_NOT_CURRENT_OR_UNCERTAIN")
        _require(expected.deadline.expires_wall_ns <= expires, "CUSTODY_DEADLINE_EXCEEDS_REQUEST_EXPIRY")
        return ProtectedBindingVerification(self.commitment(), binding.object_binding.commitment(),
            expected.material_binding_commitment(), expected.commitment())

    def contribution_binding(self, context, materials):
        verified = self.verify_bindings(context, materials)
        binding = self._checked()
        return ProtectedContributionBinding(verified.transcript_commitment, verified.stable_object_commitment,
            verified.material_binding_commitment, binding.consumer_id, binding.worker_measurement_ref,
            binding.authority_manifest_ref, binding.quorum_policy_ref, binding.epoch, binding.nonce, binding.session_binding)

    def require_contribution_binding(self, contribution, context, materials):
        actual = _copy(contribution, ProtectedContributionBinding)
        _require(actual == self.contribution_binding(context, materials), "CUSTODY_CONTRIBUTION_MIXED_OR_SUBSTITUTED")
        return actual

    def require_execution_receipt(self, codec, receipt_wire, execution_binding):
        """Correlate the existing receipt while preserving failure/uncertainty.

        Exit codes, effect labels and a receipt match do not authorize release or
        certify an observed effect. No result state is promoted by this method.
        """
        request = self._checked()
        expected = _copy(execution_binding, ProtectedExecutionBinding)
        _require(expected.transcript_commitment == self.commitment()
            and expected.scope_id == request.object_binding.scope_id, "CUSTODY_EXECUTION_TRANSCRIPT_MISMATCH")
        receipt = _codec(codec).decode(receipt_wire)
        _require(receipt.record_type == "ExecutionReceipt", "CUSTODY_EXECUTION_RECEIPT_REQUIRED")
        value = receipt.as_dict()
        for record_field, expected_field in (("scope_id", "scope_id"), ("record_id", "receipt_id"),
            ("task_id", "task_id"), ("operation_id", "operation_id"), ("permit_ref", "permit_id"),
            ("executor_session", "executor_session"), ("input_commitment", "input_commitment"),
            ("dispatch_event_ref", "dispatch_event_ref")):
            _require(value[record_field] == getattr(expected, expected_field), "CUSTODY_EXECUTION_RECEIPT_BINDING_MISMATCH")
        # Return the ordinary immutable parsed receipt, including every original
        # failure/effect/cancellation field; no synthetic custody wire record.
        return receipt


__all__ = ["CUSTODY_BINDING_PROFILE", "MATERIAL_FIELDS", "REQUIRED_OWNER_VERIFICATIONS",
    "ProtectedObjectBinding", "ProtectedRequestBinding", "CustodyMaterialExpectation", "ResolvedCustodyMaterial",
    "ProtectedOperationContext", "ProtectedBindingVerification", "ProtectedContributionBinding",
    "ProtectedExecutionBinding", "CanonicalProtectedTranscript"]
