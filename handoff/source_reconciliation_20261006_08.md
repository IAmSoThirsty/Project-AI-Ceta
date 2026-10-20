# Platform and transport source reconciliation — increment 08

Complete originals 034–042 and 045 were read before recording these decisions. Nine are DIRECT; 036 Cloud Architecture is SUPPORTING for bounded provider-facing acquisition/delivery and future expressly selected services. Original identities, hashes and maturity are preserved. No source adoption, independent acceptance or Gate A closure is claimed.

| Source | Complete lines | Applicability | SHA-256 |
|---|---:|---|---|
| 034 | 144 | DIRECT | `461edd0f774df80956fe0971629f64ab27fd814c04c95e75e5f06bc0f5c01a6b` |
| 035 | 140 | DIRECT | `35d1607cd9b603d5852bf8a4cb8a7587f950cc0cd117dbd822f6e6dcb429d5bb` |
| 036 | 141 | SUPPORTING | `d8104fedc3dbae7130b3a0f66fca43dd68327847dbbcc7fb3fc52ac44a42a9cd` |
| 037 | 139 | DIRECT | `2e60c958f6021d83573d59c0f504b80c0a0796eda216265d38d73298f5485c6e` |
| 038 | 138 | DIRECT | `c15b920e118741f8e6e552995fd981911570de23acb6abc009c46c57c0947ea8` |
| 039 | 139 | DIRECT | `a21f8308b255a4f860416c271744fb00b0780dd2d48a4e8dcfe38e5a57b0de16` |
| 040 | 140 | DIRECT | `b3bcff90ff48df2de0bc687c9a6381a964083a03c2280305799a24121699538e` |
| 041 | 139 | DIRECT | `9b7aca4d7be6b673a4b837bf7edffb76694d0f8e18b4646bb409f263c5705db3` |
| 042 | 139 | DIRECT | `05a31d1a385ddb753f733a488a762203c3d12c80578e20ff12b3c8ed394ce573` |
| 045 | 139 | DIRECT | `a48a3a3fb715a50168d32bc7d0ec80f8e3768900b19f4edf29ca88d11e024a4f` |

## Applicability and remaining obligations

Named original clause families are mapped to exact existing parent IDs in the companion working record. Requirement ownership and complete clauses remain intact.

### 034 — Shared CETA services and scope isolation

CETA supplies managed cognition/AI, identity, policy, persistence, observation, delivery and recovery to cooperating consumers. Shared installation versus project state has material isolation, resource and blast-radius consequences. This is the authorized CETA platform, not a mandate to inventory or govern other local repositories.

Keep platform defaults, application/project configuration, governance policy, installation metadata and user data distinct. Shared services do not become rival authority. Enforce exact consumer scope, quotas, revocation and privacy, and preserve stop/evidence/recovery under noisy-neighbor or provider/resource failure. Actual consumer inventory, capacity, isolation and service commitments remain unproven.

- Consumers, shared services, tenancy, configuration and contracts: REQ-04-01, REQ-04-02, REQ-04-03, REQ-04-04, REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-07-01, REQ-07-02, REQ-07-03, REQ-07-04, REQ-07-05, REQ-08-01, REQ-08-02, REQ-08-03, REQ-08-04, REQ-11-01, REQ-11-02, REQ-11-03, REQ-11-04, REQ-11-05, REQ-18-01, REQ-18-02, REQ-18-03, REQ-18-04, REQ-22-01, REQ-22-02, REQ-22-03, REQ-22-04, REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04.
- Control/data/management planes, authority, quotas and protected boundaries: REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04, REQ-29-01, REQ-29-02, REQ-29-03, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04.
- Failure, accessibility, compatibility, migration, support and lifecycle: REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04, REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05, REQ-32-01, REQ-32-02, REQ-32-03, REQ-32-04, REQ-35-01, REQ-35-02, REQ-35-03, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

### 035 — Supported local host and infrastructure dependencies

The product depends materially on Windows compute, local storage, power, OS controls, model resources, configuration, credentials, backups and recovery. An existing machine or resource inventory is not a qualified infrastructure baseline.

Separate desired configuration, provisioned resources and observed behavior. Treat host/storage/power/credential/image/model and evidence-store loss explicitly; consistent backup and restore include actual journaling files and compatibility. No facility, energy, capacity, physical control or hardware resilience claim is invented. Installation and destructive machine changes remain distinct from reversible development.

