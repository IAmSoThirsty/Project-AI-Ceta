# Layered acceptance criteria

The package defines 4,320 file-level acceptance obligations, component and subsystem gates, 43 canonical contract conformance profiles, and 20 cross-system scenarios. These are planned application checks. Package-document validation is reported separately and does not claim runtime implementation or test execution.

| Acceptance layer | Required outcome |
| --- | --- |
| [File Level Acceptance](FILE-LEVEL-ACCEPTANCE.md) | Each of the 432 logical implementation files must satisfy its exact responsibility and all ten acceptance IDs. |
| [Component Level Acceptance](COMPONENT-LEVEL-ACCEPTANCE.md) | Each of the 144 components must implement the complete flow in its README and preserve its domain invariant. |
| [Subsystem Level Acceptance](SUBSYSTEM-LEVEL-ACCEPTANCE.md) | Each of the 25 subsystems must satisfy its mission, invariant, file coverage, and integrated behavior. |
| [Cross Subsystem Acceptance](CROSS-SUBSYSTEM-ACCEPTANCE.md) | Real producers and consumers must implement the same canonical semantics through complete owner workflows. |
| [Security And Authority Acceptance](SECURITY-AND-AUTHORITY-ACCEPTANCE.md) | Every effectful entry path enforces current explicit authority and qualified isolation. |
| [State And Recovery Acceptance](STATE-AND-RECOVERY-ACCEPTANCE.md) | Canonical state remains consistent and recovery preserves user data and known security decisions. |
| [Offline Operation Acceptance](OFFLINE-OPERATION-ACCEPTANCE.md) | The declared local core product works without external connectivity. |
| [Complete User Workflow Acceptance](COMPLETE-USER-WORKFLOW-ACCEPTANCE.md) | The owner can complete the approved product workflows through usable native controls. |
| [Existing CETA Gate Reconciliation](EXISTING-CETA-GATE-RECONCILIATION.md) | Existing local acceptance cases and gates remain part of the product qualification baseline. |
| [Product Release Acceptance](PRODUCT-RELEASE-ACCEPTANCE.md) | The exact distributed candidate satisfies all mandatory scope and installed-runtime gates. |

Read [the end-to-end scenarios](END-TO-END-SCENARIOS/README.md) and [the product completion standard](../PRODUCT-COMPLETION-STANDARD.md).
