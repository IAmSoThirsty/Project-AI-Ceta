"""Exact editor-byte custody, kept separate from validated task interpretation.

The normal editor command remains intentionally small: ordinary captures use an
inline payload, while larger captures use an authenticated reference plus
bounded chunks in the TaskDrafts atomic projection store. A reference is not a
meaning proposal and cannot make its raw text accepted task state.
"""
import hashlib
import re

from .kernel_transactions import require, logical_key
from .store_transactions import commitment, identifier
from .task_meaning import MEANING_FIELDS
from .wire import canonical_bytes, strict_loads, MAX_WIRE_BYTES

_LOWER_HEX = re.compile(r"[0-9a-f]*", re.ASCII)

EDITOR_PAYLOAD_PROFILE = "ceta-task-editor-payload-v1"
EDITOR_REFERENCE_PROFILE = "ceta-task-editor-payload-reference-v1"
EDITOR_CHUNK_PROFILE = "ceta-task-editor-chunk-v1"
EDITOR_PROFILE = "ceta-task-editor-recovery-v1"
EDITOR_COMMAND_PROFILE = "ceta-task-editor-command-v1"
EDITOR_RESULT_PROFILE = "ceta-task-editor-result-v1"
EDITOR_OPERATIONS = {"task.editor_retain": "editor_retain",
                     "task.editor_load": "editor_load", "task.editor_discard": "editor_discard"}
EDITOR_MUTATIONS = frozenset(("task.editor_retain", "task.editor_discard"))

# Preserve the original bounded inline protocol. The larger limits only apply
# to the chunked custody route; no unbounded raw text reaches IPC or a cell.
MAX_UTF16_BYTES = 131072
MAX_EDITOR_UTF16_BYTES = 196608
MAX_EDITOR_DOCUMENT_UTF16_BYTES = 8 * 1024 * 1024
MAX_EDITOR_CUSTODY_UTF16_BYTES = 16 * 1024 * 1024
MAX_EDITOR_CHUNK_BYTES = 128 * 1024
MAX_EDITOR_CHUNKS = 128
MAX_EDITOR_REVISION = 2**53 - 1

DOCUMENT_FIELDS = frozenset(("document_id", "utf16le_hex", "document_revision",
                             "cursor_position", "anchor_position"))
REFERENCE_DOCUMENT_FIELDS = frozenset(("document_id", "document_revision",
    "cursor_position", "anchor_position", "utf16_bytes", "raw_commitment",
    "chunk_start", "chunk_count"))
PAYLOAD_FIELDS = frozenset(("profile", "basis_revision", "widget_revision", "documents"))
REFERENCE_FIELDS = frozenset(("profile", "basis_revision", "widget_revision", "documents",
    "capture_commitment", "chunk_count", "utf16_bytes"))
CHUNK_FIELDS = frozenset(("profile", "capture_commitment", "chunk_index", "chunk_count",
    "document", "document_offset", "utf16le_hex", "chunk_commitment"))
LINEAGE_FIELDS = frozenset(("task_basis_revision", "observed_task_revision",
    "original_instruction_commitment", "proposed_meaning_commitment", "corrected_task_revision",
    "recovery_capture_commitment", "prior_recovery_revision"))
LEGACY_LINEAGE_FIELDS = LINEAGE_FIELDS - frozenset(("observed_task_revision",))
DISPOSITION_FIELDS = frozenset(("kind", "discarded_capture_commitment",
    "consent_request_commitment", "predecessor_recovery_revision"))
EDITOR_FIELDS = frozenset(("profile", "state", "scope_id", "task_id", "owner_binding",
    "principal_id", "updated_session", "payload", "generation",
    "previous_recovery_revision", "request_id", "request_commitment", "event_id",
    "event_sequence", "previous_head", "observation_id", "lineage", "disposition",
    "staged_chunk_count"))


def _digest(domain, body):
    require(type(domain) is bytes and type(body) is bytes, "EDITOR_DIGEST_INPUT")
    return "sha256:" + hashlib.sha256(domain + body).hexdigest()


def _hex_bytes(value, code, maximum):
    require(type(value) is str and len(value) <= maximum * 2 and len(value) % 4 == 0
        and _LOWER_HEX.fullmatch(value) is not None, code)
    return bytes.fromhex(value)