- Resources, placement, topology, owners, provisioning and configuration: REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-07-01, REQ-07-02, REQ-07-03, REQ-07-04, REQ-07-05, REQ-08-01, REQ-08-02, REQ-08-03, REQ-08-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-22-01, REQ-22-02, REQ-22-03, REQ-22-04, REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04, REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05.
- Failure domains, security, physical constraints and recovery: REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04, REQ-29-01, REQ-29-02, REQ-29-03, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04, REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05, REQ-35-01, REQ-35-02, REQ-35-03.
- Evidence, maintenance, replacement and lifecycle: REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-40-01, REQ-40-02, REQ-40-03, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

### 036 — Provider-facing acquisition and delivery; offline runtime boundary

ARCH-01 declares a local product without a new mandatory cloud dependency; SPEC-22 forbids implicit external inference. Provider-backed artifact acquisition, release/update channels or expressly selected future provider integrations nevertheless require bounded provider, data, identity, cost, exit and recovery decisions. No cloud account, region, hosted runtime or live distribution service is inferred.

Cloud workload/control-plane deployment is not activated in this local engineering scope. Preserve scoped optional acquisition and an offline asset route; provider loss must not redirect private context or start cloud inference. If a provider/channel is selected, resolve actual terms, accounts/regions, data transfer, residency, cost, isolation, support, deletion and exit with evidence before activation. Reopen on any hosted service, cloud data flow, identity or external publication decision.

- Provider scope, service/dependency identity, data and support assumptions: REQ-03-01, REQ-03-02, REQ-03-03, REQ-03-04, REQ-22-01, REQ-22-02, REQ-22-03, REQ-22-04, REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04, REQ-29-01, REQ-29-02, REQ-29-03, REQ-35-01, REQ-35-02, REQ-35-03, REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05, REQ-39-01, REQ-39-02, REQ-39-03, REQ-39-04.
- Authority, egress, integrity, substitution and recovery: REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04.
- Qualification, migration, exit and lifecycle: REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

### 037 — Near-user local processing and offline authority

CETA processes and stores data near its user and must operate offline, with local physical exposure, clocks, policy freshness, constrained resources and recovery. The source applies without requiring an IoT fleet, remote control plane or invented central service.

Local operation cannot extend expired grants or use cache/model/operator labels to bypass current policy. Preserve local stop, status, evidence and recovery; clock drift, stale authority, disconnected resources, restore and update rollback require real tests. No central state exists by inference; actual distributed CBCC authorities retain their own boundaries. Site/physical controls, attestation and safe field-operation claims remain unqualified.

- Local node/workload, user, physical and dependency scope: REQ-03-01, REQ-03-02, REQ-03-03, REQ-03-04, REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-07-01, REQ-07-02, REQ-07-03, REQ-07-04, REQ-07-05, REQ-08-01, REQ-08-02, REQ-08-03, REQ-08-04, REQ-10-01, REQ-10-02, REQ-10-03, REQ-10-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-22-01, REQ-22-02, REQ-22-03, REQ-22-04, REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04.
- Local authority, freshness, privacy, identity and synchronization distinctions: REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04, REQ-29-01, REQ-29-02, REQ-29-03.
- Offline/update/degraded recovery, qualification and lifecycle: REQ-24-01, REQ-24-02, REQ-24-03, REQ-24-04, REQ-24-05, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04, REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05, REQ-32-01, REQ-32-02, REQ-32-03, REQ-32-04, REQ-35-01, REQ-35-02, REQ-35-03, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

### 038 — Process-boundary failures and genuine distributed authority

The design crosses helper process/time/trust boundaries and requires independently administered CBCC domains. Delay, partial failure, stale state, duplication, partition and concurrency are material even on one machine. No approved topology or universal exactly-once semantics is assumed.

Define per-message identity/causality, generations, bounded delivery, timeout, retry, deduplication and authority expiry. Receipt loss remains indeterminate; replay cannot repeat effects; compensation needs fresh current authority. Collocated helpers/simulations do not establish independent administrators, quorum resilience or hardware trust. Backpressure and model/observer/store/network failures must preserve stop/reconciliation capacity. The framing codec proves no distributed correctness.

