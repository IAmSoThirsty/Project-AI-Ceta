# S12 verification

## Positive oracle

Duplicate deliveries and stale workers cannot produce conflicting canonical effects.

## Required adverse fixture

A producer agent self-certifies its deliverable as independently verified.

## Verification sequence

1. Pin the exact source, input, configuration, and environment under review.
2. Construct a valid domain fixture and inspect the actual output against the positive oracle.
3. Construct the adverse fixture above and confirm the prohibited behavior is rejected or explicitly unresolved.
4. Exercise stale input, invalid scope, interruption, and duplicate delivery where relevant to this skill.
5. Inspect raw observations, artifact digests, and contract compatibility rather than trusting a producer summary.
6. Have the named independent reviewer reproduce critical checks and record discrepancies.

## Result record

Record passed, failed, blocked, skipped, not-executed, or uncertain for each obligation. Attach exact evidence and limitations. A missing environment or unexecuted test remains an open obligation. Verification of documentation structure is distinct from verification of the eventual runtime behavior.
