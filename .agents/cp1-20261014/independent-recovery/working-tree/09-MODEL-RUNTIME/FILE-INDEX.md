# 09-MODEL-RUNTIME - planned source index

Every row has a fully populated file-level construction specification. The logical path is exact within this architecture; the actual language extension and module binding are determined from the owner-selected local application.

| Specification | Logical source path | Local mapping status |
| --- | --- | --- |
| [CETA-09.01.01 / model-manifest](09.01-MODEL-REGISTRY/model-manifest.file.README.md) | ceta/model-runtime/model-registry/model-manifest | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.01.02 / model-availability-registry](09.01-MODEL-REGISTRY/model-availability-registry.file.README.md) | ceta/model-runtime/model-registry/model-availability-registry | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.01.03 / model-artifact-validator](09.01-MODEL-REGISTRY/model-artifact-validator.file.README.md) | ceta/model-runtime/model-registry/model-artifact-validator | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.02.01 / inference-session-manager](09.02-INFERENCE-RUNTIME/inference-session-manager.file.README.md) | ceta/model-runtime/inference-runtime/inference-session-manager | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.02.02 / inference-request-controller](09.02-INFERENCE-RUNTIME/inference-request-controller.file.README.md) | ceta/model-runtime/inference-runtime/inference-request-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.02.03 / inference-stream-handler](09.02-INFERENCE-RUNTIME/inference-stream-handler.file.README.md) | ceta/model-runtime/inference-runtime/inference-stream-handler | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.03.01 / model-capability-matcher](09.03-MODEL-ROUTING/model-capability-matcher.file.README.md) | ceta/model-runtime/model-routing/model-capability-matcher | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.03.02 / model-selection-engine](09.03-MODEL-ROUTING/model-selection-engine.file.README.md) | ceta/model-runtime/model-routing/model-selection-engine | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.03.03 / model-fallback-controller](09.03-MODEL-ROUTING/model-fallback-controller.file.README.md) | ceta/model-runtime/model-routing/model-fallback-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.04.01 / model-hardware-qualifier](09.04-MODEL-ADMISSION/model-hardware-qualifier.file.README.md) | ceta/model-runtime/model-admission/model-hardware-qualifier | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.04.02 / model-resource-estimator](09.04-MODEL-ADMISSION/model-resource-estimator.file.README.md) | ceta/model-runtime/model-admission/model-resource-estimator | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.04.03 / model-admission-gate](09.04-MODEL-ADMISSION/model-admission-gate.file.README.md) | ceta/model-runtime/model-admission/model-admission-gate | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.05.01 / local-inference-adapter](09.05-MODEL-INTERFACES/local-inference-adapter.file.README.md) | ceta/model-runtime/model-interfaces/local-inference-adapter | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.05.02 / connected-inference-adapter](09.05-MODEL-INTERFACES/connected-inference-adapter.file.README.md) | ceta/model-runtime/model-interfaces/connected-inference-adapter | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.05.03 / inference-contract-validator](09.05-MODEL-INTERFACES/inference-contract-validator.file.README.md) | ceta/model-runtime/model-interfaces/inference-contract-validator | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.06.01 / model-benchmark-runner](09.06-MODEL-EVALUATION/model-benchmark-runner.file.README.md) | ceta/model-runtime/model-evaluation/model-benchmark-runner | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.06.02 / model-quality-evaluator](09.06-MODEL-EVALUATION/model-quality-evaluator.file.README.md) | ceta/model-runtime/model-evaluation/model-quality-evaluator | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.06.03 / model-runtime-diagnostics](09.06-MODEL-EVALUATION/model-runtime-diagnostics.file.README.md) | ceta/model-runtime/model-evaluation/model-runtime-diagnostics | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.07.01 / model-acquisition-controller](09.07-MODEL-LIFECYCLE/model-acquisition-controller.file.README.md) | ceta/model-runtime/model-lifecycle/model-acquisition-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.07.02 / model-installation-manager](09.07-MODEL-LIFECYCLE/model-installation-manager.file.README.md) | ceta/model-runtime/model-lifecycle/model-installation-manager | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.07.03 / model-load-unload-controller](09.07-MODEL-LIFECYCLE/model-load-unload-controller.file.README.md) | ceta/model-runtime/model-lifecycle/model-load-unload-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.07.04 / model-configuration-validator](09.07-MODEL-LIFECYCLE/model-configuration-validator.file.README.md) | ceta/model-runtime/model-lifecycle/model-configuration-validator | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.08.01 / model-adaptation-planner](09.08-MODEL-CUSTOMIZATION/model-adaptation-planner.file.README.md) | ceta/model-runtime/model-customization/model-adaptation-planner | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.08.02 / training-job-controller](09.08-MODEL-CUSTOMIZATION/training-job-controller.file.README.md) | ceta/model-runtime/model-customization/training-job-controller | LOCAL-INSPECTION-REQUIRED |
| [CETA-09.08.03 / trained-artifact-validator](09.08-MODEL-CUSTOMIZATION/trained-artifact-validator.file.README.md) | ceta/model-runtime/model-customization/trained-artifact-validator | LOCAL-INSPECTION-REQUIRED |
