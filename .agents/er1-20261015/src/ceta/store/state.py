"""Versioned transaction provenance and reconstructable cells in the same DB.

This is storage mechanics. Kernel event/transition reducers, positive authority,
and provenance for budget/reservation/intent/projection values remain unqualified.
"""
import hashlib
import re

from ceta.contracts.store_transactions import (StoreCell, StoreKey, StorePosition,
    MAX_GENERATION, STORE_PROFILE, identifier, commitment)
from ceta.contracts.wire import ContractError, canonical_bytes, strict_loads

SCHEMA = {
    "store_commits": "CREATE TABLE store_commits (sequence INTEGER PRIMARY KEY, commit_wire BLOB NOT NULL, head TEXT NOT NULL)",
    "store_changes": "CREATE TABLE store_changes (commit_sequence INTEGER NOT NULL, change_index INTEGER NOT NULL, value_wire BLOB, PRIMARY KEY(commit_sequence,change_index), FOREIGN KEY(commit_sequence) REFERENCES store_commits(sequence))",
    "store_cells": "CREATE TABLE store_cells (collection TEXT NOT NULL, scope_id TEXT NOT NULL, record_id TEXT NOT NULL, generation INTEGER NOT NULL, value_wire BLOB, revision TEXT NOT NULL, PRIMARY KEY(collection,scope_id,record_id), FOREIGN KEY(scope_id) REFERENCES history_scopes(scope_id))",
}
_RECORD_TYPES = {"grant": "StandingGrant", "permit": "OperationPermit", "queue": "QueueItem"}
_DIGEST = re.compile(r"[0-9a-f]{64}")


def digest(wire):
    return hashlib.sha256(wire).hexdigest()


def head(wire):
    return "sha256:" + digest(b"CETA:store-transaction:v2\0" + wire)


