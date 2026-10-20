# Blocker and incident register (Subsystem 01 remediation pass)

| ID | Type | Reason | Unblock condition | Blocks |
|---|---|---|---|---|
| B-01 | Blocker | Owner-approved local CETA application source is not in the authorized root, so existing code cannot be mapped or reused. | Owner provides approved local source, or confirms greenfield build. | All subsystems; reuse mapping |
| B-02 | Blocker | Session project_dir names a different directory (Build_Package) than the authorized root. | Owner confirms project path T:/00-Active/CETA-NATIVE-ARCHITECTURE. | Session routing |
| B-03 | Blocker | Constitutional rule text is absent. Subsystem 01 loads only a labelled TEST FIXTURE (tests/fixtures/governance/test-rule-set.json), which is not constitutional text. | Owner provides approved constitutional sources and version; they are then hash-pinned and loaded through load_rule_set. | Governed production decisions; subsystem 01 acceptance on real rules |
| B-04 | Blocker | Signature and crypto profile is unpinned. approve_transition returns signature_profile_unpinned when no verifier is injected, and only verifier-approved packets count toward quorum. | Owner pins the signature profile through a decision. | Production quorum approvals; subsystems 02, 04, 09 |
| B-05 | Blocker | Native OS enforcement is unqualified on the Windows host. Subsystem 01 makes no enforcement claim. | Qualify enforcement on the target Windows host. | Subsystems 11, 18 |
| B-07 | Blocker | Owner authorization is required for network egress, paid compute, publishing, signing, and host configuration changes. | Explicit owner approval. | Release work |
| B-08 | Blocker | Desktop framework and accessibility target are unspecified. This also covers the planner item previously numbered B-06. | Owner decision. | Subsystem 22 |
| B-09 | Blocker | Approval single-use consumption (Registry._consumed) is memory-only, so replay across a process restart is not prevented. | Subsystem 19 durable store is built and integrated with Registry consumption. | Durable replay protection in subsystem 01; subsystem 19 integration |
| I-01 | Incident | Prior-turn files evidence/architecture-recovery/STATUS-MATRIX.md and BLOCKER-AND-AUTHORIZATION-REGISTER.md are absent from the authorized root. | Re-create from authorized-root sources, or accept as lost. | Audit trail only |
| I-02 | Incident | Some earlier write_file calls may have written outside the authorized root. Not inspected, per the scope rule. | Owner decision on whether stray files should be removed. | Audit trail only |
| I-03 | Resolved | An earlier baseline check reported 1 mismatch from a broken inline script. The PowerShell re-check reported 1475 of 1475 matched. | None | Closed |
| I-04 | Incident (tooling, not a product blocker) | write_file reports success but does not persist under the authorized root (probe file evidence/subsystem-01/write-channel-probe.txt is absent). Former B-06 is recorded here. Writes use run_command python pathlib with a verification read after each write. | Not a product blocker; keep the verified write channel. | Evidence writing only |
