"""Bounded correlated results; parsing establishes no authority or effect.

Only the requested record and its associated event/predecessor cross this
surface. Store cells, other scopes and allocation budgets are never serialized.
DENIED_RECONCILE can follow a durable commit: it does not mean no mutation.
Peer authentication, freshness and ownership remain transport/kernel duties.
"""
from dataclasses import dataclass
import hashlib
import re

from .events import EventContract, StreamPosition
from .evidence_admission import ConsumptionEvidence
from .kernel_transactions import KernelResult, require
from .local_ipc import LocalMessage, decode_message
from .manual_effect import OPERATIONS as MANUAL_OPERATIONS, encode_result as encode_manual_result, decode_result as decode_manual_result
from .task_drafts import TaskResult, TASK_OPERATIONS, validate_result
from .task_meaning import MEANING_OPERATIONS, MEANING_RESULT_PROFILE, decode_proposal
from .editor_recovery import EDITOR_OPERATIONS, EDITOR_MUTATIONS, EDITOR_RESULT_PROFILE, decode_editor_snapshot
from .store_transactions import StoreKey
from .wire import ContractError, MAX_WIRE_BYTES, ParsedRecord, RecordCodec, canonical_bytes, strict_loads

RESULT_PROFILE = "ceta-local-result-v1"
KINDS = frozenset(("COMMITTED", "EVIDENCE", "CURRENT_RECORD", "DENIED_RECONCILE"))
FIELDS = frozenset(("profile", "version", "kind", "error_code", "request_sha256",
    "message_id", "correlation_ref", "causation_ref", "sender_session",
    "receiver_generation", "operation", "scope_id", "request_record_id",
    "record_wire", "event_wire", "prior_position"))
_CODE = re.compile(r"[A-Z][A-Z0-9_]{0,79}")
_PERMIT_CHANGES = frozenset(("status", "causation_ref", "consume_event_ref"))


@dataclass(frozen=True)
class LocalResponse:
    """A correlated observation, never a command, grant or effect receipt."""

    kind: str
    error_code: str | None
    record_wire: bytes | None
    event_wire: bytes | None
    prior_position: StreamPosition | None
    original_response: bytes
    task_result: TaskResult | None = None
    manual_result_wire: bytes | None = None


def _binding(request, codec):
    require(type(request) is LocalMessage and type(codec) is RecordCodec,
            "RESULT_REQUEST_OR_CODEC_REQUIRED")
    # A manually constructed value cannot substitute its decoded attributes for
    # the exact original request that the transport delivered.
    decoded = decode_message(request.original_message, codec)
    require(decoded == request, "RESULT_REQUEST_BINDING")
    original = strict_loads(request.original_message)
    return {"request_sha256": hashlib.sha256(request.original_message).hexdigest(),
        "message_id": request.message_id, "correlation_ref": original["correlation_ref"],
        "causation_ref": original["causation_ref"], "sender_session": request.sender_session,
        "receiver_generation": request.receiver_generation, "operation": request.operation,
        "scope_id": request.scope_id, "request_record_id": request.record.record_id}


def _position(value):
    require(type(value) is dict and set(value) == {"scope_id", "next_sequence", "head"},
            "RESULT_PRIOR_POSITION")
    return StreamPosition(value["scope_id"], value["next_sequence"], value["head"])


def _position_value(position):
    require(type(position) is StreamPosition, "RESULT_PRIOR_POSITION")
    return {"scope_id": position.scope_id, "next_sequence": position.next_sequence,
            "head": position.head}


def _permit_binding(payload, supplied):
    require(payload.record_type == supplied.record_type == "OperationPermit",
            "RESULT_PERMIT_REQUIRED")
    saved, source = payload.as_dict(), supplied.as_dict()
    require(all(saved[name] == source[name] for name in source if name not in _PERMIT_CHANGES),
            "RESULT_PERMIT_BINDING")
    # A known consumption identity cannot be replaced by another event or
    # rolled back to an unconsumed current snapshot.
    if source["consume_event_ref"] is not None:
        require(saved["consume_event_ref"] == source["consume_event_ref"],
                "RESULT_CONSUMPTION_BINDING")
    if source["status"] in {"CONSUMED", "SETTLED"}:
        require(saved["status"] == "CONSUMED", "RESULT_CONSUMPTION_BINDING")
    return saved, source


