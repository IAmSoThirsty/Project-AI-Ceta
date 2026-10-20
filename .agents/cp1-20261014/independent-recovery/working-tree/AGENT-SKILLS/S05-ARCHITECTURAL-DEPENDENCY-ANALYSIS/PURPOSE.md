# S05 purpose

Use this construction skill to produce: **Typed build, runtime, data, and optional dependency maps with affected-owner and test impact.**

The required input is: Subsystem graph, local module graph, shared contracts, and a proposed change set.

The skill's distinguishing procedure is: Classify each edge; detect build cycles; identify runtime cycles that require ports; compute affected consumers; validate bootstrap and shutdown order; keep optional features from entering the required local path.

Success is measured by this oracle: **The construction graph is acyclic and every affected contract consumer is accounted for.** The specifically adverse condition is: **A runtime message loop is incorrectly treated as a mandatory build-order cycle.** Preserve this distinction in planning, implementation, testing, and reporting. The skill does not expand the assigned task's scope, change constitutional rules, or grant execution authority.
