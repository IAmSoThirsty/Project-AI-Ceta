# S17 purpose

Use this construction skill to produce: **Reproducible interruption evidence and validated safe resume, compensation, or uncertainty handling.**

The required input is: State and effect boundaries, controlled test environment, recovery rules, and fault-injection points.

The skill's distinguishing procedure is: Inject faults before and after intent, dispatch, effect, commit, and publication; restart; inspect actual resources; revalidate authority; reconcile unknowns; verify no blind replay or lost user data.

Success is measured by this oracle: **Every fault point yields the documented durable state and preserves already committed effects.** The specifically adverse condition is: **A timeout is assumed to prove no external action occurred.** Preserve this distinction in planning, implementation, testing, and reporting. The skill does not expand the assigned task's scope, change constitutional rules, or grant execution authority.