- Topology, actors, clocks, ownership, messages and consistency: REQ-04-01, REQ-04-02, REQ-04-03, REQ-04-04, REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-07-01, REQ-07-02, REQ-07-03, REQ-07-04, REQ-07-05, REQ-08-01, REQ-08-02, REQ-08-03, REQ-08-04, REQ-18-01, REQ-18-02, REQ-18-03, REQ-18-04, REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04.
- Admission, ordering, replay, expiry, effects and compensation: REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04.
- Privacy, migration, fault evidence, operations and continuity: REQ-29-01, REQ-29-02, REQ-29-03, REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05, REQ-35-01, REQ-35-02, REQ-35-03, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

### 039 — Allowed paths, reachability and explicit egress

Artifact acquisition, optional integrations, loopback paths, worker restrictions and distributed protection have material reachability, exposure, identity, interception and lifecycle consequences. Offline-first operation does not remove the need to control network paths.

Keep DNS, proxies, loopback, intranet/internet, certificates, routes, egress and telemetry in the declared resource profile. No public listener, arbitrary any-to-any access, broad firewall exception or new hosted endpoint is inferred. Select and qualify the actual local transport and permitted external flows before activation. Reachability, ping, policy files and this byte codec do not prove secure connectivity. Network loss must not trigger external-model fallback.

- Endpoints, zones, flows, dependencies and intended/observed topology: REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-22-01, REQ-22-02, REQ-22-03, REQ-22-04, REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04, REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04, REQ-33-01, REQ-33-02, REQ-33-03, REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05.
- Identity, authorization, privacy, exposure and cryptographic controls: REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04, REQ-29-01, REQ-29-02, REQ-29-03.
- Congestion, naming/certificate loss, recovery and lifecycle evidence: REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04, REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04, REQ-35-01, REQ-35-02, REQ-35-03, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

### 040 — Owner conversation, notifications and machine communications

The Companion, native controls, status, instructions, consent, tool requests and future interface modalities exchange consequential human and machine messages. Delivery, interpretation, identity, accessibility, correction and privacy affect outcomes.

Distinguish source/template/generated draft/approved content/transmission/receipt/response/evidence. Fluent text, an open signal or receipt cannot establish truth, comprehension or consent. Preserve source wording, exclusions, corrections and generated status. Accessible alternate/error/status paths must work during model/channel loss. No authority to message other people or collect audience data is inferred; actual populations, languages, comprehension and accessibility evidence remain open.

- Audience, purpose, content, channel, identity and message state: REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-09-01, REQ-09-02, REQ-09-03, REQ-09-04, REQ-10-01, REQ-10-02, REQ-10-03, REQ-10-04, REQ-12-01, REQ-12-02, REQ-12-03, REQ-12-04, REQ-12-05, REQ-13-01, REQ-13-02, REQ-13-03, REQ-13-04, REQ-13-05, REQ-15-01, REQ-15-02, REQ-15-03, REQ-32-01, REQ-32-02, REQ-32-03, REQ-32-04, REQ-33-01, REQ-33-02, REQ-33-03.
- Consent, authorization, timing, accessibility, privacy and records: REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-29-01, REQ-29-02, REQ-29-03, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04.
- Quality, failure, correction, validation and continuity: REQ-24-01, REQ-24-02, REQ-24-03, REQ-24-04, REQ-24-05, REQ-35-01, REQ-35-02, REQ-35-03, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-40-01, REQ-40-02, REQ-40-03, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

### 041 — Cross-component mapping, complete outcomes and recovery

CETA crosses domain, store, model, kernel, broker, observer, custody, user-interface and migration boundaries. Mapping, identity, timing and partial effects are material; connected components or schema matches alone are not integrated outcomes.

Preserve source/transformed/mapped/delivered/acknowledged/reconciled/compensated states distinctly. Integrate real results into canonical legal next actions, not a disconnected demo. Unknown mappings and unsupported legacy categories require provenance-preserving quarantine. Durable recovery and evidence cannot depend solely on the failed participant. Data sharing or consequential new exchange requires exact authority; ordinary authorized contract implementation continues.

