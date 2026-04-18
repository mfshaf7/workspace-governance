---
name: operator-workflow-design
description: Use when creating or changing an operator-facing workflow, command family, request path, approval path, or status/help/list/show surface so the operator experience is designed correctly from the start.
---

# Operator Workflow Design

Use this skill when the work affects what an operator sees, types, approves, or
reads as part of a workflow.

## Read First

- `workspace-root/AGENTS.md`
- `contracts/README.md`
- the owning repo `AGENTS.md`
- the owning repo's current primary operator instruction surface, if it exists

## Workflow

1. Identify the workflow owner, the adapter surface, and the canonical system
   of record.
2. Decide which semantics belong to the core workflow and which belong only to
   the adapter.
3. Define the minimum operator surfaces explicitly:
   - help or guidance
   - create or request action
   - inspect or show action
   - list or status action when multiple records exist
4. Make status visibility explicit from the start. Do not hide lifecycle or
   leave the operator guessing what can happen next.
5. Ensure there is one primary operator instruction surface in the owning repo.
6. Keep supporting contracts, templates, and standards secondary to that
   primary operator surface.
7. Make cross-repo links renderer-safe unless the doc is intentionally the
   local `workspace-root/` surface.

## Guardrails

- Do not let the adapter own the workflow meaning when the workflow should be
  source-agnostic.
- Do not call the workflow complete if the operator still has to reconstruct it
  from scattered files.
- Do not add `help` or `status` behavior as an afterthought if the operator
  needs it to use the workflow safely.