def _payload(value, request, codec):
    require(type(value["record_wire"]) is str, "RESULT_RECORD_REQUIRED")
    record_wire = value["record_wire"].encode("utf8")
    payload = codec.decode(record_wire)
    require(payload.original_wire == payload.canonical_wire, "RESULT_RECORD_CANONICAL")
    require(payload.as_dict()["scope_id"] == request.scope_id, "RESULT_SCOPE_BINDING")
    return payload


def _event(value, payload, codec):
    require(type(value["event_wire"]) is str, "RESULT_EVENT_REQUIRED")
    wire = value["event_wire"].encode("utf8")
    prior = _position(value["prior_position"])
    events = EventContract(codec)
    prepared = events.require_successor(wire, prior)
    require(prepared.record.original_wire == prepared.record.canonical_wire,
            "RESULT_EVENT_CANONICAL")
    events.require_payload(wire, payload.original_wire)
    event = prepared.record.as_dict()
    require(event["causation_ref"] == payload.as_dict()["causation_ref"],
            "RESULT_EVENT_CAUSATION")
    return prior, event


def _validate(value, request, codec):
    binding = _binding(request, codec)
    require(type(value) is dict and set(value) == FIELDS, "RESULT_FIELDS")
    require(value["profile"] == RESULT_PROFILE and type(value["version"]) is int
            and value["version"] == 1, "RESULT_VERSION")
    require(all(type(value[name]) is type(expected) and value[name] == expected
                for name, expected in binding.items()), "RESULT_REQUEST_BINDING")
    kind = value["kind"]
    require(type(kind) is str and kind in KINDS, "RESULT_KIND")
    if kind == "DENIED_RECONCILE":
        require(type(value["error_code"]) is str and _CODE.fullmatch(value["error_code"])
                and all(value[name] is None for name in ("record_wire", "event_wire", "prior_position")),
                "RESULT_DENIAL_SHAPE")
        return LocalResponse(kind, value["error_code"], None, None, None, b"")
    require(value["error_code"] is None, "RESULT_UNEXPECTED_ERROR")
    payload = _payload(value, request, codec)
    result = payload.as_dict()
    operation, source = request.operation, request.record.as_dict()
    if kind == "CURRENT_RECORD":
        require(operation in {"kernel.recover_permit", "kernel.recover_preparation"}, "RESULT_OPERATION_KIND")
        require(value["event_wire"] is None and value["prior_position"] is None,
                "RESULT_CURRENT_RECORD_SHAPE")
        if operation == "kernel.recover_preparation":
            require(payload.record_type == "OperationPermit" and result["proposal_ref"] == request.record.record_id
                    and all(result[name] == source[name] for name in
                            ("task_id", "adapter_id", "operation", "arguments_commitment", "resources")),
                    "RESULT_PROPOSAL_BINDING")
            require(not source["requires_human_approval"] or result["approval_evidence_ref"] is not None,
                    "RESULT_APPROVAL_REFERENCE_REQUIRED")
            require(result["status"] in {"PREPARED", "CONSUMED"}, "RESULT_CURRENT_STATUS")
            if result["status"] == "PREPARED":
                require(result["consume_event_ref"] is None and result["causation_ref"] == request.record.record_id,
                        "RESULT_CURRENT_PREPARED_BINDING")
            else:
                require(result["consume_event_ref"] is not None and result["causation_ref"] == result["consume_event_ref"],
                        "RESULT_CONSUMPTION_BINDING")
            return LocalResponse(kind, None, payload.original_wire, None, None, b"")
        # Match the kernel recovery selector contract. Historic settled inputs
        # remain supported only by the separate consumption-evidence route.
        require(source["status"] in {"PREPARED", "CONSUMED"}, "RESULT_RECOVERY_SELECTOR_STATE")
        if source["status"] == "PREPARED":
            require(source["consume_event_ref"] is None
                    and source["causation_ref"] == source["proposal_ref"], "RESULT_RECOVERY_SELECTOR_BINDING")
        else:
            require(source["consume_event_ref"] is not None
                    and source["causation_ref"] == source["consume_event_ref"], "RESULT_RECOVERY_SELECTOR_BINDING")
        saved, _ = _permit_binding(payload, request.record)
        require(saved["status"] in {"PREPARED", "CONSUMED"}, "RESULT_CURRENT_STATUS")
        if saved["status"] == "PREPARED":
            require(saved == source and saved["consume_event_ref"] is None,
                    "RESULT_CURRENT_PREPARED_BINDING")
        else:
            require(saved["consume_event_ref"] is not None
                    and saved["causation_ref"] == saved["consume_event_ref"],
                    "RESULT_CONSUMPTION_BINDING")
        return LocalResponse(kind, None, payload.original_wire, None, None, b"")
    prior, event = _event(value, payload, codec)
    if kind == "COMMITTED":
        require(event["actor_session"] == request.sender_session, "RESULT_EVENT_SESSION_BINDING")
    if kind == "EVIDENCE":
        require(operation == "kernel.resolve_consumption", "RESULT_OPERATION_KIND")
        saved, _ = _permit_binding(payload, request.record)
        require(all(saved[name] == source[name] for name in source
                    if name not in {"status", "causation_ref"}), "RESULT_EVIDENCE_BINDING")
        require(saved["status"] == "CONSUMED" and saved["consume_event_ref"] == event["record_id"]
                and saved["causation_ref"] == event["record_id"]
                and event["event_type"] == "kernel.permit.consumed", "RESULT_CONSUMPTION_BINDING")
    elif operation == "kernel.prepare":
        require(payload.record_type == "OperationPermit" and result["status"] == "PREPARED"
                and result["proposal_ref"] == request.record.record_id
                and result["causation_ref"] == request.record.record_id
                and result["consume_event_ref"] is None
                and result["issuance_evidence_ref"] == event["record_id"]
                and event["event_type"] == "kernel.intent.committed", "RESULT_PREPARATION_BINDING")
        require(all(result[name] == source[name] for name in
                    ("task_id", "adapter_id", "operation", "arguments_commitment", "resources")),
                "RESULT_PROPOSAL_BINDING")
        require(not source["requires_human_approval"] or result["approval_evidence_ref"] is not None,
                "RESULT_APPROVAL_REFERENCE_REQUIRED")
    elif operation == "kernel.consume":
        saved, _ = _permit_binding(payload, request.record)
        require(source["status"] == "PREPARED" and source["consume_event_ref"] is None
                and saved["status"] == "CONSUMED" and saved["consume_event_ref"] == event["record_id"]
                and saved["causation_ref"] == event["record_id"]
                and event["event_type"] == "kernel.permit.consumed", "RESULT_CONSUMPTION_BINDING")
    elif operation == "kernel.revoke":
        require(payload.record_type == "StandingGrant" and result["status"] == "REVOKED"
                and source["status"] in {"ACTIVE", "EXHAUSTED"}
                and result["revocation_generation"] == source["revocation_generation"] + 1
                and result["causation_ref"] == request.reason_ref
                and event["event_type"] == "kernel.grant.revoked", "RESULT_REVOCATION_BINDING")
        require(all(result[name] == source[name] for name in source
                    if name not in {"status", "causation_ref", "revocation_generation"}),
                "RESULT_GRANT_BINDING")
    else:
        require(False, "RESULT_OPERATION_KIND")
    return LocalResponse(kind, None, payload.original_wire, value["event_wire"].encode("utf8"), prior, b"")


