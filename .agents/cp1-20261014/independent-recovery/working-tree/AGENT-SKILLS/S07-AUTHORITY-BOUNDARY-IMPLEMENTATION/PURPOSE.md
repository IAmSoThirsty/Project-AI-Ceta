# S07 purpose

Use this construction skill to produce: **Use-time authorization checks with bounded delegation, replay protection, and revocation evidence.**

The required input is: Principal and capability contracts, trust policy, target resource model, and scoped effect requirements.

The skill's distinguishing procedure is: Bind actor, audience, proposal, inputs, target, expiry, and ancestry; validate current revocation; atomically consume single-use grants; recheck target identity at effect time; test concurrent and restored states.

Success is measured by this oracle: **A stale or revoked capability cannot authorize effects through any supported entry path.** The specifically adverse condition is: **A signature-valid token bypasses current revocation or target changes.** Preserve this distinction in planning, implementation, testing, and reporting. The skill does not expand the assigned task's scope, change constitutional rules, or grant execution authority.
