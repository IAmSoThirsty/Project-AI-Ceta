"""Immutable internal request-preview values, never operation/effect authority.

ContextEnvelope v1 remains one of the same twenty admitted records. The
PreparedRequest below is an owner-internal binding, not a twenty-first record,
a semantic-fidelity verdict, an accepted task, a grant or a permit. Its raw
content lives in bytes; canonical metadata uses hex so NFC/CRLF/NUL are not
silently rewritten. Trusted owners must be injected by composition.
"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
import hashlib

from .read_sets import ReadSet
from .store_transactions import StoreCell, commitment, identifier
from .task_drafts import decode_snapshot, draft_key
from .temporal import ClockSample, Deadline, utc_nanoseconds
from .wire import ContractError, MAX_WIRE_BYTES, ParsedRecord, canonical_bytes

REQUEST_PROFILE = "ceta-request-preview-v1"
PROFILES = frozenset(("conversation", "investigation", "coding", "monitoring",
                     "maintenance", "planning", "review", "probe", "modality"))
PARTITIONS = frozenset(("BINDING_INSTRUCTION", "QUOTATION", "HISTORY",
                        "UNTRUSTED_DATA", "VERIFIED_RECORD", "MODEL_PROPOSAL"))
FIELD_NAMES = frozenset(("objective", "secondary_objectives", "context", "constraints",
                        "exclusions", "prohibited_actions", "assumptions", "uncertainty",
                        "required_inputs", "missing_inputs", "audience", "output_format",
                        "tone", "tools", "privacy", "success_criteria"))
FIELD_STATUSES = frozenset(("USER_STATED", "RECORD_OBSERVED", "INFERRED",
                           "ASSUMED", "UNRESOLVED"))
DRIFT_STATUSES = frozenset(("UNASSESSED", "DRIFT_UNRESOLVED",
                           "DRIFT_VERIFIED", "NO_DRIFT_VERIFIED"))
MATERIAL_REASONS = frozenset(("CORRECTNESS", "SCOPE", "PRIVACY", "OBJECTIVE",
                             "RESULT", "AUTHORITY", "TARGET", "MANDATORY_OMISSION"))
MAX_ITEMS = 256
MAX_SOURCE_BYTES = 8 * 1024 * 1024
MAX_RENDERED_BYTES = 8 * 1024 * 1024
MAX_FIELD_BYTES = 65536
MAX_QUESTION_BYTES = 2040
MAX_TOKENS = 1024 * 1024
MAX_COUNTER = 2**53 - 1
MAX_MODEL_PARTS = MAX_ITEMS * 2 + 2 + len(FIELD_NAMES)
RAW_SOURCE_IDS = ("user.original", "user.latest")


def need(condition, code):
    if not condition:
        raise ContractError(code)


def integer(value, minimum=0, maximum=MAX_COUNTER):
    need(type(value) is int and minimum <= value <= maximum, "COMPILER_INTEGER")
    return value


def raw_bytes(value, maximum=MAX_SOURCE_BYTES):
    need(type(value) is bytes and len(value) <= maximum, "COMPILER_BYTES")
    return value


def identifiers(value, maximum=4096):
    need(type(value) is tuple and len(value) <= maximum, "COMPILER_IDENTIFIERS")
    for item in value:
        identifier(item)
    need(len(set(value)) == len(value), "COMPILER_DUPLICATE_IDENTIFIER")


def typed_tuple(value, kind, maximum=MAX_ITEMS):
    need(type(value) is tuple and len(value) <= maximum
         and all(type(item) is kind for item in value), "COMPILER_IMMUTABLE_ITEMS")


def byte_commitment(value):
    raw_bytes(value)
    return "sha256:" + hashlib.sha256(b"CETA:request-bytes:v1\0" + value).hexdigest()


def token_commitment(token_ids):
    need(type(token_ids) is tuple and len(token_ids) <= MAX_TOKENS, "COMPILER_TOKENS")
    for token in token_ids:
        integer(token, 0, 2**31 - 1)
    preimage = len(token_ids).to_bytes(8, "big")
    preimage += b"".join(token.to_bytes(8, "big") for token in token_ids)
    return "sha256:" + hashlib.sha256(b"CETA:request-tokens:v1\0" + preimage).hexdigest()


def metadata(value):
    """Convert only immutable internal metadata to the existing canonical profile."""
    if type(value) is bytes:
        return {"utf8_or_binary_hex": value.hex()}
    if type(value) is tuple:
        return [metadata(item) for item in value]
    if is_dataclass(value):
        return {field.name: metadata(getattr(value, field.name)) for field in fields(value)}
    return value


def metadata_commitment(value, domain=b"CETA:request-basis:v1\0"):
    return "sha256:" + hashlib.sha256(domain + canonical_bytes(metadata(value))).hexdigest()


@dataclass(frozen=True)
class TaskInput:
    snapshot_wire: bytes
    scope_id: str
    task_id: str
    principal_id: str
    owner_binding: str
    task_revision: str
    objective_revision: str
    objective_generation: int
    title: bytes
    original: bytes
    latest: bytes

    @classmethod
    def from_snapshot(cls, snapshot_wire):
        need(type(snapshot_wire) is bytes and len(snapshot_wire) <= MAX_WIRE_BYTES,
             "COMPILER_TASK_SNAPSHOT")
        value = decode_snapshot(snapshot_wire)
        revision = StoreCell(draft_key(value["scope_id"], value["task_id"]),
                             value["objective_generation"], snapshot_wire).revision
        return cls(snapshot_wire, value["scope_id"], value["task_id"], value["principal_id"],
                   value["owner_binding"], revision, value["objective_revision"],
                   value["objective_generation"], bytes.fromhex(value["title_hex"]),
                   bytes.fromhex(value["instruction_hex"]), bytes.fromhex(value["draft_hex"]))

    def __post_init__(self):
        raw_bytes(self.snapshot_wire, MAX_WIRE_BYTES)
        for item in (self.scope_id, self.task_id, self.principal_id):
            identifier(item)
        for item in (self.owner_binding, self.task_revision, self.objective_revision):
            commitment(item)
        integer(self.objective_generation, 1)
        raw_bytes(self.title, 256)
        raw_bytes(self.original, 65536)
        raw_bytes(self.latest, 65536)


@dataclass(frozen=True)
class SourceVersion:
    source_id: str
    revision: str
    selection_commitment: str

    def __post_init__(self):
        identifier(self.source_id)
        commitment(self.revision)
        commitment(self.selection_commitment)


@dataclass(frozen=True)
class SourceItem:
    """Owner-selected content and role. Text cannot promote its own partition."""
    source_id: str
    revision: str
    partition: str
    content: bytes
    mandatory: bool
    coding_only: bool = False
    audit_only: bool = False
    omission_changes_task: bool = False

    def __post_init__(self):
        identifier(self.source_id)
        need(self.source_id not in RAW_SOURCE_IDS, "COMPILER_RESERVED_SOURCE_ID")
        commitment(self.revision)
        need(type(self.partition) is str and self.partition in PARTITIONS,
             "COMPILER_PARTITION")
        raw_bytes(self.content)
        for flag in (self.mandatory, self.coding_only, self.audit_only,
                     self.omission_changes_task):
            need(type(flag) is bool, "COMPILER_SOURCE_FLAG")

    @property
    def version(self):
        body = (self.source_id, self.revision, self.partition,
                byte_commitment(self.content), self.mandatory, self.coding_only,
                self.audit_only, self.omission_changes_task)
        return SourceVersion(self.source_id, self.revision, metadata_commitment(body))


@dataclass(frozen=True)
class QuoteRequest:
    source_id: str
    revision: str
    start: int
    end: int
    mandatory: bool = True

    def __post_init__(self):
        identifier(self.source_id)
        commitment(self.revision)
        integer(self.start)
        integer(self.end, self.start + 1)
        need(type(self.mandatory) is bool, "COMPILER_QUOTE_FLAG")


@dataclass(frozen=True)
class ExactQuotation:
    request: QuoteRequest
    content: bytes

    def __post_init__(self):
        need(type(self.request) is QuoteRequest, "COMPILER_QUOTE_REQUEST")
        raw_bytes(self.content)
        need(len(self.content) == self.request.end - self.request.start,
             "COMPILER_QUOTE_LENGTH")


@dataclass(frozen=True)
class UnresolvedQuotation:
    request: QuoteRequest
    reason_code: str


def resolve_quotation(sources, request):
    """Return an actual selected-source byte slice, or an explicit unresolved value."""
    typed_tuple(sources, SourceItem)
    need(type(request) is QuoteRequest, "COMPILER_QUOTE_REQUEST")
    matches = [source for source in sources if source.source_id == request.source_id]
    if len(matches) != 1:
        return UnresolvedQuotation(request, "QUOTE_SOURCE_UNAVAILABLE")
    source = matches[0]
    if source.revision != request.revision:
        return UnresolvedQuotation(request, "QUOTE_SOURCE_REVISION_UNAVAILABLE")
    if request.end > len(source.content):
        return UnresolvedQuotation(request, "QUOTE_SOURCE_RANGE_UNAVAILABLE")
    return ExactQuotation(request, source.content[request.start:request.end])


@dataclass(frozen=True)
class MeaningField:
    name: str
    value: bytes | None
    status: str
    source_ids: tuple[str, ...]
    mandatory: bool = True

    def __post_init__(self):
        need(type(self.name) is str and self.name in FIELD_NAMES, "COMPILER_MEANING_FIELD")
        need(type(self.status) is str and self.status in FIELD_STATUSES,
             "COMPILER_MEANING_STATUS")
        if self.value is None:
            need(self.status == "UNRESOLVED", "COMPILER_UNAVAILABLE_MEANING")
        else:
            raw_bytes(self.value, MAX_FIELD_BYTES)
        identifiers(self.source_ids, MAX_ITEMS)
        need(type(self.mandatory) is bool, "COMPILER_MEANING_FLAG")
        if self.status in {"USER_STATED", "RECORD_OBSERVED"}:
            need(bool(self.source_ids), "COMPILER_MEANING_SOURCE_REQUIRED")


@dataclass(frozen=True)
class ClarificationQuestion:
    text: bytes
    reason: str
    material: bool
    dependent_task_id: str
    source_ids: tuple[str, ...]

    def __post_init__(self):
        raw_bytes(self.text, MAX_QUESTION_BYTES)
        need(bool(self.text), "COMPILER_QUESTION_EMPTY")
        need(type(self.material) is bool and type(self.reason) is str,
             "COMPILER_QUESTION_FLAG")
        need(self.reason in MATERIAL_REASONS | {"OPEN"}, "COMPILER_QUESTION_REASON")
        need(not self.material or self.reason != "OPEN", "COMPILER_MATERIAL_REASON")
        identifier(self.dependent_task_id)
        identifiers(self.source_ids, MAX_ITEMS)
        need(not self.material or bool(self.source_ids), "COMPILER_QUESTION_EVIDENCE")


@dataclass(frozen=True)
class Interpretation:
    """Inspectable proposed meaning; source labels are not a semantic proof."""
    basis_commitment: str
    fields: tuple[MeaningField, ...]
    questions: tuple[ClarificationQuestion, ...] = ()

    def __post_init__(self):
        commitment(self.basis_commitment)
        typed_tuple(self.fields, MeaningField, len(FIELD_NAMES))
        typed_tuple(self.questions, ClarificationQuestion)
        need(len({field.name for field in self.fields}) == len(self.fields),
             "COMPILER_DUPLICATE_MEANING_FIELD")
        need(any(field.name == "objective" for field in self.fields),
             "COMPILER_OBJECTIVE_REPRESENTATION_REQUIRED")


@dataclass(frozen=True)
class RuntimeBinding:
    model_configuration_id: str
    model_commitment: str
    runtime_commitment: str
    worker_id: str
    worker_generation: int
    configuration_commitment: str
    template_commitment: str
    tokenizer_commitment: str
    context_tokens: int
    maximum_output_tokens: int

    def __post_init__(self):
        identifier(self.model_configuration_id)
        identifier(self.worker_id)
        integer(self.worker_generation, 1)
        for pin in (self.model_commitment, self.runtime_commitment,
                    self.configuration_commitment, self.template_commitment,
                    self.tokenizer_commitment):
            commitment(pin)
        integer(self.context_tokens, 1, MAX_TOKENS)
        integer(self.maximum_output_tokens, 1, self.context_tokens)


@dataclass(frozen=True)
class PreparationState:
    """Relevant trusted-owner state. Deliberately contains no global journal position."""
    request_id: str
    profile: str
    scope_id: str
    task_id: str
    principal_id: str
    owner_binding: str
    session_id: str
    companion_id: str
    task_revision: str
    objective_revision: str
    objective_generation: int
    runtime: RuntimeBinding
    read_set: ReadSet
    required_resource_ids: tuple[str, ...]
    source_versions: tuple[SourceVersion, ...]
    policy_refs: tuple[str, ...]
    authority_refs: tuple[str, ...]
    observation_refs: tuple[str, ...]
    memory_refs: tuple[str, ...]
    contradiction_refs: tuple[str, ...]
    reservation_id: str
    reservation_revision: str
    reserved_output_tokens: int
    deadline: Deadline
    expires_at: str

    def __post_init__(self):
        for item in (self.request_id, self.scope_id, self.task_id, self.principal_id,
                     self.session_id, self.companion_id, self.reservation_id):
            identifier(item)
        need(type(self.profile) is str and self.profile in PROFILES, "COMPILER_PROFILE")
        for pin in (self.owner_binding, self.task_revision, self.objective_revision,
                    self.reservation_revision):
            commitment(pin)
        integer(self.objective_generation, 1)
        need(type(self.runtime) is RuntimeBinding and type(self.read_set) is ReadSet
             and type(self.deadline) is Deadline, "COMPILER_OWNER_STATE_TYPES")
        identifiers(self.required_resource_ids)
        need(bool(self.required_resource_ids), "COMPILER_DEPENDENCIES_EMPTY")
        need(self.read_set.scope_id == self.scope_id, "COMPILER_READ_SET_SCOPE")
        typed_tuple(self.source_versions, SourceVersion)
        need(len({item.source_id for item in self.source_versions}) == len(self.source_versions),
             "COMPILER_DUPLICATE_SOURCE")
        for items in (self.policy_refs, self.authority_refs, self.observation_refs,
                      self.memory_refs, self.contradiction_refs):
            identifiers(items)
        integer(self.reserved_output_tokens, 1, self.runtime.maximum_output_tokens)
        need(utc_nanoseconds(self.expires_at) == self.deadline.expires_wall_ns,
             "COMPILER_DEADLINE_WIRE_BINDING")


@dataclass(frozen=True)
class SelectedContext:
    state: PreparationState
    sources: tuple[SourceItem, ...] = ()
    quotes: tuple[QuoteRequest, ...] = ()
    omissions: tuple[Omission, ...] = ()
    drift_status: str = "DRIFT_UNRESOLVED"
    drift_evidence_ids: tuple[str, ...] = ()

    def __post_init__(self):
        need(type(self.state) is PreparationState, "COMPILER_STATE_REQUIRED")
        typed_tuple(self.sources, SourceItem)
        typed_tuple(self.quotes, QuoteRequest)
        need(len({item.source_id for item in self.sources}) == len(self.sources),
             "COMPILER_DUPLICATE_SOURCE")
        need(sum(len(item.content) for item in self.sources) <= MAX_SOURCE_BYTES,
             "COMPILER_TOTAL_SOURCE_BYTES")
        expected = tuple(item.version for item in self.sources)
        need(self.state.source_versions == expected, "COMPILER_SOURCE_VERSION_BINDING")
        typed_tuple(self.omissions, Omission)
        need(type(self.drift_status) is str and self.drift_status in DRIFT_STATUSES,
             "COMPILER_DRIFT_STATUS")
        identifiers(self.drift_evidence_ids, MAX_ITEMS)
        verified = {source.source_id for source in self.sources
                    if source.partition == "VERIFIED_RECORD"}
        need(set(self.drift_evidence_ids) <= verified, "COMPILER_DRIFT_RECORD_REQUIRED")
        if self.drift_status in {"DRIFT_VERIFIED", "NO_DRIFT_VERIFIED"}:
            need(bool(self.drift_evidence_ids), "COMPILER_DRIFT_RECORD_REQUIRED")

    def basis_commitment(self, task):
        return metadata_commitment((byte_commitment(task.snapshot_wire), self.state,
                                    self.quotes, self.omissions,
                                    self.drift_status, self.drift_evidence_ids))


@dataclass(frozen=True)
class ModelPart:
    """Only these public role/status labels and exact bytes reach rendering.

    No source ID, audit ID, read-set, authority/reservation, session, principal
    or internal request ID is implicitly projected into model-facing content.
    """
    partition: str
    content: bytes
    status: str

    def __post_init__(self):
        need(type(self.partition) is str
             and self.partition in PARTITIONS | {"ORIGINAL_INPUT", "LATEST_INPUT"},
             "COMPILER_MODEL_PARTITION")
        raw_bytes(self.content)
        need(type(self.status) is str
             and self.status in FIELD_STATUSES | {"RAW_USER_INPUT", "SOURCE_SELECTED"},
             "COMPILER_MODEL_STATUS")


@dataclass(frozen=True)
class Tokenization:
    """Injected tokenizer's claim about the exact rendered stream, including specials."""
    runtime: RuntimeBinding
    payload_commitment: str
    token_ids: tuple[int, ...]
    exact: bool
    includes_special_tokens: bool

    def __post_init__(self):
        need(type(self.runtime) is RuntimeBinding, "COMPILER_TOKENIZER_BINDING")
        commitment(self.payload_commitment)
        token_commitment(self.token_ids)
        need(type(self.exact) is bool and type(self.includes_special_tokens) is bool,
             "COMPILER_TOKENIZER_FLAGS")


