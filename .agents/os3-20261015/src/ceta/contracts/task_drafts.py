"""Typed user-input commands and CREATED task snapshots, without authority.

Exact captured UTF-8 is represented as lowercase hex. Canonical JSON never
normalizes the user's bytes. These are owner-internal task values, not additions
to the twenty admitted record schemas or authenticated consent transcripts.
"""
from dataclasses import dataclass
import hashlib

from .kernel_transactions import require, logical_key
from .store_transactions import StoreCell, commitment, identifier
from .wire import canonical_bytes, strict_loads, MAX_WIRE_BYTES
from .task_meaning import (MEANING_COMMAND_PROFILE, MEANING_OPERATIONS,
    decode_meaning, decode_proposal, meaning_key)
from .editor_recovery import (EDITOR_COMMAND_PROFILE, EDITOR_OPERATIONS,
    EDITOR_REFERENCE_PROFILE, decode_editor_chunk, decode_editor_payload,
    decode_editor_snapshot, recovery_key, validate_editor_chunk)

COMMAND_PROFILE = "ceta-task-command-v1"
TASK_PROFILE = "ceta-task-draft-v1"
CATALOG_PROFILE = "ceta-task-catalog-v1"
MAX_TEXT_BYTES = 65536
MAX_TASKS = 256
TASK_OPERATIONS = {"task.create": "create", "task.save": "save",
                   "task.load": "load", "task.list": "list", **MEANING_OPERATIONS, **EDITOR_OPERATIONS}
COMMAND_FIELDS = {"record_type", "profile", "record_id", "scope_id", "kind",
                  "task_id", "expected_revision", "title_hex", "instruction_hex", "draft_hex"}
EDITOR_COMMAND_FIELDS = {"editor_payload_hex", "editor_expected_revision",
    "editor_capture_commitment", "editor_chunk_index", "editor_chunk_hex"}
TASK_FIELDS = {"profile", "scope_id", "task_id", "owner_binding", "principal_id",
               "created_session", "updated_session", "state", "title_hex",
               "instruction_hex", "draft_hex", "objective_revision", "objective_generation", "meaning", "request_id",
               "request_commitment", "event_id", "event_sequence", "previous_head", "observation_id"}


def text_hex(text, *, maximum=MAX_TEXT_BYTES):
    require(type(text) is str, "TASK_TEXT_REQUIRED")
    try:
        raw = text.encode("utf8")
    except UnicodeError:
        require(False, "TASK_TEXT_ENCODING")
    require(len(raw) <= maximum, "TASK_TEXT_SIZE")
    return raw.hex()


def text_value(value, *, maximum=MAX_TEXT_BYTES):
    require(type(value) is str and len(value) <= maximum * 2
            and len(value) % 2 == 0 and all(c in "0123456789abcdef" for c in value), "TASK_TEXT_ENCODING")
    try:
        return bytes.fromhex(value).decode("utf8")
    except UnicodeError:
        require(False, "TASK_TEXT_ENCODING")


def task_content_revision(value):
    body = {name: value[name] for name in ("scope_id", "task_id", "title_hex", "instruction_hex", "draft_hex", "objective_generation", "meaning")}
    return "sha256:" + hashlib.sha256(b"CETA:task-objective:v1\0" + canonical_bytes(body)).hexdigest()


def draft_key(scope, task_id):
    return logical_key("projection", scope, "task-draft", task_id)


def catalog_key(scope, owner_binding):
    commitment(owner_binding)
    return logical_key("projection", scope, "task-catalog", owner_binding)


@dataclass(frozen=True)
class TaskCommand:
    record_type: str
    record_id: str
    original_wire: bytes
    canonical_wire: bytes
    commitment: str

    def as_dict(self):
        return strict_loads(self.canonical_wire)