def utf16_text_hex(text):
    """Encode text for the legacy bounded inline route."""
    require(type(text) is str, "EDITOR_TEXT_REQUIRED")
    require(len(text) <= MAX_UTF16_BYTES // 2, "EDITOR_TEXT_SIZE")
    raw = text.encode("utf-16-le", errors="surrogatepass")
    require(len(raw) <= MAX_UTF16_BYTES, "EDITOR_TEXT_SIZE")
    return raw.hex()


def _utf16_bytes(value):
    return _hex_bytes(value, "EDITOR_TEXT_ENCODING", MAX_EDITOR_DOCUMENT_UTF16_BYTES)


def utf16_text_value(value):
    return _utf16_bytes(value).decode("utf-16-le", errors="surrogatepass")


def _revision(value, code):
    require(type(value) is int and 0 <= value <= MAX_EDITOR_REVISION, code)


def _document_metadata(document, *, raw_length):
    identifier(document["document_id"])
    _revision(document["document_revision"], "EDITOR_DOCUMENT_REVISION")
    for name in ("cursor_position", "anchor_position"):
        require(type(document[name]) is int and 0 <= document[name] <= raw_length // 2,
                "EDITOR_DOCUMENT_POSITION")


def _source_documents(documents):
    """Validate exact caller-captured facts before selecting a custody route."""
    require(type(documents) is dict and set(documents) == set(MEANING_FIELDS), "EDITOR_DOCUMENTS")
    total = 0
    for document in documents.values():
        require(type(document) is dict and set(document) == DOCUMENT_FIELDS, "EDITOR_DOCUMENT_SHAPE")
        raw = _utf16_bytes(document["utf16le_hex"])
        require(len(raw) <= MAX_EDITOR_DOCUMENT_UTF16_BYTES, "EDITOR_DOCUMENT_SIZE")
        _document_metadata(document, raw_length=len(raw))
        total += len(raw)
    require(total <= MAX_EDITOR_CUSTODY_UTF16_BYTES, "EDITOR_TOTAL_CUSTODY_SIZE")
    return documents


def _inline_documents(documents):
    _source_documents(documents)
    total = sum(len(_utf16_bytes(document["utf16le_hex"])) for document in documents.values())
    require(total <= MAX_EDITOR_UTF16_BYTES
        and all(len(_utf16_bytes(document["utf16le_hex"])) <= MAX_UTF16_BYTES
                for document in documents.values()), "EDITOR_TOTAL_SIZE")
    return documents


def _document_commitment(raw):
    require(type(raw) is bytes and len(raw) % 2 == 0, "EDITOR_DOCUMENT_BYTES")
    return _digest(b"CETA:task-editor-document-utf16:v1\0", raw)


def _chunk_commitment(capture, index, document, offset, raw):
    commitment(capture)
    require(type(index) is int and 0 <= index < MAX_EDITOR_CHUNKS, "EDITOR_CHUNK_INDEX")
    require(type(document) is str and document in MEANING_FIELDS, "EDITOR_CHUNK_DOCUMENT")
    require(type(offset) is int and 0 <= offset <= MAX_EDITOR_DOCUMENT_UTF16_BYTES
        and offset % 2 == 0, "EDITOR_CHUNK_OFFSET")
    require(type(raw) is bytes and 1 <= len(raw) <= MAX_EDITOR_CHUNK_BYTES and len(raw) % 2 == 0,
            "EDITOR_CHUNK_BYTES")
    return _digest(b"CETA:task-editor-chunk:v1\0", canonical_bytes({
        "capture_commitment": capture, "chunk_index": index, "document": document,
        "document_offset": offset, "utf16le_hex": raw.hex()}))


def _reference_documents(documents):
    require(type(documents) is dict and set(documents) == set(MEANING_FIELDS), "EDITOR_DOCUMENTS")
    total, count, result = 0, 0, {}
    for name in MEANING_FIELDS:
        document = documents[name]
        require(type(document) is dict and set(document) == REFERENCE_DOCUMENT_FIELDS,
                "EDITOR_REFERENCE_DOCUMENT_SHAPE")
        length = document["utf16_bytes"]
        require(type(length) is int and 0 <= length <= MAX_EDITOR_DOCUMENT_UTF16_BYTES
            and length % 2 == 0, "EDITOR_REFERENCE_DOCUMENT_BYTES")
        _document_metadata(document, raw_length=length)
        commitment(document["raw_commitment"])
        start, chunks = document["chunk_start"], document["chunk_count"]
        require(type(start) is int and 0 <= start < MAX_EDITOR_CHUNKS
            and type(chunks) is int and 0 <= chunks <= MAX_EDITOR_CHUNKS, "EDITOR_REFERENCE_CHUNK_RANGE")
        expected = 0 if length == 0 else (length + MAX_EDITOR_CHUNK_BYTES - 1) // MAX_EDITOR_CHUNK_BYTES
        require(chunks == expected and start == count and count + chunks <= MAX_EDITOR_CHUNKS,
                "EDITOR_REFERENCE_CHUNK_LAYOUT")
        total += length
        count += chunks
        result[name] = document
    require(total <= MAX_EDITOR_CUSTODY_UTF16_BYTES and count > 0, "EDITOR_REFERENCE_SIZE")
    return result, total, count


def _reference_payload(value):
    require(type(value) is dict and set(value) == REFERENCE_FIELDS
        and value["profile"] == EDITOR_REFERENCE_PROFILE, "EDITOR_REFERENCE_SHAPE")
    commitment(value["basis_revision"])
    _revision(value["widget_revision"], "EDITOR_WIDGET_REVISION")
    _documents, total, chunks = _reference_documents(value["documents"])
    commitment(value["capture_commitment"])
    require(value["utf16_bytes"] == total and value["chunk_count"] == chunks, "EDITOR_REFERENCE_TOTAL")
    return value


def _payload(value):
    require(type(value) is dict and type(value.get("profile")) is str, "EDITOR_PAYLOAD_SHAPE")
    if value["profile"] == EDITOR_PAYLOAD_PROFILE:
        require(set(value) == PAYLOAD_FIELDS, "EDITOR_PAYLOAD_SHAPE")
        commitment(value["basis_revision"])
        _revision(value["widget_revision"], "EDITOR_WIDGET_REVISION")
        _inline_documents(value["documents"])
        return value
    if value["profile"] == EDITOR_REFERENCE_PROFILE:
        return _reference_payload(value)
    require(False, "EDITOR_PAYLOAD_PROFILE")


def payload_capture_commitment(payload):
    """Commit exact raw content without exposing it in a reference payload."""
    value = _payload(payload)
    if value["profile"] == EDITOR_REFERENCE_PROFILE:
        return value["capture_commitment"]
    return _digest(b"CETA:task-editor-inline-capture:v1\0", canonical_bytes(value))


def _reference_value(*, basis_revision, widget_revision, documents):
    _source_documents(documents)
    reference, start, total = {}, 0, 0
    for name in MEANING_FIELDS:
        document = documents[name]
        raw = _utf16_bytes(document["utf16le_hex"])
        chunks = 0 if not raw else (len(raw) + MAX_EDITOR_CHUNK_BYTES - 1) // MAX_EDITOR_CHUNK_BYTES
        reference[name] = {"document_id": document["document_id"],
            "document_revision": document["document_revision"],
            "cursor_position": document["cursor_position"], "anchor_position": document["anchor_position"],
            "utf16_bytes": len(raw), "raw_commitment": _document_commitment(raw),
            "chunk_start": start, "chunk_count": chunks}
        start += chunks
        total += len(raw)
    body = {"basis_revision": basis_revision, "widget_revision": widget_revision,
            "documents": reference, "chunk_count": start, "utf16_bytes": total}
    value = {"profile": EDITOR_REFERENCE_PROFILE, **body,
             "capture_commitment": _digest(b"CETA:task-editor-reference-capture:v1\0",
                                           canonical_bytes(body))}
    return _reference_payload(value)


def editor_payload_wire(*, basis_revision, widget_revision, documents):
    """Build an inline payload when bounded, otherwise an opaque raw reference."""
    _source_documents(documents)
    total = sum(len(_utf16_bytes(item["utf16le_hex"])) for item in documents.values())
    if (total <= MAX_EDITOR_UTF16_BYTES and all(len(_utf16_bytes(item["utf16le_hex"])) <= MAX_UTF16_BYTES
                                                 for item in documents.values())):
        value = {"profile": EDITOR_PAYLOAD_PROFILE, "basis_revision": basis_revision,
                 "widget_revision": widget_revision, "documents": documents}
    else:
        value = _reference_value(basis_revision=basis_revision, widget_revision=widget_revision,
                                 documents=documents)
    _payload(value)
    wire = canonical_bytes(value)
    decode_editor_payload(wire)
    return wire


def decode_editor_payload(wire):
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_WIRE_BYTES, "EDITOR_PAYLOAD_BYTES")
    value = _payload(strict_loads(wire))
    require(canonical_bytes(value) == wire, "EDITOR_PAYLOAD_CANONICAL")
    return value