@dataclass(frozen=True)
class Omission:
    source_id: str
    revision: str | None
    reason_code: str
    material: bool = False

    def __post_init__(self):
        identifier(self.source_id)
        if self.revision is not None:
            commitment(self.revision)
        identifier(self.reason_code)
        need(type(self.material) is bool, "COMPILER_OMISSION_FLAG")


@dataclass(frozen=True)
class PreparedRequest:
    task: TaskInput
    selection: SelectedContext
    interpretation: Interpretation
    context: ParsedRecord
    parts: tuple[ModelPart, ...]
    payload: bytes
    tokenization: Tokenization
    omissions: tuple[Omission, ...]
    prepared_clock: ClockSample
    binding_wire: bytes

    def __post_init__(self):
        need(type(self.task) is TaskInput and type(self.selection) is SelectedContext
             and type(self.interpretation) is Interpretation
             and type(self.context) is ParsedRecord
             and self.context.record_type == "ContextEnvelope"
             and type(self.prepared_clock) is ClockSample,
             "COMPILER_PREVIEW_TYPES")
        typed_tuple(self.parts, ModelPart, MAX_MODEL_PARTS)
        raw_bytes(self.payload, MAX_RENDERED_BYTES)
        need(type(self.tokenization) is Tokenization
             and self.tokenization.payload_commitment == byte_commitment(self.payload),
             "COMPILER_PREVIEW_PAYLOAD")
        typed_tuple(self.omissions, Omission, MAX_ITEMS * 3 + len(FIELD_NAMES))
        raw_bytes(self.binding_wire, MAX_WIRE_BYTES)

    @property
    def commitment(self):
        return "sha256:" + hashlib.sha256(
            b"CETA:prepared-request-preview:v1\0" + self.binding_wire).hexdigest()


