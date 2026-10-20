# 11-EXECUTION-AND-ISOLATION - planned source index

Every row has a fully populated file-level construction specification. The logical path is exact within this architecture; the actual language extension and module binding are determined from the owner-selected local application.

| Specification | Logical source path | Local mapping status |
| --- | --- | --- |
| [CETA-11.01.01 / execution-request-validator](11.01-EXECUTION-GATE/execution-request-validator.file.README.md) | ceta/execution-and-isolation/execution-gate/execution-request-validator | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.01.02 / authorization-proof-checker](11.01-EXECUTION-GATE/authorization-proof-checker.file.README.md) | ceta/execution-and-isolation/execution-gate/authorization-proof-checker | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.01.03 / execution-gate-controller](11.01-EXECUTION-GATE/execution-gate-controller.file.README.md) | ceta/execution-and-isolation/execution-gate/execution-gate-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.02.01 / execution-environment-builder](11.02-EXECUTION-SANDBOX/execution-environment-builder.file.README.md) | ceta/execution-and-isolation/execution-sandbox/execution-environment-builder | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.02.02 / execution-boundary-enforcer](11.02-EXECUTION-SANDBOX/execution-boundary-enforcer.file.README.md) | ceta/execution-and-isolation/execution-sandbox/execution-boundary-enforcer | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.02.03 / sandbox-cleanup-controller](11.02-EXECUTION-SANDBOX/sandbox-cleanup-controller.file.README.md) | ceta/execution-and-isolation/execution-sandbox/sandbox-cleanup-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.03.01 / intended-effect-register](11.03-EFFECT-CONTROL/intended-effect-register.file.README.md) | ceta/execution-and-isolation/effect-control/intended-effect-register | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.03.02 / effect-boundary-validator](11.03-EFFECT-CONTROL/effect-boundary-validator.file.README.md) | ceta/execution-and-isolation/effect-control/effect-boundary-validator | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.03.03 / actual-effect-observer](11.03-EFFECT-CONTROL/actual-effect-observer.file.README.md) | ceta/execution-and-isolation/effect-control/actual-effect-observer | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.04.01 / stop-signal-controller](11.04-STOP-AND-CANCELLATION/stop-signal-controller.file.README.md) | ceta/execution-and-isolation/stop-and-cancellation/stop-signal-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.04.02 / running-operation-terminator](11.04-STOP-AND-CANCELLATION/running-operation-terminator.file.README.md) | ceta/execution-and-isolation/stop-and-cancellation/running-operation-terminator | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.04.03 / cancellation-evidence-recorder](11.04-STOP-AND-CANCELLATION/cancellation-evidence-recorder.file.README.md) | ceta/execution-and-isolation/stop-and-cancellation/cancellation-evidence-recorder | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.05.01 / execution-transaction-manager](11.05-EXECUTION-TRANSACTIONS/execution-transaction-manager.file.README.md) | ceta/execution-and-isolation/execution-transactions/execution-transaction-manager | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.05.02 / uncertain-effect-handler](11.05-EXECUTION-TRANSACTIONS/uncertain-effect-handler.file.README.md) | ceta/execution-and-isolation/execution-transactions/uncertain-effect-handler | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.05.03 / compensation-executor](11.05-EXECUTION-TRANSACTIONS/compensation-executor.file.README.md) | ceta/execution-and-isolation/execution-transactions/compensation-executor | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.06.01 / enforcement-policy-adapter](11.06-OCTOREFLEX-BOUNDARY/enforcement-policy-adapter.file.README.md) | ceta/execution-and-isolation/octoreflex-boundary/enforcement-policy-adapter | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.06.02 / operating-system-effect-monitor](11.06-OCTOREFLEX-BOUNDARY/operating-system-effect-monitor.file.README.md) | ceta/execution-and-isolation/octoreflex-boundary/operating-system-effect-monitor | LOCAL-INSPECTION-REQUIRED |
| [CETA-11.06.03 / enforcement-attestation-adapter](11.06-OCTOREFLEX-BOUNDARY/enforcement-attestation-adapter.file.README.md) | ceta/execution-and-isolation/octoreflex-boundary/enforcement-attestation-adapter | LOCAL-INSPECTION-REQUIRED |