class TransactionState:
    def __init__(self, connection, codec, scopes):
        self.connection, self.codec, self.scopes = connection, codec, scopes

    def _value(self, cell, event_payload=None):
        if cell.key.scope_id not in self.scopes:
            raise ContractError("STORE_SCOPE_NOT_REGISTERED")
        if cell.value_wire is not None and cell.key.collection in _RECORD_TYPES:
            record = self.codec.decode(cell.value_wire)
            if (record.record_type != _RECORD_TYPES[cell.key.collection]
                    or record.record_id != cell.key.record_id
                    or record.as_dict()["scope_id"] != cell.key.scope_id):
                raise ContractError("STORE_RECORD_KEY_MISMATCH")
            if event_payload is not None and self.codec.decode(event_payload).canonical_wire != cell.value_wire:
                raise ContractError("STORE_EVENT_VALUE_MISMATCH")

    def read(self, key):
        row = self.connection.execute("SELECT generation,value_wire,revision FROM store_cells WHERE collection=? AND scope_id=? AND record_id=?",
            (key.collection, key.scope_id, key.record_id)).fetchone()
        if row is None:
            return StoreCell(key, 0, None)
        cell = StoreCell(key, row[0], row[1])
        if cell.revision != row[2]:
            raise ContractError("STORE_CELL_REVISION_MISMATCH")
        return cell

    def position(self):
        row = self.connection.execute("SELECT sequence,head FROM store_commits ORDER BY sequence DESC LIMIT 1").fetchone()
        return StorePosition(0, None) if row is None else StorePosition(row[0] + 1, row[1])

    def verify(self, checkpoint=None):
        if checkpoint is not None and type(checkpoint) is not StorePosition:
            raise ContractError("STORE_CHECKPOINT_REQUIRED")
        position, cells, seen, total_changes = StorePosition(0, None), {}, set(), 0
        next_event = {scope: 0 for scope in self.scopes}
        matched = checkpoint is None or checkpoint == position
        for sequence, wire, stored_head in self.connection.execute("SELECT sequence,commit_wire,head FROM store_commits ORDER BY sequence"):
            if type(wire) is not bytes or sequence != position.next_commit or head(wire) != stored_head:
                raise ContractError("STORE_TRANSACTION_PREFIX_MISMATCH")
            value = strict_loads(wire)
            if (type(value) is not dict or set(value) != {"profile", "sequence", "previous_head", "events", "checks", "changes"}
                    or canonical_bytes(value) != wire or value["profile"] != STORE_PROFILE
                    or type(value["sequence"]) is not int or not 0 <= value["sequence"] <= MAX_GENERATION
                    or value["sequence"] != sequence or value["previous_head"] != position.head
                    or type(value["events"]) is not list or not 1 <= len(value["events"]) <= 128
                    or type(value["checks"]) is not list or len(value["checks"]) > 128
                    or type(value["changes"]) is not list or len(value["changes"]) > 128):
                raise ContractError("STORE_TRANSACTION_METADATA_INVALID")
            events = {}
            for event in value["events"]:
                if type(event) is not dict or set(event) != {"scope_id", "sequence", "event_id", "event_sha256", "payload_sha256"}:
                    raise ContractError("STORE_EVENT_ASSOCIATION_INVALID")
                identifier(event["scope_id"])
                identifier(event["event_id"])
                if (event["scope_id"] not in next_event or type(event["sequence"]) is not int
                        or not 0 <= event["sequence"] <= MAX_GENERATION
                        or any(type(event[field]) is not str or not _DIGEST.fullmatch(event[field])
                               for field in ("event_sha256", "payload_sha256"))):
                    raise ContractError("STORE_EVENT_ASSOCIATION_INVALID")
                if event["sequence"] != next_event[event["scope_id"]]:
                    raise ContractError("STORE_EVENT_ORDER_MISMATCH")
                next_event[event["scope_id"]] += 1
                identity = (event["scope_id"], event["event_id"])
                if identity in seen:
                    raise ContractError("STORE_EVENT_ASSOCIATION_DUPLICATE")
                row = self.connection.execute("SELECT sequence,event_wire,payload_wire FROM history_events WHERE scope_id=? AND event_id=?", identity).fetchone()
                if row is None or row[0] != event["sequence"] or digest(row[1]) != event["event_sha256"] or digest(row[2]) != event["payload_sha256"]:
                    raise ContractError("STORE_EVENT_ASSOCIATION_MISMATCH")
                seen.add(identity)
                events[identity] = row[2]
            checked = set()
            for check in value["checks"]:
                if type(check) is not dict or set(check) != {"collection", "scope_id", "record_id", "revision"}:
                    raise ContractError("STORE_CHECK_METADATA_INVALID")
                key = StoreKey(check["collection"], check["scope_id"], check["record_id"])
                commitment(check["revision"])
                if key.scope_id not in self.scopes or key in checked or cells.get(key, StoreCell(key, 0, None)).revision != check["revision"]:
                    raise ContractError("STORE_RECORDED_READ_CONFLICT")
                checked.add(key)
            rows = self.connection.execute("SELECT change_index,value_wire FROM store_changes WHERE commit_sequence=? ORDER BY change_index", (sequence,)).fetchall()
            if [row[0] for row in rows] != list(range(len(value["changes"]))):
                raise ContractError("STORE_CHANGE_ASSOCIATION_MISMATCH")
            changed = set()
            for index, change in enumerate(value["changes"]):
                if type(change) is not dict or set(change) != {"collection", "scope_id", "record_id", "before_revision", "generation", "value_sha256", "event_id"}:
                    raise ContractError("STORE_CHANGE_METADATA_INVALID")
                key = StoreKey(change["collection"], change["scope_id"], change["record_id"])
                commitment(change["before_revision"])
                identifier(change["event_id"])
                before = cells.get(key, StoreCell(key, 0, None))
                wire_value = rows[index][1]
                if (wire_value is not None and type(wire_value) is not bytes
                        or key in changed or change["before_revision"] != before.revision
                        or type(change["generation"]) is not int or change["generation"] != before.generation + 1
                        or change["value_sha256"] != (None if wire_value is None else digest(wire_value))
                        or (key.scope_id, change["event_id"]) not in events
                        or before.generation == 0 and wire_value is None):
                    raise ContractError("STORE_RECONSTRUCTION_MISMATCH")
                cell = StoreCell(key, change["generation"], wire_value)
                self._value(cell, events[(key.scope_id, change["event_id"])])
                cells[key] = cell
                changed.add(key)
            total_changes += len(rows)
            position = StorePosition(sequence + 1, stored_head)
            if checkpoint == position:
                matched = True
        if not matched:
            raise ContractError("STORE_CHECKPOINT_MISMATCH")
        if self.connection.execute("SELECT count(*) FROM history_events").fetchone()[0] != len(seen):
            raise ContractError("STORE_UNASSOCIATED_EVENT")
        if self.connection.execute("SELECT count(*) FROM store_changes").fetchone()[0] != total_changes:
            raise ContractError("STORE_UNASSOCIATED_CHANGE")
        actual = {}
        for collection, scope, record_id, generation, wire, revision in self.connection.execute("SELECT * FROM store_cells"):
            cell = StoreCell(StoreKey(collection, scope, record_id), generation, wire)
            if cell.revision != revision or generation == 0:
                raise ContractError("STORE_CELL_REVISION_MISMATCH")
            actual[cell.key] = cell
        if actual != cells:
            raise ContractError("STORE_PROJECTION_DIVERGENCE")
        return position

    def insert(self, entries, checks, changes):
        # Caller already holds the sole SQLite write transaction and validated
        # both prefixes. Never wait on human/model/process activity here.
        checked = {}
        for check in (*checks, *(change.expected for change in changes)):
            if check.key.scope_id not in self.scopes:
                raise ContractError("STORE_SCOPE_NOT_REGISTERED")
            if check.key in checked and checked[check.key] != check.revision:
                raise ContractError("STORE_EXPECTATION_CONFLICT")
            checked[check.key] = check.revision
            if self.read(check.key).revision != check.revision:
                raise ContractError("STORE_REVISION_CONFLICT")
        batch_events = {}
        event_refs = []
        for entry, event in entries:
            value = event.record.as_dict()
            identity = (value["scope_id"], event.record.record_id)
            batch_events[identity] = entry.payload_wire
            event_refs.append({"scope_id": value["scope_id"], "sequence": value["sequence"],
                "event_id": event.record.record_id, "event_sha256": digest(entry.event_wire), "payload_sha256": digest(entry.payload_wire)})
        cells, metadata = [], []
        for change in changes:
            key = change.expected.key
            if (key.scope_id, change.event_id) not in batch_events:
                raise ContractError("STORE_CHANGE_EVENT_REQUIRED")
            before = self.read(key)
            if before.generation == MAX_GENERATION:
                raise ContractError("STORE_GENERATION_EXHAUSTED")
            if before.generation == 0 and change.value_wire is None:
                raise ContractError("STORE_ABSENT_DELETE_REJECTED")
            cell = StoreCell(key, before.generation + 1, change.value_wire)
            self._value(cell, batch_events[(key.scope_id, change.event_id)])
            cells.append(cell)
            metadata.append({**key.as_dict(), "before_revision": before.revision, "generation": cell.generation,
                "value_sha256": None if cell.value_wire is None else digest(cell.value_wire), "event_id": change.event_id})
        position = self.position()
        value = {"profile": STORE_PROFILE, "sequence": position.next_commit, "previous_head": position.head,
            "events": event_refs, "checks": [{**key.as_dict(), "revision": revision} for key, revision in sorted(checked.items())
                                               if key not in {change.expected.key for change in changes}],
            "changes": metadata}
        wire = canonical_bytes(value)
        new_head = head(wire)
        self.connection.execute("INSERT INTO store_commits VALUES(?,?,?)", (position.next_commit, wire, new_head))
        for index, cell in enumerate(cells):
            self.connection.execute("INSERT INTO store_changes VALUES(?,?,?)", (position.next_commit, index, cell.value_wire))
            self.connection.execute("INSERT INTO store_cells VALUES(?,?,?,?,?,?) ON CONFLICT(collection,scope_id,record_id) DO UPDATE SET generation=excluded.generation,value_wire=excluded.value_wire,revision=excluded.revision",
                (cell.key.collection, cell.key.scope_id, cell.key.record_id, cell.generation, cell.value_wire, cell.revision))
        return StorePosition(position.next_commit + 1, new_head), tuple(cells)
