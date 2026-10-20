# 07-AGENT-ORCHESTRATION - test matrix

## Unit-level acceptance coverage

Every source specification defines ten concrete test obligations: required behavior, a domain-specific adverse case, schema compatibility, stale references, access, bounds and interruption, concurrency, recovery, real integration, and independent proof. These are planned tests, not runtime results.

| Unit | Acceptance IDs | Positive oracle | Negative oracle | Initial execution state |
| --- | --- | --- | --- | --- |
| [CETA-07.01.01 / agent-identity-manifest](07.01-AGENT-REGISTRY/agent-identity-manifest.file.README.md) | AT-CETA-07.01.01-01 through AT-CETA-07.01.01-10 | Two instances of the same role remain individually attributable. | Reusing a role name reuses another agent's authenticated session. | NOT EXECUTED |
| [CETA-07.01.02 / agent-role-registry](07.01-AGENT-REGISTRY/agent-role-registry.file.README.md) | AT-CETA-07.01.02-01 through AT-CETA-07.01.02-10 | An implementation task and its final review have distinct accountable owners. | The producing agent automatically assigns itself as independent verifier. | NOT EXECUTED |
| [CETA-07.01.03 / agent-capability-matcher](07.01-AGENT-REGISTRY/agent-capability-matcher.file.README.md) | AT-CETA-07.01.03-01 through AT-CETA-07.01.03-10 | A task is assigned only to an agent that meets every required capability. | High model quality compensates for missing execution permission. | NOT EXECUTED |
| [CETA-07.02.01 / agent-task-decomposer](07.02-AGENT-PLANNING/agent-task-decomposer.file.README.md) | AT-CETA-07.02.01-01 through AT-CETA-07.02.01-10 | Every child task contributes a verifiable deliverable to the parent goal. | Decomposition adds unrelated cleanup work without owner approval. | NOT EXECUTED |
| [CETA-07.02.02 / agent-assignment-planner](07.02-AGENT-PLANNING/agent-assignment-planner.file.README.md) | AT-CETA-07.02.02-01 through AT-CETA-07.02.02-10 | Concurrent agents receive nonoverlapping source ownership and named reviewers. | Two agents edit the same canonical contract without a shared change decision. | NOT EXECUTED |
| [CETA-07.02.03 / agent-dependency-planner](07.02-AGENT-PLANNING/agent-dependency-planner.file.README.md) | AT-CETA-07.02.03-01 through AT-CETA-07.02.03-10 | Independent tasks run together while dependent integration waits for verified inputs. | A consumer starts against an unapproved producer contract. | NOT EXECUTED |
| [CETA-07.03.01 / agent-message-router](07.03-AGENT-COMMUNICATION/agent-message-router.file.README.md) | AT-CETA-07.03.01-01 through AT-CETA-07.03.01-10 | A duplicate message is recognized without repeating an effectful request. | A message impersonates another agent by changing a display field. | NOT EXECUTED |
| [CETA-07.03.02 / agent-handoff-protocol](07.03-AGENT-COMMUNICATION/agent-handoff-protocol.file.README.md) | AT-CETA-07.03.02-01 through AT-CETA-07.03.02-10 | The receiving agent reproduces the producer's artifact references before continuing. | A handoff omits an uncertain prior effect and the receiver repeats it. | NOT EXECUTED |
| [CETA-07.03.03 / agent-result-exchange](07.03-AGENT-COMMUNICATION/agent-result-exchange.file.README.md) | AT-CETA-07.03.03-01 through AT-CETA-07.03.03-10 | A reviewer receives both deliverables and the evidence needed to inspect them. | A free-text success claim is accepted as a verified result. | NOT EXECUTED |
| [CETA-07.04.01 / agent-execution-coordinator](07.04-MULTIAGENT-EXECUTION/agent-execution-coordinator.file.README.md) | AT-CETA-07.04.01-01 through AT-CETA-07.04.01-10 | A restarted coordinator discovers live assignments without launching duplicates. | A lost acknowledgement creates two active workers for one exclusive assignment. | NOT EXECUTED |
| [CETA-07.04.02 / agent-concurrency-controller](07.04-MULTIAGENT-EXECUTION/agent-concurrency-controller.file.README.md) | AT-CETA-07.04.02-01 through AT-CETA-07.04.02-10 | A stale worker cannot write after its lease is reassigned. | Lease expiry is handled only in memory and lost on restart. | NOT EXECUTED |
| [CETA-07.04.03 / agent-conflict-arbitrator](07.04-MULTIAGENT-EXECUTION/agent-conflict-arbitrator.file.README.md) | AT-CETA-07.04.03-01 through AT-CETA-07.04.03-10 | Conflicting edits remain isolated until an explicit merge decision is verified. | The most recent agent output silently overwrites an earlier verified result. | NOT EXECUTED |
| [CETA-07.05.01 / agent-progress-observer](07.05-AGENT-OBSERVABILITY/agent-progress-observer.file.README.md) | AT-CETA-07.05.01-01 through AT-CETA-07.05.01-10 | A stalled agent is shown as unresponsive without falsely completing its task. | An optimistic progress message overrides a failed execution receipt. | NOT EXECUTED |
| [CETA-07.05.02 / agent-accountability-ledger](07.05-AGENT-OBSERVABILITY/agent-accountability-ledger.file.README.md) | AT-CETA-07.05.02-01 through AT-CETA-07.05.02-10 | Each accepted artifact identifies its builder, reviewer, source revision, and decision record. | Attribution is lost when an agent role is renamed. | NOT EXECUTED |
| [CETA-07.05.03 / agent-outcome-validator](07.05-AGENT-OBSERVABILITY/agent-outcome-validator.file.README.md) | AT-CETA-07.05.03-01 through AT-CETA-07.05.03-10 | A task completes only when required tests and artifacts match its pinned contract. | The producing agent's own assertion satisfies an independent verification requirement. | NOT EXECUTED |


## Component and subsystem tests

| Component | Integrated behavior | Invariant |
| --- | --- | --- |
| [07.01](07.01-AGENT-REGISTRY/README.md) | Register agents and roles; bind authenticated execution identities; match qualified capabilities; expose availability without granting new permissions. | A role label never grants capabilities by itself. |
| [07.02](07.02-AGENT-PLANNING/README.md) | Decompose the goal; assign testable outputs; identify dependencies and shared writes; allocate agents; validate the plan before execution. | Parallelization requires disjoint writes or explicit serialized ownership. |
| [07.03](07.03-AGENT-COMMUNICATION/README.md) | Authenticate agent messages; validate task scope and sequence; deliver idempotently; acknowledge handoffs; reconcile missing or duplicate messages. | Agent messages are claims and requests, not new authority grants. |
| [07.04](07.04-MULTIAGENT-EXECUTION/README.md) | Admit ready assignments; acquire scoped write leases; execute governed work; observe cancellation; resolve conflicts through recorded decisions; release leases. | Expired leases fence old workers from further writes. |
| [07.05](07.05-AGENT-OBSERVABILITY/README.md) | Collect authoritative lifecycle events; link agent claims to observed artifacts; evaluate outcomes; expose discrepancies and pending verification. | Progress percentages are presentation estimates and cannot replace completion evidence. |


Run these flows through actual local implementations after unit tests. Bind results to exact source, dependencies, configuration, environment, and artifact bytes. A mock-only test cannot qualify a native enforcement or installed-product claim. Preserve failed, blocked, skipped, and not-executed cases separately. Use [the cross-system scenarios](../ACCEPTANCE-CRITERIA/END-TO-END-SCENARIOS/README.md) for user-workflow qualification.
