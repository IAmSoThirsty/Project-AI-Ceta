"""Revision-bound, unaccepted interpretation proposals; never positive authority."""
import hashlib

from .kernel_transactions import require, logical_key
from .store_transactions import commitment, identifier
from .wire import canonical_bytes, strict_loads

MEANING_PROFILE = "ceta-task-meaning-v1"
MEANING_COMMAND_PROFILE = "ceta-task-command-v2"
MEANING_RESULT_PROFILE = "ceta-task-meaning-result-v1"
MEANING_FIELDS = ("clarified_meaning", "scope", "exclusions", "completion_predicates",
    "assumptions", "unresolved_questions", "standing_instructions", "authority", "budgets", "evidence")
MEANING_OPERATIONS = {"task.meaning_propose": "meaning_propose", "task.meaning_load": "meaning_load"}
PROPOSAL_FIELDS = {"profile", "state", "scope_id", "task_id", "owner_binding", "principal_id",
    "updated_session", "basis_revision", "task_objective_revision", "title_hex", "instruction_hex", "draft_hex",
    "meaning", "generation", "request_id", "request_commitment", "event_id", "event_sequence",
    "previous_head", "observation_id"}

def meaning_key(scope_id, task_id):
    return logical_key("projection", scope_id, "task-meaning", task_id)

def meaning_commitment(wire):
    return "sha256:" + hashlib.sha256(b"CETA:task-meaning:v1\0" + wire).hexdigest()

def _text(value, maximum):
    require(type(value) is str and len(value) <= maximum * 2 and len(value) % 2 == 0
        and all(c in "0123456789abcdef" for c in value), "MEANING_TEXT_ENCODING")
    try: return bytes.fromhex(value).decode("utf8")
    except UnicodeError: require(False, "MEANING_TEXT_ENCODING")

def decode_meaning(value):
    require(type(value) is dict and set(value) == set(MEANING_FIELDS), "MEANING_FIELDS")
    for text in value.values(): _text(text, 16384)
    require(sum(len(text) // 2 for text in value.values()) <= 65536, "MEANING_TOTAL_SIZE")
    require(bool(_text(value["clarified_meaning"], 16384).strip())
        and bool(_text(value["scope"], 16384).strip()), "MEANING_OBJECTIVE_SCOPE_REQUIRED")
    return value

def meaning_from_text(values):
    require(type(values) is dict and set(values) == set(MEANING_FIELDS)
        and all(type(text) is str for text in values.values()), "MEANING_FIELDS")
    try: result = {name: text.encode("utf8").hex() for name, text in values.items()}
    except UnicodeError: require(False, "MEANING_TEXT_ENCODING")
    return decode_meaning(result)

def meaning_as_text(values):
    decode_meaning(values)
    return {name: _text(text, 16384) for name, text in values.items()}

def decode_proposal(wire):
    require(type(wire) is bytes, "MEANING_PROPOSAL_REQUIRED")
    value = strict_loads(wire)
    require(type(value) is dict and set(value) == PROPOSAL_FIELDS
        and value["profile"] == MEANING_PROFILE and value["state"] == "UNACCEPTED"
        and canonical_bytes(value) == wire, "MEANING_PROPOSAL_SHAPE")
    for name in ("scope_id", "task_id", "principal_id", "updated_session", "request_id", "event_id", "observation_id"):
        identifier(value[name])
    for name in ("owner_binding", "basis_revision", "task_objective_revision", "request_commitment"):
        commitment(value[name])
    require(type(value["generation"]) is int and 1 <= value["generation"] < 2**53, "MEANING_GENERATION")
    require(type(value["event_sequence"]) is int and 0 <= value["event_sequence"] < 2**53, "MEANING_EVENT_SEQUENCE")
    if value["previous_head"] is not None: commitment(value["previous_head"])
    require((value["event_sequence"] == 0) == (value["previous_head"] is None), "MEANING_EVENT_PREDECESSOR")
    require(bool(_text(value["title_hex"], 256).strip()) and bool(_text(value["instruction_hex"], 65536).strip()), "MEANING_RAW_CONTENT")
    _text(value["draft_hex"], 65536); decode_meaning(value["meaning"])
    return value
