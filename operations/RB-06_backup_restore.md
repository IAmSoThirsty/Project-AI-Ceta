# Take and restore a consistent backup

**Document ID:** RB-06  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Prerequisites

Identify the exact store library, data directory, writer ownership and approved backup target. Ensure enough space for the complete consistency unit and record source identity.

## Procedure

Use the selected consistent backup API or quiesced snapshot procedure, retaining required keys/metadata only under their protection policy. Verify snapshot integrity and category counts. Test restoration into an isolated location with a matching compatible executable. Treat restoration as a new security/runtime epoch where policy requires it.

## Required observed result

Interrupted backups never become accepted checkpoints. Restore does not reactivate expired grants or inherit hardware/model readiness.

## Fault and escalation route

When required evidence, hardware, permission or runtime is unavailable, preserve the current state and enter the affected operation's explicit blocked/recovery state. Record the exact error, scope and minimum intervention. Do not retry non-idempotent effects blindly, reset profiles, rewrite old results or weaken the operating profile. Continue unrelated safe work where permitted.

## Records and implementation link

Implementing work package: WP-02. The installed product must expose real controls or qualified commands for this procedure. This document defines those behaviours; it does not pretend a future CLI already exists. Record exact commands, actor/session, source/config, before/after observations, result, retained uncertainty and evidence paths when executing it.
