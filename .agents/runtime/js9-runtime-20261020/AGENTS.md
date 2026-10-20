# Bounded JS9 private construction graph

Root assigned these two private directories only. Canonical Source, other candidates and native execution are outside this construction lease. Preserve the user halt checkpoint.

```agents-graph
{
  "version": 1,
  "graph": {
    "id": "ceta_js9_private_runtime_construction",
    "policy": {
      "fail_closed": true,
      "require_receipts": true,
      "prohibit_self_review": true,
      "prohibit_scope_overlap": true,
      "max_parallel": 4
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
          ".agents/js9-runtime-20261020/**",
          ".agents/runtime/js9-runtime-20261020/**"
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
          ".agents/js9-runtime-20261020/**",
          ".agents/runtime/js9-runtime-20261020/**"
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
        "id": "implement_review",
        "from": "implement",
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
      }
    ]
  }
}
```
