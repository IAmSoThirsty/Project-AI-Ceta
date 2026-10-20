"""Small reference truth/accountability ledger, not a semantic oracle.

The host application MUST authenticate speakers and control verifier registration.
Do not let an LLM call ledger mutation APIs directly. All model outputs are
proposals; assertions are rendered only through the host policy gate.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return uuid4().hex


class ClaimKind(str, Enum):
    QUOTE = "quote"
    ATTRIBUTION = "attribution"
    FACT = "fact"
    PERSPECTIVE = "perspective"
    HYPOTHESIS = "hypothesis"


class Verdict(str, Enum):
    SUPPORTS = "supports"
    REFUTES = "refutes"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class CheckResult:
    verdict: Verdict
    evidence_ref: str
    explanation: str
    proposed_correction: str = ""


class TruthLedger:
    """Persist verbatim statements, proposed claims, checks, and corrections.

    Trust boundary: caller code is trusted. Model output and retrieved text are
    untrusted data. External verifiers should be separate, allowlisted tools.
    """

    def __init__(self, database: str | Path = ":memory:"):
        self.db = sqlite3.connect(str(database))
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS statements (
                id TEXT PRIMARY KEY, speaker TEXT NOT NULL,
                exact_text TEXT NOT NULL, recorded_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS claims (
                id TEXT PRIMARY KEY, kind TEXT NOT NULL,
                text TEXT NOT NULL, source_id TEXT,
                source_quote TEXT, scope TEXT NOT NULL,
                published INTEGER NOT NULL DEFAULT 0,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY(source_id) REFERENCES statements(id)
            );
            CREATE TABLE IF NOT EXISTS checks (
                id TEXT PRIMARY KEY, claim_id TEXT NOT NULL,
                verifier TEXT NOT NULL, verdict TEXT NOT NULL,
                evidence_ref TEXT NOT NULL, explanation TEXT NOT NULL,
                proposed_correction TEXT NOT NULL, recorded_at TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claims(id)
            );
            CREATE TABLE IF NOT EXISTS corrections (
                id TEXT PRIMARY KEY, claim_id TEXT NOT NULL,
                authority TEXT NOT NULL, evidence_ref TEXT NOT NULL,
                reason TEXT NOT NULL, corrected_text TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                FOREIGN KEY(claim_id) REFERENCES claims(id)
            );
        """)
        self.db.commit()

    def preserve_statement(self, speaker: str, exact_text: str) -> str:
        if not speaker or not exact_text:
            raise ValueError("A statement must have a speaker and exact text")
        statement_id = _id()
        self.db.execute(
            "INSERT INTO statements VALUES (?,?,?,?)",
            (statement_id, speaker, exact_text, _now()),
        )
        self.db.commit()
        return statement_id

    def propose_claim(
        self,
        kind: ClaimKind,
        text: str,
        *,
        source_id: str | None = None,
        source_quote: str | None = None,
        scope: dict | None = None,
    ) -> str:
        if not text:
            raise ValueError("Claim text is required")
        if kind in (ClaimKind.QUOTE, ClaimKind.ATTRIBUTION, ClaimKind.PERSPECTIVE) and not source_id:
            raise ValueError("Speaker-dependent claims need a source statement")
        if source_quote is not None:
            if not source_id:
                raise ValueError("A quotation needs a source statement")
            statement = self.db.execute(
                "SELECT exact_text FROM statements WHERE id=?", (source_id,)
            ).fetchone()
            if statement is None or source_quote not in statement["exact_text"]:
                raise ValueError("Quote is not present verbatim in the source")
        claim_id = _id()
        self.db.execute(
            "INSERT INTO claims VALUES (?,?,?,?,?,?,?,?)",
            (claim_id, kind.value, text, source_id, source_quote,
             json.dumps(scope or {}, sort_keys=True), 0, _now()),
        )
        self.db.commit()
        return claim_id

    def claim(self, claim_id: str) -> sqlite3.Row:
        claim = self.db.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()
        if claim is None:
            raise KeyError(claim_id)
        return claim

    def status(self, claim_id: str) -> str:
        claim = self.claim(claim_id)
        if self.db.execute("SELECT 1 FROM corrections WHERE claim_id=? LIMIT 1", (claim_id,)).fetchone():
            return "WITHDRAWN_AFTER_CORRECTION"
        kind = ClaimKind(claim["kind"])
        if kind is ClaimKind.QUOTE:
            if claim["source_quote"] == claim["text"] and claim["source_quote"]:
                return "VERIFIED_AS_VERBATIM_QUOTE"  # NOT verification of quote's world claim
            return "UNSUPPORTED_ATTRIBUTION"
        if kind in (ClaimKind.ATTRIBUTION, ClaimKind.PERSPECTIVE):
            # Paraphrases and motive attributions require separately reviewed semantics.
            return "NEEDS_SPEAKER_OR_HUMAN_REVIEW"
        if kind is ClaimKind.HYPOTHESIS:
            return "HYPOTHESIS_ONLY"
        results = self.db.execute(
            "SELECT verdict FROM checks WHERE claim_id=?", (claim_id,)
        ).fetchall()
        seen = {r["verdict"] for r in results}
        if Verdict.SUPPORTS.value in seen and Verdict.REFUTES.value in seen:
            return "DISPUTED"
        if Verdict.REFUTES.value in seen:
            return "REFUTED_BY_CHECK"
        if Verdict.SUPPORTS.value in seen:
            return "SUPPORTED_BY_CHECK"
        return "UNVERIFIED"

    def allowed_factual_assertion(self, claim_id: str) -> bool:
        """Host renderer must call this before presenting an unqualified fact."""
        return self.status(claim_id) == "SUPPORTED_BY_CHECK"

    def allowed_attributed_quotation(self, claim_id: str) -> bool:
        """Validates only that the words were actually spoken, not their truth."""
        return self.status(claim_id) == "VERIFIED_AS_VERBATIM_QUOTE"

    def publish(self, claim_id: str) -> None:
        if not self.allowed_factual_assertion(claim_id):
            raise PermissionError(f"Cannot publish as an established fact: {self.status(claim_id)}")
        self.db.execute("UPDATE claims SET published=1 WHERE id=?", (claim_id,))
        self.db.commit()

    def record_prior_publication(self, claim_id: str) -> None:
        """Reconcile an ALREADY issued historical claim, without approving it.

        Trusted host only; do not expose as an LLM-callable tool.
        """
        self.claim(claim_id)
        self.db.execute("UPDATE claims SET published=1 WHERE id=?", (claim_id,))
        self.db.commit()

    def run_fact_check(
        self, claim_id: str, verifier_name: str,
        trusted_verifier: Callable[[str, dict], CheckResult],
    ) -> str:
        """Only host-provisioned verifiers can establish check results.

        A check result means evidence supports/refutes a proposition, NOT infallible truth.
        """
        claim = self.claim(claim_id)
        if ClaimKind(claim["kind"]) is not ClaimKind.FACT:
            raise TypeError("Fact check is only available for factual claims")
        result = trusted_verifier(claim["text"], json.loads(claim["scope"]))
        if not isinstance(result, CheckResult) or not isinstance(result.verdict, Verdict):
            raise TypeError("Verifier must return a CheckResult")
        if not result.evidence_ref or not result.explanation:
            raise ValueError("Evidence locator and rationale are required")
        check_id = _id()
        self.db.execute(
            "INSERT INTO checks VALUES (?,?,?,?,?,?,?,?)",
            (check_id, claim_id, verifier_name, result.verdict.value,
             result.evidence_ref, result.explanation, result.proposed_correction, _now()),
        )
        self.db.commit()
        return check_id

    def speaker_correction(
        self, claim_id: str, *, authenticated_speaker: str,
        clarification_exact: str,
    ) -> str:
        """Original speaker can correct what an assistant attributed to them.

        This does NOT prove an external/world fact. The host must authenticate
        authenticated_speaker; a free-text speaker name is not authentication.
        """
        claim = self.claim(claim_id)
        if ClaimKind(claim["kind"]) not in (ClaimKind.ATTRIBUTION, ClaimKind.PERSPECTIVE):
            raise TypeError("Speaker correction cannot determine an external fact")
        if not clarification_exact:
            raise ValueError("A verbatim clarification is required")
        stmt = self.db.execute(
            "SELECT speaker FROM statements WHERE id=?", (claim["source_id"],)
        ).fetchone()
        if stmt is None or stmt["speaker"] != authenticated_speaker:
            raise PermissionError("Only the original speaker can clarify this attribution")
        ref = self.preserve_statement(authenticated_speaker, clarification_exact)
        correction_id = _id()
        self.db.execute(
            "INSERT INTO corrections VALUES (?,?,?,?,?,?,?)",
            (correction_id, claim_id, "source_speaker", ref,
             "Speaker rejected the assistant's attribution", clarification_exact, _now()),
        )
        self.db.commit()
        return correction_id

    def correct_refuted_fact(self, claim_id: str) -> str:
        """Withdraw a previously asserted claim when checks refute it without conflict."""
        claim = self.claim(claim_id)
        if ClaimKind(claim["kind"]) is not ClaimKind.FACT:
            raise TypeError("Only factual claims can be corrected with external checks")
        if self.status(claim_id) != "REFUTED_BY_CHECK":
            raise ValueError("Refuted check with no competing support is required")
        check = self.db.execute(
            "SELECT * FROM checks WHERE claim_id=? AND verdict='refutes' "
            "ORDER BY recorded_at DESC LIMIT 1", (claim_id,)
        ).fetchone()
        correction_id = _id()
        self.db.execute(
            "INSERT INTO corrections VALUES (?,?,?,?,?,?,?)",
            (correction_id, claim_id, "external_check", check["evidence_ref"],
             check["explanation"], check["proposed_correction"], _now()),
        )
        self.db.commit()
        return correction_id

    def acknowledgement(self, claim_id: str) -> str:
        """Emit acknowledgement only AFTER a correction has been recorded."""
        claim = self.claim(claim_id)
        correction = self.db.execute(
            "SELECT * FROM corrections WHERE claim_id=? ORDER BY recorded_at DESC LIMIT 1",
            (claim_id,),
        ).fetchone()
        if correction is None:
            raise ValueError("No recorded correction; do not fabricate an admission")
        if not claim["published"]:
            return (
                f'The proposed but unpublished claim "{claim["text"]}" was withdrawn. '
                f'Recorded correction: "{correction["corrected_text"]}". '
                "No prior public assertion is claimed."
            )
        if correction["authority"] == "source_speaker":
            return (
                f'I previously attributed this to you: "{claim["text"]}". '
                f'That attribution was wrong. Your clarification was: '
                f'"{correction["corrected_text"]}". '
                "I withdraw my attribution and retain your original statement."
            )
        correction_text = correction["corrected_text"]
        msg = (
            f'I previously claimed: "{claim["text"]}". '
            f'I was wrong to present it as established: the recorded check contradicts it '
            f'({correction["evidence_ref"]}). I withdraw the earlier claim.' 
        )
        if correction_text:
            msg += f' The verifier proposed: "{correction_text}" (check independently before asserting it).'
        return msg

    def unresolved_claims(self) -> list[tuple[str, str]]:
        rows = self.db.execute("SELECT id, text FROM claims ORDER BY recorded_at").fetchall()
        return [(r["id"], r["text"]) for r in rows if self.status(r["id"]) in (
            "UNVERIFIED", "HYPOTHESIS_ONLY", "NEEDS_SPEAKER_OR_HUMAN_REVIEW",
            "UNSUPPORTED_ATTRIBUTION", "DISPUTED"
        )]
