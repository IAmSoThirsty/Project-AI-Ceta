"""Host-only independent evidence plugins. No arbitrary model-provided callbacks."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class EvidenceVerdict(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    INCONCLUSIVE = "inconclusive"


@dataclass(frozen=True)
class EvidenceFinding:
    verdict: EvidenceVerdict
    locator: str
    explanation: str
    raw_evidence: bytes
    proposed_correction: str = ""
    expires_at: str | None = None

    @property
    def digest(self) -> str:
        return hashlib.sha256(self.raw_evidence).hexdigest()


@dataclass(frozen=True)
class VerifierSpec:
    verifier_id: str
    independent_group: str
    verify: Callable[[str, dict], EvidenceFinding]
    allowed_scope: str = "general"


class VerificationRegistry:
    """Construct and register verifiers inside privileged host code only.

    The registry is an in-process allowlist, not an authentication boundary.
    Its use by an untrusted model or request router would defeat the contract.
    """

    def __init__(self):
        self._entries: dict[str, VerifierSpec] = {}

    def register(self, spec: VerifierSpec) -> None:
        if not spec.verifier_id or not spec.independent_group or not callable(spec.verify):
            raise ValueError("Verifier identity, group and function required")
        if spec.verifier_id in self._entries:
            raise ValueError("Verifier is already registered")
        self._entries[spec.verifier_id] = spec

    def get(self, verifier_id: str) -> VerifierSpec:
        try:
            return self._entries[verifier_id]
        except KeyError as exc:
            raise PermissionError("Verifier not on host allowlist") from exc


def bounded_arithmetic(statement: str, scope: dict) -> EvidenceFinding:
    """Actually compute simple integer arithmetic; cannot execute expressions."""
    match = re.fullmatch(r"\s*(-?\d+)\s*([+*\-])\s*(-?\d+)\s*=\s*(-?\d+)\s*", statement)
    if not match:
        return EvidenceFinding(EvidenceVerdict.INCONCLUSIVE, "local:arithmetic:v1",
                               "Not a supported integer arithmetic expression", statement.encode())
    lhs, op, rhs, claimed = match.groups()
    a, b, value = int(lhs), int(rhs), int(claimed)
    if any(abs(v) > 10**10 for v in (a, b, value)):
        return EvidenceFinding(EvidenceVerdict.INCONCLUSIVE, "local:arithmetic:v1",
                               "Operand outside bounded verifier domain", statement.encode())
    result = {"+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b}[op]()
    supports = result == value
    return EvidenceFinding(
        EvidenceVerdict.SUPPORTS if supports else EvidenceVerdict.REFUTES,
        "local:arithmetic:v1", f"Bounded integer calculation: {a} {op} {b} = {result}",
        f"{a}|{op}|{b}|{result}".encode(), f"{a} {op} {b} = {result}" if not supports else "",
    )
