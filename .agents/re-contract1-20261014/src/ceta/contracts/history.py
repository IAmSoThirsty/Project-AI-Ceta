"""Immutable persistence ports; none of these objects establishes authority."""
from dataclasses import dataclass
from typing import Protocol

from .events import StreamPosition
from .wire import ContractError, MAX_WIRE_BYTES


@dataclass(frozen=True)
class JournalEntry:
    event_wire: bytes
    payload_wire: bytes

    def __post_init__(self):
        for wire in (self.event_wire, self.payload_wire):
            if type(wire) is not bytes or not 1 <= len(wire) <= MAX_WIRE_BYTES:
                raise ContractError("JOURNAL_ENTRY_BYTES_REQUIRED")


@dataclass(frozen=True)
class JournalCommit:
    before: StreamPosition
    after: StreamPosition
    event_ids: tuple[str, ...]


class HistoryPort(Protocol):
    """Called by the eventual sole trusted writer; not an IPC dispatch surface."""

    def position(self, scope_id: str) -> StreamPosition: ...
    def append(self, expected: StreamPosition, entries: tuple[JournalEntry, ...], *,
               checkpoints: tuple[StreamPosition, ...] = ()) -> JournalCommit: ...
    def validate(self, checkpoints: tuple[StreamPosition, ...] = ()) -> tuple[StreamPosition, ...]: ...
    def replay(self, scope_id: str, start: int = 0, limit: int = 128, *,
               checkpoints: tuple[StreamPosition, ...] = ()) -> tuple[JournalEntry, ...]: ...
