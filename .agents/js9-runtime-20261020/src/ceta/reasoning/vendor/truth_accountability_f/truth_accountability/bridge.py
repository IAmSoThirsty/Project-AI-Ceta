"""One narrow host bridge: model JSON -> trusted checks -> gated response.

This module NEVER accepts tool registration, actor privileges, or claimed
verification results from the model. The host owns the actual verifier policy.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable

from .governed import GovernedTruthCore, _unique_pairs, _reject_constant


@dataclass(frozen=True)
class GatedResponse:
    claim_id: str
    decision: str
    text: str
    established_fact: bool
    verified_delivery: bool = False


class GovernedModelBridge:
    """Produce bounded responses only from the host-side authority decision.

    A caller must never append free-form model output after this bridge.
    """

    def __init__(self, core: GovernedTruthCore,
                 host_verifier_selection: Callable[[str, dict], tuple[str, ...]],
                 host_policy_selection: Callable[[str, dict], str] | None = None,
                 host_hypothesis_release: Callable[[str, dict], bool] | None = None):
        if not callable(host_verifier_selection):
            raise ValueError("Trusted host selection callback required")
        self.core = core
        self.select_verifiers = host_verifier_selection
        self.select_policy = host_policy_selection or conservative_policy
        # A model's self-label of "hypothesis" is NEVER authority to publish
        # a claim about a person, even as qualified speculation. Release is a
        # separate host-only permission, absent by default.
        self.review_hypothesis = host_hypothesis_release

    def process(self, raw_model_json: str, *, current_source_id: str | None = None,
                trusted_scope: dict | None = None) -> GatedResponse:
        # Parse solely to enforce source capability before permitting insertion.
        obj = json.loads(raw_model_json, object_pairs_hook=_unique_pairs,
                         parse_constant=_reject_constant)
        if not isinstance(obj, dict):
            raise ValueError("The model must output one structured proposal")
        kind = obj.get("kind")
        proposed_source = obj.get("source_id")
        if proposed_source is not None and proposed_source != current_source_id:
            raise PermissionError("Proposal refers to a source outside current input scope")
        if kind in {"quote", "paraphrase"} and proposed_source != current_source_id:
            raise PermissionError("Source-bearing proposals require current source authorization")
        # Model-supplied domain, time, and evidence policy must not become
        # authoritative context. The host supplies scope for ALL claim kinds.
        if trusted_scope is not None and not isinstance(trusted_scope, dict):
            raise ValueError("Trusted scope must be an object")
        host_scope = trusted_scope or {}
        obj["scope"] = host_scope
        if kind == "fact":
            obj["policy"] = self.select_policy(obj.get("text", ""), host_scope)
        claim_id = self.core.propose_json(json.dumps(obj, ensure_ascii=False))
        if kind == "fact":
            claim = self.core._proposal(claim_id)
            scope = json.loads(claim["scope_json"])
            # This selection is host-supplied, not model-provided. A real host
            # may use domain-specific verifiers with separate trust controls.
            for verifier_id in self.select_verifiers(claim["text"], scope):
                self.core.check(claim_id, verifier_id)
        decision = self.core.decision(claim_id)
        if kind == "hypothesis":
            reviewed = (self.review_hypothesis is not None and
                        self.review_hypothesis(obj["text"], host_scope) is True)
            if not reviewed:
                return GatedResponse(claim_id, "HYPOTHESIS_HELD_FOR_REVIEW",
                    "An unverified hypothesis was recorded but not published. "
                    "The host must review its evidence, scope, and effects.", False)
        if decision.status in {"QUOTED_VERBATIM", "MEANING_REVIEWED",
                               "HYPOTHESIS_ONLY", "SUPPORTED_BY_CHECK"}:
            text = self.core.render(claim_id)
        elif kind == "paraphrase":
            claim = self.core._proposal(claim_id)
            source = self.core.original(claim["source_id"])
            text = ("I cannot substantiate that attribution. The original statement is "
                    f"preserved as: {json.dumps(source, ensure_ascii=False)}.")
        elif decision.status == "REFUTED_BY_CHECK":
            text = ("The proposed factual claim is contradicted by recorded checks "
                    f"({', '.join(decision.evidence_refs)}). This is a checked contradiction, "
                    "not a new unrestricted answer.")
        elif decision.status == "DISPUTED":
            text = "The available checks conflict. I cannot honestly establish this factual claim."
        else:
            text = f"The proposed claim is not established ({decision.status}); more evidence is required."
        return GatedResponse(claim_id, decision.status, text,
                              established_fact=decision.status == "SUPPORTED_BY_CHECK")


def conservative_policy(text: str, scope: dict) -> str:
    """Host default: allow one bounded proof for elementary arithmetic only."""
    return "standard" if arithmetic_only_policy(text, scope) else "high_stakes"


def arithmetic_only_policy(text: str, scope: dict) -> tuple[str, ...]:
    """Example only: recognize a tiny language of arithmetic equations."""
    if re.fullmatch(r"\s*-?\d+\s*[+*\-]\s*-?\d+\s*=\s*-?\d+\s*", text):
        return ("arithmetic",)
    return ()
