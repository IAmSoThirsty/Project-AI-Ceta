"""Real v2 durable mechanics with explicitly synthetic owner fixtures.

No OS authentication, protected handle, adapter dispatch, observed effect,
settlement, original acceptance case B062 or product qualification is claimed.
An exact owner allowlist supplies a PREPARED basis; caller VALIDATED labels do
not supply authority. The allocation profile reserves/charges declared limits,
not measured elapsed time, tokens, bytes or an invented refund policy.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
import sys
import threading
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from ceta.composition.kernel_service import compose_kernel
from ceta.contracts.events import EventContract
from ceta.contracts.history import JournalEntry
from ceta.contracts.kernel_transactions import (BudgetVector, KERNEL_PROFILE,
    PeerIdentity, ZERO_BUDGET, basis_key, budget_key, budget_wire, control_wire,
    deadline_text, encode_basis, intent_key, logical_key, read_basis, read_budget, resource_key,
    resource_wire, task_key, task_wire)
from ceta.contracts.read_sets import ReadSet, ResourceRevision
from ceta.contracts.store_transactions import (STORE_PROFILE, StoreChange,
    StoreExpectation, StoreKey)
from ceta.contracts.temporal import ClockSample, utc_nanoseconds
from ceta.contracts.wire import (ContractError, MAX_INTEGER, MIN_INTEGER, PROFILE,
    RecordCodec, canonical_bytes, strict_loads)
from ceta.store.journal import SqliteJournal
from test_all_records import example

INSTALLATION = "installation:kernel-fixture"
PROJECT = "project:kernel-fixture"
SCOPES = (INSTALLATION, PROJECT)
POLICY = "sha256:" + "1" * 64
ENVIRONMENT = "sha256:" + "2" * 64
ADAPTER = "sha256:" + "3" * 64
REGISTRY = "sha256:" + "4" * 64
TASK_REVISION = "sha256:" + "5" * 64
RESOURCE_REVISION = "sha256:" + "6" * 64
OWNER_INPUT = "sha256:" + "7" * 64
CHANGED = "sha256:" + "8" * 64
COST = BudgetVector((1000, 2, 1, 10, 20, 30, 40))
RECOVERY = BudgetVector((500, 1, 0, 1, 1, 1, 1))
LIMIT = COST.add(COST).add(RECOVERY)


class SyntheticOwners:
    """Opaque fixture contexts and exact allowlists, never native identity proof."""

    def __init__(self):
        self.worker_context, self.owner_context = object(), object()
        self.worker = PeerIdentity("worker:fixture", "session:worker-fixture")
        self.owner = PeerIdentity("owner:fixture", "session:owner-fixture")
        self.prepared = {}
        self.samples = (
            ClockSample("boot:fixture", 1, 0, 1_000_000_000,
                        utc_nanoseconds("2026-10-08T12:00:00Z"), 0, True),
            ClockSample("boot:fixture", 1, 0, 1_100_000_000,
                        utc_nanoseconds("2026-10-08T12:00:00.1Z"), 0, True))
        self.admission_available = True

    def authenticate(self, context):
        if context is self.worker_context:
            return self.worker
        if context is self.owner_context:
            return self.owner
        raise ContractError("FIXTURE_AUTHENTICATION_DENIED")

    def require_prepared_basis(self, proposal, basis_wire, peer):
        expected = self.prepared.get(proposal.record_id)
        if peer != self.worker or expected != (proposal.commitment, basis_wire):
            raise ContractError("FIXTURE_PREPARATION_DENIED")

    def require_admission(self, permit, basis_wire, peer):
        expected = self.prepared.get(permit.as_dict()["proposal_ref"])
        if (not self.admission_available or peer != self.worker
                or expected is None or expected[1] != basis_wire):
            raise ContractError("FIXTURE_ADMISSION_DENIED")

    def require_revocation(self, grant, peer, reason_ref):
        if (peer != self.owner or grant.as_dict()["issuer_id"] != peer.principal_id
                or reason_ref != "reason:owner-revoke"):
            raise ContractError("FIXTURE_REVOCATION_DENIED")

    def clock(self):
        return self.samples


class CommitBarrierJournal(SqliteJournal):
    """Test scheduling hook before the real writer transaction, not a fake store."""

    commit_barrier = None
    after_commit = None
    last_commit_attempt = None

    def commit(self, *args, **kwargs):
        self.last_commit_attempt = (args, kwargs)
        if self.commit_barrier is not None:
            self.commit_barrier.wait(timeout=10)
        result = super().commit(*args, **kwargs)
        if self.after_commit is not None:
            self.after_commit()
        return result


class KernelFixture:
    def __init__(self, schema, *, limit=LIMIT, grant_scope=INSTALLATION,
                 requires_approval=True, approval="evidence:fixture-approval"):
        self.schema, self.codec = schema, RecordCodec(schema)
        self.root = ROOT / ".agents/fixtures/kernel-22" / uuid.uuid4().hex
        self.root.mkdir(parents=True, exist_ok=False)
        self.owners = SyntheticOwners()
        self.fail_commit = False
        self.before_commit_action = None
        self.store = CommitBarrierJournal(self.root, self.codec, SCOPES, create=True,
                                         profile=STORE_PROFILE, before_commit=self.fault)
        self.limit, self.grant_key = limit, StoreKey("grant", grant_scope, "grant:fixture")
        self.control_key = StoreKey("projection", INSTALLATION, "kernel-control")
        self.registry_key = StoreKey("projection", INSTALLATION, "kernel-registry")
        self.read_set = ReadSet(PROJECT, 1, 1, POLICY, ENVIRONMENT, (
            ResourceRevision("resource:target", RESOURCE_REVISION),
            ResourceRevision("resource:owner-dependency", RESOURCE_REVISION)))
        self.proposal = example(schema["$defs"]["ActionProposal"])
        self.proposal.update(record_id="proposal:fixture", scope_id=PROJECT, causation_ref=None,
            task_id="task:fixture", adapter_id="adapter:fixture", adapter_version="1.0.0",
            operation="file.read", arguments_commitment=OWNER_INPUT,
            resources=[{"resource_id": "resource:target", "revision": RESOURCE_REVISION,
                        "access": "READ", "scope_id": PROJECT}],
            dependencies=[], requires_human_approval=requires_approval,
            budget=COST.as_dict(), status="PROPOSED")
        self.grant = example(schema["$defs"]["StandingGrant"])
        self.grant.update(record_id=self.grant_key.record_id, scope_id=grant_scope,
            causation_ref=None, issuer_id=self.owners.owner.principal_id,
            grantee_id=self.owners.worker.principal_id, purpose_ref=self.proposal["task_id"],
            resource_scope=self.proposal["resources"], operation_classes=["file.read"],
            budget=limit.as_dict(), valid_from="2026-10-08T11:00:00Z",
            expires_at="2026-10-08T13:00:00Z", revocation_generation=0,
            policy_commitment=POLICY, status="ACTIVE")
        self.proposal_wire, self.grant_wire = canonical_bytes(self.proposal), canonical_bytes(self.grant)
        self.basis = self.make_basis(self.proposal_wire, approval=approval)
        self.allow(self.proposal_wire, self.basis)
        self.base_keys = (self.grant_key, budget_key(self.grant_key), self.control_key,
            self.registry_key, task_key(PROJECT, "task:fixture"),
            resource_key(PROJECT, "resource:target"),
            resource_key(PROJECT, "resource:owner-dependency"),
            basis_key(PROJECT, "proposal:fixture"))
        values = {
            self.grant_key: self.grant_wire,
            budget_key(self.grant_key): budget_wire(grant_scope, self.grant_key.record_id, limit, RECOVERY),
            self.control_key: control_wire(INSTALLATION, 1, 1, POLICY, ENVIRONMENT),
            self.registry_key: canonical_bytes({"profile": KERNEL_PROFILE, "scope_id": INSTALLATION,
                "commitment": REGISTRY, "operations": [{"adapter_id": "adapter:fixture",
                "adapter_version": "1.0.0", "adapter_commitment": ADAPTER, "operation": "file.read"}]}),
            task_key(PROJECT, "task:fixture"): task_wire(PROJECT, "task:fixture", TASK_REVISION),
            resource_key(PROJECT, "resource:target"): resource_wire(PROJECT, "resource:target", RESOURCE_REVISION),
            resource_key(PROJECT, "resource:owner-dependency"): resource_wire(PROJECT, "resource:owner-dependency", RESOURCE_REVISION),
            basis_key(PROJECT, "proposal:fixture"): self.basis}
        self.seed(values)
        self.service = compose_kernel(self.store, self.codec, INSTALLATION, owners=self.owners)

    def fault(self):
        if self.fail_commit:
            raise RuntimeError("kernel fixture after all writer inserts")
        if self.before_commit_action is not None:
            self.before_commit_action()

    def make_basis(self, proposal_wire, *, approval="evidence:fixture-approval", review_refs=("review:fixture",)):
        return encode_basis(self.codec.decode(proposal_wire), self.grant_key, self.read_set,
            principal_id=self.owners.worker.principal_id, actor_session=self.owners.worker.session_id,
            adapter_commitment=ADAPTER, registry_commitment=REGISTRY,
            owner_input_commitment=OWNER_INPUT, candidate_commitment=None,
            task_revision=TASK_REVISION, review_refs=review_refs, approval_evidence_ref=approval)

    def allow(self, proposal_wire, basis_wire):
        parsed = self.codec.decode(proposal_wire)
        self.owners.prepared[parsed.record_id] = (parsed.commitment, basis_wire)

    def row(self, point, payload_wire):
        record = self.codec.decode(payload_wire)
        event = {"record_type": "EventRecord", "schema_version": "1",
            "record_id": "event:" + uuid.uuid4().hex, "scope_id": point.scope_id,
            "causation_ref": None, "sequence": point.next_sequence, "event_type": "fixture.kernel.seed",
            "actor_id": "owner:fixture", "actor_session": "session:owner-fixture",
            "recorded_at": "2026-10-08T12:00:00Z", "previous_head": point.head,
            "payload_ref": record.record_id, "payload_commitment": record.commitment,
            "canonicalization_profile": PROFILE, "signer_key_ref": None, "signature_ref": None}
        return JournalEntry(canonical_bytes(event), payload_wire)

    def observation(self, scope):
        value = example(self.schema["$defs"]["ObservationEnvelope"])
        value.update(record_id="observation:" + uuid.uuid4().hex, scope_id=scope)
        return canonical_bytes(value)

    def seed(self, values):
        points, rows, changes = [], [], []
        current = {cell.key: cell for cell in self.store.snapshot(tuple(sorted(values)))}
        for scope in sorted({key.scope_id for key in values}):
            point = self.store.position(scope)
            if scope == self.grant_key.scope_id:
                payload = self.grant_wire
            elif scope == PROJECT:
                payload = self.proposal_wire
            else:
                payload = self.observation(scope)
            row = self.row(point, payload)
            event_id = strict_loads(row.event_wire)["record_id"]
            points.append(point); rows.append(row)
            changes.extend(StoreChange(StoreExpectation(key, current[key].revision), wire, event_id)
                           for key, wire in sorted(values.items()) if key.scope_id == scope)
        self.store.commit(tuple(points), tuple(rows), changes=tuple(changes))

    def cell(self, key):
        return self.store.snapshot((key,))[0]

    def put(self, key, wire):
        point, cell = self.store.position(key.scope_id), self.cell(key)
        payload = wire if key.collection in {"grant", "permit"} else self.observation(key.scope_id)
        row = self.row(point, payload)
        return self.store.commit((point,), (row,), changes=(StoreChange(
            StoreExpectation(key, cell.revision), wire, strict_loads(row.event_wire)["record_id"]),))

    def prepare(self):
        return self.service.prepare(self.proposal_wire, self.owners.worker_context)

    def budget(self):
        return read_budget(self.cell(budget_key(self.grant_key)).value_wire, budget_key(self.grant_key))

    def issuance_key(self, proposal_id="proposal:fixture"):
        return logical_key("projection", PROJECT, "issuance", proposal_id)

    def permit_keys(self, wire):
        p = self.codec.decode(wire).as_dict()
        return (StoreKey("permit", PROJECT, p["record_id"]),
                StoreKey("reservation", PROJECT, p["reservation_ref"]), intent_key(PROJECT, p["record_id"]))

    def cut(self, extra=()):
        keys = tuple(sorted(set(self.base_keys + (self.issuance_key(),) + extra)))
        return (self.store.store_position(), tuple(self.store.position(scope) for scope in SCOPES),
                self.store.snapshot(keys), tuple(self.store.replay(scope) for scope in SCOPES))

    def reopen(self):
        self.store.close()
        self.store = CommitBarrierJournal(self.root, self.codec, SCOPES, profile=STORE_PROFILE,
                                         before_commit=self.fault)
        self.service = compose_kernel(self.store, self.codec, INSTALLATION, owners=self.owners)

    def add_proposal(self, identifier):
        value = dict(self.proposal, record_id=identifier)
        wire = canonical_bytes(value)
        basis = self.make_basis(wire)
        self.allow(wire, basis)
        self.put(basis_key(PROJECT, identifier), basis)
        return wire


class KernelTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = strict_loads((ROOT / "contracts/schemas/records.schema.json").read_bytes())

    def setUp(self):
        self.fixtures = []
        self.f = self.fixture()

    def fixture(self, **kwargs):
        fixture = KernelFixture(self.schema, **kwargs)
        self.fixtures.append(fixture)
        return fixture

    def tearDown(self):
        for fixture in self.fixtures:
            fixture.store.close()

    def denied_unchanged(self, action, *, fixture=None, extra=(), code=None):
        f = fixture or self.f
        before = f.cut(extra)
        with self.assertRaises(ContractError) as caught:
            action()
        if code is not None:
            self.assertEqual(caught.exception.code, code)
        self.assertEqual(f.cut(extra), before)
        return caught.exception.code

    def test_prepare_commits_exact_permit_reservation_intent_budget_and_two_scope_events(self):
        f, before = self.f, self.f.store.store_position()
        result = f.prepare()
        p = f.codec.decode(result.record_wire).as_dict()
        self.assertEqual(p["status"], "PREPARED")
        self.assertIsNone(p["consume_event_ref"])
        self.assertEqual(result.commit.position.next_commit, before.next_commit + 1)
        self.assertEqual({h.before.scope_id for h in result.commit.history}, set(SCOPES))
        self.assertEqual(len(result.commit.cells), 5)
        permit, reservation, intent = (f.cell(key) for key in f.permit_keys(result.record_wire))
        self.assertEqual(permit.value_wire, result.record_wire)
        self.assertEqual(strict_loads(reservation.value_wire)["state"], "HELD")
        intention = strict_loads(intent.value_wire)
        self.assertEqual(intention["state"], "INTENT_COMMITTED")
        self.assertIsNone(intention["consumption"])
        dependencies = {StoreKey(**row["key"]) for row in intention["dependencies"]}
        self.assertIn(resource_key(PROJECT, "resource:owner-dependency"), dependencies)
        self.assertEqual(f.proposal["dependencies"], [])
        self.assertEqual(f.budget(), (LIMIT, RECOVERY, COST, ZERO_BUDGET))
        event = EventContract(f.codec)
        accepted = event.require_successor(result.event_wire, result.prior_position)
        event.require_payload(result.event_wire, result.record_wire)
        self.assertEqual(p["issuance_evidence_ref"], accepted.record.record_id)
        self.assertEqual(f.store.replay(PROJECT, result.prior_position.next_sequence, 1)[0],
                         JournalEntry(result.event_wire, result.record_wire))

    def test_prepare_after_all_insert_failure_is_atomic_and_retry_is_single_commit(self):
        f, before = self.f, self.f.cut()
        f.fail_commit = True
        try:
            with self.assertRaisesRegex(RuntimeError, "after all writer inserts"):
                f.prepare()
        finally:
            f.fail_commit = False
        self.assertEqual(f.cut(), before)
        result = f.prepare()
        self.assertTrue(all(cell.generation == 1 for cell in result.commit.cells
                            if cell.key.collection != "budget"))
        self.assertEqual(f.budget(), (LIMIT, RECOVERY, COST, ZERO_BUDGET))

    def test_duplicate_proposal_cannot_reserve_twice(self):
        result = self.f.prepare()
        self.denied_unchanged(self.f.prepare, extra=self.f.permit_keys(result.record_wire),
                              code="KERNEL_PROPOSAL_ALREADY_PREPARED")

    def test_restart_consumption_is_one_use_and_resolves_exact_accepted_event(self):
        f = self.f
        prepared = f.prepare()
        f.reopen()
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        p = f.codec.decode(consumed.record_wire)
        self.assertEqual(p.as_dict()["status"], "CONSUMED")
        self.assertEqual(p.as_dict()["consume_event_ref"], strict_loads(consumed.event_wire)["record_id"])
        self.assertEqual(f.budget(), (LIMIT, RECOVERY, ZERO_BUDGET, COST))
        self.assertEqual(strict_loads(f.cell(f.permit_keys(prepared.record_wire)[1]).value_wire)["state"], "CHARGED")
        intention = strict_loads(f.cell(f.permit_keys(prepared.record_wire)[2]).value_wire)
        self.assertEqual(intention["state"], "ADMISSION_REDEEMED")
        self.assertEqual(intention["consumption"], {"sequence": consumed.prior_position.next_sequence,
            "previous_head": consumed.prior_position.head, "event_id": p.as_dict()["consume_event_ref"]})
        f.reopen()
        evidence = f.service.resolve_consumption(p)
        self.assertEqual((evidence.consumed_permit_wire, evidence.event_wire, evidence.prior_position),
                         (consumed.record_wire, consumed.event_wire, consumed.prior_position))
        self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                              extra=f.permit_keys(prepared.record_wire), code="KERNEL_PERMIT_NOT_PREPARED")
        self.denied_unchanged(lambda: f.service.consume(consumed.record_wire, f.owners.worker_context),
                              extra=f.permit_keys(prepared.record_wire), code="KERNEL_PERMIT_NOT_PREPARED")

    def test_consume_after_all_insert_failure_retains_hold_and_exact_prepared_state(self):
        f = self.f
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        before = f.cut(keys)
        f.fail_commit = True
        try:
            with self.assertRaisesRegex(RuntimeError, "after all writer inserts"):
                f.service.consume(prepared.record_wire, f.owners.worker_context)
        finally:
            f.fail_commit = False
        self.assertEqual(f.cut(keys), before)
        self.assertEqual(f.budget()[2:], (COST, ZERO_BUDGET))
        f.reopen()
        f.service.consume(prepared.record_wire, f.owners.worker_context)
        self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))

    def test_recovery_floor_prevents_second_allocation_before_and_after_charge(self):
        f = self.fixture(limit=COST.add(RECOVERY))
        second = f.add_proposal("proposal:second")
        prepared = f.prepare()
        extra = f.permit_keys(prepared.record_wire) + (f.issuance_key("proposal:second"),)
        self.denied_unchanged(lambda: f.service.prepare(second, f.owners.worker_context),
                              fixture=f, extra=extra, code="KERNEL_BUDGET_EXHAUSTED")
        f.service.consume(prepared.record_wire, f.owners.worker_context)
        f.reopen()
        self.assertEqual(f.budget(), (COST.add(RECOVERY), RECOVERY, ZERO_BUDGET, COST))
        self.denied_unchanged(lambda: f.service.prepare(second, f.owners.worker_context),
                              fixture=f, extra=extra, code="KERNEL_BUDGET_EXHAUSTED")

    def test_project_owned_grant_uses_one_scope_writer_commit(self):
        f = self.fixture(grant_scope=PROJECT)
        prepared = f.prepare()
        self.assertEqual(tuple(h.before.scope_id for h in prepared.commit.history), (PROJECT,))
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        self.assertEqual(tuple(h.before.scope_id for h in consumed.commit.history), (PROJECT,))
        self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))

    def test_default_composition_and_live_admission_always_deny(self):
        f = self.f
        closed = compose_kernel(f.store, f.codec, INSTALLATION)
        for operation in (lambda: closed.prepare(f.proposal_wire, {"authenticated": True}),
                          lambda: closed.consume(b"{}", f.owners.worker_context),
                          lambda: closed.revoke(f.grant_wire, f.owners.owner_context, "reason:owner-revoke")):
            self.denied_unchanged(operation, code="KERNEL_OWNERS_UNAVAILABLE")
        for service in (closed, f.service):
            self.denied_unchanged(service.require_runtime_admission,
                                  code="RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE")

    def test_caller_flags_and_other_authenticated_peer_cannot_supply_basis_authority(self):
        f = self.f
        self.denied_unchanged(lambda: f.service.prepare(f.proposal_wire,
            {"authenticated": True, "owner_says_allow": True, "principal_id": f.owners.worker.principal_id}),
            code="FIXTURE_AUTHENTICATION_DENIED")
        self.denied_unchanged(lambda: f.service.prepare(f.proposal_wire, f.owners.owner_context),
                              code="FIXTURE_PREPARATION_DENIED")

    def test_validated_caller_proposal_without_owner_allowlist_is_denied(self):
        f = self.f
        value = dict(f.proposal, record_id="proposal:caller-validated", status="VALIDATED")
        wire = canonical_bytes(value)
        f.put(basis_key(PROJECT, value["record_id"]), f.make_basis(wire))
        self.denied_unchanged(lambda: f.service.prepare(wire, f.owners.worker_context),
                              code="FIXTURE_PREPARATION_DENIED")

    def test_valid_shaped_spoofed_basis_does_not_match_owner_allowlist(self):
        f = self.f
        value = strict_loads(f.basis)
        value["owner_input_commitment"] = CHANGED
        f.put(basis_key(PROJECT, f.proposal["record_id"]), canonical_bytes(value))
        self.denied_unchanged(f.prepare, code="FIXTURE_PREPARATION_DENIED")

    def test_changed_proposal_arguments_and_permit_arguments_are_denied(self):
        f = self.f
        changed = canonical_bytes(dict(f.proposal, arguments_commitment=CHANGED))
        self.denied_unchanged(lambda: f.service.prepare(changed, f.owners.worker_context),
                              code="FIXTURE_PREPARATION_DENIED")
        prepared = f.prepare()
        permit = strict_loads(prepared.record_wire)
        permit["arguments_commitment"] = CHANGED
        self.denied_unchanged(lambda: f.service.consume(canonical_bytes(permit), f.owners.worker_context),
                              extra=f.permit_keys(prepared.record_wire), code="KERNEL_PERMIT_BINDING_MISMATCH")

    def test_owner_admission_denial_preserves_hold_and_permit(self):
        f = self.f
        prepared = f.prepare()
        f.owners.admission_available = False
        self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                              extra=f.permit_keys(prepared.record_wire), code="FIXTURE_ADMISSION_DENIED")
        self.assertEqual(f.budget()[2:], (COST, ZERO_BUDGET))

    def test_every_relevant_owner_state_change_denies_consumption(self):
        for kind in ("authority", "fence", "policy", "environment", "task", "target", "owner-dependency", "registry"):
            with self.subTest(kind=kind):
                f = self.fixture()
                prepared = f.prepare()
                if kind in {"authority", "fence", "policy", "environment"}:
                    value = strict_loads(f.cell(f.control_key).value_wire)
                    field = {"authority": "authority_generation", "fence": "fence_generation",
                             "policy": "policy_commitment", "environment": "environment_commitment"}[kind]
                    value[field] = 2 if kind in {"authority", "fence"} else CHANGED
                    key, wire = f.control_key, canonical_bytes(value)
                elif kind == "task":
                    key, wire = task_key(PROJECT, "task:fixture"), task_wire(PROJECT, "task:fixture", CHANGED)
                elif kind == "registry":
                    value = strict_loads(f.cell(f.registry_key).value_wire)
                    value["commitment"] = CHANGED
                    key, wire = f.registry_key, canonical_bytes(value)
                else:
                    identifier = "resource:" + kind
                    key, wire = resource_key(PROJECT, identifier), resource_wire(PROJECT, identifier, CHANGED)
                f.put(key, wire)
                self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                    fixture=f, extra=f.permit_keys(prepared.record_wire), code="KERNEL_RELEVANT_STATE_CHANGED")

    def test_unrelated_projection_change_does_not_invalidate_owner_dependency_set(self):
        f = self.f
        prepared = f.prepare()
        f.put(StoreKey("projection", PROJECT, "unrelated:fixture"), canonical_bytes({"value": 2}))
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        self.assertEqual(f.codec.decode(consumed.record_wire).as_dict()["status"], "CONSUMED")
        evidence = f.service.resolve_consumption(f.codec.decode(consumed.record_wire))
        self.assertEqual(evidence.prior_position, consumed.prior_position)

    def test_grant_purpose_operation_access_and_status_are_checked(self):
        variations = ({"status": "PENDING"}, {"purpose_ref": "task:other"},
                      {"grantee_id": "worker:other"}, {"operation_classes": ["file.write"]},
                      {"resource_scope": [dict(self.f.proposal["resources"][0], access="WRITE")]})
        for changed in variations:
            with self.subTest(changed=changed):
                f = self.fixture()
                f.put(f.grant_key, canonical_bytes(dict(f.grant, **changed)))
                self.denied_unchanged(f.prepare, fixture=f)

    def test_exact_monotonic_expiry_denies_without_mutation(self):
        f = self.f
        prepared = f.prepare()
        deadline = strict_loads(f.cell(f.permit_keys(prepared.record_wire)[2]).value_wire)["deadline"]
        sample = replace(f.owners.samples[1], monotonic_ns=deadline["expires_monotonic_ns"],
                         wall_time_ns=deadline["expires_wall_ns"] - 1)
        f.owners.samples = (f.owners.samples[1], sample)
        self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                              extra=f.permit_keys(prepared.record_wire), code="DEADLINE_EXPIRED_OR_UNCERTAIN")

    def test_exact_wall_expiry_denies_before_monotonic_expiry(self):
        f = self.f
        prepared = f.prepare()
        deadline = strict_loads(f.cell(f.permit_keys(prepared.record_wire)[2]).value_wire)["deadline"]
        sample = replace(f.owners.samples[1], monotonic_ns=deadline["expires_monotonic_ns"] - 1,
                         wall_time_ns=deadline["expires_wall_ns"])
        f.owners.samples = (f.owners.samples[1], sample)
        self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                              extra=f.permit_keys(prepared.record_wire), code="DEADLINE_EXPIRED_OR_UNCERTAIN")

    def test_new_boot_epoch_resume_or_untrusted_time_cannot_redeem_old_deadline(self):
        for changed, code in (({"boot_id": "boot:new"}, "BOOT_CHANGED"),
                              ({"durable_epoch": 2}, "TIME_EPOCH_CHANGED"),
                              ({"resume_generation": 1}, "RESUME_GENERATION_CHANGED"),
                              ({"wall_trusted": False}, "TRUSTED_TIME_UNAVAILABLE")):
            with self.subTest(changed=changed):
                f = self.fixture()
                prepared = f.prepare()
                f.reopen()
                sample = replace(f.owners.samples[1], **changed)
                f.owners.samples = (sample, sample)
                self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                    fixture=f, extra=f.permit_keys(prepared.record_wire), code=code)

    def test_revoke_before_consume_denies_and_does_not_invent_refund(self):
        f = self.f
        prepared = f.prepare()
        revoked = f.service.revoke(f.grant_wire, f.owners.owner_context, "reason:owner-revoke")
        self.assertEqual(f.codec.decode(revoked.record_wire).as_dict()["status"], "REVOKED")
        self.assertEqual(f.codec.decode(revoked.record_wire).as_dict()["revocation_generation"], 1)
        f.reopen()
        self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                              extra=f.permit_keys(prepared.record_wire), code="KERNEL_RELEVANT_STATE_CHANGED")
        self.assertEqual(f.budget()[2:], (COST, ZERO_BUDGET))

    def test_consume_before_revoke_preserves_consumption_without_effect_claim(self):
        f = self.f
        prepared = f.prepare()
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        f.service.revoke(f.grant_wire, f.owners.owner_context, "reason:owner-revoke")
        f.reopen()
        self.assertEqual(f.cell(f.permit_keys(prepared.record_wire)[0]).value_wire, consumed.record_wire)
        self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))
        self.assertEqual(f.service.resolve_consumption(f.codec.decode(consumed.record_wire)).event_wire,
                         consumed.event_wire)
        self.denied_unchanged(f.service.require_runtime_admission, code="RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE")

    def test_wrong_revoker_or_reason_and_repeated_revocation_are_denied(self):
        f = self.f
        self.denied_unchanged(lambda: f.service.revoke(f.grant_wire, f.owners.worker_context, "reason:owner-revoke"),
                              code="FIXTURE_REVOCATION_DENIED")
        self.denied_unchanged(lambda: f.service.revoke(f.grant_wire, f.owners.owner_context, "reason:caller"),
                              code="FIXTURE_REVOCATION_DENIED")
        revoked = f.service.revoke(f.grant_wire, f.owners.owner_context, "reason:owner-revoke")
        self.denied_unchanged(lambda: f.service.revoke(revoked.record_wire, f.owners.owner_context, "reason:owner-revoke"),
                              code="KERNEL_GRANT_NOT_REVOCABLE")

    def test_two_real_connections_race_has_one_durable_winner_and_no_budget_overspend(self):
        f = self.fixture(limit=COST.add(RECOVERY))
        second = f.add_proposal("proposal:race-second")
        other = CommitBarrierJournal(f.root, f.codec, SCOPES, profile=STORE_PROFILE)
        barrier = threading.Barrier(2)
        f.store.commit_barrier = other.commit_barrier = barrier
        other_service = compose_kernel(other, f.codec, INSTALLATION, owners=f.owners)
        def attempt(service, wire):
            try:
                return service.prepare(wire, f.owners.worker_context)
            except ContractError as exc:
                return exc
        before = f.store.store_position()
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(attempt, f.service, f.proposal_wire)
                b = pool.submit(attempt, other_service, second)
                results = (a.result(timeout=20), b.result(timeout=20))
        finally:
            f.store.commit_barrier = other.commit_barrier = None
            other.close()
        winners = [r for r in results if not isinstance(r, ContractError)]
        failures = [r for r in results if isinstance(r, ContractError)]
        self.assertEqual((len(winners), len(failures)), (1, 1))
        self.assertIn(failures[0].code, {"JOURNAL_REVISION_CONFLICT", "STORE_REVISION_CONFLICT"})
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)
        self.assertEqual(f.budget(), (COST.add(RECOVERY), RECOVERY, COST, ZERO_BUDGET))
        winner_id = f.codec.decode(winners[0].record_wire).as_dict()["proposal_ref"]
        loser_id = "proposal:race-second" if winner_id == "proposal:fixture" else "proposal:fixture"
        self.assertIsNone(f.cell(f.issuance_key(loser_id)).value_wire)
        loser_wire = second if loser_id == "proposal:race-second" else f.proposal_wire
        self.denied_unchanged(lambda: f.service.prepare(loser_wire, f.owners.worker_context),
                              fixture=f, code="KERNEL_BUDGET_EXHAUSTED")

    def test_budget_cas_rejects_current_value_change_even_with_fresh_history_heads(self):
        f = self.f
        other = SqliteJournal(f.root, f.codec, SCOPES, profile=STORE_PROFILE)
        key = budget_key(f.grant_key)
        before = f.cut()
        before_cells = {cell.key: cell for cell in before[2]}
        original_position = f.store.position
        competing_recovery = RECOVERY.add(BudgetVector((1, 0, 0, 0, 0, 0, 0)))
        competing_wire = budget_wire(INSTALLATION, f.grant_key.record_id, LIMIT, competing_recovery)
        competing = []

        def position_after_competing_budget(scope):
            # prepare first asks for a public stream position after its complete
            # final snapshot. Mutate only the budget through the second real
            # writer, then let both commit stream positions be freshly observed.
            if scope == PROJECT and not competing:
                point = other.position(INSTALLATION)
                cell = other.snapshot((key,))[0]
                row = f.row(point, f.observation(INSTALLATION))
                receipt = other.commit((point,), (row,), changes=(StoreChange(
                    StoreExpectation(key, cell.revision), competing_wire,
                    strict_loads(row.event_wire)["record_id"]),))
                competing.append((receipt, row))
            return original_position(scope)

        f.store.last_commit_attempt = None
        f.store.position = position_after_competing_budget
        try:
            with self.assertRaises(ContractError) as caught:
                f.prepare()
            self.assertEqual(caught.exception.code, "STORE_REVISION_CONFLICT")
        finally:
            f.store.position = original_position
            other.close()

        self.assertEqual(len(competing), 1)
        receipt, row = competing[0]
        args, kwargs = f.store.last_commit_attempt
        self.assertEqual({point.scope_id: point for point in args[0]},
                         {scope: f.store.position(scope) for scope in SCOPES})
        self.assertEqual(f.store.store_position(), receipt.position)
        self.assertEqual(receipt.position.next_commit, before[0].next_commit + 1)
        self.assertEqual(f.store.position(PROJECT), before[1][1])
        self.assertEqual(f.store.replay(PROJECT), before[3][1])
        self.assertEqual(f.store.replay(INSTALLATION), before[3][0] + (row,))
        self.assertEqual(f.cell(key).value_wire, competing_wire)
        self.assertEqual(f.budget(), (LIMIT, competing_recovery, ZERO_BUDGET, ZERO_BUDGET))
        for cell in f.store.snapshot(tuple(before_cells)):
            if cell.key != key:
                self.assertEqual(cell, before_cells[cell.key])
        new_keys = tuple(change.expected.key for change in kwargs["changes"] if change.expected.key != key)
        self.assertEqual(len(new_keys), 4)
        self.assertEqual({new_key.collection for new_key in new_keys}, {"permit", "reservation", "intent", "projection"})
        self.assertTrue(all(cell.generation == 0 and cell.value_wire is None for cell in f.store.snapshot(new_keys)))
        accepted_event_ids = {strict_loads(accepted.event_wire)["record_id"]
                              for scope in SCOPES for accepted in f.store.replay(scope)}
        for attempted in args[1]:
            self.assertNotIn(strict_loads(attempted.event_wire)["record_id"], accepted_event_ids)

    def test_two_real_connections_consume_same_permit_once_with_single_charge(self):
        f = self.f
        prepared = f.prepare()
        other = CommitBarrierJournal(f.root, f.codec, SCOPES, profile=STORE_PROFILE)
        other_service = compose_kernel(other, f.codec, INSTALLATION, owners=f.owners)
        barrier = threading.Barrier(2)
        before = f.cut(f.permit_keys(prepared.record_wire))
        f.store.commit_barrier = other.commit_barrier = barrier

        def attempt(service):
            try:
                return service.consume(prepared.record_wire, f.owners.worker_context)
            except ContractError as exc:
                return exc

        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                a = pool.submit(attempt, f.service)
                b = pool.submit(attempt, other_service)
                results = (a.result(timeout=20), b.result(timeout=20))
        finally:
            f.store.commit_barrier = other.commit_barrier = None
            other.close()

        winners = [result for result in results if not isinstance(result, ContractError)]
        failures = [result for result in results if isinstance(result, ContractError)]
        self.assertEqual((len(winners), len(failures)), (1, 1))
        self.assertIn(failures[0].code, {"JOURNAL_REVISION_CONFLICT", "STORE_REVISION_CONFLICT", "KERNEL_PERMIT_NOT_PREPARED"})
        winner = winners[0]
        keys = f.permit_keys(prepared.record_wire)
        self.assertEqual(f.store.store_position().next_commit, before[0].next_commit + 1)
        self.assertEqual(f.cell(keys[0]).value_wire, winner.record_wire)
        self.assertEqual(f.budget(), (LIMIT, RECOVERY, ZERO_BUDGET, COST))
        self.assertEqual(strict_loads(f.cell(keys[1]).value_wire)["state"], "CHARGED")
        self.assertEqual(strict_loads(f.cell(keys[2]).value_wire)["state"], "ADMISSION_REDEEMED")
        for index, scope in enumerate(SCOPES):
            self.assertEqual(f.store.position(scope).next_sequence, before[1][index].next_sequence + 1)
        consume_rows = [row for row in f.store.replay(PROJECT)
                        if strict_loads(row.event_wire)["event_type"] == "kernel.permit.consumed"]
        self.assertEqual(consume_rows, [JournalEntry(winner.event_wire, winner.record_wire)])
        f.reopen()
        resolved = f.service.resolve_consumption(f.codec.decode(winner.record_wire))
        self.assertEqual((resolved.event_wire, resolved.consumed_permit_wire, resolved.prior_position),
                         (winner.event_wire, winner.record_wire, winner.prior_position))
        self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                              extra=keys, code="KERNEL_PERMIT_NOT_PREPARED")
        self.denied_unchanged(lambda: f.service.consume(winner.record_wire, f.owners.worker_context),
                              extra=keys, code="KERNEL_PERMIT_NOT_PREPARED")

    def test_forged_consumed_record_cannot_resolve_evidence_before_consumption(self):
        f = self.f
        prepared = f.prepare()
        forged = strict_loads(prepared.record_wire)
        forged.update(status="CONSUMED", consume_event_ref="event:caller-fiction")
        self.denied_unchanged(lambda: f.service.resolve_consumption(f.codec.decode(canonical_bytes(forged))),
                              extra=f.permit_keys(prepared.record_wire), code="CONSUMPTION_EVIDENCE_UNAVAILABLE")

    def test_consumption_resolver_rejects_changed_nonce_and_false_event_reference(self):
        f = self.f
        prepared = f.prepare()
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        for field, value in (("nonce", "nonce:caller"), ("consume_event_ref", "event:caller")):
            with self.subTest(field=field):
                forged = strict_loads(consumed.record_wire)
                forged[field] = value
                self.denied_unchanged(lambda: f.service.resolve_consumption(f.codec.decode(canonical_bytes(forged))),
                    extra=f.permit_keys(prepared.record_wire), code="CONSUMED_PERMIT_BINDING_MISMATCH")

    def test_persisted_boolean_deadline_metadata_is_not_bound_to_original_permit(self):
        f = self.f
        prepared = f.prepare()
        key = f.permit_keys(prepared.record_wire)[2]
        intention = strict_loads(f.cell(key).value_wire)
        intention["deadline"]["durable_epoch"] = True
        f.put(key, canonical_bytes(intention))
        self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                              extra=f.permit_keys(prepared.record_wire), code="KERNEL_INPUT_BINDING_MISMATCH")

    def test_missing_owner_dependency_or_forged_issuance_index_cannot_consume(self):
        for mutation in ("dependencies", "issuance"):
            with self.subTest(mutation=mutation):
                f = self.fixture()
                prepared = f.prepare()
                if mutation == "dependencies":
                    key = f.permit_keys(prepared.record_wire)[2]
                    value = strict_loads(f.cell(key).value_wire)
                    value["dependencies"] = value["dependencies"][:-1]
                else:
                    key = f.issuance_key()
                    value = strict_loads(f.cell(key).value_wire)
                    value["sequence"] = 0
                    value["previous_head"] = None
                f.put(key, canonical_bytes(value))
                self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                                      fixture=f, extra=f.permit_keys(prepared.record_wire))

    def test_basis_boolean_generation_and_nested_review_refs_reject_deterministically(self):
        for field in ("authority_generation", "review_refs"):
            with self.subTest(field=field):
                value = strict_loads(self.f.basis)
                if field == "authority_generation":
                    value["read_set"][field] = True
                else:
                    value[field] = [["review:caller"]]
                with self.assertRaises(ContractError):
                    read_basis(canonical_bytes(value), self.f.codec)
        with self.assertRaises(ContractError):
            self.f.make_basis(self.f.proposal_wire, review_refs=(["review:caller"],))

    def test_required_approval_absence_rejects_but_optional_approval_can_prepare_and_consume(self):
        with self.assertRaises(ContractError) as caught:
            self.f.make_basis(self.f.proposal_wire, approval=None)
        self.assertEqual(caught.exception.code, "KERNEL_APPROVAL_REQUIRED")
        value = strict_loads(self.f.basis)
        value["approval_evidence_ref"] = None
        with self.assertRaises(ContractError) as caught:
            read_basis(canonical_bytes(value), self.f.codec)
        self.assertEqual(caught.exception.code, "KERNEL_APPROVAL_REQUIRED")
        f = self.fixture(requires_approval=False, approval=None)
        prepared = f.prepare()
        self.assertIsNone(f.codec.decode(prepared.record_wire).as_dict()["approval_evidence_ref"])
        consumed = f.service.consume(prepared.record_wire, f.owners.worker_context)
        self.assertEqual(f.codec.decode(consumed.record_wire).as_dict()["status"], "CONSUMED")

    def test_budget_namespace_boolean_overflow_and_underflow_are_rejected(self):
        wire = self.f.cell(budget_key(self.f.grant_key)).value_wire
        with self.assertRaises(ContractError) as caught:
            read_budget(wire, self.f.grant_key)
        self.assertEqual(caught.exception.code, "KERNEL_BUDGET_KEY_REQUIRED")
        for invalid in ((True, 0, 0, 0, 0, 0, 0), (2**53, 0, 0, 0, 0, 0, 0)):
            with self.subTest(invalid=invalid), self.assertRaises(ContractError):
                BudgetVector(invalid)
        with self.assertRaises(ContractError):
            ZERO_BUDGET.subtract(COST)
        with self.assertRaises(ContractError):
            budget_wire(INSTALLATION, "grant:fixture", COST, RECOVERY, COST)

    def test_clock_expiry_inside_writer_rolls_back_prepare_and_consume(self):
        for operation in ("prepare", "consume"):
            with self.subTest(operation=operation):
                f = self.fixture()
                prepared = f.prepare() if operation == "consume" else None
                extra = f.permit_keys(prepared.record_wire) if prepared else ()
                def expire():
                    sample = f.owners.samples[1]
                    later = replace(sample, monotonic_ns=sample.monotonic_ns + COST.values[0] * 1_000_000,
                                    wall_time_ns=sample.wall_time_ns + COST.values[0] * 1_000_000)
                    f.owners.samples = (sample, later)
                f.before_commit_action = expire
                action = f.prepare if prepared is None else lambda: f.service.consume(prepared.record_wire, f.owners.worker_context)
                try:
                    self.denied_unchanged(action, fixture=f, extra=extra,
                                          code="DEADLINE_EXPIRED_OR_UNCERTAIN")
                finally:
                    f.before_commit_action = None
                self.assertEqual(f.budget()[2:], (COST if prepared else ZERO_BUDGET, ZERO_BUDGET))

    def test_resume_change_inside_writer_rolls_back_prepare_and_consume(self):
        for operation in ("prepare", "consume"):
            with self.subTest(operation=operation):
                f = self.fixture()
                prepared = f.prepare() if operation == "consume" else None
                extra = f.permit_keys(prepared.record_wire) if prepared else ()
                def resume():
                    sample = replace(f.owners.samples[1], resume_generation=1)
                    f.owners.samples = (sample, sample)
                f.before_commit_action = resume
                action = f.prepare if prepared is None else lambda: f.service.consume(prepared.record_wire, f.owners.worker_context)
                try:
                    self.denied_unchanged(action, fixture=f, extra=extra,
                                          code="RESUME_GENERATION_CHANGED")
                finally:
                    f.before_commit_action = None
                self.assertEqual(f.budget()[2:], (COST if prepared else ZERO_BUDGET, ZERO_BUDGET))

    def test_expiry_after_real_commit_rejects_return_but_keeps_permit_burned(self):
        f = self.f
        prepared = f.prepare()
        keys = f.permit_keys(prepared.record_wire)
        deadline = strict_loads(f.cell(keys[2]).value_wire)["deadline"]
        before = f.store.store_position()
        def expire_after_commit():
            sample = f.owners.samples[1]
            later = replace(sample, monotonic_ns=deadline["expires_monotonic_ns"],
                            wall_time_ns=deadline["expires_wall_ns"])
            f.owners.samples = (sample, later)
        f.store.after_commit = expire_after_commit
        try:
            with self.assertRaises(ContractError) as caught:
                f.service.consume(prepared.record_wire, f.owners.worker_context)
            self.assertEqual(caught.exception.code, "DEADLINE_EXPIRED_OR_UNCERTAIN")
        finally:
            f.store.after_commit = None
        self.assertEqual(f.store.store_position().next_commit, before.next_commit + 1)
        consumed = f.codec.decode(f.cell(keys[0]).value_wire)
        self.assertEqual(consumed.as_dict()["status"], "CONSUMED")
        self.assertIsNotNone(consumed.as_dict()["consume_event_ref"])
        self.assertEqual(f.budget()[2:], (ZERO_BUDGET, COST))
        self.assertEqual(strict_loads(f.cell(keys[1]).value_wire)["state"], "CHARGED")
        f.reopen()
        evidence = f.service.resolve_consumption(consumed)
        self.assertEqual(evidence.consumed_permit_wire, consumed.canonical_wire)
        self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                              extra=keys, code="KERNEL_PERMIT_NOT_PREPARED")
        self.denied_unchanged(f.service.require_runtime_admission, code="RUNTIME_AUTHORITY_OWNERS_UNAVAILABLE")

    def test_tombstoned_issuance_keeps_duplicate_preparation_closed(self):
        f = self.f
        prepared = f.prepare()
        f.put(f.issuance_key(), None)
        self.assertEqual(f.cell(f.issuance_key()).generation, 2)
        self.assertIsNone(f.cell(f.issuance_key()).value_wire)
        self.denied_unchanged(f.prepare, extra=f.permit_keys(prepared.record_wire),
                              code="KERNEL_PROPOSAL_ALREADY_PREPARED")
        self.assertEqual(f.budget()[2:], (COST, ZERO_BUDGET))

    def test_direct_partial_parsed_record_cannot_bypass_codec_in_consumption_resolver(self):
        f = self.f
        prepared = f.prepare()
        consumed = f.codec.decode(f.service.consume(prepared.record_wire, f.owners.worker_context).record_wire)
        partial = canonical_bytes({"scope_id": PROJECT, "record_id": consumed.record_id})
        for forged in (replace(consumed, canonical_wire=partial), replace(consumed, commitment=CHANGED),
                       replace(consumed, original_sha256=CHANGED)):
            with self.subTest(forged=forged.commitment):
                self.denied_unchanged(lambda: f.service.resolve_consumption(forged),
                    extra=f.permit_keys(prepared.record_wire), code="KERNEL_PARSED_RECORD_BINDING_MISMATCH")

    def test_changed_deadline_or_dependency_order_cannot_replace_bound_intent(self):
        for mutation in ("deadline", "dependencies"):
            with self.subTest(mutation=mutation):
                f = self.fixture()
                prepared = f.prepare()
                key = f.permit_keys(prepared.record_wire)[2]
                value = strict_loads(f.cell(key).value_wire)
                if mutation == "deadline":
                    value["deadline"]["issued_monotonic_ns"] += 1
                else:
                    value["dependencies"] = list(reversed(value["dependencies"]))
                f.put(key, canonical_bytes(value))
                self.denied_unchanged(lambda: f.service.consume(prepared.record_wire, f.owners.worker_context),
                    fixture=f, extra=f.permit_keys(prepared.record_wire), code="KERNEL_INPUT_BINDING_MISMATCH")

    def test_deadline_formatter_round_trips_exact_nanoseconds_and_rejects_boolean(self):
        for value in (MIN_INTEGER, -1, 0, 1, MAX_INTEGER):
            with self.subTest(value=value):
                self.assertEqual(utc_nanoseconds(deadline_text(value)), value)
        for value in (True, False, 1.0, MIN_INTEGER - 1, MAX_INTEGER + 1):
            with self.subTest(invalid=value), self.assertRaises(ContractError) as caught:
                deadline_text(value)
            self.assertEqual(caught.exception.code, "INVALID_TEMPORAL_INTEGER")


if __name__ == "__main__":
    unittest.main()
