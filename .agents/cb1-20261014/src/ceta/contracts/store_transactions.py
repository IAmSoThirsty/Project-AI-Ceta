"""Owner-internal atomic store values; no admitted wire type or authority verdict."""
from dataclasses import dataclass
import hashlib
import re
from typing import Protocol, Callable

from .events import StreamPosition
from .history import JournalCommit, JournalEntry
from .wire import ContractError, MAX_WIRE_BYTES, canonical_bytes, strict_loads

STORE_PROFILE = "ceta-sqlite-store-v2"
COLLECTIONS = frozenset(("grant", "budget", "reservation", "permit", "intent", "queue", "projection"))
MAX_BATCH = 128
MAX_GENERATION = 2**53 - 1
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}")
_HASH = re.compile(r"sha256:[0-9a-f]{64}")


def identifier(value):
    if type(value) is not str or not _IDENTIFIER.fullmatch(value):
        raise ContractError("STORE_IDENTIFIER_INVALID")


def commitment(value):
    if type(value) is not str or not _HASH.fullmatch(value):
        raise ContractError("STORE_COMMITMENT_INVALID")


@dataclass(frozen=True, order=True)
class StoreKey:
    collection: str
    scope_id: str
    record_id: str

    def __post_init__(self):
        if type(self.collection) is not str or self.collection not in COLLECTIONS:
            raise ContractError("STORE_COLLECTION_UNSUPPORTED")
        identifier(self.scope_id)
        identifier(self.record_id)

    def as_dict(self):
        return {"collection": self.collection, "scope_id": self.scope_id, "record_id": self.record_id}


@dataclass(frozen=True)
class StoreCell:
    key: StoreKey
    generation: int
    value_wire: bytes | None

    def __post_init__(self):
        if type(self.key) is not StoreKey:
            raise ContractError("STORE_KEY_REQUIRED")
        if type(self.generation) is not int or not 0 <= self.generation <= MAX_GENERATION:
            raise ContractError("STORE_GENERATION_INVALID")
        if self.generation == 0 and self.value_wire is not None:
            raise ContractError("STORE_ABSENCE_INVALID")
        if self.value_wire is not None:
            if type(self.value_wire) is not bytes or not 1 <= len(self.value_wire) <= MAX_WIRE_BYTES:
                raise ContractError("STORE_VALUE_BYTES_REQUIRED")
            value = strict_loads(self.value_wire)
            if type(value) is not dict or canonical_bytes(value) != self.value_wire:
                raise ContractError("STORE_CANONICAL_OBJECT_REQUIRED")

    @property
    def revision(self):
        body = {**self.key.as_dict(), "generation": self.generation,
                "value_sha256": None if self.value_wire is None else hashlib.sha256(self.value_wire).hexdigest()}
        return "sha256:" + hashlib.sha256(b"CETA:store-cell:v2\0" + canonical_bytes(body)).hexdigest()


@dataclass(frozen=True)
class StoreExpectation:
    key: StoreKey
    revision: str

    def __post_init__(self):
        if type(self.key) is not StoreKey:
            raise ContractError("STORE_KEY_REQUIRED")
        commitment(self.revision)


@dataclass(frozen=True)
class StoreChange:
    expected: StoreExpectation
    value_wire: bytes | None
    event_id: str

    def __post_init__(self):
        if type(self.expected) is not StoreExpectation:
            raise ContractError("STORE_EXPECTATION_REQUIRED")
        identifier(self.event_id)
        # Validate shape/immutability before any transaction, without selecting
        # a generation or interpreting a model-authored status as authority.
        StoreCell(self.expected.key, 1, self.value_wire)


@dataclass(frozen=True)
class StorePosition:
    next_commit: int
    head: str | None

    def __post_init__(self):
        if type(self.next_commit) is not int or not 0 <= self.next_commit <= MAX_GENERATION:
            raise ContractError("STORE_POSITION_INVALID")
        if (self.next_commit == 0) != (self.head is None):
            raise ContractError("STORE_GENESIS_INVALID")
        if self.head is not None:
            commitment(self.head)


@dataclass(frozen=True)
class StoreCommit:
    history: tuple[JournalCommit, ...]
    position: StorePosition
    cells: tuple[StoreCell, ...]

    def __post_init__(self):
        if (type(self.history) is not tuple or not 1 <= len(self.history) <= MAX_BATCH
                or any(type(item) is not JournalCommit for item in self.history)
                or type(self.position) is not StorePosition or self.position.next_commit == 0
                or type(self.cells) is not tuple or len(self.cells) > MAX_BATCH
                or any(type(cell) is not StoreCell for cell in self.cells)
                or len({cell.key for cell in self.cells}) != len(self.cells)):
            raise ContractError("STORE_COMMIT_RESULT_INVALID")
        scopes = set()
        for item in self.history:
            if (type(item.before) is not StreamPosition or type(item.after) is not StreamPosition
                    or item.before.scope_id != item.after.scope_id or item.before.scope_id in scopes
                    or type(item.event_ids) is not tuple or not 1 <= len(item.event_ids) <= MAX_BATCH
                    or any(type(event_id) is not str for event_id in item.event_ids)
                    or item.after.next_sequence - item.before.next_sequence != len(item.event_ids)
                    or len(set(item.event_ids)) != len(item.event_ids)):
                raise ContractError("STORE_COMMIT_RESULT_INVALID")
            for event_id in item.event_ids:
                identifier(event_id)
            scopes.add(item.before.scope_id)


class AtomicStorePort(Protocol):
    """Internal sole-owner port; no IPC dispatcher or effect admission API."""

    def commit(self, expected: tuple[StreamPosition, ...], entries: tuple[JournalEntry, ...], *,
               checks: tuple[StoreExpectation, ...] = (), changes: tuple[StoreChange, ...] = (),
               checkpoints: tuple[StreamPosition, ...] = (),
               state_checkpoint: StorePosition | None = None,
               guard: Callable[[], None] | None = None) -> StoreCommit: ...
    def snapshot(self, keys: tuple[StoreKey, ...], *,
                 state_checkpoint: StorePosition | None = None) -> tuple[StoreCell, ...]: ...
    def store_position(self) -> StorePosition: ...
