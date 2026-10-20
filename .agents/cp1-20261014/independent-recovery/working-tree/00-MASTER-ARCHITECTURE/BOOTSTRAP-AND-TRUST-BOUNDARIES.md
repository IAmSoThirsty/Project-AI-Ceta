# Bootstrap, service authority, and trust boundaries

## Purpose

Avoid a circular design in which storage, identity, policy, or evidence must already possess a general worker capability merely to initialize the services that issue and verify those capabilities. Separate narrowly scoped internal service operations from general agent and tool effects. Both have explicit authority and observable boundaries; they are not interchangeable.

## Restricted bootstrap states

Start in uninitialized, inspecting, owner-enrollment, trust-ready, policy-ready, execution-ready, restricted-maintenance, stopping, or stopped as appropriate. The exact local implementation may refine these states but must preserve their meaning. Before execution-ready, general tool, model-triggered action, extension, network-send, and autonomous worker effects are unavailable. Safe inspection of local installation health may remain available.

The initial native process may inspect its own installation, open its designated private data root, validate storage, and perform the configured owner-enrollment or recovery challenge under the qualified local installation and operating-session trust model. This authority is limited to initialization and recovery of those designated resources. It cannot read arbitrary projects, send messages, launch unrelated commands, grant itself owner status, or activate unapproved extensions. Local reconciliation must identify the existing enrollment proof and process trust mechanisms; a display name, first-launch race, or copied data directory is insufficient ownership proof.

## Foundation activation order

Establish the approved local root and immutable architecture configuration. Open and verify canonical storage. Initialize or recover protected trust material and device/process bindings. Establish the owner through the configured verified enrollment or recovery flow. Start the minimum evidence journal and resource reserve. Load approved constitutional sources and current revocation state. Activate the execution gate only when authority, policy, evidence capacity, resource admission, and required native enforcement are all ready. Then activate tool dispatch, inference, workflows, and user-facing operations according to their prerequisites.

## Internal service authority

A canonical storage service may write its own private records under its defined service identity. A protected key service may use approved key handles for their declared purpose. An evidence service may append validated records and seal frames. These operations have bounded input schemas, authenticated callers, expected-version checks, access controls, and lifecycle scope. They do not accept arbitrary filesystem paths, shell commands, external destinations, or model-generated instructions. Changes to their authority or configuration require the applicable owner-approved governance transition.

General workers never inherit those service privileges. They submit typed requests to canonical services and route actual project, process, network, message, and extension effects through the execution gate. A service API that can cause such effects must itself require the appropriate scoped operation authority and independent observation.

## Evidence without recursive logging

Recording an evidence event does not recursively demand another signed event for each internal byte written. Define an auditable storage boundary with transaction sequence, integrity checks, protected signing, and externally inspectable frame or checkpoint anchors where configured. Record failures and discontinuities through the minimum recovery journal when possible. Reserve evidence capacity before admitting effects. If required durable intent or evidence cannot be recorded, block new effectful admission rather than performing the action and inventing a receipt later.

## Policy evaluation without self-authorization

Policy evaluation reads a pinned approved rule snapshot and authenticated facts; it does not issue itself permission to perform unrelated effects. Capability issuance consumes a validated governance decision bound to exact inputs and scope. The gate validates current capability, policy, revocation, target identity, and resources immediately before dispatch. No single model response, mutable profile, extension manifest, or renderer state can supply all of these trust facts.

## Recovery and shutdown

Restricted maintenance can inspect, export permitted diagnostics, and execute specifically authorized repair plans. It does not disable mandatory controls to restore a green status. Preserve conversations, identity records, unsent drafts, known revocations, deletion markers, and uncertain operations. Shutdown closes new admission, propagates stop, reconciles workers and effects, persists final state, and closes storage last. A forced shutdown leads to explicit recovery, not automatic replay of prior external effects.

## Qualification

Test first-run races, copied data roots, missing keys, corrupt storage, unavailable evidence capacity, stale process identities, policy load failure, disabled enforcement, and recovery from older snapshots. Verify that all general effect paths remain closed until their prerequisites are actually satisfied. Test internal service APIs for arbitrary-path, command, and destination injection so the bootstrap distinction cannot become a bypass.