def _require_commit(result, codec):
    """Check the scoped result's membership without exporting other commit data."""
    payload = codec.decode(result.record_wire)
    events = EventContract(codec)
    event = events.require_successor(result.event_wire, result.prior_position)
    scoped = tuple(item for item in result.commit.history
                   if item.before.scope_id == result.prior_position.scope_id)
    require(len(scoped) == 1, "RESULT_COMMIT_SCOPE")
    item = scoped[0]
    require(item.before == result.prior_position
            and item.after == StreamPosition(item.before.scope_id, item.before.next_sequence + 1, event.head)
            and item.event_ids == (event.record.record_id,), "RESULT_COMMIT_HISTORY")
    collection = "grant" if payload.record_type == "StandingGrant" else "permit"
    key = StoreKey(collection, payload.as_dict()["scope_id"], payload.record_id)
    cells = tuple(cell for cell in result.commit.cells if cell.key == key)
    require(len(cells) == 1 and cells[0].generation > 0
            and cells[0].value_wire == payload.canonical_wire, "RESULT_COMMIT_RECORD")


def encode_response(message: LocalMessage,
                    result: KernelResult | ConsumptionEvidence | ParsedRecord | TaskResult | ContractError,
                    codec: RecordCodec) -> bytes:
    binding = _binding(message, codec)
    if message.operation in MANUAL_OPERATIONS:
        return encode_manual_result(binding, result)
    if message.operation in TASK_OPERATIONS:
        return _encode_task_response(message, result, codec)
    value = {"profile": RESULT_PROFILE, "version": 1, **binding,
             "kind": None, "error_code": None, "record_wire": None,
             "event_wire": None, "prior_position": None}
    if type(result) is KernelResult:
        _require_commit(result, codec)
        value.update(kind="COMMITTED", record_wire=result.record_wire.decode("utf8"),
                     event_wire=result.event_wire.decode("utf8"),
                     prior_position=_position_value(result.prior_position))
    elif type(result) is ConsumptionEvidence:
        require(type(result.consumed_permit_wire) is bytes and type(result.event_wire) is bytes,
                "RESULT_EVIDENCE_REQUIRED")
        # Decode before conversion so invalid UTF-8 is a typed contract error.
        codec.decode(result.consumed_permit_wire); codec.decode(result.event_wire)
        value.update(kind="EVIDENCE", record_wire=result.consumed_permit_wire.decode("utf8"),
                     event_wire=result.event_wire.decode("utf8"),
                     prior_position=_position_value(result.prior_position))
    elif type(result) is ParsedRecord:
        require(codec.decode(result.original_wire) == result, "RESULT_PARSED_RECORD_BINDING")
        value.update(kind="CURRENT_RECORD", record_wire=result.original_wire.decode("utf8"))
    elif type(result) is ContractError:
        code = result.code
        value.update(kind="DENIED_RECONCILE", error_code=code if type(code) is str
                     and _CODE.fullmatch(code) else "INTERNAL_ERROR_RECONCILE")
    else:
        require(False, "RESULT_VALUE_REQUIRED")
    _validate(value, message, codec)
    return canonical_bytes(value)


