"""Source-bound transition predicates, without mutable state or runtime authority.

Caller-supplied witnesses are unauthenticated. The responsible kernel/store/
broker must establish them at its real boundary; a positive assessment here
does not commit, issue, redeem, dispatch, settle, or qualify anything.
"""
from dataclasses import dataclass
import hashlib

from .wire import ContractError, strict_loads

MODEL_PROFILE = "ceta-transition-assessment-v1"
_STATE_SHA = "232807fa439247ebc9a3da669710f9badf38ac5166549e3f58c6f2448aba45ca"
_RULE_SHA = "f36239d7a0d7f21829b88f529ff1b5a4a92ea37eb927afe526203376b955467c"
_CUSTODY_SHA = "35f785363a731ee2c88ec88048ef9f7c4d9b4cca6e132582876a3276d2f8c703"
_SCHEMA_SHA = "f83f8a1116492266aa9ffbbf85c4e4677218e99d8771f0de61a3affef8313f79"

# Input labels decompose the existing TR predicates. They are not new grants,
# wire record types, authenticated providers, or a second authority registry.
_GUARDS = {
    "TR-01": (("owner_authenticated", "CMP-04"), ("exact_objective_scope_accepted", "CMP-04"), ("finite_grant_recorded", "CMP-02")),
    "TR-02": (("material_interpretation_unresolved", "CMP-07"), ("bounded_question_and_raw_request_preserved", "CMP-07")),
    "TR-03": (("typed_hard_prerequisites_current", "CMP-02"), ("current_policy_satisfied", "CMP-02"), ("required_evidence_satisfied", "CMP-02")),
    "TR-04": (("executor_identity_bound", "CMP-04"), ("input_graph_lease_fence_current", "CMP-02"), ("capacity_scope_conflict_absent", "CMP-02"), ("single_claim_committed_atomically", "CMP-03")),
    "TR-05": (("actual_receipt_and_output_bound", "CMP-14"), ("required_observations_verify_exact_candidate_input", "CMP-15")),
    "TR-06": (("typed_bounded_operation_actual_inputs", "CMP-02"), ("required_staged_artifacts_bound", "CMP-11"), ("required_reviews_current", "CMP-12"), ("exact_consent_current", "CMP-04")),
    "TR-07": (("authority_and_complete_read_set_current", "CMP-02"), ("reservation_and_intent_committed_atomically", "CMP-03")),
    "TR-08": (("peer_authenticated", "CMP-04"), ("fence_permit_revocation_current", "CMP-14"), ("actual_resource_handle_preconditions_valid", "CMP-14"), ("permit_consumed_once_at_admission", "CMP-14")),
    "TR-09": (("exact_registered_operation_parameters_dispatched", "CMP-14"), ("bounded_dispatch_observed", "CMP-14")),
    "TR-10": (("actual_owned_process_termination_observed", "CMP-14"), ("exit_and_output_retained", "CMP-14")),
    "TR-11": (("independent_required_postcondition_observed", "CMP-15"), ("current_state_settlement_committed", "CMP-02")),
    "TR-12": (("possible_external_effect_without_settlement_evidence", "CMP-14"), ("spent_or_uncertain_permit_preserved", "CMP-02"), ("resource_dependent_work_fenced", "CMP-02")),
    "TR-13": (("fresh_observations_adapter_settlement_predicate", "CMP-15"), ("causal_attribution_not_invented", "CMP-02"), ("any_compensation_has_fresh_authority", "CMP-02")),
    "TR-14": (("stop_authenticated", "CMP-04"), ("new_admission_disabled_at_boundary", "CMP-02"), ("bounded_owned_worker_stop_sent", "CMP-05")),
    "TR-15": (("owned_workers_observed_stopped", "CMP-05"), ("further_admission_impossible", "CMP-02"), ("unresolved_effects_separately_recorded", "CMP-03")),
    "TR-16": (("object_scoped_proof_policy_epoch_current", "CMP-18"), ("real_required_quorum_verified", "CMP-19"), ("approved_consumer_boundary_valid", "CMP-18")),
    "TR-17": (("permitted_operation_completed", "CMP-18"), ("actual_key_buffer_cleanup_qualified_profile", "CMP-18"), ("outcome_evidence_committed", "CMP-03")),
    "TR-18": (("declared_tests_thresholds_real_configuration_match", "CMP-25"), ("reviewer_independence_and_evidence_match", "CMP-15")),
    "TR-19": (("correction_lifecycle_authorized", "CMP-02"), ("original_provenance_preserved", "CMP-03"), ("effective_retrieval_dependent_claims_updated", "CMP-08")),
    "TR-20": (("exact_rehearsal_backup_restoration_verified", "CMP-23"), ("quiescence_established", "CMP-05"), ("current_owner_cutover_approval", "CMP-04")),
}
# A named intermediate exists, but supplied clauses do not establish whether
# the principal entry is direct, abbreviated, optional, or observational.
# No subedge is synthesized. Resolution requires a recorded source decision.
_OPEN_INTERMEDIATES = {
    "TR-04": ("CLAIMED",),
    "TR-06": ("VALIDATED",),
    "TR-09": ("DISPATCHED",),
    "TR-11": ("OBSERVED",),
    "TR-13": ("OBSERVING", "RESOLVED_CURRENT_STATE"),
    "TR-20": ("AWAITING_CUTOVER",),
}
_RECORD_DOMAINS = {
    "GRAPH_NODE": ("PlanNode", "state"),
    "RECOVERY": ("RecoveryRecord", "status"),
    "MIGRATION": ("MigrationRecord", "status"),
    "QUALIFICATION": ("CapabilityQualification", "status"),
    "MEMORY": ("MemoryRecord", "lifecycle"),
    "PERMIT": ("OperationPermit", "status"),
    "GRANT": ("StandingGrant", "status"),
    "QUEUE": ("QueueItem", "status"),
    "COMPANION": ("CompanionIdentity", "status"),
    "PROPOSAL": ("ActionProposal", "status"),
}


