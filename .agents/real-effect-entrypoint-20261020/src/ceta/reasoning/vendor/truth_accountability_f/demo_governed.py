"""Four scenarios demonstrating the next four engineering increments."""
import json
import tempfile
from pathlib import Path

from truth_accountability import (
    AuthenticatedActor, EvidenceFinding, EvidenceVerdict, GovernedTruthCore,
    GovernedModelBridge, VerificationRegistry, VerifierSpec, arithmetic_only_policy,
    bounded_arithmetic,
)


with tempfile.TemporaryDirectory() as path:
    db = Path(path) / "reasoning.sqlite3"
    verifiers = VerificationRegistry()
    verifiers.register(VerifierSpec("arithmetic", "arithmetic-v1", bounded_arithmetic))
    core = GovernedTruthCore(db, verifiers)
    bridge = GovernedModelBridge(core, arithmetic_only_policy)
    speaker = AuthenticatedActor("speaker-a", frozenset({"authenticated_speaker"}))
    reviewer = AuthenticatedActor("fact-reviewer", frozenset({"fact_reviewer"}))
    host = AuthenticatedActor("host-delivery", frozenset({"delivery_host"}))

    print("\nA. Semantic fidelity, with original source preserved")
    src = core.preserve("speaker-a", "I am asking you to understand my reasoning.")
    proposal = json.dumps({"kind":"paraphrase", "text":"You demanded obedience",
                           "source_id":src, "span":[0,len(core.original(src))]})
    result = bridge.process(proposal, current_source_id=src)
    print(result.decision, ":", result.text)
    core.clarify_attribution(result.claim_id, speaker, "I asked for understanding, not obedience.")
    print("Correction:",core.acknowledgement(result.claim_id))

    print("\nB. Controlled factual check and publication")
    result = bridge.process(json.dumps({"kind":"fact","text":"2 + 2 = 4"}))
    print(result.decision, ":", result.text)
    # The host would call confirm_delivery only AFTER actual successful delivery.

    print("\nC. Historical error, verified against the same controlled rule")
    bad = core.propose("fact", "2 + 2 = 5")
    transcript = core.preserve("assistant", "2 + 2 = 5", channel="published_assistant_transcript")
    core.reconcile_historical_delivery(bad, transcript_source_id=transcript,
                                       receipt="verified-host-history-001", actor=host)
    core.check(bad,"arithmetic")
    core.correct_fact(bad,reviewer,"The calculation contradicts the former assertion")
    print(core.acknowledgement(bad))

    print("\nD. Unclassified observations and unproven hypotheses")
    for n in range(3):
        core.record_anomaly("radio.pulse.unknown", f"Unexpected pulse sequence #{n}",
                            failed_categories=["expected signal", "known interference"])
    print("Investigation queue:",core.research_queue())
    print("Integrity:",core.integrity_report())
    core.close()
