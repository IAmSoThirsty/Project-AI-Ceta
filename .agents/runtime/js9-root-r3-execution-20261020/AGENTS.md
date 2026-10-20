# Exact reviewed JS9 R3 execution scopes

Reuse the existing product plan. Candidate and destination evidence remain separate. Fixture leases record the paths excluded from a parent workspace snapshot. Only a separate exact release admits an engineering operation.

```agents-graph
{
  "version": 1,
  "graph": {
    "id": "ceta_js9_r3_execution",
    "policy": {
      "fail_closed": true,
      "max_parallel": 4,
      "prohibit_scope_overlap": true,
      "prohibit_self_review": true,
      "require_receipts": true
    },
    "nodes": {
      "discover": {
        "kind": "agent",
        "role": "explorer",
        "access": "read_only"
      },
      "plan": {
        "kind": "agent",
        "role": "architect",
        "access": "read_only"
      },
      "implement": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [
          ".agents/runtime/js9-runtime-20261020/successor-r3/**"
        ]
      },
      "candidate_fixtures": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [
          ".agents/js9-runtime-r5-20261020/.agents/fixtures/**"
        ]
      },
      "candidate_cache": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [
          ".agents/js9-runtime-r5-20261020/.local-test-output/**"
        ]
      },
      "review": {
        "kind": "agent",
        "role": "reviewer",
        "access": "read_only"
      },
      "validate": {
        "kind": "gate",
        "access": "read_only",
        "commands": [
          "git -C \"{workspace}\" diff --check"
        ]
      },
      "integrate": {
        "kind": "integration",
        "role": "integrator",
        "access": "write_scoped",
        "write_scope": [
          "contracts/CPU_OUTCOME_CAPACITY_CONNECTION_V1.md",
          "contracts/CPU_OUTCOME_RECOVERY_V1.md",
          "contracts/NATIVE_CPU_OUTCOME_PROVENANCE_V1.md",
          "contracts/NATIVE_CPU_RUNTIME_COMPOSITION_V1.md",
          "contracts/NATIVE_OWNER_SESSION_V1.md",
          "contracts/OUTCOME_CAPACITY_V1.md",
          "native/sqlite_runtime/outcome_capacity.cpp",
          "src/ceta/composition/ipc_service.py",
          "src/ceta/composition/native_cpu_outcome.py",
          "src/ceta/composition/native_cpu_runtime.py",
          "src/ceta/composition/service_process.py",
          "src/ceta/effects/native_observer.py",
          "src/ceta/identity/cpu_outcome_capacity.py",
          "src/ceta/identity/native_cpu_outcome.py",
          "src/ceta/identity/native_owner_view.py",
          "src/ceta/identity/owner_session.py",
          "src/ceta/kernel/cpu_execution.py",
          "src/ceta/kernel/cpu_outcome_recovery.py",
          "src/ceta/kernel/effect_transactions.py",
          "src/ceta/store/journal.py",
          "src/ceta/store/outcome_capacity.py",
          "tests/contract/test_cpu_capacity_connection.py",
          "tests/contract/test_cpu_execution_admission.py",
          "tests/contract/test_cpu_outcome_recovery.py",
          "tests/contract/test_cpu_recovery_registration.py",
          "tests/contract/test_native_cpu_outcome_provenance.py",
          "tests/contract/test_native_observer_origin.py",
          "tests/contract/test_native_owner_execution.py",
          "tests/contract/test_native_owner_preparation.py",
          "tests/contract/test_native_runtime_composition.py",
          "tests/contract/test_outcome_capacity.py",
          ".local-test-output/**"
        ]
      },
      "destination_evidence": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [
          ".agents/runtime/js9-runtime-20261020/successor-r3/**"
        ]
      },
      "destination_fixtures": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [
          ".agents/fixtures/**"
        ]
      }
    },
    "edges": [
      {
        "id": "discover_plan",
        "from": "discover",
        "to": "plan",
        "type": "depends_on"
      },
      {
        "id": "plan_implement",
        "from": "plan",
        "to": "implement",
        "type": "delegates_to"
      },
      {
        "id": "plan_candidate_fixtures",
        "from": "plan",
        "to": "candidate_fixtures",
        "type": "delegates_to"
      },
      {
        "id": "plan_candidate_cache",
        "from": "plan",
        "to": "candidate_cache",
        "type": "delegates_to"
      },
      {
        "id": "implement_review",
        "from": "implement",
        "to": "review",
        "type": "requires_review"
      },
      {
        "id": "candidate_fixtures_review",
        "from": "candidate_fixtures",
        "to": "review",
        "type": "requires_review"
      },
      {
        "id": "candidate_cache_review",
        "from": "candidate_cache",
        "to": "review",
        "type": "requires_review"
      },
      {
        "id": "review_validate",
        "from": "review",
        "to": "validate",
        "type": "authorizes"
      },
      {
        "id": "validate_integrate",
        "from": "validate",
        "to": "integrate",
        "type": "gates"
      },
      {
        "id": "validate_destination_evidence",
        "from": "validate",
        "to": "destination_evidence",
        "type": "depends_on"
      },
      {
        "id": "validate_destination_fixtures",
        "from": "validate",
        "to": "destination_fixtures",
        "type": "depends_on"
      }
    ]
  }
}
```
