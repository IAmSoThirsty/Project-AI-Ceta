"""Typed error semantics; diagnostics and retry references never issue authority."""
from dataclasses import dataclass
import hashlib
import re

from .wire import ContractError, ParsedRecord, RecordCodec, canonical_bytes, strict_loads

ERROR_PROFILE = "ceta-error-semantics-v1"
MAX_ERROR_DEFINITIONS = 256
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,159}")
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")
_CATEGORIES = frozenset({"DENIED", "STALE", "CONFLICT", "INDETERMINATE", "RECOVERY",
                         "INTEGRITY_FAILED", "UNAVAILABLE", "RESOURCE_EXHAUSTED", "INVALID",
                         "INCOMPLETE", "CANCELLING", "BLOCKED"})
_RECONCILE_CODES = frozenset({"EFFECT_INDETERMINATE", "PERMIT_CONSUMED", "STOP_PENDING"})


@dataclass(frozen=True)
class ErrorDefinition:
    code: str
    category: str
    next_action: str
    must_not_imply_completed_effect: bool = True

    def __post_init__(self) -> None:
        if type(self.code) is not str or not _CODE.fullmatch(self.code):
            raise ContractError("INVALID_ERROR_DEFINITION")
        if type(self.category) is not str or self.category not in _CATEGORIES:
            raise ContractError("INVALID_ERROR_CATEGORY")
        if type(self.next_action) is not str or not 1 <= len(self.next_action) <= 4096:
            raise ContractError("INVALID_ERROR_GUIDANCE")
        canonical_bytes(self.next_action)
        if self.must_not_imply_completed_effect is not True:
            raise ContractError("ERROR_COMPLETION_CLAIM_FORBIDDEN")


@dataclass(frozen=True)
class ErrorCatalog:
    """Immutable injected definitions; composition must authenticate their source."""
    definitions: tuple[ErrorDefinition, ...]

    def __post_init__(self) -> None:
        if (type(self.definitions) is not tuple
                or not 1 <= len(self.definitions) <= MAX_ERROR_DEFINITIONS
                or any(type(d) is not ErrorDefinition for d in self.definitions)):
            raise ContractError("INVALID_ERROR_CATALOG")
        if len({d.code for d in self.definitions}) != len(self.definitions):
            raise ContractError("DUPLICATE_ERROR_CODE")

    @classmethod
    def from_wire(cls, raw: bytes) -> "ErrorCatalog":
        doc = strict_loads(raw)
        if type(doc) is not dict or set(doc) != {"errors"} or type(doc["errors"]) is not list:
            raise ContractError("INVALID_ERROR_CATALOG")
        if not 1 <= len(doc["errors"]) <= MAX_ERROR_DEFINITIONS:
            raise ContractError("INVALID_ERROR_CATALOG")
        definitions = []
        for row in doc["errors"]:
            if type(row) is not dict or set(row) != {
                    "code", "category", "next_action", "must_not_imply_completed_effect"}:
                raise ContractError("INVALID_ERROR_DEFINITION")
            definitions.append(ErrorDefinition(**row))
        return cls(tuple(definitions))

    def lookup(self, code: str) -> ErrorDefinition:
        if type(code) is not str:
            raise ContractError("UNREGISTERED_ERROR_CODE")
        for definition in self.definitions:
            if definition.code == code:
                return definition
        raise ContractError("UNREGISTERED_ERROR_CODE")

    def canonical_wire(self) -> bytes:
        return canonical_bytes({"contract_type": "ErrorCatalogMetadata", "contract_version": "1",
            "error_profile": ERROR_PROFILE, "errors": [{"code": d.code, "category": d.category,
                "next_action": d.next_action, "must_not_imply_completed_effect": True}
                for d in sorted(self.definitions, key=lambda d: d.code)]})

    def commitment(self) -> str:
        domain = ("CETA:error-catalog:" + ERROR_PROFILE + "\0").encode("ascii")
        return "sha256:" + hashlib.sha256(domain + self.canonical_wire()).hexdigest()


@dataclass(frozen=True)
class ErrorAssessment:
    record: ParsedRecord
    definition: ErrorDefinition
    catalog_commitment: str

    @property
    def requires_reconciliation(self) -> bool:
        value = self.record.as_dict()
        return (value["recoverability"] == "RECONCILE" or value["effect_status"] != "NOT_STARTED"
                or value["code"] in _RECONCILE_CODES)


class ErrorContract:
    def __init__(self, codec: RecordCodec, catalog: ErrorCatalog) -> None:
        if type(codec) is not RecordCodec or type(catalog) is not ErrorCatalog:
            raise ContractError("ERROR_CONTRACT_INPUT_REQUIRED")
        self._codec, self._catalog = codec, catalog

    def decode(self, raw: bytes, *, scope_id: str, task_id: str | None,
               operation_id: str | None) -> ErrorAssessment:
        """Check shape, registration, correlation and conservative effect semantics.

        Expected context must come from authenticated request/state resolution.
        A nullable identifier remains unavailable, never an invented identity.
        No retry, refund, dispatch, settlement or success transition occurs here.
        """
        for value, nullable in ((scope_id, False), (task_id, True), (operation_id, True)):
            if value is None and nullable:
                continue
            if type(value) is not str or not _ID.fullmatch(value):
                raise ContractError("INVALID_ERROR_CONTEXT")
        record = self._codec.decode(raw)
        if record.record_type != "ErrorEnvelope":
            raise ContractError("ERROR_ENVELOPE_REQUIRED")
        value = record.as_dict()
        for field, expected in (("scope_id", scope_id), ("task_id", task_id),
                                ("operation_id", operation_id)):
            if value[field] != expected:
                raise ContractError("ERROR_CONTEXT_MISMATCH", "$." + field)
        definition = self._catalog.lookup(value["code"])
        if any(r["scope_id"] != scope_id for r in value["affected_resources"]):
            raise ContractError("ERROR_RESOURCE_SCOPE_MISMATCH")
        status, recovery = value["effect_status"], value["recoverability"]
        if status in {"MAY_HAVE_EXECUTED", "UNKNOWN"} and recovery != "RECONCILE":
            raise ContractError("ERROR_EFFECT_RECONCILIATION_REQUIRED")
        if status != "NOT_STARTED" and recovery == "RETRY_WITH_NEW_AUTHORITY":
            raise ContractError("ERROR_EFFECT_RECONCILIATION_REQUIRED")
        if value["code"] in _RECONCILE_CODES and recovery != "RECONCILE":
            raise ContractError("ERROR_EFFECT_RECONCILIATION_REQUIRED")
        if value["code"] == "EFFECT_INDETERMINATE" and status == "NOT_STARTED":
            raise ContractError("ERROR_EFFECT_STATUS_CONTRADICTION")
        return ErrorAssessment(record, definition, self._catalog.commitment())
