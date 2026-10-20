# Dependency and ownership maps

These maps distinguish construction prerequisites, runtime flow, contract ownership, trust boundaries, state, and recovery. Shared declarations are approved first; runtime mutual communication does not imply a build cycle.

| Map | Purpose |
| --- | --- |
| [Subsystem Dependency Graph](SUBSYSTEM-DEPENDENCY-GRAPH.md) | Inspect subsystem dependency graph before changing affected interfaces or ownership. |
| [Component Ownership Matrix](COMPONENT-OWNERSHIP-MATRIX.md) | Inspect component ownership matrix before changing affected interfaces or ownership. |
| [Contract Producer Consumer Map](CONTRACT-PRODUCER-CONSUMER-MAP.md) | Inspect contract producer consumer map before changing affected interfaces or ownership. |
| [Runtime Execution Flow](RUNTIME-EXECUTION-FLOW.md) | Inspect runtime execution flow before changing affected interfaces or ownership. |
| [Agent Handoff Graph](AGENT-HANDOFF-GRAPH.md) | Inspect agent handoff graph before changing affected interfaces or ownership. |
| [Trust Boundary Map](TRUST-BOUNDARY-MAP.md) | Inspect trust boundary map before changing affected interfaces or ownership. |
| [State Lifecycle Map](STATE-LIFECYCLE-MAP.md) | Inspect state lifecycle map before changing affected interfaces or ownership. |
| [Failure Recovery Map](FAILURE-RECOVERY-MAP.md) | Inspect failure recovery map before changing affected interfaces or ownership. |
| [Build Order Graph](BUILD-ORDER-GRAPH.md) | Inspect build order graph before changing affected interfaces or ownership. |
