"""Deterministic, evidence-attributed interpretation of structured societal scenarios.

Not a natural-language model, not a mind-reader, not an execution authorization system.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from typing import Any

from .graph import KnowledgeGraph
from .models import Scenario
from .relevance import EvidenceText, KnowledgeRelevance
from .semantics import LexicalRegistry


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    title: str
    requires_all: tuple[str, ...]
    supports: dict[str, int]
    contradicts: dict[str, int]
    context_matches: dict[str, dict[str, int]]
    min_score: int
    concept_ids: tuple[int, ...]
    interpretation: str
    limitation: str
    clarification_question: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Rule:
        allowed = {
            "id", "title", "requires_all", "supports", "contradicts", "context_matches",
            "min_score", "concept_ids", "interpretation", "limitation", "clarification_question",
        }
        if set(data) != allowed:
            raise ValueError(f"Invalid rule keys: missing={sorted(allowed-set(data))}, extra={sorted(set(data)-allowed)}")
        rule = cls(
            id=data["id"], title=data["title"],
            requires_all=tuple(data["requires_all"]),
            supports=dict(data["supports"]),
            contradicts=dict(data["contradicts"]),
            context_matches={k: dict(v) for k, v in data["context_matches"].items()},
            min_score=data["min_score"], concept_ids=tuple(data["concept_ids"]),
            interpretation=data["interpretation"], limitation=data["limitation"],
            clarification_question=data["clarification_question"],
        )
        if not rule.id.strip() or not rule.title.strip():
            raise ValueError("Rule ID and title required")
        if not rule.requires_all or not all(isinstance(c, str) and c.strip() for c in rule.requires_all):
            raise ValueError(f"Rule {rule.id}: at least one explicit prerequisite is required")
        if any(type(w) is not int or w < 0 for w in (*rule.supports.values(), *rule.contradicts.values())):
            raise ValueError(f"Rule {rule.id}: cue weights must be nonnegative integers")
        if any(type(w) is not int or w < 0 for mapping in rule.context_matches.values() for w in mapping.values()):
            raise ValueError(f"Rule {rule.id}: context weights must be nonnegative integers")
        if type(rule.min_score) is not int or rule.min_score < 0:
            raise ValueError(f"Rule {rule.id}: invalid threshold")
        if not all(isinstance(x, int) for x in rule.concept_ids):
            raise ValueError(f"Rule {rule.id}: concept identifiers must be integers")
        return rule


class SocietalReasoner:
    def __init__(self, graph: KnowledgeGraph, rules: list[Rule], lexical_registry: LexicalRegistry | None = None):
        self.graph = graph
        self.rules = rules
        self.lexical_registry = lexical_registry if lexical_registry is not None else LexicalRegistry.starter()
        self.knowledge_relevance = KnowledgeRelevance(graph)
        identifiers = [rule.id for rule in rules]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("Duplicate rule IDs")
        for rule in rules:
            for concept_id in rule.concept_ids:
                if graph.get(concept_id) is None:
                    raise ValueError(f"Rule {rule.id} references missing concept {concept_id}")

    @classmethod
    def default_rules(cls) -> list[Rule]:
        with files("societal_reasoning").joinpath("resources", "rules.v1.json").open(encoding="utf-8") as source:
            rows = json.load(source)
        if not isinstance(rows, list):
            raise ValueError("Rule resource must be a list")
        return [Rule.from_dict(row) for row in rows]

    @classmethod
    def starter(cls) -> SocietalReasoner:
        return cls(KnowledgeGraph.starter(), cls.default_rules())

    def assess_text(self, utterance: str, *, turn_id: str = "turn-1", speaker: str = "user",
                    material_words: tuple[str, ...] = (),
                    selected_senses: dict[str, str] | None = None,
                    context_facts: tuple[dict[str, Any], ...] = (),
                    session_id: str | None = None) -> dict[str, Any]:
        """Run the new source-fidelity boundary on ordinary text.

        Unlike ``analyze(Scenario)``, this path does not pretend to infer
        psychological cues from unstructured prose. Model-independent fallback.
        """
        from .input_boundary import Utterance, _REF
        from .claims import derive_objective, record_statements
        from .context import assemble_context

        if session_id is not None and (not isinstance(session_id, str) or not _REF.fullmatch(session_id)):
            raise ValueError("Invalid session identifier")
        captured = Utterance.capture(utterance, turn_id=turn_id, speaker=speaker)
        statements = record_statements(captured)
        meaning = self.lexical_registry.discover_in_text(
            utterance, material_words=material_words, selected_senses=selected_senses
        )
        objective = derive_objective(statements)
        context = assemble_context(context_facts)
        # The source's own words are recorded; context hypotheses are not evidence.
        # Conflicting context reports are held rather than silently choosing one.
        conflicted = {row["category"] for row in context["source_conflicts"]}
        related_sources = [EvidenceText(
            id=f"utterance:{captured.turn_id}", text=captured.text,
            origin="user_utterance", source_ref=captured.turn_id,
        )]
        excluded_context_ids = []
        for factor in context["reported_or_proposed_factors"]:
            if factor["origin"] == "model_hypothesis" or factor["category"] in conflicted:
                excluded_context_ids.append(factor["id"])
                continue
            related_sources.append(EvidenceText(
                id=f"context:{factor['id']}", text=factor["value"],
                origin=factor["origin"], source_ref=factor["source_ref"],
            ))
        knowledge = self.knowledge_relevance.suggest(related_sources)
        knowledge["excluded_context_ids"] = excluded_context_ids
        if meaning["status"] == "requires_clarification":
            response_mode = "necessary_clarification"
            clarifying_question = meaning["declared_material_assessment"]["unresolved"][0]["question"]
        elif objective["status"] == "no_explicit_request_identified":
            response_mode = "no_requested_action_identified"
            clarifying_question = None
        elif objective["status"] == "multiple_request_candidates_need_context":
            response_mode = "objective_must_be_resolved"
            clarifying_question = None
        else:
            response_mode = "respond_to_extracted_request"
            clarifying_question = None
        return {
            "version": "1", "schema": "text_assessment.v1",
            "session_id": session_id,
            "utterance": captured.to_dict(),
            "statements": [s.to_dict() for s in statements],
            "objective": objective, "semantics": meaning, "context": context,
            "knowledge_considerations": knowledge,
            "response_mode": response_mode,
            "clarification_question": clarifying_question,
            "known_limits": [
                "Surface speech acts and claim markers are heuristic proposals, not verified intent.",
                "No assertion about a person's feelings or private motives has been made.",
                "No third-party source or reported event has been independently authenticated.",
                "Natural-language context and unseen ambiguity are not comprehensively interpreted.",
                "The concept graph is consulted for lexical topics only; retrieval does not establish social facts.",
            ],
        }

    def review_draft(self, assessment: dict[str, Any], draft: str, *,
                     writing_as_user: bool = False,
                     correction_ledger: "CorrectionLedger | None" = None) -> dict[str, Any]:
        """Apply bounded, advisory surface checks against preserved source text."""
        from .input_boundary import Utterance
        from .response_review import review_draft
        from .effects import effects_from_review
        from .corrections import CorrectionLedger

        if not isinstance(assessment, dict) or assessment.get("schema") != "text_assessment.v1":
            raise ValueError("Expected validated text_assessment.v1")
        raw = assessment.get("utterance")
        if not isinstance(raw, dict) or set(raw) != {"turn_id", "speaker", "text", "sha256"}:
            raise ValueError("Malformed source record")
        source = Utterance.capture(raw["text"], turn_id=raw["turn_id"], speaker=raw["speaker"])
        if source.sha256 != raw["sha256"]:
            raise ValueError("Source integrity mismatch")
        result = review_draft(source, draft, writing_as_user=writing_as_user)
        if correction_ledger is not None:
            if not isinstance(correction_ledger, CorrectionLedger):
                raise ValueError("Expected a session-scoped CorrectionLedger")
            if assessment.get("session_id") != correction_ledger.session_id:
                raise ValueError("Correction ledger session does not match assessment")
            correction_ledger.verify_turn(source)
            added = correction_ledger.review_current_attributions(draft, addressed_speaker=source.speaker)
            result["issues"].extend(added)
            if added:
                result["status"] = "hold"
            result["correction_review_scope"] = "exact_superseded_user_quotes_only"
        result["possible_effects"] = effects_from_review(result)
        return result

    def deliberate(self, case: "DeliberationCase") -> dict[str, Any]:
        """Evaluate attributed, caller-supplied alternatives through this reasoner.

        The result concerns *argument support*, not psychological facts.
        It does not grant authority or execute actions.
        """
        from .deliberation import DeliberationCase, evaluate_case

        if not isinstance(case, DeliberationCase):
            raise ValueError("Expected validated DeliberationCase")
        return evaluate_case(case, relevance=self.knowledge_relevance)

    def compare_deliberations(self, before: "DeliberationCase", after: "DeliberationCase") -> dict[str, Any]:
        """Inspect context-sensitive changes using the same canonical engine."""
        from .deliberation import DeliberationCase, compare_cases

        if not isinstance(before, DeliberationCase) or not isinstance(after, DeliberationCase):
            raise ValueError("Expected two validated DeliberationCase records")
        return compare_cases(before, after, relevance=self.knowledge_relevance)

    def analyze(self, scenario: Scenario) -> dict[str, Any]:
        # Interpretations offered as evidence may be discussed but cannot generate
        # 'observed' cues. Caller must supply independently described evidence.
        usable = [e for e in scenario.evidence if e.origin != "interpretation"]
        cue_sources: dict[str, list[str]] = {}
        for evidence in usable:
            for cue in set(evidence.cues):
                cue_sources.setdefault(cue, []).append(evidence.id)
        observed_cues = set(cue_sources)

        matches: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        for rule in self.rules:
            missing = sorted(set(rule.requires_all) - observed_cues)
            if missing:
                trace.append({"rule_id": rule.id, "decision": "ineligible", "missing_required_cues": missing})
                continue
            positive = sorted(observed_cues & rule.supports.keys())
            negative = sorted(observed_cues & rule.contradicts.keys())
            matching_context: dict[str, dict] = {}
            context_score = 0
            for key, weights in rule.context_matches.items():
                value = scenario.context.get(key)
                if value in weights:
                    context_score += weights[value]
                    matching_context[key] = {"value": value, "weight": weights[value], "origin": "scenario_context_user_supplied"}
            # Explainable ranking points, never probability or scientific confidence.
            score = 2 * len(rule.requires_all) + sum(rule.supports[c] for c in positive)
            score += context_score
            score -= sum(rule.contradicts[c] for c in negative)
            support_ids = sorted({ev_id for cue in (*rule.requires_all, *positive) for ev_id in cue_sources[cue]})
            contrary_ids = sorted({ev_id for cue in negative for ev_id in cue_sources[cue]})
            if score >= rule.min_score:
                match = {
                    "rule_id": rule.id, "title": rule.title,
                    "interpretation": rule.interpretation,
                    "limitation": rule.limitation,
                    "rank_score_not_probability": score,
                    "required_cues": list(rule.requires_all),
                    "additional_supporting_cues": positive,
                    "counter_cues": negative,
                    "supporting_evidence_ids": support_ids,
                    "counter_evidence_ids": contrary_ids,
                    "user_supplied_context_used": matching_context,
                    "concepts": [self.graph.get(i).to_dict() for i in rule.concept_ids],
                    "evidence_origin_mix": sorted({e.origin for e in usable if e.id in support_ids}),
                }
                matches.append(match)
                trace.append({"rule_id": rule.id, "decision": "eligible", "rank_score_not_probability": score})
            else:
                trace.append({"rule_id": rule.id, "decision": "insufficient_after_counter_evidence", "rank_score_not_probability": score})

        matches.sort(key=lambda x: (-x["rank_score_not_probability"], x["rule_id"]))
        lexical = self.lexical_registry.assess(scenario.material_terms)
        competing_frames = all(cue in observed_cues for cue in (
            "derisive_form", "people_or_group_targeted", "specific_work_product", "verifiable_defect"
        ))
        if competing_frames:
            # Specific work critique and group-directed mockery can coexist.
            # Neither should be silently flattened into the other.
            verdict = "contested_interpretations"
            selected = None
        elif not matches:
            verdict = "insufficient_evidence"
            selected = None
        elif len(matches) > 1 and matches[0]["rank_score_not_probability"] - matches[1]["rank_score_not_probability"] < 2:
            verdict = "contested_interpretations"
            selected = None
        else:
            verdict = "provisional_interpretation"
            selected = matches[0]

        metadata = {
            "direct_observations": [e.to_dict() for e in scenario.evidence if e.origin == "direct_observation"],
            "user_reports": [e.to_dict() for e in scenario.evidence if e.origin == "user_report"],
            "quoted_material": [e.to_dict() for e in scenario.evidence if e.origin == "quoted_material"],
            "external_records": [e.to_dict() for e in scenario.evidence if e.origin == "external_record"],
            "prior_interpretations_not_used_as_evidence": [e.to_dict() for e in scenario.evidence if e.origin == "interpretation"],
            "not_established": list(scenario.unknowns),
        }
        # A declaration that a word is material obliges the system to honor
        # dictionary ambiguity; never silently guess the sense from its spelling.
        if lexical["status"] == "requires_clarification":
            verdict = "clarification_required"
            selected = None
        clarification = None
        if lexical["status"] == "requires_clarification":
            clarification = lexical["unresolved"][0]["question"]
        elif verdict != "provisional_interpretation":
            if competing_frames:
                clarification = "Both a concrete defect and group-directed ridicule are reported. Which specific aspect should be evaluated, and what surrounding context is available?"
            elif matches:
                rule = next(r for r in self.rules if r.id == matches[0]["rule_id"])
                clarification = rule.clarification_question
            else:
                clarification = "What observable context, words, or actions would distinguish the plausible interpretations?"

        # Source-evidenced knowledge leads can be inspected, but they cannot
        # silently become cues, satisfy a rule, or change an interpretation.
        retrieval_inputs = [EvidenceText(
            id=f"evidence:{e.id}", text=e.statement,
            origin=e.origin, source_ref=e.source_ref,
        ) for e in usable]
        retrieval_inputs.extend(EvidenceText(
            id=f"scenario_context:{key}", text=value,
            origin="user_report", source_ref=f"scenario:{scenario.id}",
        ) for key, value in sorted(scenario.context.items()) if value.strip())
        knowledge = self.knowledge_relevance.suggest(retrieval_inputs)

        return {
            "schema_version": "1.1",
            "scenario_id": scenario.id,
            "question": scenario.question,
            "status": verdict,
            "primary": selected,
            "candidates": matches,
            "epistemic_record": metadata,
            "cue_evidence_links": dict(sorted(cue_sources.items())),
            "context_reported": dict(scenario.context),
            "knowledge_considerations": knowledge,
            "material_terms": lexical,
            "clarification_question": clarification,
            "rule_trace": trace,
            "operational_boundary": "ADVISORY_ONLY_NO_EXTERNAL_ACTION_OR_AUTHORIZATION",
            "limitations": [
                "Inputs and context are provided by the caller, not independently verified.",
                "The core does not parse images, sarcasm, or free text into evidence cues.",
                "Ranking values only compare rule support; they are not calibrated probabilities.",
                "Reported behavior does not establish a person's private motives or mental state.",
                "Provisional conclusions are not facts, permissions, or judgments of legal liability.",
                "Only caller-declared material terms are checked; no full-prose lexical analysis is performed.",
            ],
        }
