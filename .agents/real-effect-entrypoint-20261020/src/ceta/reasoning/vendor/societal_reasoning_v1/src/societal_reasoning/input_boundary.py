"""Exact, non-interpretive capture of a session-scoped utterance.

This boundary deliberately does not decide what the speaker intended or felt.
Character offsets are Python Unicode string offsets; no normalized replacement is stored.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import re

_MAX_TEXT = 65536
_REF = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")


@dataclass(frozen=True, slots=True)
class Utterance:
    turn_id: str
    speaker: str
    text: str
    sha256: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip() or len(self.text) > _MAX_TEXT:
            raise ValueError("Invalid utterance content")
        if not isinstance(self.turn_id, str) or not _REF.fullmatch(self.turn_id):
            raise ValueError("Invalid turn identifier")
        if not isinstance(self.speaker, str) or not _REF.fullmatch(self.speaker):
            raise ValueError("Invalid speaker identifier")
        if self.sha256 != sha256(self.text.encode("utf-8")).hexdigest():
            raise ValueError("Invalid utterance source digest")

    @classmethod
    def capture(cls, text: str, *, turn_id: str = "turn-1", speaker: str = "user") -> Utterance:
        if not isinstance(text, str) or not text.strip() or len(text) > _MAX_TEXT:
            raise ValueError("Utterance must contain 1..65536 characters of nonblank text")
        if not isinstance(turn_id, str) or not _REF.fullmatch(turn_id):
            raise ValueError("Invalid session-scoped turn identifier")
        if not isinstance(speaker, str) or not _REF.fullmatch(speaker):
            raise ValueError("Invalid session-scoped speaker identifier")
        return cls(turn_id, speaker, text, sha256(text.encode("utf-8")).hexdigest())

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SourceSpan:
    turn_id: str
    start: int
    end: int
    text: str
    sha256: str

    def __post_init__(self) -> None:
        if type(self.start) is not int or type(self.end) is not int or not 0 <= self.start < self.end:
            raise ValueError("Invalid span offsets")
        if self.sha256 != sha256(self.text.encode("utf-8")).hexdigest():
            raise ValueError("Invalid span content digest")

    @classmethod
    def capture(cls, utterance: Utterance, start: int, end: int) -> SourceSpan:
        if type(start) is not int or type(end) is not int or not (0 <= start < end <= len(utterance.text)):
            raise ValueError("Span offsets outside source text")
        fragment = utterance.text[start:end]
        return cls(utterance.turn_id, start, end, fragment, sha256(fragment.encode("utf-8")).hexdigest())

    def verify(self, utterance: Utterance) -> None:
        if self.turn_id != utterance.turn_id or self.text != utterance.text[self.start:self.end]:
            raise ValueError("Source span does not correspond to original utterance")
        if self.sha256 != sha256(self.text.encode("utf-8")).hexdigest():
            raise ValueError("Source span fingerprint mismatch")

    def to_dict(self) -> dict:
        return asdict(self)