@dataclass(frozen=True)
class CompilationResult:
    kind: str
    task: TaskInput
    selection: SelectedContext | None = None
    interpretation: Interpretation | None = None
    prepared: PreparedRequest | None = None
    sources: tuple[SourceItem, ...] = ()
    rendered_payload: bytes | None = None
    input_tokens: int | None = None
    omissions: tuple[Omission, ...] = ()
    question: bytes | None = None
    reason_code: str | None = None

    def __post_init__(self):
        need(type(self.kind) is str
             and self.kind in {"PREVIEW", "CLARIFICATION", "OVERFLOW", "DENIED"},
             "COMPILER_RESULT_KIND")
        need(type(self.task) is TaskInput, "COMPILER_RESULT_ORIGINAL_REQUIRED")
        need(self.interpretation is None or type(self.interpretation) is Interpretation,
             "COMPILER_RESULT_INTERPRETATION")
        typed_tuple(self.sources, SourceItem)
        typed_tuple(self.omissions, Omission, MAX_ITEMS * 3 + len(FIELD_NAMES))
        need(self.selection is None or type(self.selection) is SelectedContext,
             "COMPILER_RESULT_SELECTION")
        if self.rendered_payload is not None:
            raw_bytes(self.rendered_payload, MAX_RENDERED_BYTES)
        if self.input_tokens is not None:
            integer(self.input_tokens, 0, MAX_TOKENS)
        if self.question is not None:
            raw_bytes(self.question, MAX_QUESTION_BYTES)
        if self.reason_code is not None:
            identifier(self.reason_code)
        if self.kind == "PREVIEW":
            need(type(self.prepared) is PreparedRequest
                 and self.prepared.task == self.task
                 and self.rendered_payload == self.prepared.payload,
                 "COMPILER_RESULT_PREVIEW")
            need(self.selection == self.prepared.selection
                 and self.interpretation == self.prepared.interpretation
                 and self.sources == self.prepared.selection.sources
                 and self.omissions == self.prepared.omissions
                 and self.input_tokens == len(self.prepared.tokenization.token_ids),
                 "COMPILER_RESULT_PREVIEW_COHERENCE")
        else:
            need(self.prepared is None, "COMPILER_RESULT_NO_AUTHORITY")
        need((self.question is not None) == (self.kind == "CLARIFICATION"),
             "COMPILER_RESULT_QUESTION")