def editor_payload_matches_documents(payload, documents):
    """Compare raw local ownership to an inline or reference payload exactly."""
    value = _payload(payload)
    _source_documents(documents)
    candidate = decode_editor_payload(editor_payload_wire(
        basis_revision=value["basis_revision"], widget_revision=value["widget_revision"], documents=documents))
    return canonical_bytes(candidate) == canonical_bytes(value)


def editor_chunk_wire(*, capture_commitment, chunk_index, chunk_count, document,
                      document_offset, raw):
    value = {"profile": EDITOR_CHUNK_PROFILE, "capture_commitment": capture_commitment,
        "chunk_index": chunk_index, "chunk_count": chunk_count, "document": document,
        "document_offset": document_offset, "utf16le_hex": raw.hex(),
        "chunk_commitment": _chunk_commitment(capture_commitment, chunk_index, document,
                                              document_offset, raw)}
    wire = canonical_bytes(value)
    decode_editor_chunk(wire)
    return wire


def decode_editor_chunk(wire):
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_WIRE_BYTES, "EDITOR_CHUNK_WIRE")
    value = strict_loads(wire)
    require(type(value) is dict and set(value) == CHUNK_FIELDS and value["profile"] == EDITOR_CHUNK_PROFILE
        and canonical_bytes(value) == wire, "EDITOR_CHUNK_SHAPE")
    commitment(value["capture_commitment"])
    commitment(value["chunk_commitment"])
    require(type(value["chunk_index"]) is int and 0 <= value["chunk_index"] < MAX_EDITOR_CHUNKS
        and type(value["chunk_count"]) is int and 1 <= value["chunk_count"] <= MAX_EDITOR_CHUNKS
        and value["chunk_index"] < value["chunk_count"], "EDITOR_CHUNK_INDEX")
    require(type(value["document"]) is str and value["document"] in MEANING_FIELDS
        and type(value["document_offset"]) is int and 0 <= value["document_offset"] <= MAX_EDITOR_DOCUMENT_UTF16_BYTES
        and value["document_offset"] % 2 == 0, "EDITOR_CHUNK_DOCUMENT")
    raw = _hex_bytes(value["utf16le_hex"], "EDITOR_CHUNK_ENCODING", MAX_EDITOR_CHUNK_BYTES)
    require(1 <= len(raw) <= MAX_EDITOR_CHUNK_BYTES
        and value["chunk_commitment"] == _chunk_commitment(value["capture_commitment"],
            value["chunk_index"], value["document"], value["document_offset"], raw),
        "EDITOR_CHUNK_COMMITMENT")
    return value


