
# Subsystem 01 constitutional governance core (CETA-01.01.03, CETA-01.02.02, 01.03 quorum). Standard library only (D-001).
# Fail closed: without a verified active rule set every decision is DENY.
# Rule text used by tests is a TEST FIXTURE, not constitutional text (blocker B-03).
# Signature verification has no pinned profile (blocker B-04): transitions stay blocked unless a verifier is injected.
# Native effect enforcement is unqualified (blocker B-05); this module makes no enforcement claim.
import hashlib
import hmac
import json
import secrets
import threading
import time

ALLOW = 'allow'
DENY = 'deny'
HUMAN = 'human_decision_required'
EFFECTS = (ALLOW, DENY, HUMAN)
MAX_RULES = 512
MAX_BYTES = 262144
MAX_APPROVALS = 1024
INTEGRITY_CODES = frozenset(['digest_mismatch', 'malformed', 'bounds', 'unpinned', 'duplicate_rule'])


class GovernanceError(Exception):
    def __init__(self, code, detail):
        super().__init__(code + ': ' + detail)
        self.code = code
        self.detail = detail


def _text(value, field):
    if not isinstance(value, str) or not value:
        raise GovernanceError('malformed', field + ' must be non-empty text')
    return value


def _int(value, field, minimum):
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise GovernanceError('malformed', field + ' must be an integer of at least ' + str(minimum))
    return value


class RuleSet:
    def __init__(self, constitution_id, version, digest, rules):
        self.constitution_id = constitution_id
        self.version = version
        self.digest = digest
        self.rules = rules


def _parse_rule(item, seen):
    if not isinstance(item, dict):
        raise GovernanceError('malformed', 'each rule must be an object')
    rid = _text(item.get('id'), 'rule.id')
    if rid in seen:
        raise GovernanceError('duplicate_rule', rid)
    seen.add(rid)
    effect = item.get('effect')
    if not isinstance(effect, str) or effect not in EFFECTS:
        raise GovernanceError('malformed', 'unknown effect on rule ' + rid)
    requires = item.get('requires', [])
    if not isinstance(requires, list) or not all(isinstance(k, str) and k for k in requires):
        raise GovernanceError('malformed', 'requires must be a list of fact names on rule ' + rid)
    action = _text(item.get('action'), 'rule.action')
    precedence = _int(item.get('precedence'), 'rule.precedence', 0)
    return {'id': rid, 'action': action, 'effect': effect, 'precedence': precedence, 'requires': tuple(requires)}


def load_rule_set(raw, pinned_sha256):
    if not isinstance(raw, bytes):
        raise GovernanceError('malformed', 'rule set must be bytes')
    if len(raw) == 0 or len(raw) > MAX_BYTES:
        raise GovernanceError('bounds', 'rule set size is outside the allowed range')
    if not isinstance(pinned_sha256, str) or len(pinned_sha256) != 64 or not pinned_sha256.isascii():
        raise GovernanceError('unpinned', 'a 64-character ASCII SHA-256 pin is required')
    digest = hashlib.sha256(raw).hexdigest()
    if not hmac.compare_digest(digest, pinned_sha256.lower()):
        raise GovernanceError('digest_mismatch', 'rule set bytes do not match the pinned digest')
    try:
        doc = json.loads(raw.decode('utf-8'))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise GovernanceError('malformed', 'rule set is not UTF-8 JSON')
    if not isinstance(doc, dict):
        raise GovernanceError('malformed', 'rule set root must be an object')
    constitution_id = _text(doc.get('constitution_id'), 'constitution_id')
    version = _int(doc.get('version'), 'version', 1)
    raw_rules = doc.get('rules')
    if not isinstance(raw_rules, list) or not raw_rules or len(raw_rules) > MAX_RULES:
        raise GovernanceError('malformed', 'rules must be a non-empty list within bounds')
    seen = set()
    rules = tuple(_parse_rule(item, seen) for item in raw_rules)
    return RuleSet(constitution_id, version, digest, rules)


def evaluate(rule_set, action, facts=None):
    # Returns (decision, reasons). Deny by default.
    # Any rule for this action whose required facts are missing makes the result DENY: unmet rules are never dropped.
    # A conflict at the top precedence among fully satisfied rules is HUMAN, never ALLOW.
    if rule_set is None:
        return DENY, ('no_active_rule_set',)
    action = _text(action, 'action')
    facts = {} if facts is None else facts
    if not isinstance(facts, dict):
        raise GovernanceError('malformed', 'facts must be an object')
    matched = []
    unmet = []
    for rule in rule_set.rules:
        if rule['action'] != action:
            continue
        gap = sorted(k for k in rule['requires'] if _absent(facts.get(k)))
        if gap:
            unmet.append(rule['id'] + ':' + ','.join(gap))
        else:
            matched.append(rule)
    if unmet:
        return DENY, tuple('missing_fact:' + u for u in sorted(unmet))
    if not matched:
        return DENY, ('no_matching_rule',)
    top = max(r['precedence'] for r in matched)
    top_rules = [r for r in matched if r['precedence'] == top]
    effects = set(r['effect'] for r in top_rules)
    ids = tuple(sorted(r['id'] for r in top_rules))
    if len(effects) > 1:
        return HUMAN, tuple('conflict:' + i for i in ids)
    return effects.pop(), ids



_ISSUER_KEY = secrets.token_bytes(32)


def _seal_of(digest, approved, valid_from, valid_to, nonce):
    message = repr((digest, bool(approved), valid_from, valid_to, nonce)).encode('utf-8')
    return hmac.new(_ISSUER_KEY, message, hashlib.sha256).hexdigest()


