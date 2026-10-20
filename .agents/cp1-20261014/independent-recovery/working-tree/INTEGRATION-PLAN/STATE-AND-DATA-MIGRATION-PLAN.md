# State And Data Migration Plan

## Goal

Preserve user data and current security state while changing schemas or owners.

## Required procedure

Inventory records and references; create a verified recovery point; define transformations and compatibility windows; test representative data and crash boundaries; preserve identity, conversations, drafts, revocations, deletion markers, and evidence. Declare irreversible transformations and forward-repair paths explicitly.

## Decision record

For every affected unit identify the exact source baseline, owner, proposed change, canonical contract revisions, dependencies, data and authority consequences, positive and adverse acceptance cases, recovery plan, and reviewer. Preserve the distinction between inspected facts and design decisions. If required local information is unavailable, record the blocked binding and continue only independently valid documentation or inspection work.

## Execution and verification

Use bounded source ownership and current permission. Perform conditional writes against inspected digests. Route consequential actions through the native authority and execution boundary. Capture actual tests and artifacts, not only plans. Verify real producer-consumer behavior and preserve existing user workflows. Independent review reproduces critical results on the delivered revision.

## Acceptance

The integration step is accepted only when its specified goal is observed, affected contracts and tests pass, user data and security history are preserved, and the exact source and evidence are recorded. A source path is not considered mapped merely because its logical name resembles an existing file. A rollback is not considered safe merely because a backup archive exists.

Related records: [planned source registry](../MANIFESTS-AND-TRACEABILITY/PLANNED-SOURCE-FILE-REGISTRY.md), [ownership matrix](../DEPENDENCY-MAPS/COMPONENT-OWNERSHIP-MATRIX.md), and [local reconciliation rules](../EXISTING-CETA-RECONCILIATION.md).
