"""Potential impact reminders based on concrete draft-check findings only."""

from __future__ import annotations

from typing import Any

_POSSIBLE = {
    "MISQUOTED_USER": ("quoted_speaker", "Could misrepresent the person's actual words"),
    "UNSUPPORTED_PERSON_STATE": ("described_person", "Could assign an unreported mental state or motive to a person"),
    "UNVERIFIED_FIRST_PERSON_DRAFT": ("represented_speaker", "Could put a new claim in the represented person's voice"),
    "POSSIBLE_MODALITY_STRENGTHENING": ("represented_speaker", "Could present a possibility as a commitment"),
    "POSSIBLE_NEGATION_LOSS": ("represented_speaker", "Could reverse the person's expressed position"),
    "UNSUPPORTED_USER_QUANTITY": ("represented_speaker", "Could attribute an unsupported quantity to the person"),
}


def effects_from_review(review: dict[str, Any]) -> list[dict[str, str]]:
    if not isinstance(review, dict) or not isinstance(review.get("issues"), list):
        raise ValueError("Expected reviewed draft findings")
    effects = []
    for issue in review["issues"]:
        if not isinstance(issue, dict) or issue.get("code") not in _POSSIBLE:
            continue
        participant, wording = _POSSIBLE[issue["code"]]
        effects.append({"potentially_affected_role": participant,
                        "possible_effect": wording,
                        "status": "hypothetical_not_observed",
                        "basis": issue["code"]})
    return effects