def editor_payload_chunk_wires(payload, documents):
    """Turn exact local raw documents into deterministic bounded chunk wires."""
    value = _payload(payload)
    require(value["profile"] == EDITOR_REFERENCE_PROFILE, "EDITOR_CHUNKS_REFERENCE_REQUIRED")
    require(editor_payload_matches_documents(value, documents), "EDITOR_CHUNK_SOURCE_MISMATCH")
    wires = []
    for name in MEANING_FIELDS:
        document, facts = value["documents"][name], documents[name]
        raw = _utf16_bytes(facts["utf16le_hex"])
        for local_index in range(document["chunk_count"]):
            offset = local_index * MAX_EDITOR_CHUNK_BYTES
            piece = raw[offset:offset + MAX_EDITOR_CHUNK_BYTES]
            wires.append(editor_chunk_wire(capture_commitment=value["capture_commitment"],
                chunk_index=document["chunk_start"] + local_index, chunk_count=value["chunk_count"],
                document=name, document_offset=offset, raw=piece))
    require(len(wires) == value["chunk_count"], "EDITOR_CHUNK_COUNT")
    return tuple(wires)


def validate_editor_chunk(payload, chunk):
    """Bind a bounded raw chunk to one exact referenced capture location."""
    reference = _payload(payload)
    require(reference["profile"] == EDITOR_REFERENCE_PROFILE, "EDITOR_CHUNK_REFERENCE_REQUIRED")
    value = decode_editor_chunk(chunk) if type(chunk) is bytes else chunk
    require(type(value) is dict, "EDITOR_CHUNK_SHAPE")
    require(value["capture_commitment"] == reference["capture_commitment"]
        and value["chunk_count"] == reference["chunk_count"], "EDITOR_CHUNK_CAPTURE")
    document = reference["documents"][value["document"]]
    index = value["chunk_index"]
    require(document["chunk_start"] <= index < document["chunk_start"] + document["chunk_count"],
            "EDITOR_CHUNK_DOCUMENT_INDEX")
    local_index = index - document["chunk_start"]
    raw = _hex_bytes(value["utf16le_hex"], "EDITOR_CHUNK_ENCODING", MAX_EDITOR_CHUNK_BYTES)
    require(value["document_offset"] == local_index * MAX_EDITOR_CHUNK_BYTES
        and value["document_offset"] + len(raw) <= document["utf16_bytes"]
        and (local_index + 1 == document["chunk_count"] or len(raw) == MAX_EDITOR_CHUNK_BYTES),
        "EDITOR_CHUNK_OFFSET")
    return value


