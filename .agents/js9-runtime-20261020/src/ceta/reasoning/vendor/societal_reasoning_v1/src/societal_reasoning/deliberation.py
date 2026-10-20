"""Version 1: bounded, evidence-linked deliberation over *proposed* readings.

This engine cannot infer an arbitrary person's motives from a passage. A caller
supplies candidate readings and warrants; the core checks attributed evidence,
conditional relevance, disagreement, and counterfactual changes. It never
promotes a proposed interpretation into an observed event or a personal label.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

from .context import CATEGORIES, assemble_context, compare_context
from .models import Scenario
from .relevance import EvidenceText, KnowledgeRelevance
from .input_boundary import _REF
from .semantic_support import WarrantPremise, check_premise, find_opposed_source_assertions
from .reading_support import assess_reading_sources, source_language_signals

_ROLES = frozenset({"support", "challenge"})
_PROPOSERS = frozenset({"caller", "model_proposal"})


def _bounded(value: Any, name: str, limit: int = 1024) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{name} must be a nonempty string of at most {limit} characters")
    return value


def _keys(row: Any, required: set[str], optional: set[str], name: str) -> None:
    if not isinstance(row, dict) or not required <= set(row) or set(row) - (required | optional):
        raise ValueError(f"Invalid {name} fields")


@dataclass(frozen=True, slots=True)
class ContextCondition:
    category: str
    value: str

    def __post_init__(self) -> None:
        if self.category not in CATEGORIES:
            raise ValueError("Unknown condition category")
        _bounded(self.value, "condition value")

    @classmethod
    def from_dict(cls, row: dict) -> ContextCondition:
        _keys(row, {"category", "value"}, set(), "context condition")
        if row["category"] not in CATEGORIES:
            raise ValueError("Unknown condition category")
        return cls(row["category"], _bounded(row["value"], "condition value").strip())

    def to_dict(self) -> dict:
        return {"category": self.category, "value": self.value}


@dataclass(frozen=True, slots=True)
class Warrant:
    evidence_id: str
    role: str
    rationale: str
    conditions: tuple[ContextCondition, ...] = ()
    premise: WarrantPremise | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, str) or not _REF.fullmatch(self.evidence_id):
            raise ValueError("Invalid warrant evidence ID")
        if self.role not in _ROLES:
            raise ValueError("Invalid warrant role")
        _bounded(self.rationale, "warrant rationale", 2048)
        if len(self.conditions) > 8 or any(not isinstance(c, ContextCondition) for c in self.conditions):
            raise ValueError("Invalid warrant conditions")
        if len({c.category for c in self.conditions}) != len(self.conditions):
            raise ValueError("Repeated category in warrant conditions")
        if self.premise is not None and not isinstance(self.premise, WarrantPremise):
            raise ValueError("Premise must use the validated evidence-check contract")

    @classmethod
    def from_dict(cls, row: dict) -> Warrant:
        _keys(row, {"evidence_id", "role", "rationale"}, {"conditions", "premise"}, "warrant")
        evidence_id = _bounded(row["evidence_id"], "evidence ID", 128)
        if not _REF.fullmatch(evidence_id) or row["role"] not in _ROLES:
            raise ValueError("Invalid warrant evidence ID or role")
        raw = row.get("conditions", [])
        if not isinstance(raw, list) or len(raw) > 8:
            raise ValueError("Warrant conditions must be at most eight items")
        conditions = tuple(ContextCondition.from_dict(x) for x in raw)
        if len({x.category for x in conditions}) != len(conditions):
            raise ValueError("Duplicate context condition category in one warrant")
        premise = WarrantPremise.from_dict(row["premise"]) if "premise" in row else None
        return cls(evidence_id, row["role"], _bounded(row["rationale"], "warrant rationale", 2048), conditions, premise)


@dataclass(frozen=True, slots=True)
class Hypothesis:
    id: str
    reading: str
    proposed_by: str
    warrants: tuple[Warrant, ...]
    concept_ids: tuple[int, ...] = ()
    unknowns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not _REF.fullmatch(self.id):
            raise ValueError("Invalid hypothesis ID")
        _bounded(self.reading, "proposed reading", 4096)
        if self.proposed_by not in _PROPOSERS:
            raise ValueError("Invalid hypothesis proposer")
        if not 1 <= len(self.warrants) <= 32 or any(not isinstance(w, Warrant) for w in self.warrants):
            raise ValueError("Invalid hypothesis warrants")
        if len(self.concept_ids) > 16 or len(set(self.concept_ids)) != len(self.concept_ids):
            raise ValueError("Invalid concept references")
        if any(type(cid) is not int or cid < 1 for cid in self.concept_ids):
            raise ValueError("Invalid concept ID")
        identities = [(w.evidence_id, w.role, tuple((c.category, c.value.casefold()) for c in w.conditions))
                      for w in self.warrants]
        if len(set(identities)) != len(identities):
            raise ValueError("Duplicate hypothesis warrant")
        if len(self.unknowns) > 16:
            raise ValueError("Too many unknowns")
        for unknown in self.unknowns:
            _bounded(unknown, "unknown", 512)

    @classmethod
    def from_dict(cls, row: dict) -> Hypothesis:
        _keys(row, {"id", "reading", "proposed_by", "warrants"}, {"concept_ids", "unknowns"}, "hypothesis")
        identifier = _bounded(row["id"], "hypothesis ID", 128)
        if not _REF.fullmatch(identifier) or row["proposed_by"] not in _PROPOSERS:
            raise ValueError("Invalid hypothesis ID or proposer")
        warrants = row["warrants"]
        if not isinstance(warrants, list) or not 1 <= len(warrants) <= 32:
            raise ValueError("Hypothesis requires 1..32 auditable warrants")
        parsed_warrants = tuple(Warrant.from_dict(item) for item in warrants)
        fingerprints = [(w.evidence_id, w.role, tuple((c.category, c.value.casefold()) for c in w.conditions))
                        for w in parsed_warrants]
        if len(set(fingerprints)) != len(fingerprints):
            raise ValueError("Duplicate warrant for identical evidence, role and conditions")
        raw_ids = row.get("concept_ids", [])
        if not isinstance(raw_ids, list) or len(raw_ids) > 16 or any(type(x) is not int or x < 1 for x in raw_ids):
            raise ValueError("Invalid concept ID references")
        if len(set(raw_ids)) != len(raw_ids):
            raise ValueError("Duplicate concept reference")
        unknowns = row.get("unknowns", [])
        if not isinstance(unknowns, list) or len(unknowns) > 16:
            raise ValueError("Unknowns must be a bounded list")
        return cls(identifier, _bounded(row["reading"], "proposed reading", 4096), row["proposed_by"],
                   parsed_warrants, tuple(raw_ids), tuple(_bounded(u, "unknown", 512) for u in unknowns))


@dataclass(frozen=True, slots=True)
class DeliberationCase:
    scenario: Scenario
    hypotheses: tuple[Hypothesis, ...]
    context_facts: tuple[dict, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.scenario, Scenario):
            raise ValueError("Expected Scenario")
        if not 1 <= len(self.hypotheses) <= 16 or any(not isinstance(h, Hypothesis) for h in self.hypotheses):
            raise ValueError("Expected 1..16 validated hypotheses")
        if len({h.id for h in self.hypotheses}) != len(self.hypotheses):
            raise ValueError("Duplicate hypothesis identifier")
        if len(self.scenario.evidence) > 64 or sum(len(e.statement) for e in self.scenario.evidence) > 65536:
            raise ValueError("Evidence exceeds resource bounds")
        if len(self.scenario.unknowns) > 32 or len(self.scenario.question) > 4096:
            raise ValueError("Scenario metadata exceeds resource bounds")
        for ev in self.scenario.evidence:
            if not isinstance(ev.id, str) or not _REF.fullmatch(ev.id):
                raise ValueError("Invalid evidence identifier")
            if not isinstance(ev.statement, str) or not 0 < len(ev.statement) <= 4096:
                raise ValueError("Invalid evidence statement")
            if ev.source_ref is not None and (not isinstance(ev.source_ref, str) or
                                              not ev.source_ref.strip() or len(ev.source_ref) > 512):
                raise ValueError("Invalid evidence source reference")
            if len(ev.cues) > 32:
                raise ValueError("Evidence cue limit exceeded")
        valid_ids = {ev.id for ev in self.scenario.evidence}
        if len(valid_ids) != len(self.scenario.evidence):
            raise ValueError("Duplicate source IDs in directly constructed scenario")
        for hypothesis in self.hypotheses:
            for warrant in hypothesis.warrants:
                if warrant.evidence_id not in valid_ids:
                    raise ValueError("Unknown evidence ID in hypothesis warrant")
        assemble_context(self.context_facts)

    @classmethod
    def from_dict(cls, row: dict) -> DeliberationCase:
        _keys(row, {"scenario", "hypotheses"}, {"context_facts"}, "deliberation case")
        if not isinstance(row["scenario"], dict):
            raise ValueError("Scenario must be a JSON object")
        for ev in row["scenario"].get("evidence", []):
            if not isinstance(ev, dict) or not isinstance(ev.get("id"), str) or not isinstance(ev.get("statement"), str):
                raise ValueError("Malformed evidence record")
        scenario = Scenario.from_dict(row["scenario"])
        if len(scenario.evidence) > 64 or sum(len(e.statement) for e in scenario.evidence) > 65536:
            raise ValueError("Evidence count/text limit exceeded")
        for evidence in scenario.evidence:
            if not isinstance(evidence.id, str) or not _REF.fullmatch(evidence.id):
                raise ValueError("Evidence has invalid ID")
            if not isinstance(evidence.statement, str) or not 0 < len(evidence.statement) <= 4096:
                raise ValueError("Invalid evidence text bound")
            if evidence.source_ref is not None and (not isinstance(evidence.source_ref, str) or
                                                    len(evidence.source_ref) > 512):
                raise ValueError("Invalid evidence source reference")
        raw_hypotheses = row["hypotheses"]
        if not isinstance(raw_hypotheses, list) or not 1 <= len(raw_hypotheses) <= 16:
            raise ValueError("A case requires 1..16 proposed interpretations")
        hypotheses = tuple(Hypothesis.from_dict(x) for x in raw_hypotheses)
        if len({h.id for h in hypotheses}) != len(hypotheses):
            raise ValueError("Duplicate hypothesis ID")
        evidence_ids = {ev.id for ev in scenario.evidence}
        for hypothesis in hypotheses:
            for warrant in hypothesis.warrants:
                if warrant.evidence_id not in evidence_ids:
                    raise ValueError(f"Dangling evidence reference: {warrant.evidence_id}")
        facts = row.get("context_facts", [])
        if not isinstance(facts, list) or len(facts) > 64:
            raise ValueError("Context must be a bounded list")
        context = tuple(facts)
        assemble_context(context)  # Validation including duplicate IDs and origins.
        return cls(scenario, hypotheses, context)


def _condition_verdict(conditions: tuple[ContextCondition, ...], context: dict) -> tuple[str, list[dict]]:
    if not conditions:
        return "applicable", []
    factors = [f for f in context["reported_or_proposed_factors"] if f["origin"] != "model_hypothesis"]
    conflicts = {f["category"] for f in context["source_conflicts"]}
    decisions = []
    for condition in conditions:
        vals = [x for x in factors if x["category"] == condition.category]
        if condition.category in conflicts:
            state = "unresolved_conflicting_reports"
            provenance_ids = []
        elif not vals:
            state = "not_established"
            provenance_ids = []
        elif any(x["value"].casefold().strip() == condition.value.casefold() for x in vals):
            state = "matched_report_not_independently_verified"
            provenance_ids = [x["id"] for x in vals if x["value"].casefold().strip() == condition.value.casefold()]
        else:
            state = "contrary_reported_context"
            provenance_ids = [x["id"] for x in vals]
        decisions.append({**condition.to_dict(), "decision": state, "context_factor_ids": provenance_ids})
    if any(x["decision"] == "unresolved_conflicting_reports" for x in decisions):
        return "unresolved_conflict", decisions
    if any(x["decision"] == "contrary_reported_context" for x in decisions):
        return "not_applicable_to_this_context", decisions
    if any(x["decision"] == "not_established" for x in decisions):
        return "context_not_established", decisions
    return "applicable", decisions


def evaluate_case(case: DeliberationCase, *, relevance: KnowledgeRelevance) -> dict[str, Any]:
    """Assess *support for submitted hypotheses*, never validate their truth.

    Active warrants indicate report-backed arguments, not causal proof, mind
    reading, independent confirmation, probability or justified attribution.
    """
    if not isinstance(case, DeliberationCase) or not isinstance(relevance, KnowledgeRelevance):
        raise ValueError("Expected a validated DeliberationCase and knowledge retriever")
    context = assemble_context(case.context_facts)
    evidence = {e.id: e for e in case.scenario.evidence}
    literal_oppositions = find_opposed_source_assertions(case.scenario.evidence)
    surface_signals = source_language_signals(case.scenario.evidence)
    found = []
    for hypothesis in case.hypotheses:
        linked_concepts = []
        for cid in hypothesis.concept_ids:
            concept = relevance.graph.get(cid)
            if concept is None:
                raise ValueError(f"Hypothesis references nonexistent concept {cid}")
            linked_concepts.append({"concept_id": cid, "label": concept.label, "status": concept.status,
                                    "use": "contextual_topic_only_not_supporting_evidence"})
        rows = {"support": [], "challenge": [], "deferred": [], "inactive": [], "excluded": []}
        for warrant in hypothesis.warrants:
            item = evidence[warrant.evidence_id]
            condition_state, condition_trace = _condition_verdict(warrant.conditions, context)
            premise_check = (check_premise(item, warrant.premise) if warrant.premise is not None
                             else {"status": "not_requested", "factual_truth_checked": False,
                                   "social_inference_validated": False})
            receipt = {
                "evidence_id": item.id, "evidence_origin": item.origin,
                "source_ref": item.source_ref,
                "source_sha256": sha256(item.statement.encode("utf-8")).hexdigest(),
                "evidence_text": item.statement,
                "asserted_role": warrant.role,
                "proposed_rationale": warrant.rationale,
                "rationale_semantically_verified": False,
                "premise_check": premise_check,
                "warrant_role_is_proposed_not_independently_adjudicated": True,
                "condition_state": condition_state,
                "condition_trace": condition_trace,
                "evidence_is_report_not_certified_fact": True,
            }
            if item.origin == "interpretation":
                receipt["reason"] = "prior_interpretation_cannot_count_as_observational_evidence"
                rows["excluded"].append(receipt)
            elif premise_check["status"] in {"stale_source_binding", "source_explicitly_opposes_claim",
                                             "excluded_prior_interpretation"}:
                receipt["reason"] = "premise_binding_or_explicit_polarity_failed"
                rows["excluded"].append(receipt)
            elif premise_check["status"] not in {"not_requested", "source_text_matched",
                                                    "source_asserts_literal_proposition"}:
                receipt["reason"] = "premise_not_supported_by_supplied_source"
                rows["deferred"].append(receipt)
            elif condition_state == "not_applicable_to_this_context":
                rows["inactive"].append(receipt)
            elif condition_state != "applicable":
                rows["deferred"].append(receipt)
            else:
                rows[warrant.role].append(receipt)
        # This status is deliberately about the submitted *argument*, not the
        # truth of the reading, the person, or what was actually experienced.
        if rows["support"] and rows["challenge"]:
            status = "active_pro_and_con_warrants_not_semantic_proof"
        elif rows["support"]:
            status = "active_pro_warrants_not_semantic_proof"
        elif rows["challenge"]:
            status = "active_con_warrants_only"
        else:
            status = "no_active_supporting_warrants"
        source_groups = sorted({(p["source_ref"] if p["source_ref"] is not None else "unknown-origin")
                                for p in rows["support"]})
        reading_alignment = assess_reading_sources(hypothesis.reading, case.scenario.evidence)
        found.append({
            "id": hypothesis.id, "reading": hypothesis.reading,
            "reading_source_alignment": reading_alignment,
            "proposed_by": hypothesis.proposed_by,
            "proposer_identity_authenticated": False,
            "status": status,
            "supporting_warrants": rows["support"],
            "challenging_warrants": rows["challenge"],
            "deferred_warrants": rows["deferred"],
            "inactive_warrants": rows["inactive"],
            "excluded_warrants": rows["excluded"],
            "supporting_source_refs_not_independence_proof": source_groups,
            "not_established": list(hypothesis.unknowns),
            "related_concepts_not_premises": linked_concepts,
            "conclusion_status": "proposed_interpretation_not_factual_finding",
            "semantic_entailment_checked": False,
            "related_opposed_source_reports": [
                opposite for opposite in literal_oppositions
                if any(ev_id in {w.evidence_id for w in hypothesis.warrants}
                       for ev_id in opposite["evidence_ids"])
            ],
            "bounded_premises_verified": sum(
                row["premise_check"]["status"] in {"source_text_matched", "source_asserts_literal_proposition"}
                for row in (rows["support"] + rows["challenge"])
            ),
        })
    # Only in the deliberately parsed literal subset can the supplied source
    # text directly disqualify a proposed reading. The old warrant status is
    # retained as an historical activity record, not silently rewritten.
    disqualifying_literal_states = {
        "literal_reading_opposed_by_source_reports",
        "opposed_source_reports_for_literal_reading",
        "third_party_private_state_not_independently_established",
    }
    views = [x for x in found
             if x["status"] in {"active_pro_warrants_not_semantic_proof",
                                 "active_pro_and_con_warrants_not_semantic_proof"}
             and x["reading_source_alignment"]["status"] not in disqualifying_literal_states]
    blocked_literal_readings = [x["id"] for x in found
                                if x["reading_source_alignment"]["status"] in disqualifying_literal_states]
    relevant_oppositions = any(
        row["related_opposed_source_reports"] and (row["supporting_warrants"] or row["challenging_warrants"])
        for row in found
    )
    if relevant_oppositions or len(views) > 1 or any(x["status"] == "active_pro_and_con_warrants_not_semantic_proof" for x in views):
        mode = "present_alternatives_with_sources"
    elif len(views) == 1:
        mode = "consider_one_reading_without_ascribing_motives"
    else:
        mode = "withhold_unsupported_conclusion"
    # Retrieval is *additional context*, never a premise or a way to alter
    # argument status. No topic is attached as a personality classification.
    sources = tuple(EvidenceText(id=f"evidence:{e.id}", text=e.statement, origin=e.origin,
                                 source_ref=e.source_ref) for e in case.scenario.evidence
                    if e.origin != "interpretation")
    knowledge = relevance.suggest(sources)
    return {
        "version": "1", "schema": "deliberation.v1",
        "scenario_id": case.scenario.id, "question": case.scenario.question,
        "context": context, "candidates": found,
        "literal_source_oppositions": literal_oppositions,
        "source_language_signals": surface_signals,
        "response_guidance": {"mode": mode, "host_must_decide_response": True,
                              "opposed_report_review_needed": relevant_oppositions,
                              "clarification_is_not_automatically_required": True,
                              "bounded_literal_readings_not_supported": [
                                  k for k in blocked_literal_readings if any(
                                      x["id"] == k and x["reading_source_alignment"]["status"] !=
                                      "third_party_private_state_not_independently_established" for x in found)],
                              "private_state_readings_not_established": [
                                  x["id"] for x in found if x["reading_source_alignment"]["status"] ==
                                  "third_party_private_state_not_independently_established"]},
        "known_unknowns": list(case.scenario.unknowns),
        "knowledge_considerations": knowledge,
        "claim_boundary": "warrants_and_readings_are_proposals_not_independent_factual_findings",
        "premise_validation": "optional_exact_span_or_restricted_literal_assertion_not_truth_or_social_entailment",
        "reading_validation": "automatic_restricted_literal_or_quantifier_wording_alignment_not_social_truth",
        "method": "bounded_provenance_and_context_conditional_argument_review",
        "limitations": [
            "Candidate readings and why-evidence-matters warrants are supplied, not independently discovered.",
            "An active warrant proves only that cited words are present in a supplied source record.",
            "Contrary reports, quotations, and context are not externally authenticated.",
            "No inference about private motive, consent, emotion, harm or actual effects is established.",
            "Warrant relevance and the proposed support/challenge polarity have not undergone semantic entailment review.",
            "Optional premise checks verify only literal source presence/negation in a deliberately narrow grammar, not social meaning.",
            "Opposed literal source reports can coexist or describe different events; their discovery does not decide factual truth.",
            "No winner is selected by citation counts; repeated testimony is not independent proof.",
            "The 2,000-entry lexicon is not a verified premise database and cannot promote argument status.",
            "Bounded reading-source checks do not verify social motives, a group descriptor, independent truth or semantic entailment in unrestricted English.",
        ],
    }


def compare_cases(before: DeliberationCase, after: DeliberationCase, *,
                  relevance: KnowledgeRelevance) -> dict[str, Any]:
    """Compare two declared cases; never assert what happened in real life."""
    if before.scenario.id != after.scenario.id or before.scenario.question != after.scenario.question:
        raise ValueError("Context comparison requires the same scenario ID and question")
    if {h.id for h in before.hypotheses} != {h.id for h in after.hypotheses}:
        raise ValueError("Both cases must use the same candidate hypothesis IDs")
    old = evaluate_case(before, relevance=relevance)
    new = evaluate_case(after, relevance=relevance)
    before_items = {x["id"]: x for x in old["candidates"]}
    after_items = {x["id"]: x for x in new["candidates"]}
    altered = []
    for key in sorted(before_items):
        x, y = before_items[key], after_items[key]
        changes = []
        for field in ("reading", "proposed_by", "status", "supporting_warrants", "challenging_warrants",
                      "deferred_warrants", "inactive_warrants", "excluded_warrants", "not_established",
                      "reading_source_alignment",
                      "related_concepts_not_premises", "related_opposed_source_reports", "bounded_premises_verified"):
            if x[field] != y[field]:
                changes.append(field)
        if changes:
            altered.append({"id": key, "before_status": x["status"], "after_status": y["status"],
                            "changed_fields": changes})
    inputs_changed = [
        {"evidence_id": key, "before": x, "after": y}
        for key in sorted({e.id for e in before.scenario.evidence} | {e.id for e in after.scenario.evidence})
        if (x := next((e.to_dict() for e in before.scenario.evidence if e.id == key), None)) !=
           (y := next((e.to_dict() for e in after.scenario.evidence if e.id == key), None))
    ]
    return {
        "version": "1", "schema": "deliberation_comparison.v1", "scenario_id": before.scenario.id,
        "context_change": compare_context(before.context_facts, after.context_facts),
        "evidence_changes": inputs_changed,
        "literal_oppositions_before": old["literal_source_oppositions"],
        "literal_oppositions_after": new["literal_source_oppositions"],
        "candidate_changes": altered,
        "response_mode_before": old["response_guidance"]["mode"],
        "response_mode_after": new["response_guidance"]["mode"],
        "classification": "declared_case_comparison_not_observed_real_world_causation",
        "before": old, "after": new,
    }