def _bound_json(raw: bytes, expected_sha: str):
    if type(raw) is not bytes or hashlib.sha256(raw).hexdigest() != expected_sha:
        raise ContractError("TRANSITION_SOURCE_IDENTITY_MISMATCH")
    return strict_loads(raw)


@dataclass(frozen=True)
class Guard:
    name: str
    required_provider: str


@dataclass(frozen=True)
class PredicateWitness:
    """Unauthenticated input claim; evidence references are not proof checks."""
    predicate: str
    provider_component: str
    satisfied: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if (type(self.predicate) is not str or not self.predicate
                or type(self.provider_component) is not str
                or type(self.satisfied) is not bool
                or type(self.evidence_refs) is not tuple
                or len(self.evidence_refs) > 64
                or any(type(ref) is not str or not 1 <= len(ref) <= 1024
                       for ref in self.evidence_refs)
                or len(set(self.evidence_refs)) != len(self.evidence_refs)):
            raise ContractError("INVALID_TRANSITION_WITNESS")


@dataclass(frozen=True)
class TransitionRule:
    rule_id: str
    domain: str
    from_state: str
    to_state: str
    required_predicate: str
    on_failure: str
    acceptance_ids: tuple[str, ...]
    guards: tuple[Guard, ...]
    unresolved_intermediates: tuple[str, ...]
    required_intermediates: tuple[str, ...] = ()


@dataclass(frozen=True)
class TransitionAssessment:
    """A pure model result, never a state change or executable permission."""
    rule_id: str | None
    predicates_satisfied: bool
    direct_edge_supported: bool
    unresolved_intermediates: tuple[str, ...]
    unmet_predicates: tuple[str, ...]
    reason: str
    on_failure: str | None
    acceptance_ids: tuple[str, ...]
    implementation_status: str = "IMPLEMENTED_NOT_QUALIFIED"
    runtime_authorized: bool = False