def _sealed(approval):
    seal = getattr(approval, '_seal', None)
    if not isinstance(seal, str) or not seal.isascii() or approval.nonce is None:
        return False
    expected = _seal_of(approval.digest, True, approval.valid_from, approval.valid_to, approval.nonce)
    return hmac.compare_digest(expected, seal)


class TransitionApproval:
    # Issued only by approve_transition, which seals it with the module issuer key.
    # A directly constructed instance has no valid seal and Registry.activate refuses it.
    # Residual limit: the issuer key lives in process memory; same-process code can read it.
    def __init__(self, digest, approved, reasons, valid_from=None, valid_to=None, nonce=None, seal=None):
        self.digest = digest
        self.approved = approved
        self.reasons = tuple(reasons)
        self.valid_from = valid_from
        self.valid_to = valid_to
        self.nonce = nonce
        self.consumed = False
        self._seal = seal


def _absent(value):
    # Missing facts are None, empty text, and False. Zero and other values are present.
    return value is None or value is False or value == ''


def _number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GovernanceError('malformed', field + ' must be a number')
    return value


def approve_transition(digest, approvals, eligible, threshold, now, valid_from, valid_to, verifier=None, aliases=None):
    if not isinstance(digest, str) or len(digest) != 64 or not digest.isascii():
        raise GovernanceError('malformed', 'transition digest must be a SHA-256 hex string')
    if not isinstance(approvals, list) or len(approvals) > MAX_APPROVALS:
        raise GovernanceError('malformed', 'approvals must be a bounded list')
    if not isinstance(eligible, (set, frozenset)):
        raise GovernanceError('malformed', 'eligible principals must be a set')
    _int(threshold, 'threshold', 1)
    _number(now, 'now')
    _number(valid_from, 'valid_from')
    _number(valid_to, 'valid_to')
    if valid_from > valid_to:
        raise GovernanceError('malformed', 'validity window is inverted')
    if verifier is None:
        return TransitionApproval(digest, False, ('signature_profile_unpinned',), valid_from, valid_to)
    if not (valid_from <= now <= valid_to):
        return TransitionApproval(digest, False, ('outside_validity',), valid_from, valid_to)
    if aliases is not None and (not isinstance(aliases, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in aliases.items())):
        raise GovernanceError('malformed', 'aliases must map text to text')
    voters = set()
    reasons = []
    for ap in approvals:
        pid = ap.get('principal_id') if isinstance(ap, dict) else None
        if not isinstance(pid, str):
            reasons.append('ineligible_principal')
            continue
        canon = pid if aliases is None else aliases.get(pid, pid)
        if canon not in eligible:
            reasons.append('ineligible_principal')
            continue
        if ap.get('proposal_digest') != digest:
            reasons.append('wrong_proposal:' + pid)
            continue
        if canon in voters:
            reasons.append('duplicate_principal:' + canon)
            continue
        try:
            ok = verifier(ap) is True
        except Exception:
            ok = False
        if not ok:
            reasons.append('bad_signature:' + pid)
            continue
        voters.add(canon)
    tally = str(len(voters)) + '/' + str(threshold)
    if len(voters) < threshold:
        return TransitionApproval(digest, False, ('quorum_not_met:' + tally,) + tuple(reasons), valid_from, valid_to)
    nonce = secrets.token_hex(16)
    seal = _seal_of(digest, True, valid_from, valid_to, nonce)
    return TransitionApproval(digest, True, ('quorum_met:' + tally,) + tuple(reasons), valid_from, valid_to, nonce, seal)


class Registry:
    # One complete immutable RuleSet at a time. Integrity failures clear the active set (fail closed, no fallback).
    # Policy refusals (window, replay, rollback, unapproved) keep the current set.
    # Each approval is consumed at most once by this registry. Consumed nonces are held in memory only; see hostile review.
    def __init__(self, now=None):
        self._lock = threading.Lock()
        self._now = now if now is not None else time.time
        self._active = None
        self._consumed = set()
        self._activated_windows = set()
        self.history = []
        self.last_refusal = None
    def active(self):
        return self._active
    def activate(self, raw, pinned_sha256, approval):
        with self._lock:
            try:
                candidate = load_rule_set(raw, pinned_sha256)
                if not isinstance(approval, TransitionApproval) or not approval.approved or approval.digest != candidate.digest:
                    raise GovernanceError('unapproved_transition', 'no approval bound to this rule set digest')
                if not _sealed(approval):
                    raise GovernanceError('unapproved_transition', 'approval was not issued by approve_transition')
                if approval.nonce is None or approval.consumed or approval.nonce in self._consumed:
                    raise GovernanceError('approval_replayed', 'approval was already consumed')
                now = self._now()
                if not (approval.valid_from <= now <= approval.valid_to):
                    raise GovernanceError('outside_validity', 'activation time is outside the approval window')
                current = self._active
                if current is not None and candidate.version == current.version and candidate.digest == current.digest:
                    self._consumed.add(approval.nonce)
                    approval.consumed = True
                    self.last_refusal = None
                    return current
                window = (candidate.digest, approval.valid_from, approval.valid_to)
                if window in self._activated_windows:
                    raise GovernanceError('approval_replayed', 'this proposal digest and window were already activated')
                if current is not None and candidate.version < current.version:
                    raise GovernanceError('version_rollback', 'candidate version is older than the active revision')
                if current is not None and candidate.version == current.version:
                    if candidate.digest != current.digest:
                        raise GovernanceError('version_conflict', 'same version with different content')
                    result = current
                else:
                    self._active = candidate
                    self.history.append((candidate.version, candidate.digest))
                    self._activated_windows.add(window)
                    result = candidate
                self._consumed.add(approval.nonce)
                approval.consumed = True
                self.last_refusal = None
                return result
            except GovernanceError as exc:
                self.last_refusal = exc.code
                if exc.code in INTEGRITY_CODES:
                    self._active = None
                raise
