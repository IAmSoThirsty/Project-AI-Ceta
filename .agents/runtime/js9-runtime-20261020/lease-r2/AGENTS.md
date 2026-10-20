# Bounded JS9 lease fragment

Override only the candidate write scope and add a disjoint evidence writer. Existing review and validation gates are inherited unchanged.

```agents-graph
{
  "version": 1,
  "graph": {
    "id": "ceta_js9_private_runtime_construction",
    "override_nodes": {
      "implement": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [
          ".agents/js9-runtime-20261020/**"
        ]
      }
    },
    "nodes": {
      "evidence": {
        "kind": "agent",
        "role": "worker",
        "access": "write_scoped",
        "write_scope": [
          ".agents/runtime/js9-runtime-20261020/**"
        ]
      }
    },
    "edges": [
      {
        "id": "plan_evidence",
        "from": "plan",
        "to": "evidence",
        "type": "delegates_to"
      },
      {
        "id": "evidence_review",
        "from": "evidence",
        "to": "review",
        "type": "requires_review"
      }
    ]
  }
}
```
