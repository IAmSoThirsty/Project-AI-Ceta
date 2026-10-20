"""Explicit, local-only correction and supersession records.

A correction changes which *reported words* are active for subsequent response
planning. It does not prove factual truth, infer what the speaker meant, edit
source history, silently infer corrections from ordinary disagreement, or persist
personal records. The caller supplies target, corrective turn and exact span.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re

from .claims import record_statements
from .input_boundary import SourceSpan, Utterance, _REF

_CURRENT_QUOTE = re.compile(
    r'\b(?:you\s+(?:currently|now)\s+(?:say|state|maintain)|'
    r'your\s+(?:current|latest)\s+(?:statement|position)\s+is)'
    r'\s*[:,-]?\s*["\u201c]([^"\u201d]+)["\u201d]', re.I
)


@dataclass(frozen=True, slots=True)
class CorrectionEvent:
    session_id: str
    sequence: int
    target_turn: str
    correction_turn: str
    speaker: str
    target_sha256: str
    correction_sha256: str
    corrected_source_span: SourceSpan
    chain_sha256: str
    status: str = "explicit_speaker_correction_not_independently_verified"

    def to_dict(self) -> dict:
        return asdict(self)


class CorrectionLedger:
    """One bounded in-memory session. No implicit cross-session memory."""

    def __init__(self, session_id: str) -> None:
        if not isinstance(session_id, str) or not _REF.fullmatch(session_id):
            raise ValueError("Invalid session identifier")
        self.session_id = session_id
        self._turns: dict[str, Utterance] = {}
        self._events: list[CorrectionEvent] = []
        self._replaced: dict[str, str] = {}
        self._used_correction_turns: set[str] = set()
        self._closed = False

    def add_turn(self, utterance: Utterance) -> None:
        self._require_open()
        if not isinstance(utterance, Utterance):
            raise ValueError("A captured Utterance is required")
        if utterance.turn_id in self._turns:
            raise ValueError("Duplicate turn ID in session")
        if len(self._turns) >= 1024:
            raise ValueError("Session turn limit reached")
        self._turns[utterance.turn_id] = utterance

    def correct(self, target_turn: str, correction_turn: str, *, start: int, end: int) -> CorrectionEvent:
        self._require_open()
        if target_turn not in self._turns or correction_turn not in self._turns:
            raise ValueError("Both target and correction turns must exist in this session")
        if target_turn == correction_turn:
            raise ValueError("Self-correction requires a separate later turn")
        if target_turn in self._replaced:
            raise ValueError("Target has already been superseded; correct its current successor")
        if correction_turn in self._used_correction_turns:
            raise ValueError("Correction turn was already used for a supersession")
        if len(self._events) >= 256:
            raise ValueError("Session correction limit reached")
        original = self._turns[target_turn]
        corrective = self._turns[correction_turn]
        if original.speaker != corrective.speaker:
            raise ValueError("Only the original speaker can supersede their own statement")
        if list(self._turns).index(correction_turn) <= list(self._turns).index(target_turn):
            raise ValueError("Correction must be recorded after the target turn")
        statements = record_statements(corrective)
        if not statements or statements[0].speech_act_proposal != "possible_correction":
            raise ValueError("An explicit correction marker is required, not an inferred disagreement")
        span = SourceSpan.capture(corrective, start, end)
        if not span.text.strip():
            raise ValueError("Correction cannot select blank text")
        # A content fingerprint links the event to source turns and previous
        # corrections; it is an integrity aid, not a cryptographic signature.
        payload = {
            "session": self.session_id, "sequence": len(self._events) + 1,
            "target": target_turn, "correction": correction_turn,
            "speaker": original.speaker, "target_sha256": original.sha256,
            "correction_sha256": corrective.sha256, "span": span.to_dict(),
            "previous_chain_sha256": self._events[-1].chain_sha256 if self._events else None,
        }
        event = CorrectionEvent(
            session_id=self.session_id, sequence=payload["sequence"],
            target_turn=target_turn, correction_turn=correction_turn,
            speaker=original.speaker, target_sha256=original.sha256,
            correction_sha256=corrective.sha256, corrected_source_span=span,
            chain_sha256=sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                         ensure_ascii=False).encode("utf-8")).hexdigest(),
        )
        self._replaced[target_turn] = correction_turn
        self._used_correction_turns.add(correction_turn)
        self._events.append(event)
        return event

    def active_state(self) -> dict:
        self._require_open()
        superseded = []
        for key, successor in self._replaced.items():
            current = successor
            visited = {key}
            while current in self._replaced:
                if current in visited:
                    raise ValueError("Correction cycle detected")
                visited.add(current)
                current = self._replaced[current]
            superseded.append({"turn_id": key, "successor": successor, "effective_successor": current,
                               "status": "superseded_report_preserved_for_history"})
        return {
            "session_id": self.session_id,
            "turns_recorded": len(self._turns),
            "corrections_recorded": len(self._events),
            "active_turn_ids": [key for key in self._turns if key not in self._replaced],
            "superseded_turns": superseded,
            "correction_events": [event.to_dict() for event in self._events],
            "epistemic_scope": "explicit_report_supersession_not_independent_fact_verification",
            "persistence": "in_memory_only_no_implicit_person_profile",
        }

    def verify_turn(self, utterance: Utterance) -> None:
        self._require_open()
        known = self._turns.get(utterance.turn_id)
        if known != utterance:
            raise ValueError("Source utterance does not match this session's record")

    def review_current_attributions(self, draft: str, *, addressed_speaker: str = "user") -> list[dict]:
        """Find stale verbatim user quotes presented as current, not all paraphrases."""
        self._require_open()
        if not isinstance(draft, str) or len(draft) > 65536:
            raise ValueError("Invalid draft length or type")
        if not isinstance(addressed_speaker, str) or not _REF.fullmatch(addressed_speaker):
            raise ValueError("Invalid addressed speaker")
        issues = []
        for matched in _CURRENT_QUOTE.finditer(draft):
            # A historical report such as 'You said "..."' remains true
            # after a correction and MUST NOT be held as a current claim.
            # Only explicit present-position attributions are inspected.
            for old_id in self._replaced:
                old = self._turns[old_id]
                if old.speaker != addressed_speaker:
                    continue  # Only review quotes attributed to the addressed speaker.
                if matched.group(1) == old.text:
                    issues.append({
                        "code": "SUPERSEDED_USER_QUOTE_AS_CURRENT",
                        "span": matched.group(),
                        "target_turn": old_id,
                        "current_successor": self._replaced[old_id],
                        "reason": "A superseded historical quote is presented as the current user statement",
                        "severity": "hold",
                    })
        return issues

    def purge(self) -> dict:
        """Drop in-memory content and permanently close this ledger instance."""
        self._require_open()
        counts = {"turns_purged": len(self._turns), "corrections_purged": len(self._events)}
        self._turns.clear()
        self._events.clear()
        self._replaced.clear()
        self._used_correction_turns.clear()
        self._closed = True
        return counts

    def _require_open(self) -> None:
        if self._closed:
            raise ValueError("Session ledger was purged and is closed")
