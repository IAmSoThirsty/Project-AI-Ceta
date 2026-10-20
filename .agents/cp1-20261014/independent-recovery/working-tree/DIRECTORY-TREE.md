# Complete package directory tree

Generated from the actual archive staging tree. Every directory has its own README; each planned implementation file has a populated .file.README.md specification. No implementation source is present.

```text
CETA-NATIVE-ARCHITECTURE/
|-- 00-MASTER-ARCHITECTURE/
|   |-- 00.01-PRODUCT-IDENTITY/
|   |   |-- README.md
|   |   |-- architecture-invariants.file.README.md
|   |   `-- product-identity.file.README.md
|   |-- 00.02-SYSTEM-TOPOLOGY/
|   |   |-- README.md
|   |   |-- architecture-graph.file.README.md
|   |   |-- component-ownership-map.file.README.md
|   |   `-- subsystem-registry.file.README.md
|   |-- 00.03-RUNTIME-LIFECYCLE/
|   |   |-- README.md
|   |   |-- application-bootstrap.file.README.md
|   |   |-- lifecycle-coordinator.file.README.md
|   |   `-- shutdown-coordinator.file.README.md
|   |-- 00.04-INTEGRATION-BASELINE/
|   |   |-- README.md
|   |   |-- compatibility-mapper.file.README.md
|   |   |-- existing-component-inspector.file.README.md
|   |   `-- integration-conflict-detector.file.README.md
|   |-- 00.05-ARCHITECTURE-ASSURANCE/
|   |   |-- README.md
|   |   |-- architectural-invariant-checker.file.README.md
|   |   |-- contract-ownership-validator.file.README.md
|   |   `-- dependency-validator.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BOOTSTRAP-AND-TRUST-BOUNDARIES.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 01-CONSTITUTIONAL-GOVERNANCE/
|   |-- 01.01-CONSTITUTIONAL-SOURCES/
|   |   |-- README.md
|   |   |-- constitution-registry.file.README.md
|   |   |-- constitutional-rule-catalog.file.README.md
|   |   `-- rule-version-loader.file.README.md
|   |-- 01.02-POLICY-ENGINE/
|   |   |-- README.md
|   |   |-- policy-conflict-resolver.file.README.md
|   |   |-- policy-evaluator.file.README.md
|   |   `-- policy-interpreter.file.README.md
|   |-- 01.03-GOVERNANCE-TRANSITIONS/
|   |   |-- README.md
|   |   |-- governance-packet-validator.file.README.md
|   |   |-- governance-quorum-controller.file.README.md
|   |   `-- transition-proposal-builder.file.README.md
|   |-- 01.04-THIRSTY-LANG/
|   |   |-- README.md
|   |   |-- governed-rule-compiler.file.README.md
|   |   |-- language-parser.file.README.md
|   |   `-- policy-type-checker.file.README.md
|   |-- 01.05-POLICY-ASSURANCE/
|   |   |-- README.md
|   |   |-- constitutional-change-validator.file.README.md
|   |   |-- policy-invariant-checker.file.README.md
|   |   `-- rule-traceability-mapper.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 02-IDENTITY-AND-AUTHORITY/
|   |-- 02.01-PRINCIPAL-IDENTITY/
|   |   |-- README.md
|   |   |-- identity-binding-controller.file.README.md
|   |   |-- identity-proof-verifier.file.README.md
|   |   `-- principal-registry.file.README.md
|   |-- 02.02-SESSION-AUTHORITY/
|   |   |-- README.md
|   |   |-- authenticated-session-manager.file.README.md
|   |   |-- session-expiration-controller.file.README.md
|   |   `-- session-scope-validator.file.README.md
|   |-- 02.03-CAPABILITY-TOKENS/
|   |   |-- README.md
|   |   |-- capability-scope-evaluator.file.README.md
|   |   |-- capability-token-issuer.file.README.md
|   |   `-- capability-token-validator.file.README.md
|   |-- 02.04-DELEGATED-AUTHORITY/
|   |   |-- README.md
|   |   |-- authority-revocation-controller.file.README.md
|   |   |-- delegation-boundary-checker.file.README.md
|   |   `-- delegation-graph.file.README.md
|   |-- 02.05-AUTHORITY-RECOVERY/
|   |   |-- README.md
|   |   |-- authority-integrity-verifier.file.README.md
|   |   |-- authority-rotation-manager.file.README.md
|   |   `-- owner-recovery-controller.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 03-COMPANION-INTELLIGENCE/
|   |-- 03.01-COMPANION-IDENTITY/
|   |   |-- README.md
|   |   |-- companion-capability-profile.file.README.md
|   |   |-- companion-identity-lifecycle.file.README.md
|   |   `-- companion-profile.file.README.md
|   |-- 03.02-DIALOGUE-INTELLIGENCE/
|   |   |-- README.md
|   |   |-- conversation-controller.file.README.md
|   |   |-- dialogue-state-manager.file.README.md
|   |   `-- response-planning-engine.file.README.md
|   |-- 03.03-CONTINUITY-AND-ADAPTATION/
|   |   |-- README.md
|   |   |-- companion-continuity-manager.file.README.md
|   |   |-- continuity-recovery-controller.file.README.md
|   |   `-- interaction-adaptation-engine.file.README.md
|   |-- 03.04-INITIATIVE-AND-DELIBERATION/
|   |   |-- README.md
|   |   |-- collaborative-deliberation-engine.file.README.md
|   |   |-- initiative-authority-filter.file.README.md
|   |   `-- initiative-proposal-engine.file.README.md
|   |-- 03.05-COMPANION-OPERATIONS/
|   |   |-- README.md
|   |   |-- companion-activity-presenter.file.README.md
|   |   |-- companion-task-coordinator.file.README.md
|   |   `-- companion-tool-requester.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 04-PERSISTENT-MEMORY/
|   |-- 04.01-MEMORY-RECORDS/
|   |   |-- README.md
|   |   |-- episodic-memory-store.file.README.md
|   |   |-- procedural-memory-store.file.README.md
|   |   `-- semantic-memory-store.file.README.md
|   |-- 04.02-MEMORY-INDEXING/
|   |   |-- README.md
|   |   |-- memory-index-builder.file.README.md
|   |   |-- semantic-memory-retriever.file.README.md
|   |   `-- temporal-memory-retriever.file.README.md
|   |-- 04.03-MEMORY-CONSOLIDATION/
|   |   |-- README.md
|   |   |-- memory-conflict-resolver.file.README.md
|   |   |-- memory-consolidation-engine.file.README.md
|   |   `-- memory-significance-analyzer.file.README.md
|   |-- 04.04-MEMORY-PROVENANCE/
|   |   |-- README.md
|   |   |-- memory-evidence-validator.file.README.md
|   |   |-- memory-source-linker.file.README.md
|   |   `-- memory-version-tracker.file.README.md
|   |-- 04.05-MEMORY-LIFECYCLE/
|   |   |-- README.md
|   |   |-- memory-access-policy.file.README.md
|   |   |-- memory-deletion-coordinator.file.README.md
|   |   `-- memory-retention-controller.file.README.md
|   |-- 04.06-MEMORY-PORTABILITY/
|   |   |-- README.md
|   |   |-- memory-export-controller.file.README.md
|   |   |-- memory-import-controller.file.README.md
|   |   `-- memory-reconstruction-validator.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 05-CONTEXT-INTELLIGENCE/
|   |-- 05.01-CONTEXT-INPUTS/
|   |   |-- README.md
|   |   |-- context-source-selector.file.README.md
|   |   |-- project-context-resolver.file.README.md
|   |   `-- session-context-resolver.file.README.md
|   |-- 05.02-CONTEXT-ASSEMBLY/
|   |   |-- README.md
|   |   |-- authority-context-injector.file.README.md
|   |   |-- context-composition-engine.file.README.md
|   |   `-- relevance-ranking-engine.file.README.md
|   |-- 05.03-CONTEXT-BUDGETING/
|   |   |-- README.md
|   |   |-- context-budget-controller.file.README.md
|   |   |-- context-overflow-handler.file.README.md
|   |   `-- context-priority-allocator.file.README.md
|   |-- 05.04-CONTEXT-COMPRESSION/
|   |   |-- README.md
|   |   |-- context-compaction-engine.file.README.md
|   |   |-- critical-state-preserver.file.README.md
|   |   `-- summary-integrity-validator.file.README.md
|   |-- 05.05-CONTEXT-ASSURANCE/
|   |   |-- README.md
|   |   |-- context-contamination-detector.file.README.md
|   |   |-- context-snapshot-manager.file.README.md
|   |   `-- source-attribution-checker.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 06-AGENT-SKILLS-AND-LEARNING/
|   |-- 06.01-SKILL-DEFINITIONS/
|   |   |-- README.md
|   |   |-- skill-contract-registry.file.README.md
|   |   |-- skill-dependency-resolver.file.README.md
|   |   `-- skill-manifest-schema.file.README.md
|   |-- 06.02-SKILL-DISCOVERY/
|   |   |-- README.md
|   |   |-- skill-catalog.file.README.md
|   |   |-- skill-compatibility-checker.file.README.md
|   |   `-- skill-matching-engine.file.README.md
|   |-- 06.03-SKILL-EXECUTION/
|   |   |-- README.md
|   |   |-- skill-input-validator.file.README.md
|   |   |-- skill-invocation-controller.file.README.md
|   |   `-- skill-result-validator.file.README.md
|   |-- 06.04-SKILL-LEARNING/
|   |   |-- README.md
|   |   |-- skill-approval-workflow.file.README.md
|   |   |-- skill-candidate-generator.file.README.md
|   |   `-- skill-learning-evaluator.file.README.md
|   |-- 06.05-SKILL-LIFECYCLE/
|   |   |-- README.md
|   |   |-- skill-audit-recorder.file.README.md
|   |   |-- skill-revocation-controller.file.README.md
|   |   `-- skill-version-manager.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 07-AGENT-ORCHESTRATION/
|   |-- 07.01-AGENT-REGISTRY/
|   |   |-- README.md
|   |   |-- agent-capability-matcher.file.README.md
|   |   |-- agent-identity-manifest.file.README.md
|   |   `-- agent-role-registry.file.README.md
|   |-- 07.02-AGENT-PLANNING/
|   |   |-- README.md
|   |   |-- agent-assignment-planner.file.README.md
|   |   |-- agent-dependency-planner.file.README.md
|   |   `-- agent-task-decomposer.file.README.md
|   |-- 07.03-AGENT-COMMUNICATION/
|   |   |-- README.md
|   |   |-- agent-handoff-protocol.file.README.md
|   |   |-- agent-message-router.file.README.md
|   |   `-- agent-result-exchange.file.README.md
|   |-- 07.04-MULTIAGENT-EXECUTION/
|   |   |-- README.md
|   |   |-- agent-concurrency-controller.file.README.md
|   |   |-- agent-conflict-arbitrator.file.README.md
|   |   `-- agent-execution-coordinator.file.README.md
|   |-- 07.05-AGENT-OBSERVABILITY/
|   |   |-- README.md
|   |   |-- agent-accountability-ledger.file.README.md
|   |   |-- agent-outcome-validator.file.README.md
|   |   `-- agent-progress-observer.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 08-TASK-AND-WORKFLOW-ENGINE/
|   |-- 08.01-TASK-DEFINITION/
|   |   |-- README.md
|   |   |-- task-contract.file.README.md
|   |   |-- task-lifecycle-controller.file.README.md
|   |   `-- task-state-validator.file.README.md
|   |-- 08.02-WORKFLOW-GRAPHS/
|   |   |-- README.md
|   |   |-- workflow-dependency-resolver.file.README.md
|   |   |-- workflow-graph-builder.file.README.md
|   |   `-- workflow-transition-engine.file.README.md
|   |-- 08.03-DURABLE-EXECUTION/
|   |   |-- README.md
|   |   |-- durable-task-runner.file.README.md
|   |   |-- interrupted-task-resumer.file.README.md
|   |   `-- task-checkpoint-controller.file.README.md
|   |-- 08.04-FAILURE-HANDLING/
|   |   |-- README.md
|   |   |-- compensation-workflow.file.README.md
|   |   |-- retry-policy-controller.file.README.md
|   |   `-- task-failure-classifier.file.README.md
|   |-- 08.05-WORKFLOW-COMPLETION/
|   |   |-- README.md
|   |   |-- completion-evidence-checker.file.README.md
|   |   |-- deliverable-validator.file.README.md
|   |   `-- task-finalization-controller.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 09-MODEL-RUNTIME/
|   |-- 09.01-MODEL-REGISTRY/
|   |   |-- README.md
|   |   |-- model-artifact-validator.file.README.md
|   |   |-- model-availability-registry.file.README.md
|   |   `-- model-manifest.file.README.md
|   |-- 09.02-INFERENCE-RUNTIME/
|   |   |-- README.md
|   |   |-- inference-request-controller.file.README.md
|   |   |-- inference-session-manager.file.README.md
|   |   `-- inference-stream-handler.file.README.md
|   |-- 09.03-MODEL-ROUTING/
|   |   |-- README.md
|   |   |-- model-capability-matcher.file.README.md
|   |   |-- model-fallback-controller.file.README.md
|   |   `-- model-selection-engine.file.README.md
|   |-- 09.04-MODEL-ADMISSION/
|   |   |-- README.md
|   |   |-- model-admission-gate.file.README.md
|   |   |-- model-hardware-qualifier.file.README.md
|   |   `-- model-resource-estimator.file.README.md
|   |-- 09.05-MODEL-INTERFACES/
|   |   |-- README.md
|   |   |-- connected-inference-adapter.file.README.md
|   |   |-- inference-contract-validator.file.README.md
|   |   `-- local-inference-adapter.file.README.md
|   |-- 09.06-MODEL-EVALUATION/
|   |   |-- README.md
|   |   |-- model-benchmark-runner.file.README.md
|   |   |-- model-quality-evaluator.file.README.md
|   |   `-- model-runtime-diagnostics.file.README.md
|   |-- 09.07-MODEL-LIFECYCLE/
|   |   |-- README.md
|   |   |-- model-acquisition-controller.file.README.md
|   |   |-- model-configuration-validator.file.README.md
|   |   |-- model-installation-manager.file.README.md
|   |   `-- model-load-unload-controller.file.README.md
|   |-- 09.08-MODEL-CUSTOMIZATION/
|   |   |-- README.md
|   |   |-- model-adaptation-planner.file.README.md
|   |   |-- trained-artifact-validator.file.README.md
|   |   `-- training-job-controller.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 10-TOOLS-AND-CAPABILITIES/
|   |-- 10.01-TOOL-REGISTRY/
|   |   |-- README.md
|   |   |-- tool-capability-index.file.README.md
|   |   |-- tool-discovery-engine.file.README.md
|   |   `-- tool-manifest.file.README.md
|   |-- 10.02-TOOL-CONTRACTS/
|   |   |-- README.md
|   |   |-- tool-effect-classifier.file.README.md
|   |   |-- tool-input-validator.file.README.md
|   |   `-- tool-output-validator.file.README.md
|   |-- 10.03-LOCAL-OPERATIONS/
|   |   |-- README.md
|   |   |-- application-control-adapter.file.README.md
|   |   |-- command-execution-adapter.file.README.md
|   |   `-- filesystem-tool-adapter.file.README.md
|   |-- 10.04-NETWORK-OPERATIONS/
|   |   |-- README.md
|   |   |-- browser-operation-adapter.file.README.md
|   |   |-- external-resource-adapter.file.README.md
|   |   `-- network-request-adapter.file.README.md
|   |-- 10.05-TOOL-EXECUTION-RESULTS/
|   |   |-- README.md
|   |   |-- tool-dispatch-controller.file.README.md
|   |   |-- tool-execution-receipt.file.README.md
|   |   `-- tool-result-normalizer.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 11-EXECUTION-AND-ISOLATION/
|   |-- 11.01-EXECUTION-GATE/
|   |   |-- README.md
|   |   |-- authorization-proof-checker.file.README.md
|   |   |-- execution-gate-controller.file.README.md
|   |   `-- execution-request-validator.file.README.md
|   |-- 11.02-EXECUTION-SANDBOX/
|   |   |-- README.md
|   |   |-- execution-boundary-enforcer.file.README.md
|   |   |-- execution-environment-builder.file.README.md
|   |   `-- sandbox-cleanup-controller.file.README.md
|   |-- 11.03-EFFECT-CONTROL/
|   |   |-- README.md
|   |   |-- actual-effect-observer.file.README.md
|   |   |-- effect-boundary-validator.file.README.md
|   |   `-- intended-effect-register.file.README.md
|   |-- 11.04-STOP-AND-CANCELLATION/
|   |   |-- README.md
|   |   |-- cancellation-evidence-recorder.file.README.md
|   |   |-- running-operation-terminator.file.README.md
|   |   `-- stop-signal-controller.file.README.md
|   |-- 11.05-EXECUTION-TRANSACTIONS/
|   |   |-- README.md
|   |   |-- compensation-executor.file.README.md
|   |   |-- execution-transaction-manager.file.README.md
|   |   `-- uncertain-effect-handler.file.README.md
|   |-- 11.06-OCTOREFLEX-BOUNDARY/
|   |   |-- README.md
|   |   |-- enforcement-attestation-adapter.file.README.md
|   |   |-- enforcement-policy-adapter.file.README.md
|   |   `-- operating-system-effect-monitor.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 12-ENGINEERING-INTELLIGENCE/
|   |-- 12.01-PROJECT-DISCOVERY/
|   |   |-- README.md
|   |   |-- code-structure-indexer.file.README.md
|   |   |-- dependency-analysis-engine.file.README.md
|   |   `-- repository-inspector.file.README.md
|   |-- 12.02-ENGINEERING-PLANNING/
|   |   |-- README.md
|   |   |-- change-risk-analyzer.file.README.md
|   |   |-- implementation-sequencer.file.README.md
|   |   `-- requirement-to-task-planner.file.README.md
|   |-- 12.03-CODE-CONSTRUCTION/
|   |   |-- README.md
|   |   |-- change-transaction-controller.file.README.md
|   |   |-- multifile-change-coordinator.file.README.md
|   |   `-- source-edit-planner.file.README.md
|   |-- 12.04-TESTING-AND-DEBUGGING/
|   |   |-- README.md
|   |   |-- diagnostic-repair-planner.file.README.md
|   |   |-- failure-reproduction-engine.file.README.md
|   |   `-- test-generation-planner.file.README.md
|   |-- 12.05-ENGINEERING-REVIEW/
|   |   |-- README.md
|   |   |-- code-review-engine.file.README.md
|   |   |-- engineering-contract-validator.file.README.md
|   |   `-- regression-risk-evaluator.file.README.md
|   |-- 12.06-ENGINEERING-DELIVERY/
|   |   |-- README.md
|   |   |-- build-verification-coordinator.file.README.md
|   |   |-- documentation-sync-controller.file.README.md
|   |   `-- implementation-report-generator.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 13-NATIVE-DEVELOPMENT-WORKSPACE/
|   |-- 13.01-PROJECT-MANAGEMENT/
|   |   |-- README.md
|   |   |-- project-session-controller.file.README.md
|   |   |-- project-structure-explorer.file.README.md
|   |   `-- workspace-project-registry.file.README.md
|   |-- 13.02-SOURCE-EDITOR/
|   |   |-- README.md
|   |   |-- editor-diagnostics-presenter.file.README.md
|   |   |-- editor-state-manager.file.README.md
|   |   `-- source-document-controller.file.README.md
|   |-- 13.03-CHANGE-INSPECTION/
|   |   |-- README.md
|   |   |-- change-history-viewer.file.README.md
|   |   |-- change-staging-controller.file.README.md
|   |   `-- file-diff-presenter.file.README.md
|   |-- 13.04-TERMINAL-WORKSPACE/
|   |   |-- README.md
|   |   |-- command-output-presenter.file.README.md
|   |   |-- terminal-lifecycle-manager.file.README.md
|   |   `-- terminal-session-controller.file.README.md
|   |-- 13.05-VERSION-CONTROL/
|   |   |-- README.md
|   |   |-- isolated-workspace-manager.file.README.md
|   |   |-- revision-comparison-controller.file.README.md
|   |   `-- source-control-adapter.file.README.md
|   |-- 13.06-DEVELOPMENT-PREVIEW/
|   |   |-- README.md
|   |   |-- application-preview-controller.file.README.md
|   |   |-- visual-inspection-presenter.file.README.md
|   |   `-- workspace-recovery-controller.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 14-AUTOMATION-AND-SCHEDULING/
|   |-- 14.01-SCHEDULE-DEFINITIONS/
|   |   |-- README.md
|   |   |-- schedule-contract.file.README.md
|   |   |-- schedule-registry.file.README.md
|   |   `-- schedule-validation-engine.file.README.md
|   |-- 14.02-TIME-TRIGGERS/
|   |   |-- README.md
|   |   |-- one-time-trigger-controller.file.README.md
|   |   |-- recurring-trigger-controller.file.README.md
|   |   `-- time-window-evaluator.file.README.md
|   |-- 14.03-EVENT-TRIGGERS/
|   |   |-- README.md
|   |   |-- event-condition-evaluator.file.README.md
|   |   |-- resource-change-watcher.file.README.md
|   |   `-- system-event-listener.file.README.md
|   |-- 14.04-AUTOMATION-DISPATCH/
|   |   |-- README.md
|   |   |-- automation-concurrency-controller.file.README.md
|   |   |-- automation-job-dispatcher.file.README.md
|   |   `-- scheduled-authority-validator.file.README.md
|   |-- 14.05-AUTOMATION-CONTINUITY/
|   |   |-- README.md
|   |   |-- automation-outcome-recorder.file.README.md
|   |   |-- automation-recovery-controller.file.README.md
|   |   `-- missed-trigger-reconciler.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 15-COMMUNICATION-AND-INTERACTION/
|   |-- 15.01-CONVERSATION/
|   |   |-- README.md
|   |   |-- conversation-history-presenter.file.README.md
|   |   |-- conversation-stream-handler.file.README.md
|   |   `-- message-session-controller.file.README.md
|   |-- 15.02-VOICE/
|   |   |-- README.md
|   |   |-- speech-input-controller.file.README.md
|   |   |-- speech-output-controller.file.README.md
|   |   `-- voice-session-coordinator.file.README.md
|   |-- 15.03-CHANNELS/
|   |   |-- README.md
|   |   |-- communication-channel-registry.file.README.md
|   |   |-- incoming-message-router.file.README.md
|   |   `-- outgoing-message-controller.file.README.md
|   |-- 15.04-ATTACHMENTS/
|   |   |-- README.md
|   |   |-- attachment-ingestion-controller.file.README.md
|   |   |-- attachment-storage-linker.file.README.md
|   |   `-- attachment-type-validator.file.README.md
|   |-- 15.05-HUMAN-INTERVENTION/
|   |   |-- README.md
|   |   |-- decision-response-handler.file.README.md
|   |   |-- human-decision-requester.file.README.md
|   |   `-- interaction-notification-router.file.README.md
|   |-- 15.06-MULTIMODAL-INTERACTION/
|   |   |-- README.md
|   |   |-- image-input-controller.file.README.md
|   |   |-- media-context-extractor.file.README.md
|   |   `-- multimodal-session-coordinator.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 16-KNOWLEDGE-AND-RESEARCH/
|   |-- 16.01-SOURCE-INGESTION/
|   |   |-- README.md
|   |   |-- document-ingestion-engine.file.README.md
|   |   |-- structured-data-ingestion.file.README.md
|   |   `-- web-content-ingestion-engine.file.README.md
|   |-- 16.02-KNOWLEDGE-EXTRACTION/
|   |   |-- README.md
|   |   |-- document-structure-extractor.file.README.md
|   |   |-- entity-relation-extractor.file.README.md
|   |   `-- knowledge-normalization-engine.file.README.md
|   |-- 16.03-KNOWLEDGE-INDEXING/
|   |   |-- README.md
|   |   |-- fulltext-knowledge-index.file.README.md
|   |   |-- knowledge-graph-builder.file.README.md
|   |   `-- semantic-knowledge-index.file.README.md
|   |-- 16.04-RESEARCH-REASONING/
|   |   |-- README.md
|   |   |-- claim-verification-planner.file.README.md
|   |   |-- evidence-weighting-engine.file.README.md
|   |   `-- source-comparison-engine.file.README.md
|   |-- 16.05-RESEARCH-OUTPUT/
|   |   |-- README.md
|   |   |-- citation-construction-engine.file.README.md
|   |   |-- research-state-preserver.file.README.md
|   |   `-- research-synthesis-controller.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 17-EVIDENCE-AND-PROVENANCE/
|   |-- 17.01-EVIDENCE-CAPTURE/
|   |   |-- README.md
|   |   |-- evidence-artifact-register.file.README.md
|   |   |-- execution-evidence-collector.file.README.md
|   |   `-- input-output-recorder.file.README.md
|   |-- 17.02-CRYPTOGRAPHIC-INTEGRITY/
|   |   |-- README.md
|   |   |-- artifact-digest-generator.file.README.md
|   |   |-- cryptographic-verification-engine.file.README.md
|   |   `-- evidence-signature-controller.file.README.md
|   |-- 17.03-PROVENANCE-GRAPHS/
|   |   |-- README.md
|   |   |-- evidence-lineage-index.file.README.md
|   |   |-- provenance-chain-validator.file.README.md
|   |   `-- provenance-relationship-builder.file.README.md
|   |-- 17.04-IMMUTABLE-FRAMES/
|   |   |-- README.md
|   |   |-- evidence-frame-constructor.file.README.md
|   |   |-- evidence-frame-sealer.file.README.md
|   |   `-- evidence-frame-verifier.file.README.md
|   |-- 17.05-REPLAY-AND-VERIFICATION/
|   |   |-- README.md
|   |   |-- deterministic-replay-controller.file.README.md
|   |   |-- evidence-gap-detector.file.README.md
|   |   `-- independent-result-verifier.file.README.md
|   |-- 17.06-EVIDENCE-ACCESS/
|   |   |-- README.md
|   |   |-- evidence-export-controller.file.README.md
|   |   |-- evidence-query-engine.file.README.md
|   |   `-- evidence-report-builder.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 18-SECURITY-AND-ENFORCEMENT/
|   |-- 18.01-CRYPTOGRAPHIC-IDENTITY/
|   |   |-- README.md
|   |   |-- cryptographic-key-manager.file.README.md
|   |   |-- device-trust-binding.file.README.md
|   |   `-- signature-trust-verifier.file.README.md
|   |-- 18.02-SECRET-PROTECTION/
|   |   |-- README.md
|   |   |-- encrypted-secret-vault.file.README.md
|   |   |-- secret-access-controller.file.README.md
|   |   `-- secret-rotation-coordinator.file.README.md
|   |-- 18.03-SECURITY-POLICY/
|   |   |-- README.md
|   |   |-- security-boundary-registry.file.README.md
|   |   |-- security-enforcement-adapter.file.README.md
|   |   `-- security-policy-evaluator.file.README.md
|   |-- 18.04-RISK-AND-ANOMALY/
|   |   |-- README.md
|   |   |-- behavioral-anomaly-detector.file.README.md
|   |   |-- execution-risk-evaluator.file.README.md
|   |   `-- security-alert-controller.file.README.md
|   |-- 18.05-INCIDENT-RESPONSE/
|   |   |-- README.md
|   |   |-- containment-response-engine.file.README.md
|   |   |-- incident-state-controller.file.README.md
|   |   `-- security-recovery-verifier.file.README.md
|   |-- 18.06-SECURITY-ASSURANCE/
|   |   |-- README.md
|   |   |-- dependency-integrity-checker.file.README.md
|   |   |-- security-audit-generator.file.README.md
|   |   `-- trust-chain-validator.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 19-STATE-AND-RECOVERY/
|   |-- 19.01-STATE-REGISTER/
|   |   |-- README.md
|   |   |-- state-history-controller.file.README.md
|   |   |-- state-record-registry.file.README.md
|   |   `-- state-transition-validator.file.README.md
|   |-- 19.02-DURABLE-STORAGE/
|   |   |-- README.md
|   |   |-- storage-consistency-coordinator.file.README.md
|   |   |-- storage-integrity-checker.file.README.md
|   |   `-- transactional-storage-controller.file.README.md
|   |-- 19.03-SNAPSHOTS/
|   |   |-- README.md
|   |   |-- snapshot-creation-engine.file.README.md
|   |   |-- snapshot-integrity-verifier.file.README.md
|   |   `-- snapshot-retention-controller.file.README.md
|   |-- 19.04-RECOVERY/
|   |   |-- README.md
|   |   |-- interrupted-operation-recovery.file.README.md
|   |   |-- persistent-state-restoration.file.README.md
|   |   `-- uncertain-state-reconciler.file.README.md
|   |-- 19.05-MIGRATION/
|   |   |-- README.md
|   |   |-- migration-execution-controller.file.README.md
|   |   |-- migration-reversal-validator.file.README.md
|   |   `-- schema-migration-planner.file.README.md
|   |-- 19.06-ARCHIVAL/
|   |   |-- README.md
|   |   |-- conversation-archive-controller.file.README.md
|   |   |-- historical-state-retriever.file.README.md
|   |   `-- project-history-archive.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 20-RESOURCE-MANAGEMENT/
|   |-- 20.01-HARDWARE-DISCOVERY/
|   |   |-- README.md
|   |   |-- compute-availability-monitor.file.README.md
|   |   |-- hardware-capability-profiler.file.README.md
|   |   `-- storage-capacity-monitor.file.README.md
|   |-- 20.02-RESOURCE-BUDGETING/
|   |   |-- README.md
|   |   |-- compute-budget-controller.file.README.md
|   |   |-- execution-time-budget-controller.file.README.md
|   |   `-- memory-budget-controller.file.README.md
|   |-- 20.03-WORKLOAD-ADMISSION/
|   |   |-- README.md
|   |   |-- concurrent-workload-planner.file.README.md
|   |   |-- workload-admission-controller.file.README.md
|   |   `-- workload-requirement-estimator.file.README.md
|   |-- 20.04-RESOURCE-PRESSURE/
|   |   |-- README.md
|   |   |-- graceful-degradation-coordinator.file.README.md
|   |   |-- resource-pressure-detector.file.README.md
|   |   `-- workload-throttling-controller.file.README.md
|   |-- 20.05-OPERATIONAL-DIAGNOSTICS/
|   |   |-- README.md
|   |   |-- offline-operation-qualifier.file.README.md
|   |   |-- performance-diagnostics-engine.file.README.md
|   |   `-- resource-telemetry-recorder.file.README.md
|   |-- 20.06-INFERENCE-ACCOUNTING/
|   |   |-- README.md
|   |   |-- inference-usage-ledger.file.README.md
|   |   |-- task-inference-budget-controller.file.README.md
|   |   `-- token-consumption-meter.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 21-EXTENSIONS-AND-INTEROPERABILITY/
|   |-- 21.01-EXTENSION-MANIFESTS/
|   |   |-- README.md
|   |   |-- extension-contract-validator.file.README.md
|   |   |-- extension-dependency-resolver.file.README.md
|   |   `-- extension-manifest-schema.file.README.md
|   |-- 21.02-EXTENSION-LIFECYCLE/
|   |   |-- README.md
|   |   |-- extension-installation-controller.file.README.md
|   |   |-- extension-revocation-controller.file.README.md
|   |   `-- extension-version-manager.file.README.md
|   |-- 21.03-INTEROPERABILITY-CONTRACTS/
|   |   |-- README.md
|   |   |-- external-capability-adapter.file.README.md
|   |   |-- interprocess-message-adapter.file.README.md
|   |   `-- protocol-compatibility-validator.file.README.md
|   |-- 21.04-EXTENSION-SECURITY/
|   |   |-- README.md
|   |   |-- extension-authority-controller.file.README.md
|   |   |-- extension-integrity-verifier.file.README.md
|   |   `-- extension-isolation-controller.file.README.md
|   |-- 21.05-NATIVE-EXTENSION-KIT/
|   |   |-- README.md
|   |   |-- extension-documentation-builder.file.README.md
|   |   |-- extension-template-generator.file.README.md
|   |   `-- extension-test-harness.file.README.md
|   |-- 21.06-EXTENSION-CATALOG/
|   |   |-- README.md
|   |   |-- extension-catalog-registry.file.README.md
|   |   |-- extension-compatibility-evaluator.file.README.md
|   |   `-- extension-review-controller.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 22-DESKTOP-AND-USER-EXPERIENCE/
|   |-- 22.01-APPLICATION-SHELL/
|   |   |-- README.md
|   |   |-- application-navigation-router.file.README.md
|   |   |-- desktop-shell-controller.file.README.md
|   |   `-- window-state-manager.file.README.md
|   |-- 22.02-COMMAND-CENTER/
|   |   |-- README.md
|   |   |-- active-task-dashboard.file.README.md
|   |   |-- operational-health-presenter.file.README.md
|   |   `-- system-overview-dashboard.file.README.md
|   |-- 22.03-AGENT-CONTROL/
|   |   |-- README.md
|   |   |-- agent-activity-dashboard.file.README.md
|   |   |-- agent-capability-viewer.file.README.md
|   |   `-- agent-task-inspector.file.README.md
|   |-- 22.04-GOVERNANCE-INTERFACE/
|   |   |-- README.md
|   |   |-- authority-delegation-view.file.README.md
|   |   |-- authorization-request-view.file.README.md
|   |   `-- governance-decision-history.file.README.md
|   |-- 22.05-INTELLIGENCE-INTERFACE/
|   |   |-- README.md
|   |   |-- companion-conversation-view.file.README.md
|   |   |-- context-inspection-view.file.README.md
|   |   `-- memory-explorer-view.file.README.md
|   |-- 22.06-EVIDENCE-INTERFACE/
|   |   |-- README.md
|   |   |-- evidence-timeline-view.file.README.md
|   |   |-- execution-verification-view.file.README.md
|   |   `-- provenance-graph-view.file.README.md
|   |-- 22.07-USER-CONTROLS/
|   |   |-- README.md
|   |   |-- accessibility-preferences.file.README.md
|   |   |-- application-settings-controller.file.README.md
|   |   `-- notification-preferences.file.README.md
|   |-- 22.08-OWNER-ONBOARDING/
|   |   |-- README.md
|   |   |-- first-run-setup-controller.file.README.md
|   |   |-- hardware-qualification-view.file.README.md
|   |   `-- local-ownership-verification.file.README.md
|   |-- 22.09-NATIVE-MAINTENANCE/
|   |   |-- README.md
|   |   |-- application-update-view.file.README.md
|   |   |-- backup-management-view.file.README.md
|   |   `-- restore-and-repair-view.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 23-TESTING-AND-QUALIFICATION/
|   |-- 23.01-TEST-ARCHITECTURE/
|   |   |-- README.md
|   |   |-- test-case-registry.file.README.md
|   |   |-- test-fixture-controller.file.README.md
|   |   `-- test-result-normalizer.file.README.md
|   |-- 23.02-CONTRACT-TESTING/
|   |   |-- README.md
|   |   |-- authority-boundary-test-runner.file.README.md
|   |   |-- governance-invariant-test-runner.file.README.md
|   |   `-- interface-contract-test-runner.file.README.md
|   |-- 23.03-INTEGRATION-TESTING/
|   |   |-- README.md
|   |   |-- application-lifecycle-test-runner.file.README.md
|   |   |-- cross-subsystem-test-coordinator.file.README.md
|   |   `-- durable-recovery-test-runner.file.README.md
|   |-- 23.04-ADVERSARIAL-AND-FAILURE-TESTS/
|   |   |-- README.md
|   |   |-- authority-bypass-test-runner.file.README.md
|   |   |-- interruption-fault-injector.file.README.md
|   |   `-- malicious-input-test-engine.file.README.md
|   |-- 23.05-PRODUCT-QUALIFICATION/
|   |   |-- README.md
|   |   |-- acceptance-criteria-evaluator.file.README.md
|   |   |-- qualification-gate-controller.file.README.md
|   |   `-- release-evidence-validator.file.README.md
|   |-- 23.06-USER-EXPERIENCE-TESTING/
|   |   |-- README.md
|   |   |-- accessibility-test-coordinator.file.README.md
|   |   |-- interface-behavior-test-runner.file.README.md
|   |   `-- performance-regression-test-runner.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- 24-BUILD-AND-RELEASE/
|   |-- 24.01-BUILD-ORCHESTRATION/
|   |   |-- README.md
|   |   |-- build-configuration-controller.file.README.md
|   |   |-- build-dependency-validator.file.README.md
|   |   `-- reproducible-build-coordinator.file.README.md
|   |-- 24.02-VERSION-MANAGEMENT/
|   |   |-- README.md
|   |   |-- component-compatibility-checker.file.README.md
|   |   |-- product-version-controller.file.README.md
|   |   `-- release-manifest-generator.file.README.md
|   |-- 24.03-PACKAGING/
|   |   |-- README.md
|   |   |-- application-package-builder.file.README.md
|   |   |-- installer-generation-controller.file.README.md
|   |   `-- offline-package-validator.file.README.md
|   |-- 24.04-RELEASE-INTEGRITY/
|   |   |-- README.md
|   |   |-- release-artifact-signer.file.README.md
|   |   |-- release-integrity-verifier.file.README.md
|   |   `-- release-provenance-recorder.file.README.md
|   |-- 24.05-UPDATE-AND-ROLLBACK/
|   |   |-- README.md
|   |   |-- release-rollback-manager.file.README.md
|   |   |-- update-execution-controller.file.README.md
|   |   `-- update-package-validator.file.README.md
|   |-- 24.06-PRODUCT-COMPLETION/
|   |   |-- README.md
|   |   |-- completion-gate-evaluator.file.README.md
|   |   |-- end-to-end-product-verifier.file.README.md
|   |   `-- release-qualification-reporter.file.README.md
|   |-- ACCEPTANCE.md
|   |-- AGENT-ASSIGNMENTS.md
|   |-- ARCHITECTURE.md
|   |-- BUILD-SEQUENCE.md
|   |-- DEPENDENCIES.md
|   |-- FAILURE-AND-RECOVERY.md
|   |-- FILE-INDEX.md
|   |-- INTEGRATION.md
|   |-- INTERFACE-CONTRACTS.md
|   |-- README.md
|   `-- TEST-MATRIX.md
|-- ACCEPTANCE-CRITERIA/
|   |-- END-TO-END-SCENARIOS/
|   |   |-- E2E-01-OWNER-SETUP-AND-LOCAL-STARTUP.md
|   |   |-- E2E-02-OFFLINE-COMPANION-MEMORY-CONTEXT.md
|   |   |-- E2E-03-GOVERNED-LOCAL-ENGINEERING-CHANGE.md
|   |   |-- E2E-04-BOUNDED-MULTIAGENT-HANDOFF.md
|   |   |-- E2E-05-STOP-AND-REVOCATION-RACE.md
|   |   |-- E2E-06-CRASH-AFTER-POSSIBLE-EFFECT.md
|   |   |-- E2E-07-MEMORY-CORRECTION-DELETION-PORTABILITY.md
|   |   |-- E2E-08-SKILL-LEARNING-AND-REVOCATION.md
|   |   |-- E2E-09-SCHEDULE-DOWNTIME-AND-AUTHORITY-RENEWAL.md
|   |   |-- E2E-10-SOURCE-TO-CLAIM-RESEARCH.md
|   |   |-- E2E-11-MODEL-LIFECYCLE-AND-PRIVATE-FALLBACK.md
|   |   |-- E2E-12-VOICE-MEDIA-AND-EXACT-DECISIONS.md
|   |   |-- E2E-13-PROTECTED-SECRETS-AND-ROTATION.md
|   |   |-- E2E-14-OPTIONAL-EXTENSION-ISOLATION.md
|   |   |-- E2E-15-BACKUP-RESTORE-AND-USER-DATA.md
|   |   |-- E2E-16-SCHEMA-MIGRATION-AND-REVERSAL.md
|   |   |-- E2E-17-UPDATE-ROLLBACK-AND-ARTIFACT-BINDING.md
|   |   |-- E2E-18-ADVERSARIAL-BOUNDARY-COVERAGE.md
|   |   |-- E2E-19-RESOURCE-PRESSURE-AND-RESPONSIVENESS.md
|   |   |-- E2E-20-COMPLETE-INSTALLED-PRODUCT.md
|   |   `-- README.md
|   |-- COMPLETE-USER-WORKFLOW-ACCEPTANCE.md
|   |-- COMPONENT-LEVEL-ACCEPTANCE.md
|   |-- CROSS-SUBSYSTEM-ACCEPTANCE.md
|   |-- EXISTING-CETA-GATE-RECONCILIATION.md
|   |-- FILE-LEVEL-ACCEPTANCE.md
|   |-- OFFLINE-OPERATION-ACCEPTANCE.md
|   |-- PRODUCT-RELEASE-ACCEPTANCE.md
|   |-- README.md
|   |-- SECURITY-AND-AUTHORITY-ACCEPTANCE.md
|   |-- STATE-AND-RECOVERY-ACCEPTANCE.md
|   `-- SUBSYSTEM-LEVEL-ACCEPTANCE.md
|-- AGENT-ROLES/
|   |-- R01-ARCHITECTURE-COORDINATOR/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R02-EXISTING-SYSTEM-RECONCILER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R03-CONSTITUTIONAL-GOVERNANCE-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R04-IDENTITY-AND-AUTHORITY-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R05-COMPANION-INTELLIGENCE-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R06-MEMORY-AND-CONTEXT-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R07-AGENT-ORCHESTRATION-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R08-WORKFLOW-AND-AUTOMATION-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R09-MODEL-RUNTIME-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R10-TOOL-AND-EXECUTION-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R11-ENGINEERING-WORKSPACE-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R12-COMMUNICATION-AND-UX-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R13-KNOWLEDGE-AND-RESEARCH-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R14-EVIDENCE-AND-PROVENANCE-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R15-SECURITY-AND-CRYPTOGRAPHY-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R16-STATE-AND-RECOVERY-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R17-RESOURCE-AND-PERFORMANCE-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R18-INTEGRATION-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R19-TEST-AND-QUALIFICATION-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R20-INDEPENDENT-ADVERSARIAL-VERIFIER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- R21-BUILD-AND-RELEASE-ENGINEER/
|   |   |-- AUTHORITY-BOUNDARIES.md
|   |   |-- COMPLETION-STANDARD.md
|   |   |-- FAILURE-RESPONSE.md
|   |   |-- HANDOFF-PROTOCOL.md
|   |   |-- INPUT-CONTRACTS.md
|   |   |-- MISSION.md
|   |   |-- OUTPUT-CONTRACTS.md
|   |   |-- OWNED-SUBSYSTEMS.md
|   |   |-- README.md
|   |   |-- REQUIRED-SKILLS.md
|   |   `-- RESPONSIBILITIES.md
|   |-- CROSS-AGENT-HANDOFF-CONTRACT.md
|   |-- HUMAN-AUTHORITY-BOUNDARY.md
|   |-- README.md
|   `-- ROLE-ASSIGNMENT-MATRIX.md
|-- AGENT-SKILLS/
|   |-- S01-LOCAL-BASELINE-INSPECTION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S02-REQUIREMENTS-DECOMPOSITION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S03-CONTRACT-FIRST-DESIGN/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S04-FILE-SPECIFICATION-IMPLEMENTATION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S05-ARCHITECTURAL-DEPENDENCY-ANALYSIS/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S06-CONSTITUTIONAL-POLICY-IMPLEMENTATION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S07-AUTHORITY-BOUNDARY-IMPLEMENTATION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S08-STATE-TRANSITION-ENGINEERING/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S09-DURABLE-STORAGE-ENGINEERING/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S10-CRYPTOGRAPHIC-INTEGRITY-ENGINEERING/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S11-MEMORY-AND-RETRIEVAL-ENGINEERING/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S12-AGENT-WORKFLOW-ENGINEERING/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S13-MODEL-INFERENCE-QUALIFICATION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S14-TOOL-EXECUTION-BOUNDARY-ENGINEERING/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S15-DESKTOP-INTERFACE-IMPLEMENTATION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S16-TEST-GENERATION-AND-EXECUTION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S17-FAILURE-INJECTION-AND-RECOVERY/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S18-ADVERSARIAL-SECURITY-REVIEW/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S19-EVIDENCE-CHAIN-VALIDATION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S20-PERFORMANCE-AND-RESOURCE-ANALYSIS/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S21-CROSS-SUBSYSTEM-INTEGRATION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S22-DOCUMENTATION-AND-TRACEABILITY/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S23-RELEASE-QUALIFICATION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S24-INDEPENDENT-REPRODUCTION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- S25-NO-PROOF-NO-CLAIM-VERIFICATION/
|   |   |-- FAILURE-HANDLING.md
|   |   |-- HANDOFF.md
|   |   |-- INPUTS.md
|   |   |-- OUTPUTS.md
|   |   |-- PREREQUISITES.md
|   |   |-- PROCEDURE.md
|   |   |-- PURPOSE.md
|   |   |-- README.md
|   |   |-- SKILL.md
|   |   `-- VERIFICATION.md
|   |-- README.md
|   `-- SKILL-REGISTRY.md
|-- DEPENDENCY-MAPS/
|   |-- AGENT-HANDOFF-GRAPH.md
|   |-- BUILD-ORDER-GRAPH.md
|   |-- COMPONENT-OWNERSHIP-MATRIX.md
|   |-- CONTRACT-PRODUCER-CONSUMER-MAP.md
|   |-- FAILURE-RECOVERY-MAP.md
|   |-- README.md
|   |-- RUNTIME-EXECUTION-FLOW.md
|   |-- STATE-LIFECYCLE-MAP.md
|   |-- SUBSYSTEM-DEPENDENCY-GRAPH.md
|   `-- TRUST-BOUNDARY-MAP.md
|-- IMPLEMENTATION-SEQUENCE/
|   |-- PHASE-00-LOCAL-CETA-DISCOVERY.md
|   |-- PHASE-01-ARCHITECTURE-RECONCILIATION.md
|   |-- PHASE-02-CORE-CONTRACTS-AND-STATE.md
|   |-- PHASE-03-AUTHORITY-AND-ENFORCEMENT.md
|   |-- PHASE-04-INTELLIGENCE-FOUNDATIONS.md
|   |-- PHASE-05-AGENTS-AND-WORKFLOWS.md
|   |-- PHASE-06-ENGINEERING-AND-OPERATIONS.md
|   |-- PHASE-07-USER-EXPERIENCE-AND-EXTENSIONS.md
|   |-- PHASE-08-FULL-SYSTEM-QUALIFICATION.md
|   |-- PHASE-09-PRODUCT-DELIVERY.md
|   `-- README.md
|-- INTEGRATION-PLAN/
|   |-- CANONICAL-FILE-OWNERSHIP.md
|   |-- DESIGN-DECISION-REGISTER.md
|   |-- EXISTING-APPLICATION-INVENTORY.md
|   |-- EXISTING-BEHAVIOR-PRESERVATION.md
|   |-- INCREMENTAL-INTEGRATION-ORDER.md
|   |-- INTEGRATION-ROLLBACK-PLAN.md
|   |-- INTERFACE-COMPATIBILITY-PLAN.md
|   |-- LOCAL-SOURCE-PATH-MAPPING.md
|   |-- README.md
|   |-- REUSE-EXTEND-CREATE-DECISION-MATRIX.md
|   `-- STATE-AND-DATA-MIGRATION-PLAN.md
|-- INTERFACE-CONTRACTS/
|   |-- AGENTS-AND-TASKS/
|   |   |-- README.md
|   |   |-- agent-handoff.contract.md
|   |   |-- agent-manifest.contract.md
|   |   |-- agent-message.contract.md
|   |   |-- scheduled-task.contract.md
|   |   |-- skill-manifest.contract.md
|   |   |-- task-definition.contract.md
|   |   `-- workflow-transition.contract.md
|   |-- AUTHORITY/
|   |   |-- README.md
|   |   |-- authenticated-session.contract.md
|   |   |-- authority-delegation.contract.md
|   |   |-- authority-revocation.contract.md
|   |   |-- capability-token.contract.md
|   |   |-- governance-packet.contract.md
|   |   |-- policy-decision.contract.md
|   |   `-- principal-identity.contract.md
|   |-- EXECUTION/
|   |   |-- README.md
|   |   |-- execution-request.contract.md
|   |   |-- execution-result.contract.md
|   |   |-- intended-effect.contract.md
|   |   |-- isolation-context.contract.md
|   |   |-- stop-signal.contract.md
|   |   `-- uncertain-operation.contract.md
|   |-- INTELLIGENCE/
|   |   |-- README.md
|   |   |-- context-snapshot.contract.md
|   |   |-- inference-request.contract.md
|   |   |-- inference-response.contract.md
|   |   |-- knowledge-source.contract.md
|   |   |-- memory-record.contract.md
|   |   |-- model-manifest.contract.md
|   |   `-- research-claim.contract.md
|   |-- STATE-AND-EVIDENCE/
|   |   |-- README.md
|   |   |-- evidence-receipt.contract.md
|   |   |-- persistent-checkpoint.contract.md
|   |   |-- provenance-link.contract.md
|   |   |-- recovery-report.contract.md
|   |   |-- state-transition.contract.md
|   |   `-- verification-result.contract.md
|   |-- TOOLS-AND-RESOURCES/
|   |   |-- README.md
|   |   |-- resource-budget.contract.md
|   |   |-- tool-invocation.contract.md
|   |   |-- tool-manifest.contract.md
|   |   |-- tool-result.contract.md
|   |   `-- workload-admission.contract.md
|   |-- USER-INTERACTION/
|   |   |-- README.md
|   |   |-- application-error.contract.md
|   |   |-- desktop-command.contract.md
|   |   |-- human-decision-request.contract.md
|   |   |-- human-decision-response.contract.md
|   |   `-- notification-event.contract.md
|   |-- CONTRACT-COMMON-RULES.md
|   `-- README.md
|-- MANIFESTS-AND-TRACEABILITY/
|   |-- AGENT-ASSIGNMENT-INDEX.md
|   |-- CONTRACT-REFERENCE-INDEX.md
|   |-- FEATURE-OWNERSHIP-MATRIX.md
|   |-- FILE-TO-TEST-MATRIX.md
|   |-- PACKAGE-COMPLETENESS-REPORT.md
|   |-- PACKAGE-FILE-INVENTORY.md
|   |-- PLANNED-SOURCE-FILE-REGISTRY.md
|   |-- README.md
|   |-- REQUIREMENT-TO-FILE-MATRIX.md
|   |-- SKILL-DEPENDENCY-INDEX.md
|   |-- SUBSYSTEM-REGISTRY.md
|   `-- TEST-TO-EVIDENCE-MATRIX.md
|-- DIRECTORY-TREE.md
|-- EXISTING-CETA-RECONCILIATION.md
|-- GLOBAL-ENGINEERING-RULES.md
|-- MASTER-README.md
|-- PACKAGE-INTEGRITY.md
|-- PACKAGE-MANIFEST.md
|-- PRODUCT-COMPLETION-STANDARD.md
`-- README.md
```
