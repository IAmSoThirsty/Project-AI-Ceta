# Grant, inspect and revoke continuing work

**Document ID:** RB-02  
**Package edition:** 1.0 / 2026-10-06  
**Document state:** WRITTEN_IMPLEMENTATION_SPECIFICATION  
**Implementation and runtime evidence:** NOT_STARTED / NOT_RUN in this delivered package.

## Prerequisites

Have an authenticated owner interaction and an identified project. Define exactly which observations, preparations or effects are requested and the finite time/resource budget.

## Procedure

Create a standing grant through the trusted approval surface. Display watched resources, permitted operations, expiry and remaining limits. Observe its actual subscriptions and notifications. Revoke it while queued or active work exists, then confirm no new dependent admission succeeds and unresolved effects remain accurately recorded.

## Required observed result

Current grant state and task context remain inspectable. Renewal is explicit and cannot revive old consumed permits or stale reviewed candidates.

## Fault and escalation route

When required evidence, hardware, permission or runtime is unavailable, preserve the current state and enter the affected operation's explicit blocked/recovery state. Record the exact error, scope and minimum intervention. Do not retry non-idempotent effects blindly, reset profiles, rewrite old results or weaken the operating profile. Continue unrelated safe work where permitted.

## Records and implementation link

Implementing work package: WP-05. The installed product must expose real controls or qualified commands for this procedure. This document defines those behaviours; it does not pretend a future CLI already exists. Record exact commands, actor/session, source/config, before/after observations, result, retained uncertainty and evidence paths when executing it.
