"""Conservative, deterministic source-span and speech-act *proposals*.

A captured claim records what the person SAID, not independently proven reality.
Unclassified language stays unclassified. Do not infer psychological traits.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import re

from .input_boundary import SourceSpan, Utterance

# Only surface features are marked; they are not a natural language parse.
_WORD = re.compile(r"\b[\w']+\b", re.UNICODE)
_NUMBER = re.compile(r"\b\d+(?:[,.]\d+)*(?:%|st|nd|rd|th)?\b")
_CLAUSE = re.compile(r"[^.!?;\n]+(?:[.!?;]+|$)", re.UNICODE)
_MODALITY = frozenset(("might", "may", "could", "perhaps", "possibly", "probably", "maybe", "would", "should", "must", "will"))
_NEGATION = frozenset(("not", "never", "no", "cannot", "can't", "won't", "don't", "didn't", "doesn't", "isn't", "wasn't", "weren't"))
_CONDITION = frozenset(("if", "unless", "provided", "assuming"))
_CORRECTIONS = ("no,", "no.", "i meant", "i did not mean", "i didn't mean", "that's not what", "that is not what", "to correct", "correction:")
_COMMANDS = frozenset(("please", "begin", "start", "stop", "show", "write", "draft", "build", "create", "continue", "explain", "list", "compare", "check", "review", "remove", "add", "delete", "tell", "give"))


@dataclass(frozen=True, slots=True)
class RecordedStatement:
    id: str
    speaker: str
    source: SourceSpan
    speech_act_proposal: str
    proposition_status: str
    modality_markers: tuple[str, ...]
    negation_markers: tuple[str, ...]
    conditional_markers: tuple[str, ...]
    numeric_literals: tuple[str, ...]

    def to_dict(self) -> dict:
        return asdict(self)


def record_statements(utterance: Utterance) -> list[RecordedStatement]:
    out: list[RecordedStatement] = []
    for match in _CLAUSE.finditer(utterance.text):
        raw = match.group()
        trimmed = raw.strip()
        if not trimmed:
            continue
        leading = len(raw) - len(raw.lstrip())
        trailing = len(raw.rstrip())
        span = SourceSpan.capture(utterance, match.start() + leading, match.start() + trailing)
        clean = span.text
        words = tuple(w.group().casefold() for w in _WORD.finditer(clean))
        # A quoted expression is not automatically the speaker's own belief.
        full_quote = (clean.startswith(('"', '“', "'")) and clean.endswith(('"', '”', "'")))
        lower = clean.casefold()
        if full_quote:
            act = "quoted_material"
        elif lower.startswith(_CORRECTIONS):
            act = "possible_correction"
        elif clean.endswith("?"):
            act = "question"
        elif words and words[0] in _COMMANDS:
            act = "possible_request"
        elif words and words[0] in {"what", "why", "how", "who", "where", "when", "which", "can", "could", "would", "will"}:
            act = "possible_question_or_request"
        elif words and ("i" in words or "we" in words):
            act = "speaker_statement"
        else:
            act = "unclassified"
        out.append(RecordedStatement(
            id=f"{utterance.turn_id}:s{len(out)+1}", speaker=utterance.speaker,
            source=span, speech_act_proposal=act,
            proposition_status="speaker_report_not_independently_verified" if act == "speaker_statement" else "unclassified_not_asserted",
            modality_markers=tuple(w for w in words if w in _MODALITY),
            negation_markers=tuple(w for w in words if w in _NEGATION),
            conditional_markers=tuple(w for w in words if w in _CONDITION),
            numeric_literals=tuple(m.group() for m in _NUMBER.finditer(clean)),
        ))
    return out


def derive_objective(statements: list[RecordedStatement]) -> dict:
    candidates = [x for x in statements if x.speech_act_proposal in {"question", "possible_request", "possible_question_or_request"}]
    if not candidates:
        return {"status": "no_explicit_request_identified", "text": None, "source": None}
    if len(candidates) != 1:
        return {"status": "multiple_request_candidates_need_context", "text": None,
                "source_candidates": [item.source.to_dict() for item in candidates]}
    chosen = candidates[0]
    return {"status": "provisional_extraction_not_intent_verification",
            "text": chosen.source.text, "source": chosen.source.to_dict()}
