---
name: workspace-change-router
description: Use when a request is made at the workspace level without a repo specified and Codex must classify the task, route it to the owning repo, and choose the highest real workflow maturity that exists.
---

# Workspace Change Router

Use this skill when the user asks for a feature, fix, or review from the
workspace root and does not name the owning repo.

## Read First

- `contracts/repos.yaml`
- `contracts/products.yaml`
- `contracts/components.yaml`
- `contracts/task-types.yaml`
- `workspace-root/AGENTS.md`

## Workflow

1. Classify the task by control plane:
   - workspace governance
   - shared platform
   - product runtime composition
   - Telegram behavior
   - host enforcement
   - security governance
2. Pick the owner repo from the contracts, not from convenience.
3. Check whether the task already has an `active` `dev-integration` profile and
   prefer that lane for fast workflow or API iteration before stage.
4. Check the product maturity before implying stage or prod flow.
5. Route to the owner repo's `AGENTS.md` and `README.md`.
6. If the request changes more than one control plane, name the primary owner
   and the required secondary updates.
7. If the request spans multiple repos and one repo's validation or remote
   `main` state will gate another, use `cross-repo-sequencer`.
8. If the task is changing an operator-facing command family, request path,
   approval path, or status/help surface, use `operator-workflow-design`.

## Guardrails

- Do not route active work to retired repos.
- Do not skip an active `dev-integration` lane and jump straight to stage when
  the work is still in fast iteration.
- Do not invent a governed promotion path for products that do not have one.
- If the task introduces a new product, shared component, or control plane,
  stop and use the architecture discussion gate first.
