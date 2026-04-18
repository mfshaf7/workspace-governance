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

## Workflow

1. Identify the real change class.
2. Check the product or repo workflow maturity.
3. List the minimum evidence that should exist.
4. Call out what is still missing instead of implying completion.

## Minimum Checks

- owner repo change exists
- validation ran at the owning layer
- docs changed when behavior or ownership changed
- one primary operator instruction surface exists when operator workflow shape changed
- operator-facing docs use the correct renderer-safe link model for their audience
- cross-repo dependency order is accounted for when one repo's validation depends on another repo landing first
- if the work is meant to land in Git, a repo branch and meaningful PR summary exist unless the user explicitly asked for direct landing or the repo's documented workflow says otherwise
- skills are reinstalled and live-skill sync is verified when skill source or registry changed
- if the user is being asked to restart and meaningful workspace-level pending items remain, a session handoff record exists
- security review is referenced when identity, secrets, delivery, runtime, or
  AI controls changed
- live evidence exists when the change affected governed runtime state

If any of those are missing, say the work is not complete yet.