def materialize_editor_payload(payload, chunks):
    """Reassemble a retained reference only after every bound chunk is present."""
    reference = _payload(payload)
    require(reference["profile"] == EDITOR_REFERENCE_PROFILE
        and type(chunks) in {tuple, list}, "EDITOR_MATERIALIZE_REQUIRED")
    require(len(chunks) == reference["chunk_count"], "EDITOR_MATERIALIZE_COUNT")
    decoded = [validate_editor_chunk(reference, item) for item in chunks]
    require([item["chunk_index"] for item in decoded] == list(range(reference["chunk_count"])),
            "EDITOR_MATERIALIZE_ORDER")
    documents = {}
    for name in MEANING_FIELDS:
        metadata = reference["documents"][name]
        pieces = [item for item in decoded if item["document"] == name]
        require(len(pieces) == metadata["chunk_count"], "EDITOR_MATERIALIZE_DOCUMENT")
        raw = b"".join(bytes.fromhex(item["utf16le_hex"]) for item in pieces)
        require(len(raw) == metadata["utf16_bytes"] and _document_commitment(raw) == metadata["raw_commitment"],
                "EDITOR_MATERIALIZE_COMMITMENT")
        documents[name] = {"document_id": metadata["document_id"], "utf16le_hex": raw.hex(),
            "document_revision": metadata["document_revision"],
            "cursor_position": metadata["cursor_position"], "anchor_position": metadata["anchor_position"]}
    _source_documents(documents)
    return {"basis_revision": reference["basis_revision"], "widget_revision": reference["widget_revision"],
            "documents": documents}


def editor_documents_as_text(documents):
    """Decode an inline/materialized document map without losing source facts."""
    _source_documents(documents)
    return {name: {"text": utf16_text_value(document["utf16le_hex"]),
        **{key: document[key] for key in ("document_id", "document_revision",
                                           "cursor_position", "anchor_position")}}
        for name, document in documents.items()}


def recovery_key(scope_id, task_id):
    return logical_key("projection", scope_id, "task-editor", task_id)


def editor_chunk_key(scope_id, task_id, capture, index):
    commitment(capture)
    require(type(index) is int and 0 <= index < MAX_EDITOR_CHUNKS, "EDITOR_CHUNK_INDEX")
    identifier(task_id)
    digest = hashlib.sha256((task_id + "\0" + capture + "\0" + str(index)).encode("ascii")).hexdigest()
    return logical_key("projection", scope_id, "task-editor-chunk", digest)


def recovery_commitment(wire):
    decode_editor_snapshot(wire)
    return _digest(b"CETA:task-editor-recovery:v1\0", wire)