- Participants, flows, contracts, source/target meaning and ownership: REQ-04-01, REQ-04-02, REQ-04-03, REQ-04-04, REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-07-01, REQ-07-02, REQ-07-03, REQ-07-04, REQ-07-05, REQ-09-01, REQ-09-02, REQ-09-03, REQ-09-04, REQ-10-01, REQ-10-02, REQ-10-03, REQ-10-04, REQ-11-01, REQ-11-02, REQ-11-03, REQ-11-04, REQ-11-05, REQ-12-01, REQ-12-02, REQ-12-03, REQ-12-04, REQ-12-05, REQ-13-01, REQ-13-02, REQ-13-03, REQ-13-04, REQ-13-05, REQ-18-01, REQ-18-02, REQ-18-03, REQ-18-04, REQ-22-01, REQ-22-02, REQ-22-03, REQ-22-04, REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04, REQ-39-01, REQ-39-02, REQ-39-03, REQ-39-04.
- Authority, transformations, delivery, evidence, privacy and control: REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-24-01, REQ-24-02, REQ-24-03, REQ-24-04, REQ-24-05, REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04, REQ-29-01, REQ-29-02, REQ-29-03.
- Partial failure, reconciliation, compensation, migration and lifecycle: REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04, REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05, REQ-32-01, REQ-32-02, REQ-32-03, REQ-32-04, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04, REQ-35-01, REQ-35-02, REQ-35-03, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

### 042 — Typed programmatic ports and transport limits

Local typed ports, tool/broker operations, event/admin/recovery paths and provider interfaces expose or consume consequential programmatic operations. A REST server is not required for API obligations to apply.

Model each actual synchronous/asynchronous/long-running/streamed/batch/admin/recovery operation with bounded schema, caller, current scope/policy, timing, truthful errors, retry/idempotency and evidence. Pagination and rate controls apply to operations that actually use them; do not invent a new web service. Implemented v1 record framing rejects hostile size/length before body parsing and preserves original bytes. Authentication, message envelope, generations, replay state, capacity and dispatch remain open.

- Consumers, operations, schemas, versions and contract ownership: REQ-04-01, REQ-04-02, REQ-04-03, REQ-04-04, REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-16-01, REQ-16-02, REQ-16-03, REQ-16-04, REQ-18-01, REQ-18-02, REQ-18-03, REQ-18-04, REQ-22-01, REQ-22-02, REQ-22-03, REQ-22-04, REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04, REQ-33-01, REQ-33-02, REQ-33-03, REQ-40-01, REQ-40-02, REQ-40-03.
- Validation, identity, authority, data, timing, limits and errors: REQ-07-01, REQ-07-02, REQ-07-03, REQ-07-04, REQ-07-05, REQ-08-01, REQ-08-02, REQ-08-03, REQ-08-04, REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04, REQ-29-01, REQ-29-02, REQ-29-03, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04.
- Compatibility, abuse, partial effects, recovery, testing and lifecycle: REQ-24-01, REQ-24-02, REQ-24-03, REQ-24-04, REQ-24-05, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04, REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05, REQ-32-01, REQ-32-02, REQ-32-03, REQ-32-04, REQ-35-01, REQ-35-02, REQ-35-03, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

### 045 — Whole-system assets, threats and enforceable controls

The system handles private data, identity, authority, keys, hostile inputs, models, tools, source history and external effects. Security is material across every entry, management, supplier and recovery path; no clean scan or pure unit test establishes whole-system security.

Retain the trusted-host and broker assumptions and separate administrator compromise from actual distributed protection. Malicious processes/repository inputs/models, forged approval, inherited handles, reparse paths, denial, replay and supplier mutation require real enforcement. Framing is one bounded pre-parser control; it does not authenticate senders, protect keys or prevent allocation before the caller invokes it. Incident/containment, residual risk, independent review and recovery evidence remain unresolved without accepting risk on the owner’s behalf.

