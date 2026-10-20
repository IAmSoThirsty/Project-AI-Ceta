# Error semantics contract

WP-01 contract increment for REQ-04-03 and REQ-20-01/04. Profile:
`ceta-error-semantics-v1`. Existing ErrorEnvelope schema version 1 is unchanged.
The supplied twenty error definitions remain the initial registered catalog.

ErrorCatalog injects and freezes 1–256 unique bounded definitions. Unknown
categories, malformed guidance, duplicate codes and a false completion guard
reject. The composition owner must authenticate the catalog and bind its source
identity; constructing one is not source adoption. Canonical internal metadata
sorts definitions by code and includes an explicit type, version and profile.
The commitment hashes ASCII `CETA:error-catalog:ceta-error-semantics-v1`, one zero
byte and canonical metadata. It is not a public wire record, event head or permit.

ErrorContract uses the existing strict decoder and requires the exact expected
scope, task and operation from authenticated request/state resolution. Nullable
task/operation IDs remain unavailable and must match the expected null. Affected
resource scopes must match. A null diagnostic revision remains unknown; it is
not an absence proof, a usable read set or authority to create/overwrite a file.
Original record bytes, all fields and canonical commitment remain intact.

The catalog category, recoverability and effect status have distinct meanings.
UNKNOWN and MAY_HAVE_EXECUTED require RECONCILE. Any possible or observed effect
forbids RETRY_WITH_NEW_AUTHORITY on that unresolved error; reconciliation and new
preparation/admission are separate future kernel actions. OBSERVED_EFFECT is
not verified success. It still requires effect reconciliation/settlement even
when the remaining error calls for a decision, resource or permanent refusal.
EFFECT_INDETERMINATE, PERMIT_CONSUMED and STOP_PENDING require RECONCILE, including
when the attempted repeated operation has NOT_STARTED. EFFECT_INDETERMINATE
cannot assert NOT_STARTED. These are conservative report predicates derived
from the catalog guidance and semantic transaction/effect requirements.

The validator neither infers nor rewrites effect state from an exception, code,
timeout, exit value or explanation. Runtime owners must supply actual evidence;
forged schema-valid reports remain untrusted. Retry-policy and diagnostic refs
are retained references and confer no permission. Ref resolution, diagnostic
access/redaction, owned process termination, spend accounting, independent
readback, settlement and compensation must be enforced by the future owning
use cases. No dispatch, refund, automatic retry or success transition exists in
this pure contract.

Current tests use synthetic fixtures, exercise all twenty supplied definitions,
and probe shape/context/effect combinations, immutability and identity changes.
They do not execute B016/B031/B064 or the required real store/broker/supervisor
failure scenarios. Gate A and full runtime qualification remain open.
