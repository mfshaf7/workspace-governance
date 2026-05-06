---
name: done-criteria-enforcer
description: Use when deciding whether work is actually complete, especially for cross-repo, production-impacting, or architecture-relevant changes that require evidence, review, or follow-up artifacts.
---

# Done Criteria Enforcer

Use this skill before closing work that changed architecture, delivery, runtime,
or live governed state.

## Read First

- `contracts/change-classes.yaml`
- `contracts/evidence-obligations.yaml`
- `contracts/review-obligations.yaml`
- `contracts/products.yaml`
- `docs/instruction-and-skill-governance.md`

## Workflow

1. Identify the real change class.
2. Check the product or repo workflow maturity.
3. List the minimum evidence that should exist.
4. If you are about to recommend a restart or session close, run the restart-readiness gate first.
5. Call out what is still missing instead of implying completion.

## Restart-Readiness Gate

Before telling the operator that a restart is safe or recommended:

- check for meaningful workspace-level local-only state that would be lost or harder to rediscover after a restart
- treat pending architecture/workflow discussion, local-only review or handoff notes, and unlanded workspace-level state as handoff-worthy by default
- if that state exists, create or refresh the single local-only `docs/archive/session-handoff-current.md` record first
- keep zero or one session handoff at a time; remove stale `docs/archive/session-handoff-*.md` records instead of accumulating dated files
- only after the handoff is current should you say the restart is ready
- if the workspace is being described as clean or restart-ready, the WGCF
  clean-state scope must pass so branch lifecycle, repo structure, and
  workspace layout are checked through the current catalog path
- do not wait for the operator to ask whether a handoff is needed

## Minimum Checks

- owner repo change exists
- validation ran at the owning layer
- docs changed when behavior or ownership changed
- one primary operator instruction surface exists when operator workflow shape changed
- operator-facing docs use the correct renderer-safe link model for their audience
- cross-repo dependency order is accounted for when one repo's validation depends on another repo landing first
- if the work is meant to land in Git, a Landing Unit exists with a repo branch
  and meaningful PR summary unless the user explicitly approved direct landing
  or the repo's documented workflow says otherwise
- if source-backed ART items are being closed, a finalized Review Packet maps
  the landed source evidence to each covered item
- if non-source ART items are being closed, the completion evidence explicitly
  states the non-source proof instead of inventing merge evidence
- if a Feature or Epic is being closed, every child is covered by a finalized
  Review Packet or explicitly marked as non-source evidence only
- if repo review controls exist and the work is landing through a PR, Codex review was requested or explicitly waived and the PR records the result
- skills are reinstalled and live-skill sync is verified when skill source or registry changed
- instruction-and-skill governance validation is complete when AGENTS, skill
  source, skill registry, or installed skill behavior changed
- if the user is being asked to restart and meaningful workspace-level pending items remain, `docs/archive/session-handoff-current.md` exists and is current
- if a restart is being recommended, the session handoff was refreshed before the recommendation rather than only after the operator asked about it
- if the work was proven in `dev-integration`, the active profile's
  `stage_handoff.required_checks` and `devint-promote-check` still match the
  landed workflow surface before calling the handoff ready
- if the work is being described as closed after `dev-integration`, the
  documented handoff path is complete too; source landing alone is not closure
  when governed `stage` rehearsal is still required
- security review is referenced when identity, secrets, delivery, runtime, or
  AI controls changed
- live evidence exists when the change affected governed runtime state

If any of those are missing, say the work is not complete yet.
