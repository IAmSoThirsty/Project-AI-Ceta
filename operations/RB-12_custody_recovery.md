# Recover custody or replace authority domains

**Document ID:** RB-12  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Prerequisites

Keep ciphertext, key-lineage metadata, revocation and original domain evidence intact. Obtain the required real recovery quorum and new-platform evidence.

## Procedure

Follow the reviewed threshold/envelope recovery protocol. Rotate affected identity/share/session bindings without reconstructing the universal root in CETA. Confirm old authority is invalid under the declared assumptions, verify the new worker/recipient boundary and exercise authorized repeat reads of unchanged objects.

## Required observed result

Recovery preserves legitimate access without a hidden all-powerful master key. Missing domains or attestation block protected release rather than silently weakening the profile.

## Fault and escalation route

When required evidence, hardware, permission or runtime is unavailable, preserve the current state and enter the affected operation's explicit blocked/recovery state. Record the exact error, scope and minimum intervention. Do not retry non-idempotent effects blindly, reset profiles, rewrite old results or weaken the operating profile. Continue unrelated safe work where permitted.

## Records and implementation link

Implementing work package: WP-14. The installed product must expose real controls or qualified commands for this procedure. This document defines those behaviours; it does not pretend a future CLI already exists. Record exact commands, actor/session, source/config, before/after observations, result, retained uncertainty and evidence paths when executing it.
