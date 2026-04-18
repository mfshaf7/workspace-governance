# Session Handoff 2026-04-19

This record preserves the important workspace-level context from the current
discussion so a new session can resume without depending on chat memory.

## Current Durable State

These are already real, merged, and governed:

- `dev-integration` exists as the default fast local iteration lane when an
  active profile is available.
- `idea-workflow` exists as the first active `dev-integration` profile.
- `dev-integration` profile lifecycle and admission now exist:
  - `proposed`
  - `active`
  - `suspended`
  - `retired`
- operator-facing workflow doctrine now requires one clear primary operator
  instruction surface in the owning repo.
- the self-improvement system now has:
  - machine-visible signal audit
  - improvement candidates
  - after-action closure
- the workspace instruction system now has stronger skills and a live-skill
  sync control that validates the installed skill tree under `~/.codex/skills`.

## Current Skills And Controls

Current registered workspace skill set includes:

- `workspace-change-router`
- `architecture-discussion-gate`
- `contract-drift-check`
- `dev-integration-first`
- `done-criteria-enforcer`
- `operator-workflow-design`
- `cross-repo-sequencer`
- `self-improvement-review`

The local workspace audit now checks that the live installed skills match the
governed skill source and registry.

## Pending Follow-Ups

These were discussed and intentionally left for later work.

### 1. Telegram `/idea` Workflow Follow-Ups

Deferred feature ideas for the broker-backed Telegram surface:

- accept shorthand record ids such as `/idea show 41` in addition to
  `/idea show idea-41`
- support status-filtered list surfaces such as:
  - `/idea list status <status>`
  - `/idea list all status <status>`

These belong primarily to:

- `openclaw-telegram-enhanced/`
- `operator-orchestration-service/`

### 2. Dev-Integration Productization

Current state is strong enough to use now, but not yet fully productized.

Still deferred:

- a friendlier catalog or launch surface for approved profiles
- a richer request surface than the current generic admission model plus
  current adapter

Current design choice remains:

- request a new profile when none fits
- self-serve sessions from approved `active` profiles

### 3. Self-Improvement Detection Beyond Doctrine

Current state is much better, but still hybrid:

- machine-visible signals are audited
- conversation-visible signals still rely on agent discipline plus doctrine

A possible future improvement is stronger automatic candidate creation or a
more explicit signal queue for conversation-visible misses.

## Resume Guidance

If the next session needs to resume quickly:

1. treat this file as the chat-context handoff
2. trust the merged contracts, skills, and runbooks as the real system state
3. start from the highest-priority pending item above instead of re-deriving
   the whole architecture

## Suggested Next Discussion Order

1. decide whether to take the `/idea` follow-ups now or leave them parked
2. decide how far to productize `dev-integration`
3. decide whether the self-improvement system needs another step beyond the
   current candidate-plus-audit model
