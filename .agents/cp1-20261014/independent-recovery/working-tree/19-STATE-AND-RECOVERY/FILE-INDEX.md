# 19-STATE-AND-RECOVERY - planned source index

Every row has a fully populated file-level construction specification. The logical path is exact within this architecture; the actual language extension and module binding are determined from the owner-selected local application.

| Specification | Logical source path | Local mapping status |
| --- | --- | --- |
| [CETA-19.01.01 / state-record-registry](19.01-STATE-REGISTER/state-record-registry.file.README.md) | ceta/state-and-recovery/state-register/state-record-registry | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.01.02 / state-transition-validator](19.01-STATE-REGISTER/state-transition-validator.file.README.md) | ceta/state-and-recovery/state-register/state-transition-validator | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.01.03 / state-history-controller](19.01-STATE-REGISTER/state-history-controller.file.README.md) | ceta/state-and-recovery/state-register/state-history-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.02.01 / transactional-storage-controller](19.02-DURABLE-STORAGE/transactional-storage-controller.file.README.md) | ceta/state-and-recovery/durable-storage/transactional-storage-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.02.02 / storage-integrity-checker](19.02-DURABLE-STORAGE/storage-integrity-checker.file.README.md) | ceta/state-and-recovery/durable-storage/storage-integrity-checker | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.02.03 / storage-consistency-coordinator](19.02-DURABLE-STORAGE/storage-consistency-coordinator.file.README.md) | ceta/state-and-recovery/durable-storage/storage-consistency-coordinator | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.03.01 / snapshot-creation-engine](19.03-SNAPSHOTS/snapshot-creation-engine.file.README.md) | ceta/state-and-recovery/snapshots/snapshot-creation-engine | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.03.02 / snapshot-integrity-verifier](19.03-SNAPSHOTS/snapshot-integrity-verifier.file.README.md) | ceta/state-and-recovery/snapshots/snapshot-integrity-verifier | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.03.03 / snapshot-retention-controller](19.03-SNAPSHOTS/snapshot-retention-controller.file.README.md) | ceta/state-and-recovery/snapshots/snapshot-retention-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.04.01 / interrupted-operation-recovery](19.04-RECOVERY/interrupted-operation-recovery.file.README.md) | ceta/state-and-recovery/recovery/interrupted-operation-recovery | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.04.02 / persistent-state-restoration](19.04-RECOVERY/persistent-state-restoration.file.README.md) | ceta/state-and-recovery/recovery/persistent-state-restoration | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.04.03 / uncertain-state-reconciler](19.04-RECOVERY/uncertain-state-reconciler.file.README.md) | ceta/state-and-recovery/recovery/uncertain-state-reconciler | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.05.01 / schema-migration-planner](19.05-MIGRATION/schema-migration-planner.file.README.md) | ceta/state-and-recovery/migration/schema-migration-planner | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.05.02 / migration-execution-controller](19.05-MIGRATION/migration-execution-controller.file.README.md) | ceta/state-and-recovery/migration/migration-execution-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.05.03 / migration-reversal-validator](19.05-MIGRATION/migration-reversal-validator.file.README.md) | ceta/state-and-recovery/migration/migration-reversal-validator | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.06.01 / conversation-archive-controller](19.06-ARCHIVAL/conversation-archive-controller.file.README.md) | ceta/state-and-recovery/archival/conversation-archive-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.06.02 / project-history-archive](19.06-ARCHIVAL/project-history-archive.file.README.md) | ceta/state-and-recovery/archival/project-history-archive | LOCAL-INSPECTION-REQUIRED |
| [CETA-19.06.03 / historical-state-retriever](19.06-ARCHIVAL/historical-state-retriever.file.README.md) | ceta/state-and-recovery/archival/historical-state-retriever | LOCAL-INSPECTION-REQUIRED |