def decode_command(wire):
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_WIRE_BYTES, "TASK_COMMAND_SIZE")
    value = strict_loads(wire)
    require(type(value) is dict, "TASK_COMMAND_FIELDS")
    meaning_kind = value.get("kind") in MEANING_OPERATIONS.values()
    editor_kind = value.get("kind") in EDITOR_OPERATIONS.values()
    fields = (COMMAND_FIELDS | {"meaning_hex", "meaning_expected_revision"} if meaning_kind
        else COMMAND_FIELDS | EDITOR_COMMAND_FIELDS if editor_kind else COMMAND_FIELDS)
    require(set(value) == fields, "TASK_COMMAND_FIELDS")
    require(value["profile"] == (MEANING_COMMAND_PROFILE if meaning_kind else EDITOR_COMMAND_PROFILE if editor_kind else COMMAND_PROFILE)
        and value["record_type"] == "TaskCommand", "TASK_COMMAND_PROFILE")
    identifier(value["record_id"]); identifier(value["scope_id"])
    require(type(value["kind"]) is str and value["kind"] in TASK_OPERATIONS.values(), "TASK_COMMAND_KIND")
    kind = value["kind"]
    if editor_kind:
        identifier(value["task_id"])
        require(all(value[n] is None for n in ("expected_revision", "title_hex", "instruction_hex", "draft_hex")),
                "EDITOR_COMMAND_SHAPE")
        payload_hex, expected = value["editor_payload_hex"], value["editor_expected_revision"]
        capture, index, chunk_hex = (value["editor_capture_commitment"],
            value["editor_chunk_index"], value["editor_chunk_hex"])
        if kind == "editor_load":
            require(payload_hex is None and chunk_hex is None, "EDITOR_LOAD_SHAPE")
            if expected is None:
                require(capture is None and index is None, "EDITOR_LOAD_SHAPE")
            else:
                commitment(expected); commitment(capture)
                require(type(index) is int and 0 <= index < 128, "EDITOR_LOAD_CHUNK_INDEX")
        elif kind == "editor_discard":
            commitment(expected)
            require(payload_hex is None and capture is None and index is None and chunk_hex is None,
                    "EDITOR_DISCARD_SHAPE")
        else:
            if expected is not None: commitment(expected)
            require(type(payload_hex) is str and 2 <= len(payload_hex) <= MAX_WIRE_BYTES * 2
                and len(payload_hex) % 2 == 0 and all(c in "0123456789abcdef" for c in payload_hex),
                "EDITOR_COMMAND_PAYLOAD")
            payload = decode_editor_payload(bytes.fromhex(payload_hex))
            if payload["profile"] == EDITOR_REFERENCE_PROFILE:
                commitment(capture)
                require(capture == payload["capture_commitment"]
                    and type(index) is int and 0 <= index < payload["chunk_count"]
                    and type(chunk_hex) is str and 2 <= len(chunk_hex) <= MAX_WIRE_BYTES * 2
                    and len(chunk_hex) % 2 == 0 and all(c in "0123456789abcdef" for c in chunk_hex),
                    "EDITOR_REFERENCE_COMMAND")
                require(decode_editor_chunk(bytes.fromhex(chunk_hex))["chunk_index"] == index,
                        "EDITOR_REFERENCE_CHUNK_INDEX")
                validate_editor_chunk(payload, bytes.fromhex(chunk_hex))
            else:
                require(capture is None and index is None and chunk_hex is None,
                        "EDITOR_INLINE_COMMAND")
    elif meaning_kind:
        identifier(value["task_id"])
        require(all(value[n] is None for n in ("title_hex", "instruction_hex", "draft_hex")), "MEANING_COMMAND_SHAPE")
        if kind == "meaning_load":
            require(all(value[n] is None for n in ("expected_revision", "meaning_hex", "meaning_expected_revision")), "MEANING_LOAD_SHAPE")
        else:
            commitment(value["expected_revision"])
            if value["meaning_expected_revision"] is not None: commitment(value["meaning_expected_revision"])
            raw = text_value(value["meaning_hex"], maximum=140000).encode("utf8")
            meaning = strict_loads(raw); decode_meaning(meaning)
            require(canonical_bytes(meaning) == raw, "MEANING_CANONICAL")
    elif kind == "list":
        require(all(value[n] is None for n in ("task_id", "expected_revision", "title_hex", "instruction_hex", "draft_hex")), "TASK_LIST_SHAPE")
    else:
        identifier(value["task_id"])
        if kind == "load":
            require(all(value[n] is None for n in ("expected_revision", "title_hex", "instruction_hex", "draft_hex")), "TASK_LOAD_SHAPE")
        else:
            title = text_value(value["title_hex"], maximum=256)
            require(bool(title.strip()), "TASK_TITLE_REQUIRED")
            text_value(value["draft_hex"])
            if kind == "create":
                require(value["expected_revision"] is None, "TASK_CREATE_REVISION")
                require(bool(text_value(value["instruction_hex"]).strip()), "TASK_INSTRUCTION_REQUIRED")
            else:
                commitment(value["expected_revision"])
                require(value["instruction_hex"] is None, "TASK_ORIGINAL_INSTRUCTION_IMMUTABLE")
    canonical = canonical_bytes(value)
    return TaskCommand("TaskCommand", value["record_id"], wire, canonical,
        "sha256:" + hashlib.sha256(b"CETA:task-command:v1\0" + canonical).hexdigest())


