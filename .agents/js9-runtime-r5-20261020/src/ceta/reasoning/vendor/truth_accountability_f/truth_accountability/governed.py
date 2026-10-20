"""Standalone, host-governed truth accounting reference.

This is a deterministic authority gate and evidence/event ledger, NOT a general
semantic validator, independent oracle of truth, production authentication
system, or direct integration into Societal Reasoning Core Version 1.

A model may submit untrusted proposals only. Only trusted host application code
can call the methods that register verifiers, authenticate actors, confirm
speaker meaning, append checks, confirm actual delivery or enter corrections.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Iterator
from uuid import uuid4

from .semantic import Modality, PropositionAnnotation, SpeechAct, semantic_warnings
from .verifiers import EvidenceFinding, EvidenceVerdict, VerificationRegistry


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return uuid4().hex


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON object key")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise ValueError(f"Non-finite JSON constant is forbidden: {value}")


def _hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


# A positive event maps to exactly one host-authorized database record.
# The recorded row fingerprint is committed inside the event chain. This
# detects unsynchronized edits and deletions in decision-critical tables.
# It is NOT a replacement for an external trust anchor or protected HMAC key.
_SEALED_TABLE_KEYS = {
    "sources_v2": ("id",), "proposals_v2": ("id",),
    "checks_v2": ("id",), "meaning_reviews_v2": ("id",),
    "deliveries_v2": ("id",), "corrections_v2": ("id",),
    "dependencies_v2": ("upstream_id", "downstream_id"),
    "invalidations_v2": ("claim_id", "root_claim_id"),
    "anomalies_v2": ("id",), "hypotheses_v2": ("id",),
    "sense_issues_v2": ("id",), "sense_resolutions_v2": ("id",),
    "perspectives_v2": ("id",),
}
_EVENT_RECORD_TYPES = {
    "SOURCE_PRESERVED": "sources_v2",
    "CLAIM_PROPOSED": "proposals_v2",
    "EVIDENCE_CHECK": "checks_v2",
    "MEANING_REVIEW": "meaning_reviews_v2",
    "DELIVERED": "deliveries_v2",
    "HISTORICAL_DELIVERY_RECONCILED": "deliveries_v2",
    "CLAIM_WITHDRAWN": "corrections_v2",
    "DEPENDENCY_LINKED": "dependencies_v2",
    "DEPENDENCY_INVALIDATED": "invalidations_v2",
    "ANOMALY_UNRESOLVED": "anomalies_v2",
    "HYPOTHESIS_PROPOSED": "hypotheses_v2",
    "MATERIAL_AMBIGUITY": "sense_issues_v2",
    "SENSE_RESOLVED": "sense_resolutions_v2",
    "PERSPECTIVE_RECORDED": "perspectives_v2",
}


@dataclass(frozen=True)
class AuthenticatedActor:
    """Claims about authentication supplied by the trusted host, not proof.

    These objects MUST NOT be built from a user/LLM-provided actor_id or role.
    """
    actor_id: str
    roles: frozenset[str]


@dataclass(frozen=True)
class Decision:
    claim_id: str
    status: str
    evidence_refs: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    supports: int = 0
    refutes: int = 0
    requires_independent_groups: int = 0


class GovernedTruthCore:
    """A SINGLE new host authority gate. The original TruthLedger is retained
    for compatibility and illustration; it must not be used as a production
    bypass alongside this path.
    """

    CLAIM_KINDS = frozenset({"quote", "paraphrase", "fact", "hypothesis"})
    POLICIES = {"standard": 1, "high_stakes": 2}

    def __init__(self, database: str | Path = ":memory:", registry: VerificationRegistry | None = None,
                 *, audit_key: bytes | None = None):
        # An optional stable, host-held key authenticates new audit records.
        # NEVER store this key in the SQLite database or source archives.
        if audit_key is not None and (not isinstance(audit_key, bytes) or len(audit_key) < 32):
            raise ValueError("Host audit key must be at least 32 secret bytes")
        self._audit_key = audit_key
        self.db = sqlite3.connect(str(database), timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.execute("PRAGMA busy_timeout=5000")
        self.verifiers = registry if registry is not None else VerificationRegistry()
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS sources_v2 (
              id TEXT PRIMARY KEY, actor_id TEXT NOT NULL, channel TEXT NOT NULL,
              exact_utf8 BLOB NOT NULL, sha256 TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS proposals_v2 (
              id TEXT PRIMARY KEY, kind TEXT NOT NULL,
              text TEXT NOT NULL, source_id TEXT, span_start INTEGER, span_end INTEGER,
              scope_json TEXT NOT NULL, annotations_json TEXT NOT NULL,
              warnings_json TEXT NOT NULL, evidence_policy TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(source_id) REFERENCES sources_v2(id)
            );
            CREATE TABLE IF NOT EXISTS checks_v2 (
              id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, verifier_id TEXT NOT NULL,
              independent_group TEXT NOT NULL, verdict TEXT NOT NULL,
              locator TEXT NOT NULL, explanation TEXT NOT NULL,
              evidence_sha256 TEXT NOT NULL, correction_proposal TEXT NOT NULL,
              checked_at TEXT NOT NULL, expires_at TEXT,
              FOREIGN KEY(claim_id) REFERENCES proposals_v2(id)
            );
            CREATE TABLE IF NOT EXISTS meaning_reviews_v2 (
              id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, actor_id TEXT NOT NULL,
              role TEXT NOT NULL, verdict TEXT NOT NULL, justification TEXT NOT NULL,
              created_at TEXT NOT NULL,
              FOREIGN KEY(claim_id) REFERENCES proposals_v2(id)
            );
            CREATE TABLE IF NOT EXISTS deliveries_v2 (
              id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, delivered_text TEXT NOT NULL,
              transport_receipt TEXT NOT NULL UNIQUE, delivered_at TEXT NOT NULL,
              FOREIGN KEY(claim_id) REFERENCES proposals_v2(id)
            );
            CREATE TABLE IF NOT EXISTS corrections_v2 (
              id TEXT PRIMARY KEY, claim_id TEXT NOT NULL UNIQUE,
              authority TEXT NOT NULL, authority_actor TEXT NOT NULL,
              evidence_ref TEXT NOT NULL, correction_text TEXT NOT NULL,
              reason TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(claim_id) REFERENCES proposals_v2(id)
            );
            CREATE TABLE IF NOT EXISTS dependencies_v2 (
              upstream_id TEXT NOT NULL, downstream_id TEXT NOT NULL,
              PRIMARY KEY(upstream_id, downstream_id),
              FOREIGN KEY(upstream_id) REFERENCES proposals_v2(id),
              FOREIGN KEY(downstream_id) REFERENCES proposals_v2(id)
            );
            CREATE TABLE IF NOT EXISTS invalidations_v2 (
              id TEXT PRIMARY KEY, claim_id TEXT NOT NULL, root_claim_id TEXT NOT NULL,
              reason TEXT NOT NULL, created_at TEXT NOT NULL,
              UNIQUE(claim_id, root_claim_id),
              FOREIGN KEY(claim_id) REFERENCES proposals_v2(id),
              FOREIGN KEY(root_claim_id) REFERENCES proposals_v2(id)
            );
            CREATE TABLE IF NOT EXISTS anomalies_v2 (
              id TEXT PRIMARY KEY, source_id TEXT, fingerprint TEXT NOT NULL,
              description TEXT NOT NULL, failed_categories_json TEXT NOT NULL,
              features_json TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(source_id) REFERENCES sources_v2(id)
            );
            CREATE TABLE IF NOT EXISTS hypotheses_v2 (
              id TEXT PRIMARY KEY, anomaly_id TEXT NOT NULL, hypothesis TEXT NOT NULL,
              falsifiable_test TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(anomaly_id) REFERENCES anomalies_v2(id)
            );
            CREATE TABLE IF NOT EXISTS sense_issues_v2 (
              id TEXT PRIMARY KEY, source_id TEXT NOT NULL, span_start INTEGER NOT NULL,
              span_end INTEGER NOT NULL, term TEXT NOT NULL,
              material_reason TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(source_id) REFERENCES sources_v2(id)
            );
            CREATE TABLE IF NOT EXISTS sense_resolutions_v2 (
              id TEXT PRIMARY KEY, issue_id TEXT NOT NULL UNIQUE,
              reference_kind TEXT NOT NULL, source_locator TEXT NOT NULL,
              selected_sense TEXT NOT NULL, reviewer_id TEXT NOT NULL,
              domain_scope TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(issue_id) REFERENCES sense_issues_v2(id)
            );
            CREATE TABLE IF NOT EXISTS perspectives_v2 (
              id TEXT PRIMARY KEY, source_id TEXT NOT NULL, subject_key TEXT NOT NULL,
              span_start INTEGER NOT NULL, span_end INTEGER NOT NULL,
              report_kind TEXT NOT NULL, context_json TEXT NOT NULL, created_at TEXT NOT NULL,
              FOREIGN KEY(source_id) REFERENCES sources_v2(id)
            );
            CREATE TABLE IF NOT EXISTS audit_events_v2 (
              seq INTEGER PRIMARY KEY, event_kind TEXT NOT NULL,
              object_id TEXT NOT NULL, payload_json TEXT NOT NULL,
              previous_hash TEXT NOT NULL, event_hash TEXT NOT NULL,
              created_at TEXT NOT NULL
            );
        """)
        self.db.commit()

    def _event_identity(self, kind: str, object_id: str, payload: dict) -> tuple[str, dict]:
        if kind not in _EVENT_RECORD_TYPES:
            raise RuntimeError(f"Unknown audit event type: {kind}")
        table = _EVENT_RECORD_TYPES[kind]
        if kind == "EVIDENCE_CHECK":
            key = {"id": payload["check_id"]}
        elif kind == "MEANING_REVIEW":
            key = {"id": payload["review_id"]}
        elif kind in {"DELIVERED", "HISTORICAL_DELIVERY_RECONCILED"}:
            key = {"id": payload["delivery_id"]}
        elif kind == "CLAIM_WITHDRAWN":
            key = {"id": payload["correction_id"]}
        elif kind == "SENSE_RESOLVED":
            key = {"id": payload["resolution_id"]}
        elif kind == "DEPENDENCY_LINKED":
            key = {"upstream_id": payload["upstream"], "downstream_id": object_id}
        elif kind == "DEPENDENCY_INVALIDATED":
            key = {"claim_id": object_id, "root_claim_id": payload["root"]}
        else:
            key = {"id": object_id}
        if tuple(key) != _SEALED_TABLE_KEYS[table]:
            raise RuntimeError("Invalid internal seal key")
        return table, key

    def _row_digest(self, table: str, key: dict) -> str | None:
        if table not in _SEALED_TABLE_KEYS or tuple(key) != _SEALED_TABLE_KEYS[table]:
            raise ValueError("Unknown table or invalid row identity")
        where = " AND ".join(f"{name}=?" for name in key)
        row = self.db.execute(f"SELECT * FROM {table} WHERE {where}", tuple(key.values())).fetchone()
        if row is None:
            return None
        canonical = {}
        for name in row.keys():
            value = row[name]
            if isinstance(value, bytes):
                canonical[name] = {"type": "BLOB", "sha256": _hash(value), "bytes": len(value)}
            else:
                canonical[name] = value
        return _hash(_json({"table": table, "row": canonical}).encode("utf-8"))

    def _event_hash(self, record: dict) -> str:
        data = _json(record).encode("utf-8")
        if self._audit_key is not None:
            return hmac.new(self._audit_key, data, hashlib.sha256).hexdigest()
        return _hash(data)

    def audit_anchor(self) -> dict:
        """Return an externally storable last-event anchor; copying inside the DB is not independent."""
        row = self.db.execute("SELECT seq,event_hash FROM audit_events_v2 ORDER BY seq DESC LIMIT 1").fetchone()
        return {"seq": row["seq"], "event_hash": row["event_hash"]} if row else {"seq": 0, "event_hash": "0"*64}

    def _require_integrity(self) -> None:
        report = self.integrity_report()
        if not report["ok"]:
            raise RuntimeError("Decision ledger integrity failure; review required before use")

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            # Writes MUST also refuse a compromised ledger. Otherwise a
            # subsequent legitimate event could extend an untrusted history.
            self._require_integrity()
            yield
            self.db.commit()
        except BaseException:
            self.db.rollback()
            raise

    def _event(self, kind: str, object_id: str, payload: dict) -> None:
        """Bind one specific newly written record to the audit chain in the transaction."""
        table, key = self._event_identity(kind, object_id, payload)
        fingerprint = self._row_digest(table, key)
        if fingerprint is None:
            raise RuntimeError("Cannot seal a missing decision record")
        payload = dict(payload)
        payload["sealed_record"] = {"table": table, "key": key,
                                    "row_sha256": fingerprint}
        last = self.db.execute(
            "SELECT seq,event_hash FROM audit_events_v2 ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        seq = 1 if last is None else last["seq"] + 1
        previous = "0" * 64 if last is None else last["event_hash"]
        when = _now()
        data = _json(payload)
        digest = self._event_hash({"seq": seq, "kind": kind, "id": object_id,
                                   "payload": payload, "previous": previous,
                                   "created_at": when})
        self.db.execute("INSERT INTO audit_events_v2 VALUES (?,?,?,?,?,?,?)",
                        (seq, kind, object_id, data, previous, digest, when))

    def _source(self, source_id: str) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM sources_v2 WHERE id=?", (source_id,)).fetchone()
        if row is None:
            raise KeyError("Unknown source")
        return row

    def _proposal(self, claim_id: str) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM proposals_v2 WHERE id=?", (claim_id,)).fetchone()
        if row is None:
            raise KeyError("Unknown claim")
        return row

    def preserve(self, actor_id: str, exact_text: str, *, channel: str = "conversation") -> str:
        if not actor_id or not isinstance(exact_text, str) or not exact_text:
            raise ValueError("An identified actor and exact text are required")
        if not isinstance(channel, str) or not channel or len(channel) > 100:
            raise ValueError("Invalid channel")
        raw = exact_text.encode("utf-8")
        if len(raw) > 1024 * 1024:
            raise ValueError("Reference source exceeds 1 MiB")
        source_id = _id()
        sha = _hash(raw)
        with self._transaction():
            self.db.execute("INSERT INTO sources_v2 VALUES (?,?,?,?,?,?)",
                            (source_id, actor_id, channel, raw, sha, _now()))
            self._event("SOURCE_PRESERVED", source_id, {"sha256": sha, "actor_id": actor_id})
        return source_id

    def original(self, source_id: str) -> str:
        row = self._source(source_id)
        raw = bytes(row["exact_utf8"])
        if _hash(raw) != row["sha256"]:
            raise RuntimeError("Original source integrity mismatch")
        return raw.decode("utf-8")

    def propose(self, kind: str, text: str, *, source_id: str | None = None,
                span: tuple[int, int] | None = None, scope: dict | None = None,
                annotations: PropositionAnnotation | None = None,
                policy: str = "standard") -> str:
        """Untrusted proposition proposal; annotations are suggestions, not facts.

        Spans use Python Unicode character offsets, NOT UTF-8 byte positions.
        """
        if kind not in self.CLAIM_KINDS:
            raise ValueError("Unknown kind")
        if not isinstance(text, str) or not text or len(text) > 16384:
            raise ValueError("Invalid claim text")
        if policy not in self.POLICIES:
            raise ValueError("Unknown evidence policy")
        if kind in ("quote", "paraphrase") and source_id is None:
            raise ValueError("Speaker-dependent claims require source")
        if span is not None and source_id is None:
            raise ValueError("Span requires source")
        source_fragment = ""
        if source_id:
            original = self.original(source_id)
            if span is None:
                if kind in ("quote", "paraphrase"):
                    raise ValueError("Quoted or paraphrased span required")
            else:
                start, end = span
                if (not isinstance(start, int) or isinstance(start, bool) or
                    not isinstance(end, int) or isinstance(end, bool) or
                    start < 0 or end > len(original) or start >= end):
                    raise ValueError("Invalid source span")
                source_fragment = original[start:end]
        if kind == "quote" and source_fragment != text:
            raise ValueError("Verbatim quotation must match exact recorded span")
        if scope is not None and not isinstance(scope, dict):
            raise TypeError("Scope must be an object")
        annotation = annotations or PropositionAnnotation()
        if not isinstance(annotation, PropositionAnnotation):
            raise TypeError("Annotations must be structured")
        if not isinstance(annotation.speech_act, SpeechAct) or not isinstance(annotation.modality, Modality):
            raise TypeError("Invalid annotation enums")
        if annotation.negated is not None and not isinstance(annotation.negated, bool):
            raise TypeError("Negation must be boolean or unknown")
        if any(not isinstance(v, str) or len(v) > 256 for v in
               (annotation.quantifier, annotation.time_scope, annotation.spatial_scope, annotation.referent)):
            raise ValueError("Invalid annotation fields")
        fields = {"speech_act": annotation.speech_act.value, "modality": annotation.modality.value,
                  "negated": annotation.negated, "quantifier": annotation.quantifier,
                  "time_scope": annotation.time_scope, "spatial_scope": annotation.spatial_scope,
                  "referent": annotation.referent}
        scopes = scope or {}
        warnings = semantic_warnings(source_fragment, text) if source_fragment else ()
        claim_id = _id()
        # Encode now to validate serializability BEFORE opening the transaction.
        scope_json, annotation_json, warnings_json = _json(scopes), _json(fields), _json(list(warnings))
        with self._transaction():
            self.db.execute("INSERT INTO proposals_v2 VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (claim_id, kind, text, source_id, span[0] if span else None,
                             span[1] if span else None, scope_json, annotation_json,
                             warnings_json, policy, _now()))
            self._event("CLAIM_PROPOSED", claim_id, {"kind": kind, "text_sha256": _hash(text.encode()),
                                                      "source_id": source_id, "warnings": list(warnings)})
        return claim_id

    def propose_json(self, payload: str) -> str:
        """Strict boundary accepting model JSON as a PROPOSAL, never an approval."""
        if not isinstance(payload, str) or len(payload.encode("utf-8")) > 32768:
            raise ValueError("Model proposal payload too large")
        obj = json.loads(payload, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant)
        if not isinstance(obj, dict):
            raise ValueError("Top-level JSON must be an object")
        allowed = {"kind", "text", "source_id", "span", "scope", "annotations", "policy"}
        if set(obj) - allowed or not {"kind", "text"} <= set(obj):
            raise ValueError("Unknown keys or required keys missing")
        a = obj.get("annotations", {})
        if not isinstance(a, dict) or set(a) - {"speech_act", "modality", "negated", "quantifier", "time_scope", "spatial_scope", "referent"}:
            raise ValueError("Invalid annotation keys")
        if a.get("negated") is not None and not isinstance(a.get("negated"), bool):
            raise ValueError("Negation must be boolean or unknown")
        for key in ("quantifier", "time_scope", "spatial_scope", "referent"):
            if key in a and (not isinstance(a[key], str) or len(a[key]) > 256):
                raise ValueError("Invalid annotation value")
        annotation = PropositionAnnotation(
            speech_act=SpeechAct(a.get("speech_act", "unknown")),
            modality=Modality(a.get("modality", "unknown")),
            negated=a.get("negated"),
            quantifier=a.get("quantifier", "unspecified"),
            time_scope=a.get("time_scope", "unspecified"),
            spatial_scope=a.get("spatial_scope", "unspecified"),
            referent=a.get("referent", "unspecified"),
        )
        span = obj.get("span")
        if span is not None and (not isinstance(span, list) or len(span) != 2):
            raise ValueError("Span must be [start,end]")
        return self.propose(obj["kind"], obj["text"], source_id=obj.get("source_id"),
                            span=tuple(span) if span else None, scope=obj.get("scope"),
                            annotations=annotation, policy=obj.get("policy", "standard"))

    def review_meaning(self, claim_id: str, reviewer: AuthenticatedActor,
                       verdict: str, justification: str) -> str:
        claim = self._proposal(claim_id)
        if claim["kind"] != "paraphrase":
            raise TypeError("Only speaker-dependent paraphrases use meaning review")
        if verdict not in {"aligned", "rejected"} or not justification.strip():
            raise ValueError("Review must give a verdict and justification")
        source = self._source(claim["source_id"])
        role = "speaker" if reviewer.actor_id == source["actor_id"] else "reviewer"
        if role == "speaker" and "authenticated_speaker" not in reviewer.roles:
            raise PermissionError("Source-speaker identity has not been authenticated by host")
        if role == "reviewer" and "meaning_reviewer" not in reviewer.roles:
            raise PermissionError("Not an authorized meaning reviewer")
        review_id = _id()
        with self._transaction():
            self.db.execute("INSERT INTO meaning_reviews_v2 VALUES (?,?,?,?,?,?,?)",
                            (review_id, claim_id, reviewer.actor_id, role, verdict, justification, _now()))
            self._event("MEANING_REVIEW", claim_id, {"review_id": review_id, "role": role, "verdict": verdict})
        return review_id

    def flag_material_ambiguity(self, source_id: str, *, span: tuple[int, int],
                                term: str, reason: str, reviewer: AuthenticatedActor) -> str:
        """Known ambiguities are explicitly declared; no universal automatic detector."""
        if "meaning_reviewer" not in reviewer.roles:
            raise PermissionError("Authorized meaning reviewer required")
        source_text = self.original(source_id)
        if (not isinstance(span, tuple) or len(span) != 2 or
            any(not isinstance(n, int) or isinstance(n, bool) for n in span) or
            span[0] < 0 or span[1] > len(source_text) or span[0] >= span[1] or
            not term or source_text[span[0]:span[1]].casefold() != term.casefold()):
            raise ValueError("The ambiguous word must match a concrete source span")
        if not reason.strip():
            raise ValueError("Why ambiguity matters is required")
        issue_id = _id()
        with self._transaction():
            self.db.execute("INSERT INTO sense_issues_v2 VALUES (?,?,?,?,?,?,?)",
                            (issue_id, source_id, span[0], span[1], term, reason, _now()))
            self._event("MATERIAL_AMBIGUITY", issue_id, {"source_id": source_id,
                       "term": term, "span": list(span), "reviewer_id": reviewer.actor_id})
            # Existing approved meanings now require a sense review. Dependents
            # must be reconsidered; the issue alone does not prove they were wrong.
            affected = self.db.execute("""SELECT id FROM proposals_v2
                WHERE source_id=? AND kind='paraphrase' AND span_start < ?
                AND span_end > ?""", (source_id, span[1], span[0])).fetchall()
            for row in affected:
                self._invalidate_descendants(row["id"], "Unresolved material ambiguity")
        return issue_id

    def resolve_dictionary_sense(self, issue_id: str, *, selected_sense: str,
                                 source_locator: str, reviewer: AuthenticatedActor,
                                 reference_kind: str = "MERRIAM_WEBSTER",
                                 domain_scope: str = "general") -> str:
        if "meaning_reviewer" not in reviewer.roles or not reviewer.actor_id:
            raise PermissionError("Authorized meaning reviewer required")
        if not selected_sense.strip() or not source_locator.strip():
            raise ValueError("Selected sense and authenticable source locator are required")
        if reference_kind not in {"MERRIAM_WEBSTER", "USER_GLOSSARY", "TECHNICAL_GLOSSARY"}:
            raise ValueError("Unsupported sense reference type")
        if reference_kind == "MERRIAM_WEBSTER":
            url = urlparse(source_locator)
            if (url.scheme != "https" or url.hostname not in {"merriam-webster.com", "www.merriam-webster.com"}
                or not url.path.startswith("/dictionary/") or url.username or url.password):
                raise ValueError("Merriam-Webster references need a matching HTTPS dictionary URL")
        if reference_kind == "TECHNICAL_GLOSSARY" and domain_scope == "general":
            raise ValueError("Technical glossary needs its domain scope")
        if not self.db.execute("SELECT 1 FROM sense_issues_v2 WHERE id=?", (issue_id,)).fetchone():
            raise KeyError("Unknown ambiguity")
        resolution_id = _id()
        with self._transaction():
            self.db.execute("INSERT INTO sense_resolutions_v2 VALUES (?,?,?,?,?,?,?,?)",
                            (resolution_id, issue_id, reference_kind, source_locator, selected_sense,
                             reviewer.actor_id, domain_scope, _now()))
            self._event("SENSE_RESOLVED", issue_id, {"resolution_id": resolution_id,
                        "reference_kind": reference_kind, "locator": source_locator,
                        "domain_scope": domain_scope, "reviewer_id": reviewer.actor_id,
                        "sense_sha256": _hash(selected_sense.encode())})
        return resolution_id

    def record_perspective(self, source_id: str, *, subject_key: str,
                           span: tuple[int,int], report_kind: str,
                           context: dict | None = None) -> str:
        """Store what a speaker reports, not an independently established fact."""
        source = self.original(source_id)
        if not subject_key or len(subject_key) > 200 or not re.fullmatch(r"[A-Za-z0-9_.:-]+", subject_key):
            raise ValueError("Use a stable subject identifier")
        if report_kind not in {"experience", "belief", "observation", "interpretation"}:
            raise ValueError("Unknown perspective report kind")
        if not isinstance(span, tuple) or len(span) != 2 or any(
            not isinstance(n,int) or isinstance(n,bool) for n in span
        ) or span[0] < 0 or span[1] > len(source) or span[0] >= span[1]:
            raise ValueError("Perspective report must have a verbatim source span")
        if context is not None and not isinstance(context, dict):
            raise ValueError("Context must be a structured object")
        context_json = _json(context or {})
        rid = _id()
        with self._transaction():
            self.db.execute("INSERT INTO perspectives_v2 VALUES (?,?,?,?,?,?,?,?)",
                            (rid,source_id,subject_key,span[0],span[1],report_kind,context_json,_now()))
            self._event("PERSPECTIVE_RECORDED", rid, {"source_id":source_id,
                "subject":subject_key,"kind":report_kind,"span":list(span)})
        return rid

    def compare_perspectives(self, subject_key: str) -> dict:
        """Comparison never decides an external factual dispute by vote."""
        self._require_integrity()
        rows = self.db.execute("SELECT * FROM perspectives_v2 WHERE subject_key=? ORDER BY created_at,id",
                               (subject_key,)).fetchall()
        reports = []
        contexts = set()
        for row in rows:
            source = self._source(row["source_id"])
            original = self.original(row["source_id"])
            context = json.loads(row["context_json"])
            contexts.add(_json(context))
            reports.append({"id":row["id"], "speaker":source["actor_id"],
                            "reported_exact":original[row["span_start"]:row["span_end"]],
                            "report_kind":row["report_kind"], "context":context,
                            "epistemic_status":"SPEAKER_REPORT_NOT_EXTERNAL_FACT_VERIFICATION"})
        return {"subject_key": subject_key, "reports": reports,
                "context_variants": len(contexts),
                "comparison_status": "DIFFERING_CONTEXTS" if len(contexts)>1 else "SAME_RECORDED_CONTEXT",
                "fact_resolution": "REQUIRES_INDEPENDENT_EVIDENCE"}

    def check(self, claim_id: str, verifier_id: str) -> str:
        claim = self._proposal(claim_id)
        if claim["kind"] != "fact":
            raise TypeError("Independent fact verification requires a factual claim")
        verifier = self.verifiers.get(verifier_id)
        scope = json.loads(claim["scope_json"])
        if verifier.allowed_scope != "general" and scope.get("domain") != verifier.allowed_scope:
            raise PermissionError("Verifier not authorized for this claim domain")
        finding = verifier.verify(claim["text"], scope)
        if (not isinstance(finding, EvidenceFinding) or
            not isinstance(finding.verdict, EvidenceVerdict) or
            not isinstance(finding.raw_evidence, bytes) or
            not finding.locator or not finding.explanation):
            raise ValueError("Verifier produced incomplete/invalid evidence")
        if finding.expires_at:
            expiry = datetime.fromisoformat(finding.expires_at)
            if expiry.tzinfo is None:
                raise ValueError("Evidence expiry must have timezone")
        check_id = _id()
        with self._transaction():
            self.db.execute("INSERT INTO checks_v2 VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                            (check_id, claim_id, verifier.verifier_id, verifier.independent_group,
                             finding.verdict.value, finding.locator, finding.explanation,
                             finding.digest, finding.proposed_correction, _now(), finding.expires_at))
            self._event("EVIDENCE_CHECK", claim_id, {"check_id": check_id,
                        "verifier_id": verifier_id, "independent_group": verifier.independent_group,
                        "evidence_sha256": finding.digest, "verdict": finding.verdict.value})
        return check_id

    def _active_checks(self, claim_id: str) -> tuple[list[sqlite3.Row], bool]:
        rows = self.db.execute("SELECT * FROM checks_v2 WHERE claim_id=? ORDER BY checked_at, id",
                               (claim_id,)).fetchall()
        now = datetime.now(timezone.utc)
        active = [r for r in rows if not r["expires_at"] or datetime.fromisoformat(r["expires_at"]) > now]
        return active, bool(rows)

    def decision(self, claim_id: str) -> Decision:
        # All supported decisions MUST fail closed if a committed record changed.
        self._require_integrity()
        claim = self._proposal(claim_id)
        warnings = tuple(json.loads(claim["warnings_json"]))
        if self.db.execute("SELECT 1 FROM corrections_v2 WHERE claim_id=?", (claim_id,)).fetchone():
            return Decision(claim_id, "WITHDRAWN", warnings=warnings)
        if self.db.execute("SELECT 1 FROM invalidations_v2 WHERE claim_id=?", (claim_id,)).fetchone():
            return Decision(claim_id, "NEEDS_RECONSIDERATION", warnings=warnings)
        kind = claim["kind"]
        if kind == "quote":
            # Verify source integrity again before rendering.
            source = self.original(claim["source_id"])
            if source[claim["span_start"]:claim["span_end"]] != claim["text"]:
                return Decision(claim_id, "SOURCE_MISMATCH", warnings=warnings)
            return Decision(claim_id, "QUOTED_VERBATIM", warnings=warnings)
        if kind == "paraphrase":
            sense_rows = self.db.execute("""SELECT s.id AS issue_id, r.reference_kind,
                r.domain_scope, r.created_at AS resolution_at FROM sense_issues_v2 AS s
                LEFT JOIN sense_resolutions_v2 AS r ON r.issue_id=s.id
                WHERE s.source_id=? AND s.span_start < ? AND s.span_end > ?""",
                (claim["source_id"], claim["span_end"], claim["span_start"])).fetchall()
            claim_domain = json.loads(claim["scope_json"]).get("domain", "general")
            if any(r["resolution_at"] is None or
                   (r["reference_kind"] == "TECHNICAL_GLOSSARY" and r["domain_scope"] != claim_domain)
                   for r in sense_rows):
                return Decision(claim_id, "NEEDS_SENSE_RESOLUTION", warnings=warnings)
            reviews = self.db.execute("SELECT verdict,role,created_at FROM meaning_reviews_v2 WHERE claim_id=?",
                                      (claim_id,)).fetchall()
            seen = {r["verdict"] for r in reviews}
            latest_sense = max((r["resolution_at"] for r in sense_rows), default=None)
            new_review_after_resolution = not latest_sense or any(r["created_at"] > latest_sense for r in reviews)
            risk_requires_speaker = bool(warnings)
            speaker_approved = any(r["role"] == "speaker" and r["verdict"] == "aligned"
                                   and (not latest_sense or r["created_at"] > latest_sense)
                                   for r in reviews)
            status = ("MEANING_DISPUTED" if "rejected" in seen else
                      "NEEDS_MEANING_REVIEW" if not seen or not new_review_after_resolution or
                          (risk_requires_speaker and not speaker_approved) else
                      "MEANING_REVIEWED")
            return Decision(claim_id, status, warnings=warnings)
        if kind == "hypothesis":
            return Decision(claim_id, "HYPOTHESIS_ONLY", warnings=warnings)
        checks, had_any = self._active_checks(claim_id)
        if not checks:
            return Decision(claim_id, "STALE_EVIDENCE" if had_any else "UNVERIFIED", warnings=warnings)
        support_groups = {r["independent_group"] for r in checks if r["verdict"] == "supports"}
        refute_groups = {r["independent_group"] for r in checks if r["verdict"] == "refutes"}
        refs = tuple(sorted(set(r["locator"] for r in checks)))
        threshold = self.POLICIES[claim["evidence_policy"]]
        if support_groups and refute_groups:
            state = "DISPUTED"
        elif len(support_groups) >= threshold:
            state = "SUPPORTED_BY_CHECK"
        elif len(refute_groups) >= threshold:
            state = "REFUTED_BY_CHECK"
        else:
            state = "INSUFFICIENT_EVIDENCE"
        return Decision(claim_id, state, refs, warnings, len(support_groups),
                        len(refute_groups), threshold)

    def render(self, claim_id: str) -> str:
        """Only output constructor for unqualified *supported* assertions.

        The caller must deliver returned text unchanged; no subsequent LLM
        can add ungoverned assertions if the gate is to hold.
        """
        claim = self._proposal(claim_id)
        decision = self.decision(claim_id)
        kind = claim["kind"]
        if kind == "quote" and decision.status == "QUOTED_VERBATIM":
            speaker = self._source(claim["source_id"])["actor_id"]
            return f"Recorded statement from {speaker}: {_json(claim['text'])} (quotation only, not fact verification)"
        if kind == "hypothesis" and decision.status == "HYPOTHESIS_ONLY":
            return f"Unverified hypothesis: {claim['text']}"
        if kind == "paraphrase" and decision.status == "MEANING_REVIEWED":
            speaker = self._source(claim["source_id"])["actor_id"]
            return f"Reviewed paraphrase of {speaker}'s statement: {claim['text']} (not external fact verification)"
        if kind == "fact" and decision.status == "SUPPORTED_BY_CHECK":
            return f"Evidence supports within recorded scope: {claim['text']} [checks: {', '.join(decision.evidence_refs)}]"
        raise PermissionError(f"Gate did not authorize this assertion: {decision.status}")

    def render_qualified(self, claim_id: str) -> str:
        """Explicitly qualified description of a claim, NEVER factual approval."""
        claim = self._proposal(claim_id)
        decision = self.decision(claim_id)
        if decision.status in {"QUOTED_VERBATIM", "HYPOTHESIS_ONLY", "MEANING_REVIEWED", "SUPPORTED_BY_CHECK"}:
            return self.render(claim_id)
        return f"Claim not established ({decision.status}): {_json(claim['text'])}"

    def confirm_delivery(self, claim_id: str, delivered_text: str, receipt: str,
                         actor: AuthenticatedActor) -> str:
        """Host must call AFTER successful real delivery, not mere generation."""
        if "delivery_host" not in actor.roles or not receipt:
            raise PermissionError("Only trusted delivery host may confirm delivery")
        authorized_text = self.render(claim_id)
        if delivered_text != authorized_text:
            raise ValueError("Delivered text does not match gate-approved rendering")
        did = _id()
        with self._transaction():
            self.db.execute("INSERT INTO deliveries_v2 VALUES (?,?,?,?,?)",
                            (did, claim_id, delivered_text, receipt, _now()))
            self._event("DELIVERED", claim_id, {"delivery_id": did, "receipt": receipt,
                                               "text_sha256": _hash(delivered_text.encode())})
        return did

    def reconcile_historical_delivery(self, claim_id: str, *, transcript_source_id: str,
                                      receipt: str, actor: AuthenticatedActor) -> str:
        """Record an ACTUAL previously delivered message, even if it was wrong.

        Required evidence is a host-supplied transcript source record. This is
        not general proof the claimed delivery occurred: the trusted host must
        verify its receipt and transcript outside this reference implementation.
        Do not expose this entrypoint to models or user-controlled actor fields.
        """
        if "delivery_host" not in actor.roles or not receipt:
            raise PermissionError("Only a trusted delivery host can reconcile history")
        source = self._source(transcript_source_id)
        if source["channel"] != "published_assistant_transcript":
            raise PermissionError("A designated historical assistant transcript is required")
        delivered_text = self.original(transcript_source_id)
        claim = self._proposal(claim_id)
        if delivered_text.strip() != claim["text"].strip():
            raise ValueError("This conservative adapter requires the whole prior answer to be the exact claim; do not equate a quoted or negated mention with an assertion")
        did = _id()
        with self._transaction():
            self.db.execute("INSERT INTO deliveries_v2 VALUES (?,?,?,?,?)",
                            (did, claim_id, delivered_text, receipt, _now()))
            self._event("HISTORICAL_DELIVERY_RECONCILED", claim_id,
                        {"delivery_id": did, "source_id": transcript_source_id,
                         "receipt": receipt, "text_sha256": _hash(delivered_text.encode())})
        return did

    def add_dependency(self, upstream_id: str, downstream_id: str) -> None:
        self._proposal(upstream_id)
        self._proposal(downstream_id)
        if upstream_id == downstream_id:
            raise ValueError("Self-dependency forbidden")
        # A cycle would occur when the proposed child already reaches the parent.
        reachable = {downstream_id}
        queue = [downstream_id]
        while queue:
            node = queue.pop(0)
            for row in self.db.execute("SELECT downstream_id FROM dependencies_v2 WHERE upstream_id=?", (node,)):
                nxt = row["downstream_id"]
                if nxt == upstream_id:
                    raise ValueError("Dependency cycle forbidden")
                if nxt not in reachable:
                    reachable.add(nxt)
                    queue.append(nxt)
        with self._transaction():
            exists = self.db.execute("SELECT 1 FROM dependencies_v2 WHERE upstream_id=? AND downstream_id=?",
                                     (upstream_id, downstream_id)).fetchone()
            if not exists:
                self.db.execute("INSERT INTO dependencies_v2 VALUES (?,?)", (upstream_id, downstream_id))
                self._event("DEPENDENCY_LINKED", downstream_id, {"upstream": upstream_id})
            if self.decision(upstream_id).status in {"WITHDRAWN", "NEEDS_RECONSIDERATION"}:
                self._invalidate_descendants(upstream_id, "Linked to an already-invalid upstream claim")

    def _invalidate_descendants(self, root_id: str, reason: str) -> None:
        """Apply transitive invalidation while inside correction transaction."""
        visited = {root_id}
        queue = [root_id]
        while queue:
            node = queue.pop(0)
            rows = self.db.execute("SELECT downstream_id FROM dependencies_v2 WHERE upstream_id=?", (node,))
            for row in rows:
                nxt = row["downstream_id"]
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)
                    invalidation_id = _id()
                    self.db.execute("INSERT OR IGNORE INTO invalidations_v2 VALUES (?,?,?,?,?)",
                                    (invalidation_id, nxt, root_id, reason, _now()))
                    self._event("DEPENDENCY_INVALIDATED", nxt, {"root": root_id, "reason": reason})

    def _record_correction(self, claim_id: str, authority: str, actor_id: str,
                           evidence_ref: str, correction_text: str, reason: str) -> str:
        correction_id = _id()
        with self._transaction():
            self.db.execute("INSERT INTO corrections_v2 VALUES (?,?,?,?,?,?,?,?)",
                            (correction_id, claim_id, authority, actor_id,
                             evidence_ref, correction_text, reason, _now()))
            self._event("CLAIM_WITHDRAWN", claim_id, {"correction_id": correction_id,
                        "authority": authority, "evidence_ref": evidence_ref,
                        "corrected_text_sha256": _hash(correction_text.encode())})
            self._invalidate_descendants(claim_id, "An upstream claim was withdrawn")
        return correction_id

    def clarify_attribution(self, claim_id: str, speaker: AuthenticatedActor,
                            clarification_exact: str) -> str:
        claim = self._proposal(claim_id)
        if claim["kind"] != "paraphrase":
            raise TypeError("Speaker clarification is for attributed meaning, not world facts")
        original_speaker = self._source(claim["source_id"])["actor_id"]
        if speaker.actor_id != original_speaker or "authenticated_speaker" not in speaker.roles:
            raise PermissionError("Authenticated original speaker required")
        if not clarification_exact or not isinstance(clarification_exact, str):
            raise ValueError("Exact speaker clarification required")
        ref = self.preserve(speaker.actor_id, clarification_exact, channel="speaker_clarification")
        return self._record_correction(claim_id, "source_speaker", speaker.actor_id, ref,
                                       clarification_exact, "Speaker corrected an attributed meaning")

    def correct_fact(self, claim_id: str, reviewer: AuthenticatedActor,
                     reason: str) -> str:
        claim = self._proposal(claim_id)
        if claim["kind"] != "fact":
            raise TypeError("External fact correction requires a factual claim")
        if "fact_reviewer" not in reviewer.roles:
            raise PermissionError("Trusted fact reviewer required")
        decision = self.decision(claim_id)
        if decision.status != "REFUTED_BY_CHECK":
            raise ValueError("Independent refuting evidence satisfying policy is required")
        if not reason.strip():
            raise ValueError("Review reason required")
        check = self.db.execute("SELECT * FROM checks_v2 WHERE claim_id=? AND verdict='refutes' ORDER BY checked_at DESC, id DESC LIMIT 1",
                                (claim_id,)).fetchone()
        if check is None:
            raise ValueError("No refuting check")
        return self._record_correction(claim_id, "external_evidence", reviewer.actor_id,
                                       check["locator"], check["correction_proposal"], reason)

    def acknowledgement(self, claim_id: str) -> str:
        self._require_integrity()
        claim = self._proposal(claim_id)
        correction = self.db.execute("SELECT * FROM corrections_v2 WHERE claim_id=?", (claim_id,)).fetchone()
        if correction is None:
            raise ValueError("No correction recorded")
        delivered = self.db.execute("SELECT * FROM deliveries_v2 WHERE claim_id=? ORDER BY delivered_at LIMIT 1",
                                    (claim_id,)).fetchone()
        if delivered is None:
            return f"An unpublished proposal was withdrawn: {_json(claim['text'])}. No previous public assertion is claimed."
        prior = delivered["delivered_text"]
        if correction["authority"] == "source_speaker":
            return (f"I previously published: {_json(prior)}. That attributed meaning was corrected "
                    f"by the source speaker: {_json(correction['correction_text'])}. "
                    "I withdraw the earlier attribution.")
        return (f"I previously published: {_json(prior)}. Independent recorded checks now refute "
                f"the factual claim ({correction['evidence_ref']}). I withdraw it. "
                "Any replacement claim requires its own verification.")

    def record_anomaly(self, fingerprint: str, description: str,
                       *, source_id: str | None = None,
                       failed_categories: list[str] | None = None,
                       features: dict | None = None) -> str:
        if not isinstance(fingerprint, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,100}", fingerprint):
            raise ValueError("Use a bounded, stable anomaly fingerprint")
        if not isinstance(description, str) or not description:
            raise ValueError("Description required")
        if source_id:
            self._source(source_id)
        if failed_categories is not None and (not isinstance(failed_categories, list) or
                any(not isinstance(item, str) for item in failed_categories)):
            raise ValueError("Invalid category list")
        if features is not None and not isinstance(features, dict):
            raise ValueError("Features must be object")
        categories_json = _json(failed_categories or [])
        features_json = _json(features or {})
        anomaly_id = _id()
        with self._transaction():
            self.db.execute("INSERT INTO anomalies_v2 VALUES (?,?,?,?,?,?,?)",
                            (anomaly_id, source_id, fingerprint, description,
                             categories_json, features_json, _now()))
            self._event("ANOMALY_UNRESOLVED", anomaly_id, {"fingerprint": fingerprint,
                        "source_id": source_id, "description_sha256": _hash(description.encode())})
        return anomaly_id

    def research_queue(self, minimum_repeat: int = 3) -> list[dict]:
        self._require_integrity()
        if not isinstance(minimum_repeat, int) or minimum_repeat < 2:
            raise ValueError("Minimum repeat must be at least two")
        rows = self.db.execute("""SELECT fingerprint, COUNT(*) AS sample_count
            FROM anomalies_v2 GROUP BY fingerprint HAVING COUNT(*) >= ?
            ORDER BY sample_count DESC, fingerprint""", (minimum_repeat,)).fetchall()
        return [{"fingerprint": r["fingerprint"], "observations": r["sample_count"],
                 "status": "INVESTIGATION_CANDIDATE_NOT_DISCOVERY"} for r in rows]

    def hypothesize(self, anomaly_id: str, text: str, falsifiable_test: str) -> str:
        if not self.db.execute("SELECT 1 FROM anomalies_v2 WHERE id=?", (anomaly_id,)).fetchone():
            raise KeyError("Unknown anomaly")
        if not text.strip() or not falsifiable_test.strip():
            raise ValueError("A hypothesis and possible test are required")
        hypothesis_id = _id()
        with self._transaction():
            self.db.execute("INSERT INTO hypotheses_v2 VALUES (?,?,?,?,?,?)",
                            (hypothesis_id, anomaly_id, text, falsifiable_test, "UNTESTED", _now()))
            self._event("HYPOTHESIS_PROPOSED", hypothesis_id, {"anomaly_id": anomaly_id,
                        "status": "UNTESTED", "text_sha256": _hash(text.encode())})
        return hypothesis_id

    def integrity_report(self, *, expected_anchor: dict | None = None) -> dict:
        """Check hash links, row seals and inserted/deleted rows.

        Hashes alone cannot resist a DB writer who rebuilds the entire chain.
        Host-held audit_key and an independent stored tip are needed for stronger
        tamper evidence and rollback detection. Existing unsealed DBs fail closed.
        """
        problems: list[str] = []
        previous = "0" * 64
        expected_seq = 1
        seen: dict[str,set[tuple]] = {name:set() for name in _SEALED_TABLE_KEYS}
        expected_seals: dict[tuple, str] = {}
        for ev in self.db.execute("SELECT * FROM audit_events_v2 ORDER BY seq"):
            if ev["seq"] != expected_seq or ev["previous_hash"] != previous:
                problems.append(f"Broken audit chain link at sequence {ev['seq']}")
            try:
                payload = json.loads(ev["payload_json"], object_pairs_hook=_unique_pairs,
                                     parse_constant=_reject_constant)
                table, key = self._event_identity(ev["event_kind"], ev["object_id"], payload)
                sealed = payload["sealed_record"]
                if (not isinstance(sealed, dict) or sealed.get("table") != table or
                    sealed.get("key") != key or
                    not isinstance(sealed.get("row_sha256"), str) or
                    not re.fullmatch(r"[a-f0-9]{64}", sealed["row_sha256"])):
                    raise ValueError("Invalid or absent row seal")
                row_key = tuple(key.values())
                slot = (table,row_key)
                # Append-only rows are immutable, so an event cannot assign a
                # second conflicting fingerprint to the same record.
                if slot in expected_seals and expected_seals[slot] != sealed["row_sha256"]:
                    problems.append(f"Conflicting row seals: {table} {row_key}")
                expected_seals[slot] = sealed["row_sha256"]
                seen[table].add(row_key)
                observed = self._row_digest(table,key)
                if observed != sealed["row_sha256"]:
                    problems.append(f"Stored row modified or missing: {table} {row_key}")
                expected = self._event_hash({"seq": ev["seq"], "kind": ev["event_kind"],
                            "id": ev["object_id"], "payload": payload,
                            "previous": ev["previous_hash"], "created_at": ev["created_at"]})
                if not hmac.compare_digest(expected, ev["event_hash"]):
                    problems.append(f"Event digest mismatch at sequence {ev['seq']}")
            except (ValueError, TypeError, KeyError, sqlite3.Error, OverflowError):
                problems.append(f"Malformed audit event at sequence {ev['seq']}")
            previous = ev["event_hash"]
            expected_seq += 1
        for table, columns in _SEALED_TABLE_KEYS.items():
            col_names = ",".join(columns)
            try:
                for row in self.db.execute(f"SELECT {col_names} FROM {table}"):
                    row_key = tuple(row[col] for col in columns)
                    if row_key not in seen[table]:
                        problems.append(f"Unsealed or inserted row: {table} {row_key}")
            except sqlite3.Error:
                problems.append(f"Cannot read table: {table}")
        if expected_anchor is not None:
            tip = {"seq":expected_seq - 1, "event_hash":previous}
            if expected_anchor != tip:
                problems.append("Independent external anchor mismatch")
        return {"ok": not problems, "problems": problems,
                "event_count": expected_seq - 1,
                "verification_mode": "HOST_HELD_HMAC" if self._audit_key else "UNKEYED_DIGESTS_ONLY"}

    def close(self) -> None:
        self.db.close()
