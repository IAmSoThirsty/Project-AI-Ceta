"""CMP03 reference views: independent oracles over real owned SQLite prefixes.

Task cases call the existing TaskDrafts producer with the explicitly synthetic
message identity fixture. Kernel cases call the actual kernel, then explicitly
normalize only sequence/previous_head on its output entries to build a genesis
reference fixture: the kernel seed contains an unsupported ActionProposal.
Those normalized entries are not represented as the original accepted prefix.
Memory/effect records are labelled shape fixtures, never authority or deletion
observations. No protected identity, effect settlement, production acceptance,
independent administration domain or original B-case qualification is asserted.
All scratch roots are fresh T: CETA paths and remain available after failures.
"""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from ceta.contracts.events import EventContract, StreamPosition
from ceta.contracts.history import JournalEntry
from ceta.contracts.store_transactions import STORE_PROFILE
from ceta.contracts.wire import (ContractError, MAX_WIRE_BYTES, PROFILE,
    RecordCodec, canonical_bytes, strict_loads)
from ceta.store.journal import SqliteJournal
from ceta.store.projections import (MAX_PROJECTION_BYTES, MAX_PROJECTION_EVENTS,
    PROJECTION_PROFILE, MemoryReference, ProjectedRecord, ProjectionReducer,
    ProjectionRegistration, ProjectionSnapshot)
import test_kernel_transactions as kernel_infrastructure
import test_task_drafts as task_infrastructure
from test_all_records import example

SCOPE = kernel_infrastructure.PROJECT
OTHER_SCOPE = kernel_infrastructure.INSTALLATION
TASK = "task:projection-custody"
STAMP = "2026-10-11T18:00:00Z"
HASH = "sha256:" + "9" * 64


class ProjectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())

    def setUp(self):
        self.codec = RecordCodec(deepcopy(self.schema))
        self.events = EventContract(self.codec)
        self.reducer = ProjectionReducer(self.codec)
        self.stores, self.fixtures = [], []

    def tearDown(self):
        for fixture in self.fixtures:
            fixture.store.close()
        for store in self.stores:
            store.close()

    def reject(self, call, code=None):
        with self.assertRaises(ContractError) as caught:
            call()
        if code is not None:
            self.assertEqual(caught.exception.code, code)
        return caught.exception

    def value(self, record_type, record_id, *, scope=SCOPE, **changes):
        result = example(self.schema["$defs"][record_type])
        result.update(record_id=record_id, scope_id=scope, **changes)
        return result

    def row(self, value, event_type="observation.accepted", *, point=None,
            event_id=None, actor="observer:projection-fixture", raw=None, **event_changes):
        point = StreamPosition(value["scope_id"], 0, None) if point is None else point
        payload = canonical_bytes(value) if raw is None else raw
        record = self.codec.decode(payload)
        event = {"record_type": "EventRecord", "schema_version": "1",
            "record_id": event_id or "event:" + uuid.uuid4().hex,
            "scope_id": point.scope_id, "causation_ref": value["causation_ref"],
            "sequence": point.next_sequence, "event_type": event_type,
            "actor_id": actor, "actor_session": "session:projection-fixture",
            "recorded_at": STAMP, "previous_head": point.head,
            "payload_ref": record.record_id, "payload_commitment": record.commitment,
            "canonicalization_profile": PROFILE, "signer_key_ref": None, "signature_ref": None}
        event.update(event_changes)
        return JournalEntry(canonical_bytes(event), payload)

    def next_point(self, row):
        parsed = self.events.preimages(row.event_wire)
        event = parsed.record.as_dict()
        return StreamPosition(event["scope_id"], event["sequence"] + 1, parsed.head)

    def observations(self, count=2, *, scope=SCOPE):
        rows, point = [], StreamPosition(scope, 0, None)
        for index in range(count):
            row = self.row(self.value("ObservationEnvelope", "observation:" + str(index), scope=scope), point=point)
            rows.append(row); point = self.next_point(row)
        return tuple(rows), point

    def normalized(self, originals, *, scope=SCOPE):
        """Only a labelled fixture chain, retaining actual producer payloads."""
        point, result = StreamPosition(scope, 0, None), []
        for original in originals:
            event = strict_loads(original.event_wire)
            self.assertEqual(event["scope_id"], scope)
            event.update(sequence=point.next_sequence, previous_head=point.head)
            row = JournalEntry(canonical_bytes(event), original.payload_wire)
            result.append(row); point = self.next_point(row)
        return tuple(result), point

    def changed(self, original, *, payload_changes=None, event_changes=None, point=None):
        value = strict_loads(original.payload_wire)
        value.update(payload_changes or {})
        event = strict_loads(original.event_wire)
        event.update(event_changes or {})
        payload = canonical_bytes(value)
        event["payload_commitment"] = self.codec.decode(payload).commitment
        if point is not None:
            event.update(sequence=point.next_sequence, previous_head=point.head)
        return JournalEntry(canonical_bytes(event), payload)

    def fresh_journal(self, *, scopes=(SCOPE,)):
        root = ROOT / ".agents/fixtures/projections-cmp03" / uuid.uuid4().hex
        root.mkdir(parents=True, exist_ok=False)
        store = SqliteJournal(root, self.codec, scopes, create=True)
        self.stores.append(store)
        return store

    def task_fixture(self):
        root = ROOT / ".agents/fixtures/projections-cmp03" / uuid.uuid4().hex
        fixture = task_infrastructure._Fixture(deepcopy(self.schema), root=root)
        self.fixtures.append(fixture)
        return fixture

    def kernel_fixture(self, *, grant_scope=SCOPE):
        fixture = kernel_infrastructure.KernelFixture(deepcopy(self.schema), grant_scope=grant_scope)
        self.fixtures.append(fixture)
        return fixture

    def kernel_entries(self):
        fixture = self.kernel_fixture()
        prepared = fixture.prepare()
        consumed = fixture.service.consume(prepared.record_wire, fixture.owners.worker_context)
        originals = (JournalEntry(prepared.event_wire, prepared.record_wire),
                     JournalEntry(consumed.event_wire, consumed.record_wire))
        rows, point = self.normalized(originals)
        return fixture, prepared, consumed, rows, point

    def task_entries(self):
        fixture = self.task_fixture()
        created = fixture.create(TASK, instruction="NO consent.\r\nCafe\u0301\x00", draft="Original draft")
        from ceta.contracts.task_drafts import draft_key
        revision = fixture.cell(draft_key(SCOPE, TASK)).revision
        saved = fixture.call("save", task_id=TASK, title="Changed title", draft="Changed draft",
                             expected_revision=revision)
        return fixture, created, saved, tuple(fixture.store.replay(SCOPE))

    @staticmethod
    def table_rows(store):
        names = [row[0] for row in store._connection.execute(
            "SELECT name FROM sqlite_schema WHERE type='table' AND name NOT GLOB 'sqlite_*' ORDER BY name")]
        return tuple((name, tuple(sorted(store._connection.execute(
            'SELECT * FROM "' + name + '"').fetchall(), key=repr))) for name in names)

    def test_empty_prefix_is_scoped_deterministic_and_has_no_authority_records(self):
        first = self.reducer.rebuild(SCOPE, (), expected_position=StreamPosition(SCOPE, 0, None))
        second = self.reducer.rebuild(SCOPE, ())
        other = self.reducer.rebuild(OTHER_SCOPE, ())
        self.assertEqual(first, second)
        self.assertEqual(first.sha256, second.sha256)
        self.assertNotEqual(first.sha256, other.sha256)
        self.assertEqual(first.profile, PROJECTION_PROFILE)
        self.assertEqual(first.position, StreamPosition(SCOPE, 0, None))
        self.assertEqual((first.records, first.memory_references, first.entries), ((), (), ()))

    def test_full_rebuild_and_validated_tail_have_exact_equal_views_and_original_bytes(self):
        rows, final = self.observations(3)
        first_point = self.next_point(rows[0])
        first = self.reducer.rebuild(SCOPE, rows[:1], expected_position=first_point)
        before = first.sha256
        appended = self.reducer.reduce(first, rows[1:], expected_before=first_point, expected_after=final)
        full = self.reducer.rebuild(SCOPE, rows, expected_position=final)
        self.assertEqual(appended, full)
        self.assertEqual(appended.sha256, full.sha256)
        self.assertEqual(full.entries, rows)
        self.assertEqual(first.sha256, before)
        self.assertEqual([item.subject_id for item in full.select("observations")],
                         ["observation:0", "observation:1", "observation:2"])
        self.assertIsNot(full.entries[0], rows[0])
        self.assertEqual(full.records[0].event_wire, rows[0].event_wire)
        self.assertEqual(full.records[0].payload_wire, rows[0].payload_wire)

    def test_generic_noncanonical_raw_bytes_are_retained_and_affect_identity(self):
        value = self.value("ObservationEnvelope", "observation:pretty")
        canonical = self.row(value, event_id="event:pretty")
        pretty = JournalEntry(canonical.event_wire, json.dumps(value, indent=2).encode("utf-8"))
        first, second = self.reducer.rebuild(SCOPE, (canonical,)), self.reducer.rebuild(SCOPE, (pretty,))
        self.assertEqual(first.position, second.position)
        self.assertEqual(first.records[0].payload(), second.records[0].payload())
        self.assertNotEqual(first.sha256, second.sha256)
        self.assertEqual(second.records[0].payload_wire, pretty.payload_wire)

    def test_detached_record_payload_cannot_mutate_snapshot(self):
        rows, _ = self.observations(1)
        view = self.reducer.rebuild(SCOPE, rows)
        before = view.sha256
        value = view.records[0].payload()
        value["method"] = "invented admission"
        self.assertEqual(view.sha256, before)
        self.assertNotEqual(view.records[0].payload()["method"], value["method"])
        with self.assertRaises(FrozenInstanceError):
            view.records[0].subject_id = "observation:replacement"

    def test_expected_scope_head_and_sequence_must_bind_exact_prefix(self):
        rows, final = self.observations(1)
        for point in (StreamPosition(OTHER_SCOPE, 1, final.head),
                      StreamPosition(SCOPE, 1, HASH), StreamPosition(SCOPE, 0, None)):
            with self.subTest(point=point):
                self.reject(lambda: self.reducer.rebuild(SCOPE, rows, expected_position=point))

    def test_reordered_gap_wrong_prior_and_cross_scope_entries_are_rejected(self):
        rows, _ = self.observations(2)
        bad_prior = self.changed(rows[1], event_changes={"previous_head": HASH})
        bad_sequence = self.changed(rows[1], event_changes={"sequence": 4})
        foreign, _ = self.observations(1, scope=OTHER_SCOPE)
        for batch in (rows[::-1], (rows[1],), (rows[0], bad_prior),
                      (rows[0], bad_sequence), foreign):
            with self.subTest(batch=batch):
                self.reject(lambda: self.reducer.rebuild(SCOPE, batch))

    def test_unknown_event_is_not_ignored_and_typed_mismatch_is_rejected(self):
        observation = self.value("ObservationEnvelope", "observation:unknown")
        unknown = self.row(observation, "fixture.unregistered")
        self.reject(lambda: self.reducer.rebuild(SCOPE, (unknown,)), "PROJECTION_EVENT_UNREGISTERED")
        policy = self.value("PolicyDecision", "policy:wrong")
        wrong = self.row(policy, "observation.accepted")
        self.reject(lambda: self.reducer.rebuild(SCOPE, (wrong,)), "PROJECTION_EVENT_PAYLOAD_TYPE_MISMATCH")

    def test_duplicate_event_identity_and_changed_payload_type_cannot_be_laundered(self):
        rows, _ = self.observations(1)
        duplicate = self.row(self.value("ObservationEnvelope", "observation:new"),
            point=self.next_point(rows[0]), event_id=strict_loads(rows[0].event_wire)["record_id"])
        self.reject(lambda: self.reducer.rebuild(SCOPE, rows + (duplicate,)), "PROJECTION_EVENT_ID_DUPLICATE")
        policy = self.value("PolicyDecision", "observation:0")
        alternate = self.row(policy, "fixture.policy", point=self.next_point(rows[0]))
        reducer = ProjectionReducer(self.codec, registrations=(ProjectionRegistration("fixture.policy", "PolicyDecision"),))
        self.reject(lambda: reducer.rebuild(SCOPE, rows + (alternate,)), "PROJECTION_PAYLOAD_ID_TYPE_CHANGED")

    def test_registration_is_explicit_bounded_typed_and_cannot_override_builtin(self):
        bad = ((ProjectionRegistration("observation.accepted", "ObservationEnvelope"),),
               (ProjectionRegistration("fixture.x", "ObservationEnvelope"),) * 2,
               (),)
        self.reject(lambda: ProjectionReducer(self.codec, registrations=bad[0]),
                    "PROJECTION_EVENT_REGISTRATION_DUPLICATE")
        self.reject(lambda: ProjectionReducer(self.codec, registrations=bad[1]),
                    "PROJECTION_EVENT_REGISTRATION_DUPLICATE")
        self.reject(lambda: ProjectionReducer(self.codec, registrations=[]), "PROJECTION_REGISTRY_BOUND")
        registrations = tuple(ProjectionRegistration("fixture." + str(i), "ObservationEnvelope") for i in range(129))
        self.reject(lambda: ProjectionReducer(self.codec, registrations=registrations), "PROJECTION_REGISTRY_BOUND")
        for event_type, payload_type in ((True, "ObservationEnvelope"), ("", "MemoryRecord"),
                                         ("fixture.x", "ActionProposal"), ("fixture.x", True)):
            with self.subTest(event_type=event_type, payload_type=payload_type):
                self.reject(lambda: ProjectionRegistration(event_type, payload_type))

    def test_registration_order_has_one_commitment_and_caller_mutation_has_no_effect(self):
        first = ProjectionRegistration("fixture.first", "ObservationEnvelope")
        second = ProjectionRegistration("fixture.second", "PolicyDecision")
        left = ProjectionReducer(self.codec, registrations=(first, second))
        right = ProjectionReducer(self.codec, registrations=(second, first))
        self.assertEqual(left.registry_commitment, right.registry_commitment)
        object.__setattr__(first, "payload_type", "PolicyDecision")
        row = self.row(self.value("ObservationEnvelope", "observation:registered"), "fixture.first")
        self.assertEqual(left.rebuild(SCOPE, (row,)).records[0].collection, "observations")
        with self.assertRaises(TypeError):
            left._registry["fixture.first"] = "PolicyDecision"

    def test_caller_schema_mutation_does_not_weaken_captured_codec(self):
        supplied_schema = deepcopy(self.schema)
        supplied_codec = RecordCodec(supplied_schema)
        reducer = ProjectionReducer(supplied_codec)
        rows, _ = self.observations(1)
        value = strict_loads(rows[0].payload_wire)
        value["invented_authority"] = True
        invalid = JournalEntry(rows[0].event_wire, canonical_bytes(value))
        # RecordCodec already detaches its schema input. Exercise that guarantee,
        # then mutate the caller-owned codec itself with a still-strict schema.
        supplied_schema["$defs"]["ObservationEnvelope"]["properties"]["method"]["maxLength"] = 1
        self.assertNotEqual(supplied_codec._schema, supplied_schema)
        shape = supplied_codec._schema["$defs"]["ObservationEnvelope"]
        shape["properties"]["invented_authority"] = {"type": "boolean"}
        shape["required"].append("invented_authority")
        self.reject(lambda: reducer.rebuild(SCOPE, (invalid,)), "UNKNOWN_FIELD")
        fresh = ProjectionReducer(supplied_codec)
        self.assertNotEqual(fresh.registry_commitment, reducer.registry_commitment)
        cached = reducer.rebuild(SCOPE, rows)
        self.reject(lambda: fresh.reduce(cached, (), expected_before=cached.position), "PROJECTION_REGISTRY_CHANGED")

    def test_schema_or_event_registry_change_requires_rebuild_not_tail_reinterpretation(self):
        rows, _ = self.observations(1)
        cached = self.reducer.rebuild(SCOPE, rows)
        changed = ProjectionReducer(self.codec, registrations=(ProjectionRegistration("fixture.extra", "MemoryRecord"),))
        self.reject(lambda: changed.reduce(cached, (), expected_before=cached.position), "PROJECTION_REGISTRY_CHANGED")

    def test_forged_cached_records_cannot_become_a_validated_tail_basis(self):
        rows, _ = self.observations(1)
        cached = self.reducer.rebuild(SCOPE, rows)
        forged = replace(cached, records=())
        self.reject(lambda: self.reducer.reduce(forged, (), expected_before=cached.position), "PROJECTION_VIEW_DIVERGENCE")
        record = replace(cached.records[0], subject_id="observation:forged")
        forged = replace(cached, records=(record,))
        self.reject(lambda: self.reducer.reduce(forged, (), expected_before=cached.position), "PROJECTION_VIEW_DIVERGENCE")

    def test_forged_bool_float_and_mutated_frozen_positions_are_revalidated(self):
        rows, _ = self.observations(1)
        cached = self.reducer.rebuild(SCOPE, rows)
        for sequence in (True, 1.0, -1, 2**53):
            position = StreamPosition(SCOPE, 1, cached.position.head)
            object.__setattr__(position, "next_sequence", sequence)
            with self.subTest(sequence=sequence):
                self.reject(lambda: self.reducer.reduce(cached, (), expected_before=position))
        for sequence in (True, 0.0, -1, 2**53):
            with self.subTest(record_sequence=sequence):
                self.reject(lambda: ProjectedRecord("observations", "observation:x", "event:x", sequence,
                    rows[0].event_wire, rows[0].payload_wire), "PROJECTION_SEQUENCE")

    def test_uninitialized_exact_dataclasses_and_codec_fail_with_contract_diagnostics(self):
        rows, _ = self.observations(1)
        cached = self.reducer.rebuild(SCOPE, rows)
        actions = (lambda: self.reducer.rebuild(SCOPE, (object.__new__(JournalEntry),)),
            lambda: self.reducer.reduce(object.__new__(ProjectionSnapshot), (), expected_before=cached.position),
            lambda: self.reducer.reduce(cached, (), expected_before=object.__new__(StreamPosition)),
            lambda: ProjectionReducer(self.codec, registrations=(object.__new__(ProjectionRegistration),)),
            lambda: ProjectionReducer(object.__new__(RecordCodec)))
        for action in actions:
            with self.subTest(action=action):
                self.reject(action)

    def test_snapshot_order_duplicates_collections_and_memory_types_are_strict(self):
        rows, _ = self.observations(2)
        snapshot = self.reducer.rebuild(SCOPE, rows)
        for records in (snapshot.records[::-1], (snapshot.records[0],) * 2, list(snapshot.records)):
            with self.subTest(records=records):
                self.reject(lambda: replace(snapshot, records=records))
        for collection in ("authority", True, None):
            with self.subTest(collection=collection):
                self.reject(lambda: snapshot.select(collection), "PROJECTION_COLLECTION")
        for lifecycle, deletion in ((True, "NOT_REQUESTED"), ("ACTIVE", True), ("UNKNOWN", "PARTIAL")):
            with self.subTest(lifecycle=lifecycle, deletion=deletion):
                self.reject(lambda: MemoryReference("memory:x", lifecycle, deletion, None))

    def test_typed_payload_sequence_and_duplicate_json_fail_without_partial_view(self):
        rows, _ = self.observations(1)
        value = strict_loads(rows[0].payload_wire)
        invalid_payloads = (canonical_bytes(dict(value, record_id=True)),
            canonical_bytes(dict(value, observed_at=False)),
            rows[0].payload_wire[:-1] + b',"record_id":"observation:substituted"}')
        for payload in invalid_payloads:
            with self.subTest(payload=payload[:100]):
                self.reject(lambda: self.reducer.rebuild(SCOPE, (JournalEntry(rows[0].event_wire, payload),)))
        for sequence in (True, 0.0):
            event = strict_loads(rows[0].event_wire)
            event["sequence"] = sequence
            # Deliberately malformed wire must reach the reducer, not be
            # rejected by the production encoder while building the fixture.
            invalid = JournalEntry(json.dumps(event, sort_keys=True, separators=(",", ":")).encode(),
                rows[0].payload_wire)
            with self.subTest(sequence=sequence):
                self.reject(lambda: self.reducer.rebuild(SCOPE, (invalid,)))

    def test_mutated_exact_frozen_entry_record_and_memory_instances_are_revalidated(self):
        rows, _ = self.observations(1)
        forged_entry = replace(rows[0])
        object.__setattr__(forged_entry, "event_wire", bytearray(forged_entry.event_wire))
        self.reject(lambda: self.reducer.rebuild(SCOPE, (forged_entry,)), "JOURNAL_ENTRY_BYTES_REQUIRED")
        cached = self.reducer.rebuild(SCOPE, rows)
        object.__setattr__(cached.records[0], "sequence", True)
        self.reject(lambda: self.reducer.reduce(cached, (), expected_before=cached.position), "PROJECTION_SEQUENCE")
        reducer, memory_rows = self.memory_entries()
        memory_view = reducer.rebuild(SCOPE, memory_rows)
        object.__setattr__(memory_view.memory_references[0], "claimed_lifecycle", "APPROVED")
        self.reject(lambda: reducer.reduce(memory_view, (), expected_before=memory_view.position),
                    "PROJECTION_MEMORY_LIFECYCLE_UNSUPPORTED")

    def test_tail_requires_exact_cached_before_and_declared_after_positions(self):
        rows, final = self.observations(2)
        cached = self.reducer.rebuild(SCOPE, rows[:1])
        self.reject(lambda: self.reducer.reduce(cached, rows[1:], expected_before=StreamPosition(SCOPE, 0, None)),
                    "PROJECTION_SNAPSHOT_PREFIX_MISMATCH")
        self.reject(lambda: self.reducer.reduce(cached, rows[1:], expected_before=cached.position,
            expected_after=StreamPosition(SCOPE, final.next_sequence, HASH)), "PROJECTION_ACCEPTED_PREFIX_MISMATCH")
        self.assertEqual(self.reducer.reduce(cached, (), expected_before=cached.position), cached)

    def test_true_event_and_byte_resource_ceilings_reject_before_reduction(self):
        self.assertEqual(MAX_PROJECTION_EVENTS, 65536)
        self.assertEqual(MAX_PROJECTION_BYTES, 64 * 1024 * 1024)
        rows, _ = self.observations(1)
        self.reject(lambda: self.reducer.rebuild(SCOPE, rows * (MAX_PROJECTION_EVENTS + 1)),
                    "PROJECTION_EVENT_BOUND_EXCEEDED")
        large = JournalEntry(b"{}", b"x" * MAX_WIRE_BYTES)
        count = MAX_PROJECTION_BYTES // (len(large.event_wire) + len(large.payload_wire)) + 1
        self.reject(lambda: self.reducer.rebuild(SCOPE, (large,) * count), "PROJECTION_BYTE_BOUND_EXCEEDED")
        self.reject(lambda: self.reducer.rebuild(SCOPE, list(rows)), "PROJECTION_EVENT_BOUND_EXCEEDED")

    def test_real_task_create_save_complete_prefix_matches_sqlite_observed_position(self):
        fixture, created, saved, rows = self.task_entries()
        before = self.table_rows(fixture.store)
        observed = fixture.store.position(SCOPE)
        view = fixture.store.projection(SCOPE, expected_position=observed)
        self.assertEqual(view, self.reducer.rebuild(SCOPE, rows, expected_position=observed))
        self.assertEqual(self.table_rows(fixture.store), before)
        self.assertEqual(view.entries, rows)
        drafts = view.select("task_drafts")
        self.assertEqual(len(drafts), 1)
        self.assertEqual(drafts[0].subject_id, TASK)
        self.assertEqual(drafts[0].event_wire, rows[-1].event_wire)
        self.assertEqual(drafts[0].payload_wire, rows[-1].payload_wire)
        self.assertNotIn("Changed draft", drafts[0].payload_wire.decode("utf-8"))
        self.assertNotEqual(created.snapshot_wire, saved.snapshot_wire)

    def test_actual_meaning_editor_retention_and_discard_use_distinct_reference_collections(self):
        from ceta.contracts.task_drafts import command_wire, draft_key
        from ceta.contracts.task_meaning import MEANING_FIELDS, meaning_from_text
        from ceta.contracts.editor_recovery import editor_payload_wire, recovery_key
        fixture, _, saved, _ = self.task_entries()
        basis = fixture.cell(draft_key(SCOPE, TASK)).revision
        meaning = command_wire("meaning_propose", SCOPE, "command:projection-meaning", task_id=TASK,
            expected_revision=basis, meaning=meaning_from_text({name: "Unaccepted: " + name for name in MEANING_FIELDS}))
        message, context = fixture.message(meaning); proposed = fixture.tasks(message, context)
        docs = {name: {"document_id": "editor-document:" + uuid.uuid4().hex,
            "utf16le_hex": ("Rejected " + name + "\ud800").encode("utf-16-le", errors="surrogatepass").hex(),
            "document_revision": 0, "cursor_position": 0, "anchor_position": 0} for name in MEANING_FIELDS}
        payload = editor_payload_wire(basis_revision=basis, widget_revision=1, documents=docs)
        retain = command_wire("editor_retain", SCOPE, "command:projection-retain", task_id=TASK, editor_payload=payload)
        message, context = fixture.message(retain); retained = fixture.tasks(message, context)
        recovery_revision = fixture.cell(recovery_key(SCOPE, TASK)).revision
        discard = command_wire("editor_discard", SCOPE, "command:projection-discard", task_id=TASK,
            editor_expected_revision=recovery_revision)
        message, context = fixture.message(discard); discarded = fixture.tasks(message, context)
        rows = tuple(fixture.store.replay(SCOPE))
        self.assertEqual([strict_loads(row.event_wire)["event_type"] for row in rows],
            ["task.created", "task.draft.saved", "task.meaning.proposed", "task.editor.retained", "task.editor.discarded"])
        view = fixture.store.projection(SCOPE)
        self.assertEqual([item.subject_id for item in view.select("task_drafts")], [TASK])
        self.assertEqual([item.subject_id for item in view.select("task_meanings")], [TASK])
        self.assertEqual([item.subject_id for item in view.select("task_editors")], [TASK])
        self.assertEqual(view.select("task_editors")[0].payload_wire, rows[-1].payload_wire)
        self.assertEqual(strict_loads(discarded.snapshot_wire)["payload"], strict_loads(retained.snapshot_wire)["payload"])
        self.assertEqual(fixture.call("load", task_id=TASK).snapshot_wire, saved.snapshot_wire)
        self.assertEqual(proposed.kind, "TASK_MEANING_PROPOSAL")

    def test_task_update_without_create_duplicate_create_and_actor_change_are_rejected(self):
        _, _, _, rows = self.task_entries()
        update_only, _ = self.normalized(rows[1:])
        self.reject(lambda: self.reducer.rebuild(SCOPE, update_only), "PROJECTION_TASK_CREATION_MISSING")
        repeated = self.changed(rows[0], event_changes={"record_id": "event:duplicate-create"},
                                point=self.next_point(rows[0]))
        self.reject(lambda: self.reducer.rebuild(SCOPE, rows[:1] + (repeated,)), "PROJECTION_TASK_ALREADY_CREATED")
        foreign = self.changed(rows[1], event_changes={"actor_id": "operator:other"})
        self.reject(lambda: self.reducer.rebuild(SCOPE, rows[:1] + (foreign,)), "PROJECTION_TASK_OWNER_CHANGED")

    def test_task_observation_binding_is_checked_after_commitment_rebinding(self):
        _, _, _, rows = self.task_entries()
        mutations = ({"method": "caller says accepted"}, {"observer_session": "session:other"},
            {"observed_at": STAMP}, {"valid_until": STAMP}, {"completeness": "PARTIAL"},
            {"epistemic_status": "ATTRIBUTED"}, {"payload_ref": "task:other"})
        for change in mutations:
            altered = self.changed(rows[1], payload_changes=change)
            with self.subTest(change=change):
                self.reject(lambda: self.reducer.rebuild(SCOPE, rows[:1] + (altered,)), "PROJECTION_TASK_BINDING")

    def test_task_events_require_exact_canonical_wire_without_normalizing_original_evidence(self):
        _, _, _, rows = self.task_entries()
        for target in ("event", "payload"):
            original = rows[0]
            altered = JournalEntry(json.dumps(strict_loads(original.event_wire), indent=2).encode()
                if target == "event" else original.event_wire,
                json.dumps(strict_loads(original.payload_wire), indent=2).encode()
                if target == "payload" else original.payload_wire)
            with self.subTest(target=target):
                self.reject(lambda: self.reducer.rebuild(SCOPE, (altered,)), "PROJECTION_TASK_CANONICAL_EVENT_REQUIRED")

    def test_actual_kernel_issued_and_consumed_payloads_rebuild_one_burned_canonical_permit(self):
        fixture, prepared, consumed, rows, final = self.kernel_entries()
        before = self.table_rows(fixture.store)
        view = self.reducer.rebuild(SCOPE, rows, expected_position=final)
        permit = self.codec.decode(consumed.record_wire).as_dict()
        self.assertEqual(len(view.select("permits")), 1)
        self.assertEqual(view.select("permits")[0].subject_id, permit["record_id"])
        self.assertEqual(view.select("permits")[0].payload_wire, consumed.record_wire)
        self.assertEqual(view.select("permits")[0].payload()["status"], "CONSUMED")
        self.assertEqual(self.table_rows(fixture.store), before)
        issued = self.reducer.rebuild(SCOPE, rows[:1])
        self.assertEqual(self.reducer.reduce(issued, rows[1:], expected_before=issued.position, expected_after=final), view)
        self.assertEqual(self.codec.decode(prepared.record_wire).as_dict()["status"], "PREPARED")

    def test_full_kernel_fixture_keeps_unsupported_seed_visible_instead_of_dropping_it(self):
        fixture, _, _, _, _ = self.kernel_entries()
        before = self.table_rows(fixture.store)
        self.reject(lambda: fixture.store.projection(SCOPE), "PROJECTION_EVENT_UNREGISTERED")
        self.assertEqual(self.table_rows(fixture.store), before)

    def test_permit_reference_alias_cannot_reset_consumed_canonical_permit(self):
        _, prepared, consumed, rows, final = self.kernel_entries()
        alias = self.row(strict_loads(prepared.record_wire), "fixture.permit-reference", point=final)
        reducer = ProjectionReducer(self.codec, registrations=(ProjectionRegistration("fixture.permit-reference", "OperationPermit"),))
        view = reducer.rebuild(SCOPE, rows + (alias,))
        self.assertEqual(view.select("permits")[0].payload_wire, consumed.record_wire)
        self.assertEqual(view.select("permits")[0].payload()["status"], "CONSUMED")
        self.assertEqual(view.select("permit_references")[0].payload_wire, prepared.record_wire)

    def test_duplicate_consume_missing_issuance_and_tampered_permit_are_rejected(self):
        _, _, _, rows, final = self.kernel_entries()
        duplicate = self.changed(rows[1], payload_changes={"consume_event_ref": "event:second-consume",
            "causation_ref": "event:second-consume"}, event_changes={"record_id": "event:second-consume",
            "causation_ref": "event:second-consume"}, point=final)
        self.reject(lambda: self.reducer.rebuild(SCOPE, rows + (duplicate,)), "PROJECTION_PERMIT_CONSUMED_TWICE")
        consumed_only, _ = self.normalized(rows[1:])
        self.reject(lambda: self.reducer.rebuild(SCOPE, consumed_only), "PROJECTION_PERMIT_ISSUANCE_MISSING")
        changed = self.changed(rows[1], payload_changes={"arguments_commitment": HASH})
        self.reject(lambda: self.reducer.rebuild(SCOPE, rows[:1] + (changed,)), "PROJECTION_PERMIT_CONTENT_CHANGED")
        foreign = self.changed(rows[1], event_changes={"actor_id": "worker:other"})
        self.reject(lambda: self.reducer.rebuild(SCOPE, rows[:1] + (foreign,)), "PROJECTION_PERMIT_ACTOR_CHANGED")

    def test_actual_revocation_and_active_grant_reference_alias_are_separate(self):
        fixture = self.kernel_fixture()
        revoked = fixture.service.revoke(fixture.grant_wire, fixture.owners.owner_context, "reason:owner-revoke")
        rows, final = self.normalized((JournalEntry(revoked.event_wire, revoked.record_wire),))
        alias = self.row(strict_loads(fixture.grant_wire), "fixture.grant-reference", point=final)
        reducer = ProjectionReducer(self.codec, registrations=(ProjectionRegistration("fixture.grant-reference", "StandingGrant"),))
        view = reducer.rebuild(SCOPE, rows + (alias,))
        self.assertEqual(view.select("grants")[0].payload_wire, revoked.record_wire)
        self.assertEqual(view.select("grants")[0].payload()["status"], "REVOKED")
        self.assertEqual(view.select("grant_references")[0].payload()["status"], "ACTIVE")
        repeated = self.changed(rows[0], event_changes={"record_id": "event:repeated-revocation"}, point=final)
        self.reject(lambda: self.reducer.rebuild(SCOPE, rows + (repeated,)), "PROJECTION_GRANT_REVOCATION_NOT_ADVANCED")

    def test_actual_cross_scope_development_allocation_is_only_an_allow_claim(self):
        fixture = self.kernel_fixture(grant_scope=OTHER_SCOPE); fixture.prepare()
        actual = tuple(row for row in fixture.store.replay(OTHER_SCOPE)
            if strict_loads(row.event_wire)["event_type"] == "kernel.development.allocation")
        self.assertEqual(len(actual), 1)
        rows, point = self.normalized(actual, scope=OTHER_SCOPE)
        view = self.reducer.rebuild(OTHER_SCOPE, rows, expected_position=point)
        value = view.select("policy_decisions")[0].payload()
        self.assertEqual(value["outcome"], "ALLOW")
        self.assertEqual(value["reason_codes"], ["DEVELOPMENT_ALLOCATION_PROFILE"])
        self.assertEqual(value["authority_owner_id"], "kernel:cmp02")
        malformed = self.changed(rows[0], payload_changes={"authority_owner_id": "owner:caller"})
        self.reject(lambda: self.reducer.rebuild(OTHER_SCOPE, (malformed,)), "PROJECTION_ALLOCATION_BINDING")

    def memory_entries(self, *, deletion="NOT_REQUESTED", evidence=(), after="ARCHIVED"):
        memory = self.value("MemoryRecord", "memory:fixture", lifecycle="ACTIVE", retention_policy_ref="policy:retention")
        life = self.value("MemoryLifecycleEvent", "memory-lifecycle:fixture", memory_ref=memory["record_id"],
            policy_ref=memory["retention_policy_ref"], before="ACTIVE", after=after,
            payload_deletion_state=deletion, evidence_refs=list(evidence))
        first = self.row(memory, "fixture.memory")
        second = self.row(life, "fixture.memory-lifecycle", point=self.next_point(first))
        reducer = ProjectionReducer(self.codec, registrations=(ProjectionRegistration("fixture.memory", "MemoryRecord"),
            ProjectionRegistration("fixture.memory-lifecycle", "MemoryLifecycleEvent")))
        return reducer, (first, second)

    def test_registered_memory_lifecycle_projects_claims_and_retains_all_raw_evidence(self):
        reducer, rows = self.memory_entries()
        view = reducer.rebuild(SCOPE, rows)
        self.assertEqual(view.memory_references, (MemoryReference("memory:fixture", "ARCHIVED", "NOT_REQUESTED", "memory-lifecycle:fixture"),))
        self.assertEqual(view.select("memory_records")[0].payload_wire, rows[0].payload_wire)
        self.assertEqual(view.select("memory_lifecycles")[0].payload_wire, rows[1].payload_wire)
        self.assertEqual(view.entries, rows)

    def test_memory_policy_prior_state_and_unresolved_reference_are_not_inferred(self):
        reducer, rows = self.memory_entries()
        for change in ({"policy_ref": "policy:other"}, {"before": "CANDIDATE"}):
            altered = self.changed(rows[1], payload_changes=change)
            with self.subTest(change=change):
                self.reject(lambda: reducer.rebuild(SCOPE, rows[:1] + (altered,)), "PROJECTION_MEMORY_STATE_OR_POLICY_BINDING")
        unresolved = self.changed(rows[1], payload_changes={"memory_ref": "memory:other"})
        self.reject(lambda: reducer.rebuild(SCOPE, rows[:1] + (unresolved,)), "PROJECTION_MEMORY_REFERENCE_UNRESOLVED")
        alone, _ = self.normalized(rows[1:])
        self.reject(lambda: reducer.rebuild(SCOPE, alone), "PROJECTION_MEMORY_REFERENCE_UNRESOLVED")

    def test_memory_deletion_requires_observed_state_and_evidence_refs_but_stays_a_claim(self):
        reducer, rows = self.memory_entries(after="DELETED_PAYLOAD")
        self.reject(lambda: reducer.rebuild(SCOPE, rows), "MEMORY_DELETION_CLAIM_UNSUPPORTED")
        for state in ("LOCAL_DELETION_OBSERVED", "BACKUP_RETENTION_PENDING", "PARTIAL"):
            with self.subTest(state=state):
                reducer, rows = self.memory_entries(after="DELETED_PAYLOAD", deletion=state)
                self.reject(lambda: reducer.rebuild(SCOPE, rows), "MEMORY_DELETION_EVIDENCE_MISSING")
                reducer, rows = self.memory_entries(after="DELETED_PAYLOAD", deletion=state, evidence=("evidence:synthetic-deletion",))
                view = reducer.rebuild(SCOPE, rows)
                self.assertEqual(view.memory_references[0].claimed_deletion_state, state)
                self.assertEqual(view.memory_references[0].claimed_lifecycle, "DELETED_PAYLOAD")

    def effect_entries(self, *, receipt_operation="operation:fixture", effect_operation="operation:fixture", receipt_ref="receipt:fixture"):
        receipt = self.value("ExecutionReceipt", "receipt:fixture", operation_id=receipt_operation,
            effect_status="PROCESS_EXITED", cancellation_state="NONE")
        effect = self.value("EffectObservation", "effect:fixture", operation_id=effect_operation,
            receipt_ref=receipt_ref, verdict="UNKNOWN", causal_attribution="UNESTABLISHED", independence_class="SAME_ACTOR")
        first = self.row(receipt, "fixture.receipt")
        second = self.row(effect, "fixture.effect", point=self.next_point(first))
        reducer = ProjectionReducer(self.codec, registrations=(ProjectionRegistration("fixture.receipt", "ExecutionReceipt"),
            ProjectionRegistration("fixture.effect", "EffectObservation")))
        return reducer, (first, second)

    def test_registered_receipt_and_same_operation_effect_keep_uncertainty_and_raw_records(self):
        reducer, rows = self.effect_entries()
        view = reducer.rebuild(SCOPE, rows)
        self.assertEqual(view.select("execution_receipts")[0].payload_wire, rows[0].payload_wire)
        self.assertEqual(view.select("effect_observations")[0].payload_wire, rows[1].payload_wire)
        effect = view.select("effect_observations")[0].payload()
        self.assertEqual((effect["verdict"], effect["causal_attribution"], effect["independence_class"]),
                         ("UNKNOWN", "UNESTABLISHED", "SAME_ACTOR"))

    def test_effect_receipt_must_precede_effect_and_belong_to_same_operation(self):
        for options in ({"receipt_ref": "receipt:absent"}, {"effect_operation": "operation:other"}):
            reducer, rows = self.effect_entries(**options)
            with self.subTest(options=options):
                self.reject(lambda: reducer.rebuild(SCOPE, rows), "PROJECTION_EFFECT_RECEIPT_REFERENCE_UNRESOLVED")
        reducer, rows = self.effect_entries()
        only, _ = self.normalized(rows[1:])
        self.reject(lambda: reducer.rebuild(SCOPE, only), "PROJECTION_EFFECT_RECEIPT_REFERENCE_UNRESOLVED")
        reducer, rows = self.effect_entries(receipt_ref=None)
        only, _ = self.normalized(rows[1:])
        self.assertEqual(len(reducer.rebuild(SCOPE, only).select("effect_observations")), 1)

    def test_sqlite_projection_reads_all_rows_beyond_replay_page_and_reopens_identically(self):
        store = self.fresh_journal()
        rows, final = self.observations(130)
        store.append(StreamPosition(SCOPE, 0, None), rows[:128])
        store.append(self.next_point(rows[127]), rows[128:])
        self.assertEqual(len(store.replay(SCOPE)), 128)
        before = self.table_rows(store)
        view = store.projection(SCOPE, expected_position=final, checkpoints=(self.next_point(rows[0]),))
        self.assertEqual(len(view.entries), 130)
        self.assertEqual(view.position, final)
        self.assertEqual(view, self.reducer.rebuild(SCOPE, rows, expected_position=final))
        self.assertEqual(self.table_rows(store), before)
        root = store.path.parent; store.close()
        reopened = SqliteJournal(root, self.codec, (SCOPE,))
        self.stores.append(reopened)
        self.assertEqual(reopened.projection(SCOPE), view)

    def test_sqlite_stale_expected_head_unknown_scope_and_bad_checkpoint_preserve_rows(self):
        store = self.fresh_journal(); rows, final = self.observations(1)
        store.append(StreamPosition(SCOPE, 0, None), rows)
        before = self.table_rows(store)
        self.reject(lambda: store.projection(SCOPE, expected_position=StreamPosition(SCOPE, 0, None)),
                    "JOURNAL_PROJECTION_REVISION_CONFLICT")
        self.reject(lambda: store.projection("project:unknown"), "JOURNAL_SCOPE_NOT_REGISTERED")
        self.reject(lambda: store.projection(SCOPE, checkpoints=(StreamPosition(SCOPE, 1, HASH),)),
                    "JOURNAL_CHECKPOINT_MISMATCH")
        self.reject(lambda: store.projection(SCOPE, checkpoints=(final, final)), "JOURNAL_CHECKPOINT_SET_INVALID")
        self.assertEqual(self.table_rows(store), before)
        self.assertEqual(store.projection(SCOPE).position, final)

    def test_sqlite_projection_rejects_corruption_in_other_scope_before_disclosure(self):
        store = self.fresh_journal(scopes=(SCOPE, OTHER_SCOPE))
        rows, _ = self.observations(1); foreign, _ = self.observations(1, scope=OTHER_SCOPE)
        store.append(StreamPosition(SCOPE, 0, None), rows)
        store.append(StreamPosition(OTHER_SCOPE, 0, None), foreign)
        store._connection.execute("UPDATE history_events SET original_payload_sha256=? WHERE scope_id=?", ("0" * 64, OTHER_SCOPE))
        corrupted = self.table_rows(store)
        self.reject(lambda: store.projection(SCOPE), "JOURNAL_PREFIX_MISMATCH")
        self.assertEqual(self.table_rows(store), corrupted)

    def test_sqlite_unknown_event_refusal_is_read_only_and_cannot_return_partial_view(self):
        store = self.fresh_journal()
        rows, _ = self.observations(1)
        unknown = self.row(self.value("ObservationEnvelope", "observation:unknown"), "fixture.new-event", point=self.next_point(rows[0]))
        store.append(StreamPosition(SCOPE, 0, None), rows + (unknown,))
        before = self.table_rows(store)
        self.reject(lambda: store.projection(SCOPE), "PROJECTION_EVENT_UNREGISTERED")
        self.assertEqual(self.table_rows(store), before)
        registered = store.projection(SCOPE, registrations=(ProjectionRegistration("fixture.new-event", "ObservationEnvelope"),))
        self.assertEqual(len(registered.entries), 2)
        self.assertEqual(self.table_rows(store), before)

    def test_read_only_sqlite_connection_derives_exact_projection_and_rejects_writers(self):
        fixture, _, _, rows = self.task_entries()
        expected = fixture.store.projection(SCOPE)
        root = fixture.root; fixture.store.close()
        read_only = SqliteJournal(root, self.codec, kernel_infrastructure.SCOPES, profile=STORE_PROFILE, read_only=True)
        self.stores.append(read_only)
        before = self.table_rows(read_only)
        self.assertEqual(read_only.projection(SCOPE), expected)
        self.assertEqual(read_only.projection(SCOPE).entries, rows)
        self.assertTrue(read_only.storage_identity()["read_only"])
        self.reject(lambda: read_only.append(expected.position, (rows[0],)), "JOURNAL_READ_ONLY")
        self.reject(lambda: read_only.commit((expected.position,), (rows[0],)), "JOURNAL_READ_ONLY")
        self.assertEqual(self.table_rows(read_only), before)

    def test_read_failure_preserves_primary_exception_when_rollback_observation_fails(self):
        store = self.fresh_journal(); rows, _ = self.observations(1)
        store.append(StreamPosition(SCOPE, 0, None), rows)
        actual_connection = store._connection
        primary = RuntimeError("controlled reducer interruption")

        class RollbackFault:
            def __getattr__(self, name):
                return getattr(actual_connection, name)

            def execute(self, sql, *args):
                if sql == "ROLLBACK":
                    raise RuntimeError("controlled rollback observation failure")
                return actual_connection.execute(sql, *args)

        store._connection = RollbackFault()
        with patch.object(ProjectionReducer, "rebuild", side_effect=primary):
            with self.assertRaises(RuntimeError) as caught:
                store.projection(SCOPE)
        self.assertIs(caught.exception, primary)
        self.assertIn("JOURNAL_PROJECTION_ROLLBACK_UNOBSERVED", primary.__notes__)
        self.assertTrue(actual_connection.in_transaction)
        store._connection = actual_connection
        actual_connection.execute("ROLLBACK")
        self.assertEqual(store.projection(SCOPE).entries, rows)


if __name__ == "__main__":
    unittest.main()
