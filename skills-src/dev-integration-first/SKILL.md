---
name: dev-integration-first
description: Use when a workflow already has an active dev-integration profile or when fast local iteration should happen in dev-integration before governed stage rehearsal.
---

# Dev-Integration First

Use this skill when a task targets a workflow that already has a registered
`dev-integration` profile, or when the work is changing too quickly for stage
to be the right first lane.

## Read First

- `contracts/developer-integration-policy.yaml`
- `contracts/developer-integration-profiles.yaml`
- `platform-engineering/docs/runbooks/dev-integration-profiles.md`
- the owning repo profile README for the selected profile

## Workflow

1. Check whether a suitable profile already exists and is `active`.
2. If an active profile exists, prefer that lane before stage for:
   - operator-facing workflow iteration
   - cross-repo API iteration
   - canonical-backend write-path iteration
3. Choose the profile and record the source state that will feed it:
   - current branches
   - worktrees
   - dirty local state when allowed
4. Use the shared `devint-*` commands from `platform-engineering`.
5. Verify the session manifest captures both:
   - runtime shape from the profile
   - source state from the participating repos
6. Use stage only after the shape is already proven and the change has crossed
   back into reviewed commits plus governed promotion.
7. When a miss appears after local proof, classify it through
   `contracts/developer-integration-policy.yaml` `live_miss_escalation` before
   patching:
   - return to `dev-integration` when workflow shape, operator inputs, or
     backend write semantics are still changing and the profile can reproduce
     the issue
   - route to the platform or backend boundary when local proof already passed
     and the remaining failure is identity, networking, persistence, form
     writability, or platform projection behavior
   - continue governed rehearsal only when reviewed commits and handoff
     evidence exist and blocker, defect, or risk state has been recorded where
     needed
8. When a profile uses `runtime.state_model: persistent`, treat its shared
   `devint-smoke` action as read-only.
   - if a workflow still needs mutating smoke, look for or admit a separate
     disposable companion profile instead of pointing smoke at the persistent
     working lane

## Guardrails

- Do not route straight to stage when an active profile already exists for the
  same class of work.
- Do not keep patching inside a live/shared runtime after the first serious
  miss until the miss has been classified as profile-owned workflow work,
  platform/backend boundary work, or governed rehearsal work.
- Do not use `proposed`, `suspended`, or `retired` profiles as normal
  self-serve lanes.
- Do not treat a dev-integration session as stage evidence.
- Do not require push or PR for normal dev-integration iteration.
- Do not let shared smoke or test traffic write into a persistent devint
  working lane. Use a disposable companion profile for mutating smoke.