def command_wire(kind, scope, command_id, *, task_id=None, expected_revision=None,
                 title=None, instruction=None, draft=None, meaning=None, meaning_expected_revision=None,
                 editor_payload=None, editor_expected_revision=None,
                 editor_capture_commitment=None, editor_chunk_index=None, editor_chunk=None):
    value = {"record_type": "TaskCommand", "profile": COMMAND_PROFILE, "record_id": command_id,
        "scope_id": scope, "kind": kind, "task_id": task_id, "expected_revision": expected_revision,
        "title_hex": None if title is None else text_hex(title, maximum=256),
        "instruction_hex": None if instruction is None else text_hex(instruction),
        "draft_hex": None if draft is None else text_hex(draft)}
    if kind in MEANING_OPERATIONS.values():
        value.update(profile=MEANING_COMMAND_PROFILE, meaning_hex=None if meaning is None else canonical_bytes(decode_meaning(meaning)).hex(),
            meaning_expected_revision=meaning_expected_revision)
    else:
        require(meaning is None and meaning_expected_revision is None, "MEANING_UNEXPECTED_INPUT")
    if kind in EDITOR_OPERATIONS.values():
        if editor_payload is not None: decode_editor_payload(editor_payload)
        if editor_chunk is not None: decode_editor_chunk(editor_chunk)
        value.update(profile=EDITOR_COMMAND_PROFILE,
            editor_payload_hex=None if editor_payload is None else editor_payload.hex(),
            editor_expected_revision=editor_expected_revision,
            editor_capture_commitment=editor_capture_commitment,
            editor_chunk_index=editor_chunk_index,
            editor_chunk_hex=None if editor_chunk is None else editor_chunk.hex())
    else:
        require(editor_payload is None and editor_expected_revision is None
            and editor_capture_commitment is None and editor_chunk_index is None and editor_chunk is None,
            "EDITOR_UNEXPECTED_INPUT")
    wire = canonical_bytes(value); decode_command(wire)
    return wire


def decode_snapshot(wire):
    value = strict_loads(wire)
    require(type(value) is dict and set(value) == TASK_FIELDS and value["profile"] == TASK_PROFILE
            and value["state"] == "CREATED" and canonical_bytes(value) == wire, "TASK_SNAPSHOT_SHAPE")
    for name in ("scope_id", "task_id", "principal_id", "created_session", "updated_session",
                 "request_id", "event_id", "observation_id"):
        identifier(value[name])
    for name in ("owner_binding", "objective_revision", "request_commitment"):
        commitment(value[name])
    require(type(value["event_sequence"]) is int and 0 <= value["event_sequence"] < 2**53, "TASK_EVENT_SEQUENCE")
    if value["previous_head"] is not None: commitment(value["previous_head"])
    require((value["event_sequence"] == 0) == (value["previous_head"] is None), "TASK_EVENT_PREDECESSOR")
    require(bool(text_value(value["title_hex"], maximum=256).strip())
            and bool(text_value(value["instruction_hex"]).strip()), "TASK_CONTENT_REQUIRED")
    text_value(value["draft_hex"])
    require(type(value["objective_generation"]) is int and 1 <= value["objective_generation"] < 2**53,
            "TASK_OBJECTIVE_GENERATION")
    require(type(value["meaning"]) is dict and set(value["meaning"]) == {
        "clarified_meaning", "scope", "exclusions", "completion_predicates", "assumptions",
        "unresolved_questions", "standing_instructions", "authority", "budgets", "evidence"}
        and all(item is None for item in value["meaning"].values()), "TASK_MEANING_UNAVAILABLE")
    require(task_content_revision(value) == value["objective_revision"], "TASK_OBJECTIVE_REVISION")
    return value