def _lineage(value, payload, previous):
    # Earlier v1 retained records predate the explicit observation field. They
    # remain decodable as exact historic wires; the next mutation emits the
    # complete current lineage rather than silently rewriting the old record.
    require(type(value) is dict and set(value) in {LINEAGE_FIELDS, LEGACY_LINEAGE_FIELDS},
            "EDITOR_LINEAGE_SHAPE")
    for name in ("task_basis_revision", "original_instruction_commitment",
                 "corrected_task_revision", "recovery_capture_commitment"):
        commitment(value[name])
    if "observed_task_revision" in value:
        commitment(value["observed_task_revision"])
    proposed = value["proposed_meaning_commitment"]
    require(proposed is None or (type(proposed) is str and commitment(proposed) is None),
            "EDITOR_LINEAGE_PROPOSAL")
    require(value["recovery_capture_commitment"] == payload_capture_commitment(payload)
        and value["prior_recovery_revision"] == previous, "EDITOR_LINEAGE_BINDING")


def _disposition(value, payload, previous, request_commitment, state):
    if state != "DISCARDED":
        require(value is None, "EDITOR_DISPOSITION_UNEXPECTED")
        return
    require(type(value) is dict and set(value) == DISPOSITION_FIELDS
        and value["kind"] == "EXPLICIT_DISCARD", "EDITOR_DISPOSITION_SHAPE")
    for name in ("discarded_capture_commitment", "consent_request_commitment",
                 "predecessor_recovery_revision"):
        commitment(value[name])
    require(value["discarded_capture_commitment"] == payload_capture_commitment(payload)
        and value["consent_request_commitment"] == request_commitment
        and value["predecessor_recovery_revision"] == previous, "EDITOR_DISPOSITION_BINDING")


def decode_editor_snapshot(wire):
    require(type(wire) is bytes and 1 <= len(wire) <= MAX_WIRE_BYTES, "EDITOR_SNAPSHOT_BYTES")
    value = strict_loads(wire)
    require(type(value) is dict and set(value) == EDITOR_FIELDS and value["profile"] == EDITOR_PROFILE
        and type(value["state"]) is str and value["state"] in {"STAGING", "RETAINED", "DISCARDED"}
        and canonical_bytes(value) == wire, "EDITOR_SNAPSHOT_SHAPE")
    for name in ("scope_id", "task_id", "principal_id", "updated_session", "request_id", "event_id",
                 "observation_id"):
        identifier(value[name])
    for name in ("owner_binding", "request_commitment"):
        commitment(value[name])
    require(type(value["generation"]) is int and 1 <= value["generation"] <= MAX_EDITOR_REVISION,
            "EDITOR_GENERATION")
    previous = value["previous_recovery_revision"]
    require((value["generation"] == 1) == (previous is None), "EDITOR_RECOVERY_PREDECESSOR")
    if previous is not None:
        commitment(previous)
    _revision(value["event_sequence"], "EDITOR_EVENT_SEQUENCE")
    if value["previous_head"] is not None:
        commitment(value["previous_head"])
    require((value["event_sequence"] == 0) == (value["previous_head"] is None),
            "EDITOR_EVENT_PREDECESSOR")
    payload = _payload(value["payload"])
    require(type(value["staged_chunk_count"]) is int and 0 <= value["staged_chunk_count"] <= MAX_EDITOR_CHUNKS,
            "EDITOR_STAGED_CHUNKS")
    if payload["profile"] == EDITOR_PAYLOAD_PROFILE:
        require(value["state"] != "STAGING" and value["staged_chunk_count"] == 0, "EDITOR_INLINE_STATE")
    else:
        chunks = payload["chunk_count"]
        require(value["staged_chunk_count"] <= chunks, "EDITOR_STAGED_CHUNKS")
        if value["state"] == "STAGING":
            require(1 <= value["staged_chunk_count"] < chunks, "EDITOR_STAGING_STATE")
        else:
            require(value["staged_chunk_count"] == chunks, "EDITOR_REFERENCE_COMPLETION")
    require(value["state"] != "DISCARDED" or value["generation"] > 1,
            "EDITOR_DISCARD_WITHOUT_RETENTION")
    _lineage(value["lineage"], payload, previous)
    _disposition(value["disposition"], payload, previous, value["request_commitment"], value["state"])
    return value

