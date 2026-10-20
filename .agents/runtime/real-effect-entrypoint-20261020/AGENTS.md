# Private manual real-effect entrypoint implementation

Root authorized the existing real-effect plan's manual profile entrypoint and minimum composition wiring. Candidate writes are confined to `.agents/real-effect-entrypoint-20261020/**`. Source, Q5, D3, native artifacts and installed configuration remain read-only. No application, native, profile, authentication or effect execution is released. Pure controls may run in owned fixtures. A different named reviewer must review the exact frozen successor before integration.

```agents-graph
{
  "version": 1,
  "graph": {
    "id": "ceta_private_manual_real_effect_entrypoint",
    "policy": {"fail_closed": true, "require_receipts": true, "prohibit_self_review": true, "prohibit_scope_overlap": true, "max_parallel": 4},
    "nodes": {
      "discover": {"kind": "agent", "role": "explorer", "access": "read_only"},
      "plan": {"kind": "agent", "role": "architect", "access": "read_only"},
      "implement": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [".agents/real-effect-entrypoint-20261020/**"]
      },
      "review": {"kind": "agent", "role": "reviewer", "access": "read_only"},
      "validate": {"kind": "gate", "access": "read_only", "commands": ["git -C \"{workspace}\" diff --check"]},
      "integrate": {"kind": "integration", "role": "integrator", "access": "write_scoped", "write_scope": [".agents/real-effect-entrypoint-20261020/**"]},
      "evidence": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [".agents/runtime/real-effect-entrypoint-20261020/**"]
      }
    },
    "edges": [
      {"id": "discover_entrypoint_plan", "from": "discover", "to": "plan", "type": "depends_on"},
      {"id": "plan_entrypoint_implement", "from": "plan", "to": "implement", "type": "delegates_to"},
      {"id": "entrypoint_implement_review", "from": "implement", "to": "review", "type": "requires_review"},
      {"id": "plan_entrypoint_evidence", "from": "plan", "to": "evidence", "type": "delegates_to"},
      {"id": "entrypoint_evidence_review", "from": "evidence", "to": "review", "type": "requires_review"},
      {"id": "entrypoint_review_validate", "from": "review", "to": "validate", "type": "authorizes"},
      {"id": "entrypoint_validate_integrate", "from": "validate", "to": "integrate", "type": "gates"}
    ]
  }
}
```