def decode_catalog(wire, scope, owner):
    value = strict_loads(wire)
    require(type(value) is dict and set(value) == {"profile", "scope_id", "owner_binding", "task_ids"}
            and value["profile"] == CATALOG_PROFILE and value["scope_id"] == scope and value["owner_binding"] == owner
            and canonical_bytes(value) == wire and type(value["task_ids"]) is list
            and len(value["task_ids"]) <= MAX_TASKS, "TASK_CATALOG_SHAPE")
    for task_id in value["task_ids"]: identifier(task_id)
    require(len(set(value["task_ids"])) == len(value["task_ids"]), "TASK_CATALOG_DUPLICATE")
    return tuple(value["task_ids"])


@dataclass(frozen=True)
class TaskResult:
    """A current observation; generation/revision are optimistic concurrency data."""
    kind: str
    snapshot_wire: bytes | None = None
    generation: int = 0
    task_ids: tuple[str, ...] = ()
    current_task_revision: str | None = None


def validate_result(result, command, operation):
    require(type(result) is TaskResult and type(result.kind) is str and type(command) is TaskCommand
            and decode_command(command.original_wire) == command
            and operation in TASK_OPERATIONS and TASK_OPERATIONS[operation] == command.as_dict()["kind"], "TASK_RESULT_BINDING")
    source = command.as_dict()
    if operation in EDITOR_OPERATIONS:
        require(type(result.task_ids) is tuple and result.task_ids == () and type(result.generation) is int,
                "EDITOR_RESULT_SHAPE")
        commitment(result.current_task_revision)
        if result.kind == "TASK_EDITOR_ABSENT":
            require(operation == "task.editor_load" and result.snapshot_wire is None and result.generation == 0
                and source["editor_expected_revision"] is None, "EDITOR_ABSENT_RESULT")
            return None
        if result.kind == "TASK_EDITOR_CHUNK":
            require(operation == "task.editor_load" and type(result.snapshot_wire) is bytes
                and result.generation > 0 and source["editor_expected_revision"] is not None,
                "EDITOR_CHUNK_RESULT")
            chunk = decode_editor_chunk(result.snapshot_wire)
            require(chunk["capture_commitment"] == source["editor_capture_commitment"]
                and chunk["chunk_index"] == source["editor_chunk_index"],
                "EDITOR_CHUNK_RESULT_BINDING")
            return source["editor_expected_revision"]
        require(result.kind in {"TASK_EDITOR_STAGING", "TASK_EDITOR_RETAINED", "TASK_EDITOR_DISCARDED"}
            and type(result.snapshot_wire) is bytes and result.generation > 0, "EDITOR_RESULT_SHAPE")
        snapshot = decode_editor_snapshot(result.snapshot_wire)
        require((snapshot["scope_id"], snapshot["task_id"], snapshot["generation"])
            == (source["scope_id"], source["task_id"], result.generation)
            and result.kind == "TASK_EDITOR_" + snapshot["state"], "EDITOR_RESULT_BINDING")
        if operation != "task.editor_load":
            require(snapshot["request_id"] == command.record_id and snapshot["request_commitment"] == command.commitment
                and snapshot["previous_recovery_revision"] == source["editor_expected_revision"], "EDITOR_RESULT_COMMAND")
            if operation == "task.editor_retain":
                # An editor recovery capture can legitimately preserve a
                # prior observed task basis after a concurrent task save.  The
                # returned current revision is the service observation; the
                # snapshot must bind the exact command payload to its durable
                # lineage rather than silently rebasing raw text.
                require(canonical_bytes(snapshot["payload"]).hex() == source["editor_payload_hex"]
                    and snapshot["lineage"]["task_basis_revision"] == snapshot["payload"]["basis_revision"]
                    and "observed_task_revision" in snapshot["lineage"]
                    and snapshot["lineage"]["observed_task_revision"] == result.current_task_revision,
                    "EDITOR_RESULT_PAYLOAD")
                if snapshot["payload"]["profile"] == EDITOR_REFERENCE_PROFILE:
                    require(snapshot["state"] in {"STAGING", "RETAINED"}
                        and snapshot["payload"]["capture_commitment"] == source["editor_capture_commitment"]
                        and snapshot["staged_chunk_count"] == source["editor_chunk_index"] + 1,
                        "EDITOR_REFERENCE_RESULT")
                else:
                    require(result.kind == "TASK_EDITOR_RETAINED", "EDITOR_INLINE_RESULT")
            else:
                require(result.kind == "TASK_EDITOR_DISCARDED", "EDITOR_DISCARD_RESULT")
        return StoreCell(recovery_key(source["scope_id"], source["task_id"]), result.generation,
                         result.snapshot_wire).revision
    if operation in MEANING_OPERATIONS:
        require(type(result.kind) is str and result.task_ids == () and type(result.generation) is int, "MEANING_RESULT_SHAPE")
        commitment(result.current_task_revision)
        if result.kind == "TASK_MEANING_ABSENT":
            require(operation == "task.meaning_load" and result.snapshot_wire is None and result.generation == 0, "MEANING_ABSENT_RESULT")
            return None
        require(result.kind in {"TASK_MEANING_PROPOSAL", "TASK_MEANING_STALE"}
            and type(result.snapshot_wire) is bytes and result.generation > 0, "MEANING_RESULT_SHAPE")
        proposal = decode_proposal(result.snapshot_wire)
        require((proposal["scope_id"], proposal["task_id"], proposal["generation"])
            == (source["scope_id"], source["task_id"], result.generation), "MEANING_RESULT_BINDING")
        require((proposal["basis_revision"] != result.current_task_revision)
            == (result.kind == "TASK_MEANING_STALE"), "MEANING_RESULT_FRESHNESS")
        if operation == "task.meaning_propose":
            require(result.kind == "TASK_MEANING_PROPOSAL" and result.current_task_revision == source["expected_revision"]
                and proposal["request_id"] == command.record_id and proposal["request_commitment"] == command.commitment
                and canonical_bytes(proposal["meaning"]).hex() == source["meaning_hex"], "MEANING_RESULT_COMMAND")
        return StoreCell(meaning_key(source["scope_id"], source["task_id"]), result.generation, result.snapshot_wire).revision
    require(result.current_task_revision is None, "TASK_RESULT_UNEXPECTED_MEANING")
    if result.kind == "TASK_ABSENT":
        require(operation == "task.load" and result.snapshot_wire is None
                and type(result.generation) is int and result.generation == 0 and result.task_ids == (), "TASK_ABSENT_RESULT")
        return None
    if operation == "task.list":
        require(result.kind == "TASK_LIST" and result.snapshot_wire is None and type(result.generation) is int and result.generation == 0
                and type(result.task_ids) is tuple and len(result.task_ids) <= MAX_TASKS
                , "TASK_LIST_RESULT")
        for task_id in result.task_ids: identifier(task_id)
        require(len(set(result.task_ids)) == len(result.task_ids), "TASK_LIST_RESULT")
        return None
    require(result.kind in {"TASK_SNAPSHOT", "TASK_UNCHANGED"} and result.task_ids == () and type(result.generation) is int
            and result.generation > 0 and type(result.snapshot_wire) is bytes, "TASK_SNAPSHOT_RESULT")
    snapshot = decode_snapshot(result.snapshot_wire)
    require(snapshot["objective_generation"] == result.generation, "TASK_RESULT_GENERATION")
    require(snapshot["scope_id"] == source["scope_id"] and snapshot["task_id"] == source["task_id"], "TASK_RESULT_SCOPE")
    revision = StoreCell(draft_key(source["scope_id"], source["task_id"]), result.generation, result.snapshot_wire).revision
    if result.kind == "TASK_UNCHANGED":
        require(operation == "task.save" and revision == source["expected_revision"]
                and all(snapshot[n] == source[n] for n in ("title_hex", "draft_hex")), "TASK_UNCHANGED_BINDING")
    elif operation in {"task.create", "task.save"}:
        require(snapshot["request_id"] == command.record_id and snapshot["request_commitment"] == command.commitment
                and all(snapshot[n] == source[n] for n in ("title_hex", "draft_hex")), "TASK_RESULT_COMMAND")
        if operation == "task.create":
            require(snapshot["instruction_hex"] == source["instruction_hex"], "TASK_RESULT_ORIGINAL")
    return revision
