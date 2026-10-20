# S08 purpose

Use this construction skill to produce: **A validated state machine with atomic transitions, causal records, and terminal-state rules.**

The required input is: Canonical state owner, transition contract, expected versions, and lifecycle requirements.

The skill's distinguishing procedure is: Enumerate legal states; define guards and effects; use expected-version updates; record transition causes; define cancellation and uncertainty; replay committed history to verify consistency.

Success is measured by this oracle: **Conflicting updates cannot both commit and terminal states cannot be bypassed.** The specifically adverse condition is: **A restarted worker overwrites a newer stop or revocation state.** Preserve this distinction in planning, implementation, testing, and reporting. The skill does not expand the assigned task's scope, change constitutional rules, or grant execution authority.
