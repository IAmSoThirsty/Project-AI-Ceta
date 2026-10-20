# End-to-end qualification scenarios

Twenty concrete scenarios exercise complete native workflows and adverse conditions. Each identifies participating subsystems, preconditions, action sequence, expected observations, fault variants, required evidence, and cleanup. All initial application execution states are NOT EXECUTED.

| Scenario | Required outcome |
| --- | --- |
| [E2E-01-OWNER-SETUP-AND-LOCAL-STARTUP](E2E-01-OWNER-SETUP-AND-LOCAL-STARTUP.md) | Only the verified owner obtains the configured authority; local data, identity, and setup state persist; no general effects occur before prerequisites are ready. |
| [E2E-02-OFFLINE-COMPANION-MEMORY-CONTEXT](E2E-02-OFFLINE-COMPANION-MEMORY-CONTEXT.md) | The exact decision and source attribution survive restart; local inference works; context preserves explicit constraints and labels inferred content. |
| [E2E-03-GOVERNED-LOCAL-ENGINEERING-CHANGE](E2E-03-GOVERNED-LOCAL-ENGINEERING-CHANGE.md) | Only approved files and effects change; existing owner edits are preserved; source, tests, artifacts, and evidence identify the same revision. |
| [E2E-04-BOUNDED-MULTIAGENT-HANDOFF](E2E-04-BOUNDED-MULTIAGENT-HANDOFF.md) | Assignments remain bounded; handoffs preserve remaining obligations and uncertainty; no two active writers own the same canonical file. |
| [E2E-05-STOP-AND-REVOCATION-RACE](E2E-05-STOP-AND-REVOCATION-RACE.md) | No new unauthorized effect starts after the effective boundary; owned workers stop or are explicitly reported residual; committed and uncertain effects remain distinct. |
| [E2E-06-CRASH-AFTER-POSSIBLE-EFFECT](E2E-06-CRASH-AFTER-POSSIBLE-EFFECT.md) | The operation remains uncertain until evidence resolves it; an already committed effect is not blindly repeated; fresh authority is required for new effects. |
| [E2E-07-MEMORY-CORRECTION-DELETION-PORTABILITY](E2E-07-MEMORY-CORRECTION-DELETION-PORTABILITY.md) | Corrections preserve exact history; export scope is exact; deletion invalidates active derived retrieval and later restoration reconciles known deletion markers. |
| [E2E-08-SKILL-LEARNING-AND-REVOCATION](E2E-08-SKILL-LEARNING-AND-REVOCATION.md) | Candidate content cannot execute before qualification and approval; active runs pin revisions; revocation blocks new invocations. |
| [E2E-09-SCHEDULE-DOWNTIME-AND-AUTHORITY-RENEWAL](E2E-09-SCHEDULE-DOWNTIME-AND-AUTHORITY-RENEWAL.md) | Occurrence identities prevent duplicates; catch-up obeys the approved bound; expired grants pause effects; schedule delivery is distinct from task completion. |
| [E2E-10-SOURCE-TO-CLAIM-RESEARCH](E2E-10-SOURCE-TO-CLAIM-RESEARCH.md) | Every material claim has relevant exact support; repeated copies are not independent evidence; contradictions and date uncertainty remain visible. |
| [E2E-11-MODEL-LIFECYCLE-AND-PRIVATE-FALLBACK](E2E-11-MODEL-LIFECYCLE-AND-PRIVATE-FALLBACK.md) | Private data stays local without explicit export authority; capabilities and resource limits are measured; process loss does not leave stale ready state. |
| [E2E-12-VOICE-MEDIA-AND-EXACT-DECISIONS](E2E-12-VOICE-MEDIA-AND-EXACT-DECISIONS.md) | Unclear recognition does not trigger destructive action; media observations retain source regions; playback and command state remain separate. |
| [E2E-13-PROTECTED-SECRETS-AND-ROTATION](E2E-13-PROTECTED-SECRETS-AND-ROTATION.md) | Secret values do not appear in model context or ordinary logs; only the intended destination receives access; stale leases are invalidated. |
| [E2E-14-OPTIONAL-EXTENSION-ISOLATION](E2E-14-OPTIONAL-EXTENSION-ISOLATION.md) | Installation does not grant ambient authority; code and manifest identity remain bound; revoked exports cannot start new work; local core operation does not depend on the extension. |
| [E2E-15-BACKUP-RESTORE-AND-USER-DATA](E2E-15-BACKUP-RESTORE-AND-USER-DATA.md) | User data is preserved as declared; integrity and restoreability are separately verified; later known security decisions remain effective. |
| [E2E-16-SCHEMA-MIGRATION-AND-REVERSAL](E2E-16-SCHEMA-MIGRATION-AND-REVERSAL.md) | No mixed incompatible schema is exposed; data and authority history survive; reversal limits are explicit and tested. |
| [E2E-17-UPDATE-ROLLBACK-AND-ARTIFACT-BINDING](E2E-17-UPDATE-ROLLBACK-AND-ARTIFACT-BINDING.md) | Installed bytes match the reviewed candidate; source-to-package evidence is intact; rollback preserves user data and known revocations. |
| [E2E-18-ADVERSARIAL-BOUNDARY-COVERAGE](E2E-18-ADVERSARIAL-BOUNDARY-COVERAGE.md) | Every denied request is blocked at the native boundary with observable evidence; alternate UI, terminal, maintenance, retry, and recovery paths enforce the same controls. |
| [E2E-19-RESOURCE-PRESSURE-AND-RESPONSIVENESS](E2E-19-RESOURCE-PRESSURE-AND-RESPONSIVENESS.md) | Admission reservations prevent oversubscription; stop and evidence remain usable; degradation preserves governance; usage is not double-counted. |
| [E2E-20-COMPLETE-INSTALLED-PRODUCT](E2E-20-COMPLETE-INSTALLED-PRODUCT.md) | Every approved mandatory workflow works in the actual delivered application and is bound to the tested source and package; no unfinished requirement is silently removed. |
