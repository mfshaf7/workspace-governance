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
- security review is referenced when identity, secrets, delivery, runtime, or
  AI controls changed
- live evidence exists when the change affected governed runtime state

If any of those are missing, say the work is not complete yet.
