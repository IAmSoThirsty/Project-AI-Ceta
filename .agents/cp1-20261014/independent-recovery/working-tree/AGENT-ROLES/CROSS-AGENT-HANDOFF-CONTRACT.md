# Construction handoff contract

## Required fields

Every handoff contains a stable handoff ID and revision; sender and receiver identities; task, requirement, subsystem, component, and logical-unit IDs; approved scope; mapped local paths; before and after source digests; contract revisions; produced artifact references and digests; actual test fixtures, commands or procedures, environment, logs, and results; independent review state; completed and remaining acceptance obligations; known committed effects; uncertain operations; current cancellation and authority state; ownership and resource leases; recovery or rollback constraints; and pending human decisions.

## Transfer protocol

Freeze the referenced revision. Validate that every reference exists and is accessible to the receiver. Send the bounded handoff and obtain an acknowledgement of its exact digest. The receiver inspects the artifacts and prerequisites before accepting ownership. Transfer or release the write lease explicitly; a stale sender cannot continue publishing. If inputs, contracts, source, or authority change, create a new handoff revision and revalidate affected work.

## Acceptance and uncertainty

A receiver does not inherit expired permissions or assume the sender's claims are verified. Completed, failed, blocked, not-executed, and uncertain obligations remain distinct. An unknown external effect is never omitted to simplify the handoff. Independent review identifies a verifier who did not produce the same change. Preserve raw evidence and explicit gaps rather than replacing them with a persuasive summary.
