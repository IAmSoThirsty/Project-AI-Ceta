from truth_accountability import CheckResult, ClaimKind, TruthLedger, Verdict

ledger = TruthLedger()
source = ledger.preserve_statement("person-1", "I am asking you to understand my reasoning.")
incorrect = ledger.propose_claim(ClaimKind.ATTRIBUTION, "You demanded obedience", source_id=source)
print("Initial policy decision:", ledger.status(incorrect))
ledger.record_prior_publication(incorrect)  # Recording a past mistake, not publishing now.
ledger.speaker_correction(
    incorrect,
    authenticated_speaker="person-1",
    clarification_exact="I asked you to understand, not to obey.",
)
print("After the correction:", ledger.status(incorrect))
print("Acknowledgement:", ledger.acknowledgement(incorrect))

world_claim = ledger.propose_claim(ClaimKind.FACT, "2 + 2 = 5")
ledger.record_prior_publication(world_claim)
ledger.run_fact_check(
    world_claim,
    "test-only-arithmetic-checker",
    lambda text, scope: CheckResult(
        Verdict.REFUTES, "local-fixture-arithmetic", "2 + 2 equals 4", "2 + 2 = 4"
    ),
)
ledger.correct_refuted_fact(world_claim)
print("Factual correction:", ledger.acknowledgement(world_claim))
