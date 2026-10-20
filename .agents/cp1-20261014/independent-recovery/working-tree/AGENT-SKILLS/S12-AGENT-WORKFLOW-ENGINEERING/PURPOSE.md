# S12 purpose

Use this construction skill to produce: **Bounded multi-agent execution with fenced ownership, durable handoffs, and separate review.**

The required input is: Task graph, agent roles, skill manifests, resource limits, authority scope, and handoff contracts.

The skill's distinguishing procedure is: Decompose outputs; pin roles and skills; acquire write leases; persist assignments; validate messages and handoffs; reconcile worker loss; require evidence-backed finalization.

Success is measured by this oracle: **Duplicate deliveries and stale workers cannot produce conflicting canonical effects.** The specifically adverse condition is: **A producer agent self-certifies its deliverable as independently verified.** Preserve this distinction in planning, implementation, testing, and reporting. The skill does not expand the assigned task's scope, change constitutional rules, or grant execution authority.