@dataclass(frozen=True, init=False)
class TransitionModel:
    catalog: tuple[tuple[str, tuple[str, ...]], ...]
    record_enumerations: tuple[tuple[str, str, tuple[str, ...]], ...]
    state_families: tuple[tuple[str, tuple[str, ...]], ...]
    rules: tuple[TransitionRule, ...]
    direct_edges: tuple[TransitionRule, ...]
    source_hashes: tuple[tuple[str, str], ...]

    def __init__(self, state_catalog: bytes, transition_rules: bytes,
                 records_schema: bytes, custody_specification: bytes) -> None:
        catalog = _bound_json(state_catalog, _STATE_SHA)
        source = _bound_json(transition_rules, _RULE_SHA)
        schema = _bound_json(records_schema, _SCHEMA_SHA)
        if (type(custody_specification) is not bytes
                or hashlib.sha256(custody_specification).hexdigest() != _CUSTODY_SHA):
            raise ContractError("TRANSITION_SOURCE_IDENTITY_MISMATCH")
        preserved = tuple((key, tuple(value)) for key, value in catalog.items()
                          if type(value) is list)
        families = [(key.upper(), values) for key, values in preserved
                    if key in ("supervisor", "task", "effect", "vault")]
        enums = tuple((name, field, tuple(value["enum"]))
                      for name, definition in schema["$defs"].items()
                      for field, value in definition.get("properties", {}).items()
                      if "enum" in value)
        for domain, (record, field) in _RECORD_DOMAINS.items():
            families.append((domain, tuple(schema["$defs"][record]["properties"][field]["enum"])))
        family_map = dict(families)
        rules = []
        for entry in source["rules"]:
            rule_id = entry["id"]
            if (rule_id not in _GUARDS or entry["domain"] not in family_map
                    or entry["from"] not in family_map[entry["domain"]]
                    or entry["to"] not in family_map[entry["domain"]]):
                raise ContractError("TRANSITION_SOURCE_DOMAIN_MISMATCH")
            intermediate = _OPEN_INTERMEDIATES.get(rule_id, ())
            if any(state not in family_map[entry["domain"]] for state in intermediate):
                raise ContractError("TRANSITION_INTERMEDIATE_MISSING")
            rules.append(TransitionRule(
                rule_id, entry["domain"], entry["from"], entry["to"],
                entry["required_predicate"], entry["on_failure"],
                tuple(entry["acceptance_ids"]),
                tuple(Guard(name, owner) for name, owner in _GUARDS[rule_id]),
                intermediate, {"TR-16": ("VERIFYING",), "TR-17": ("ZEROIZING",)}.get(rule_id, ())))
        if tuple(rule.rule_id for rule in rules) != tuple(_GUARDS):
            raise ContractError("TRANSITION_RULE_COVERAGE_MISMATCH")
        principal = {rule.rule_id: rule for rule in rules}
        # REQ-25-01 explicitly supplies these four normal edges. Preserve the
        # principal TR-16/17 entries; do not permit their abbreviated shortcuts.
        normal_vault = (
            ("TR-16", "SEALED", "VERIFYING",
             (Guard("object_request_metadata_provenance_valid", "CMP-18"),)),
            ("TR-16", "VERIFYING", "AUTHORIZED_RELEASE", principal["TR-16"].guards),
            ("TR-17", "AUTHORIZED_RELEASE", "ZEROIZING",
             (Guard("permitted_operation_completed", "CMP-18"),
              Guard("qualified_secret_handling_available", "CMP-18"))),
            ("TR-17", "ZEROIZING", "SEALED", principal["TR-17"].guards),
        )
        direct = [rule for rule in rules
                  if not rule.unresolved_intermediates and not rule.required_intermediates]
        for rule_id, before, after, guards in normal_vault:
            source_rule = principal[rule_id]
            direct.append(TransitionRule(
                rule_id, "VAULT", before, after,
                "REQ-25-01 normal sequence; REQ-25-02/04 boundary duties; "
                + source_rule.required_predicate, source_rule.on_failure,
                tuple(sorted(set(source_rule.acceptance_ids)
                             | {"B089", "B093", "B095", "B096"})), guards, ()))
        object.__setattr__(self, "direct_edges", tuple(direct))
        object.__setattr__(self, "catalog", preserved)
        object.__setattr__(self, "record_enumerations", enums)
        object.__setattr__(self, "state_families", tuple(families))
        object.__setattr__(self, "rules", tuple(rules))
        object.__setattr__(self, "source_hashes", (
            ("state_catalog.json", _STATE_SHA), ("transition_rules.json", _RULE_SHA),
            ("schemas/records.schema.json", _SCHEMA_SHA),
            ("docs/specification/25_defensive_vault_custody.md", _CUSTODY_SHA)))

    def rule(self, rule_id: str) -> TransitionRule:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule
        raise ContractError("UNKNOWN_TRANSITION_RULE")

    def assess(self, domain: str, from_state: str, to_state: str,
               witnesses: tuple[PredicateWitness, ...]) -> TransitionAssessment:
        """Evaluate supplied claims; never infer missing edges or current truth."""
        families = dict(self.state_families)
        if (type(domain) is not str or domain not in families
                or type(from_state) is not str or from_state not in families[domain]
                or type(to_state) is not str or to_state not in families[domain]):
            raise ContractError("UNKNOWN_TRANSITION_STATE")
        if (type(witnesses) is not tuple or len(witnesses) > 64
                or any(type(witness) is not PredicateWitness for witness in witnesses)):
            raise ContractError("INVALID_TRANSITION_WITNESSES")
        candidates = self.direct_edges + tuple(
            rule for rule in self.rules if rule.unresolved_intermediates or rule.required_intermediates)
        chosen = tuple(rule for rule in candidates
                       if (rule.domain, rule.from_state, rule.to_state)
                       == (domain, from_state, to_state))
        if not chosen:
            return TransitionAssessment(
                None, False, False, (), (), "VERIFIED_UNRESOLVED", None, ())
        rule = chosen[0]
        claims = {w.predicate: w for w in witnesses}
        if len(claims) != len(witnesses):
            raise ContractError("DUPLICATE_TRANSITION_WITNESS")
        allowed = {g.name for g in rule.guards}
        if set(claims) - allowed:
            raise ContractError("UNKNOWN_TRANSITION_PREDICATE")
        unmet = tuple(g.name for g in rule.guards
                      if (g.name not in claims
                          or not claims[g.name].satisfied
                          or not claims[g.name].evidence_refs
                          or claims[g.name].provider_component != g.required_provider))
        if rule.required_intermediates:
            reason = "SOURCE_DEFINED_SEQUENCE_SHORTCUT_DENIED"
        elif rule.unresolved_intermediates:
            reason = "VERIFIED_UNRESOLVED"
        elif unmet:
            reason = "PREDICATE_NOT_ESTABLISHED"
        else:
            reason = "PREDICATES_SATISFIED_UNDER_SUPPLIED_INPUTS"
        return TransitionAssessment(
            rule.rule_id, not unmet, not rule.unresolved_intermediates and not rule.required_intermediates and not unmet,
            rule.unresolved_intermediates, unmet, reason,
            rule.on_failure, rule.acceptance_ids)