def decode_response(wire: bytes, request: LocalMessage, codec: RecordCodec) -> LocalResponse:
    if request.operation in MANUAL_OPERATIONS:
        value = decode_manual_result(wire, _binding(request, codec))
        return LocalResponse(value['kind'], value['error_code'], None, None, None,
            wire, manual_result_wire=wire)
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_WIRE_BYTES, "RESULT_SIZE")
    value = strict_loads(wire)
    if request.operation in TASK_OPERATIONS:
        response = _validate_task_response(value, request, codec)
        require(canonical_bytes(value) == wire, "RESULT_CANONICAL")
        return LocalResponse(response.kind, response.error_code, None, None, None, wire, response.task_result)
    response = _validate(value, request, codec)
    require(canonical_bytes(value) == wire, "RESULT_CANONICAL")
    return LocalResponse(response.kind, response.error_code, response.record_wire,
                         response.event_wire, response.prior_position, wire)


def _validate_task_response(value, request, codec):
    binding = _binding(request, codec)
    fields = set(binding) | {"profile", "version", "kind", "error_code", "snapshot_wire", "generation", "task_ids", "revision"}
    meaning_route = request.operation in MEANING_OPERATIONS
    editor_route = request.operation in EDITOR_OPERATIONS
    if meaning_route or editor_route: fields.add("current_task_revision")
    require(type(value) is dict and set(value) == fields and value["profile"] == (MEANING_RESULT_PROFILE if meaning_route
        else EDITOR_RESULT_PROFILE if editor_route else "ceta-task-result-v1")
            and type(value["version"]) is int and value["version"] == 1, "TASK_RESULT_FIELDS")
    require(all(type(value[n]) is type(expected) and value[n] == expected for n, expected in binding.items()), "RESULT_REQUEST_BINDING")
    require(type(value["kind"]) is str, "TASK_RESULT_SHAPE")
    if value["kind"] == "DENIED_RECONCILE":
        require(type(value["error_code"]) is str and _CODE.fullmatch(value["error_code"])
                and value["snapshot_wire"] is None and type(value["generation"]) is int and value["generation"] == 0
                and value["task_ids"] == [] and value["revision"] is None, "TASK_DENIAL_SHAPE")
        require(not meaning_route or value["current_task_revision"] is None, "MEANING_DENIAL_SHAPE")
        require(not editor_route or value["current_task_revision"] is None, "EDITOR_DENIAL_SHAPE")
        return LocalResponse("DENIED_RECONCILE", value["error_code"], None, None, None, b"")
    require(value["error_code"] is None and type(value["task_ids"]) is list
            and (value["snapshot_wire"] is None or type(value["snapshot_wire"]) is str), "TASK_RESULT_SHAPE")
    result = TaskResult(value["kind"], None if value["snapshot_wire"] is None else value["snapshot_wire"].encode("utf8"),
                        value["generation"], tuple(value["task_ids"]), value.get("current_task_revision"))
    revision = validate_result(result, request.record, request.operation)
    require(value["revision"] == revision, "TASK_RESULT_REVISION")
    if request.operation in {"task.create", "task.save"} and result.kind == "TASK_SNAPSHOT":
        snapshot = strict_loads(result.snapshot_wire)
        require(snapshot["updated_session"] == request.sender_session, "TASK_RESULT_SESSION")
        if request.operation == "task.create":
            require(snapshot["created_session"] == request.sender_session and result.generation == 1, "TASK_CREATED_RESULT")
    if request.operation == "task.meaning_propose":
        require(decode_proposal(result.snapshot_wire)["updated_session"] == request.sender_session, "MEANING_RESULT_SESSION")
    if request.operation in EDITOR_MUTATIONS:
        require(decode_editor_snapshot(result.snapshot_wire)["updated_session"] == request.sender_session, "EDITOR_RESULT_SESSION")
    return LocalResponse(result.kind, None, None, None, None, b"", result)


def _encode_task_response(message, result, codec):
    value = {"profile": "ceta-task-result-v1", "version": 1, **_binding(message, codec),
             "kind": None, "error_code": None, "snapshot_wire": None, "generation": 0, "task_ids": [], "revision": None}
    if message.operation in MEANING_OPERATIONS:
        value.update(profile=MEANING_RESULT_PROFILE, current_task_revision=None)
    if message.operation in EDITOR_OPERATIONS:
        value.update(profile=EDITOR_RESULT_PROFILE, current_task_revision=None)
    if type(result) is ContractError:
        code = result.code
        value.update(kind="DENIED_RECONCILE", error_code=code if type(code) is str and _CODE.fullmatch(code)
                     else "INTERNAL_ERROR_RECONCILE")
    else:
        revision = validate_result(result, message.record, message.operation)
        value.update(kind=result.kind, snapshot_wire=None if result.snapshot_wire is None else result.snapshot_wire.decode("utf8"),
                     generation=result.generation, task_ids=list(result.task_ids), revision=revision)
        if message.operation in MEANING_OPERATIONS or message.operation in EDITOR_OPERATIONS:
            value["current_task_revision"] = result.current_task_revision
    _validate_task_response(value, message, codec)
    return canonical_bytes(value)
