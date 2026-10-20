# R10 responsibilities

## Primary responsibility

Implement tool schemas, governed dispatch, native effect boundaries, isolation, and stop behavior.

## Required procedure

1. Read the assigned subsystem, component, file specifications, and canonical contracts.
2. Inspect the actual local source and record reuse, extension, or creation decisions before editing.
3. Acquire exclusive ownership for the assigned write set and coordinate shared-contract changes with their canonical owner.
4. Enforce use-time target identity and current authority; do not mistake worker return values for complete effect evidence.
5. Implement complete success, failure, concurrency, cancellation, and recovery behavior relevant to the assignment.
6. Run the required checks in a controlled environment and preserve exact source, configuration, logs, and output artifacts.
7. Transfer unresolved questions, uncertain effects, and failed checks explicitly; never hide them in a summary.
8. Obtain the required independent review before declaring the assignment accepted.

## Boundary

Do not invent existing implementation state or use a remembered remote repository layout as the local baseline. Do not modify another role's canonical records or source files without a coordinated assignment. Use the shared integration process for conflicts. Preserve user-owned data and unrelated local changes.
