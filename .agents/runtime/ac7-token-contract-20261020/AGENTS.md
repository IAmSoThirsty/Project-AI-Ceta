# Bounded AC7 token-contract repair

Code and controlled tests only; no host profile or native execution is authorized by this lease.

```agents-graph
{
  "version": 1,
  "graph": {
    "id": "ceta_ac7_token_contract20",
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
          ".agents/ac7-token-contract-20261020/**",
          ".agents/runtime/ac7-token-contract-20261020/**"
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
          ".agents/ac7-token-contract-20261020/**",
          ".agents/runtime/ac7-token-contract-20261020/**"
        ]
      }
    },
    "edges": [
      {
        "id": "d_p",
        "from": "discover",
        "to": "plan",
        "type": "depends_on"
      },
      {
        "id": "p_i",
        "from": "plan",
        "to": "implement",
        "type": "delegates_to"
      },
      {
        "id": "i_r",
        "from": "implement",
        "to": "review",
        "type": "requires_review"
      },
      {
        "id": "r_v",
        "from": "review",
        "to": "validate",
        "type": "authorizes"
      },
      {
        "id": "v_i",
        "from": "validate",
        "to": "integrate",
        "type": "gates"
      }
    ]
  }
}
```
