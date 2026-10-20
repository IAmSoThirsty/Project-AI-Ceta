# Relevant-state contract

Engineering WP-01 increment; parent obligations REQ-07-05 and REQ-19-01/02/03.
Profile: `ceta-relevant-state-v1`, contract type `RelevantReadSet`, version `1`.
Code: src/ceta/contracts/read_sets.py. No permission issuer or store is introduced.

A ReadSet captures one logical scope, authority and fence generations, exact
policy/environment commitments and 1–4096 unique resource IDs with non-null
revision commitments. Generations are exact integers in 0..2^53-1. Null, mtime,
display name or caller confidence cannot stand in for a revision. Authenticated
resource absence needs an explicit registered representation and evidence; this
contract does not invent an absence hash or permit creation from null revision.

The kernel's admitted operation registry and trusted target resolution determine
the complete required-resource list. Captured dependencies must match that list
exactly. The current trusted state owner supplies actual current values. Checks
reject changed scope, authority/fence generation (including rollback), policy,
environment, missing current resource revision and changed relevant resource.
Unrelated current resources can change without invalidating preparation. There
is no dependency on the global journal head or telemetry counter. The accepted
prior event head remains a distinct append/causality binding.

Canonical metadata uses the existing ceta-json-integer-nfc-v1 bytes with resources
sorted by resource ID. SHA-256 identifies ASCII
`CETA:read-set:ceta-relevant-state-v1`, one zero byte and those canonical bytes.
This commitment binds preparation metadata and confers no authority. Comparing
whole current-snapshot commitments would accidentally invalidate unrelated work;
the predicate compares only the declared relevant dependencies and mandatory
authority/policy/environment basis.

The original twenty record schemas are unchanged. ActionProposal has resources
and dependencies; it does not have a supplied read_set field. RelevantReadSet is
internal typed metadata, rejected by the twenty-record dispatch. Future trusted
store composition must bind its versioned identity to exact preparation/issuance
evidence. The operation's complete input commitment must include all governed
inputs; it cannot be replaced by only this read-set hash. Any exposed RPC or new
event-payload encoding requires a coordinated contract/decoder amendment.

A worker cannot define the required dependencies or authenticate current state
by constructing one of these objects. Kernel admission must independently resolve
scope, resources, principal, task, grant, policy, reviews, consent, adapter,
arguments, candidate, deadline, budget and issuance/consume state. At the actual
irreversible boundary the broker must combine current revision validation with
protected resource handles and atomic consume/fencing. This pure check cannot
close the gap between an earlier read and a later write or undo a completed
effect. Revoke-before and revoke-after orderings remain real integration work.

The current tests use synthetic values. They demonstrate relevant/irrelevant
comparison, malformed/incomplete input denial, immutability and canonical
identity. They do not execute B060/B061/B062, produce effects, qualify physical
resource identity or establish authenticated IPC. Gate A remains open.
