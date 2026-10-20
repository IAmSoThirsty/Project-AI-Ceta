# Failure and recovery map

| Failure class | Immediate response | Recovery owner | Required proof before continuation |
| --- | --- | --- | --- |
| Invalid schema or unsupported version | Reject before privileged work | Contract producer and consumer | Corrected compatible input and conformance test |
| Expired or revoked authority | Close affected admission | Identity and authority | Fresh scoped decision and current revocation check |
| Changed target or source | Preserve both versions; block stale write | Owning component and integration | Inspected current identity and renewed proposal |
| Worker or model process loss | Stop descendants where owned; record last observation | Workflow and execution | Process identity, cleanup, checkpoint, and effect reconciliation |
| Unknown external result | Persist uncertainty; prohibit blind retry | Execution and state recovery | Actual target state or authoritative receipt |
| Disk or memory pressure | Preserve control reserve; throttle or stop work | Resource management | Measured safe capacity and durable outcome records |
| Corrupt canonical data | Restrict affected service; preserve evidence | State and recovery | Verified restoration and known-security-state reconciliation |
| Evidence gap or invalid signature | Block unsupported completion claims | Evidence and provenance | Correct binding, trusted verification, or explicit unresolved gap |
| Extension boundary failure | Revoke and isolate affected extension | Security and extension lifecycle | Containment, repaired qualification, independent review |
| Update or migration interruption | Keep mixed versions inactive; restore or resume safely | State and release | Consistent schema, preserved user data, installed-runtime checks |

Safe recovery preserves identity, conversations, drafts, exact source, known revocations, deletion decisions, and uncertain effects. A repair is not successful merely because errors disappeared from the interface. Reproduce the original failing condition and verify the corrected behavior before reopening the affected path.