- Assets, actors, assumptions, trust boundaries and attack paths: REQ-04-01, REQ-04-02, REQ-04-03, REQ-04-04, REQ-05-01, REQ-05-02, REQ-05-03, REQ-05-04, REQ-06-01, REQ-06-02, REQ-06-03, REQ-06-04, REQ-16-01, REQ-16-02, REQ-16-03, REQ-16-04, REQ-19-01, REQ-19-02, REQ-19-03, REQ-19-04, REQ-19-05, REQ-20-01, REQ-20-02, REQ-20-03, REQ-20-04, REQ-21-01, REQ-21-02, REQ-21-03, REQ-21-04, REQ-21-05, REQ-22-01, REQ-22-02, REQ-22-03, REQ-22-04, REQ-23-01, REQ-23-02, REQ-23-03, REQ-23-04, REQ-35-01, REQ-35-02, REQ-35-03.
- Prevention, detection, custody, cryptography, privacy and audit: REQ-07-01, REQ-07-02, REQ-07-03, REQ-07-04, REQ-07-05, REQ-08-01, REQ-08-02, REQ-08-03, REQ-08-04, REQ-10-01, REQ-10-02, REQ-10-03, REQ-10-04, REQ-25-01, REQ-25-02, REQ-25-03, REQ-25-04, REQ-26-01, REQ-26-02, REQ-26-03, REQ-26-04, REQ-27-01, REQ-27-02, REQ-27-03, REQ-27-04, REQ-28-01, REQ-28-02, REQ-28-03, REQ-29-01, REQ-29-02, REQ-29-03.
- Control loss, incidents, recovery, independent evidence and lifecycle: REQ-24-01, REQ-24-02, REQ-24-03, REQ-24-04, REQ-24-05, REQ-30-01, REQ-30-02, REQ-30-03, REQ-30-04, REQ-31-01, REQ-31-02, REQ-31-03, REQ-31-04, REQ-31-05, REQ-32-01, REQ-32-02, REQ-32-03, REQ-32-04, REQ-33-01, REQ-33-02, REQ-33-03, REQ-34-01, REQ-34-02, REQ-34-03, REQ-34-04, REQ-36-01, REQ-36-02, REQ-36-03, REQ-36-04, REQ-37-01, REQ-37-02, REQ-37-03, REQ-37-04, REQ-38-01, REQ-38-02, REQ-38-03, REQ-38-04, REQ-38-05, REQ-40-01, REQ-40-02, REQ-40-03, REQ-41-01, REQ-41-02, REQ-41-03, REQ-41-04, REQ-42-01, REQ-42-02, REQ-42-03.

## Implemented framing and evidence

The desktop pure contract leaf now validates a four-byte unsigned big-endian body length before receiver allocation; encodes exact original strict-record bytes; and rejects malformed, oversized, truncated, trailing or concatenated complete frames before body parsing. Existing twenty schemas, canonical record commitments and original-byte preservation remain unchanged. ADR-021 records the working engineering choice.

Thirteen targeted framing tests passed. The source-bound complete application contract suite run11 passed 107 tests with zero failures/errors/skips and unchanged watched bytes. It includes all prior 94 contract tests plus thirteen framing tests. Neither suite exercises a real IPC transport, native peer authentication, durable replay state, kernel admission, OS containment or actual effects. No production entry point was created.

The future transport still needs authenticated session/profile and message-envelope contracts, bounded header/body reads, deadlines, cancellation, generations, replay, fences, current policy and resource checks. A complete buffer already allocated by a caller cannot be made safe retroactively by this codec. Strict records remain untrusted until actual boundary validation.

## Inspection correction

The first status summary used a PowerShell wildcard for the literal ?? marker and misclassified tracked changes. A StartsWith("?? ") check recovered the actual nine modified tracked paths and 122 untracked paths before specification mutation. A guessed test-file location was also corrected using rg to locate tests/contract/test_wire.py. No deletion, discard, reset or source/runtime mutation resulted from these read-only mistakes. All ten original displays were complete; their hashes and exact line counts were checked.

## Current state

53 source applicability decisions are assessed; 353 remain unresolved. Fifteen implementation tickets retain the original requirement groups and all 128 full cases remain NOT_RUN. WP-00/WP-01 are IN_PROGRESS; dependent WP-02 onward is not started. Current source/allocation/preservation checks are recorded separately. The full local-first, persistent, governed intelligence product and all lifecycle obligations remain active.

Read complete unresolved original 047 Privacy Architecture and subsequent sources; continue all 353 remaining source applicability decisions and the full identity, policy, authenticated message-envelope/transport, effect and migration contract before Gate A and WP-02. The full finished-product objective remains active.
