---
name: workspace-change-router
description: Use when a request is made at the workspace level without a repo specified and Codex must classify the task, route it to the owning repo, and choose the highest real workflow maturity that exists.
---

# Workspace Change Router

Use this skill when the user asks for a feature, fix, or review from the
workspace root and does not name the owning repo.

## Read First

- `workspace-root/ARCHITECTURE.md`
- `contracts/repos.yaml`
- `contracts/products.yaml`
- `contracts/components.yaml`
- `contracts/task-types.yaml`
- `contracts/work-home-routing.yaml`
- `docs/work-home-routing-contract.md`
- `workspace-root/AGENTS.md`

## Workflow

1. Classify the task by control plane:
   - workspace governance
   - shared platform
   - product runtime composition
   - Telegram behavior
   - host enforcement
   - security governance
2. Classify the work-tracking home before execution:
   - use `docs/work-home-routing-contract.md`
   - route accepted initiative work, blockers, risks, scope changes, and
     completion truth to `Workspace Delivery ART`
   - route owner-repo-only maintenance to the owner repo when it is outside
     accepted initiative work
   - route new business or architecture ideas to `Workspace Proposals` before
     decomposition
   - route repeated workflow misses to improvement candidates
   - classify plumbing by impact, not by name
   - route AGENTS, registered skill source, installed skill behavior, and
     workspace instruction governance changes to `workspace-governance` unless
     the machine-readable skill owner says a repo-owned skill source is the
     implementation home
   - for source-backed work, choose the Landing Unit separately from the ART
     item; ART decomposition, Git branches, and completion evidence are not
     one-to-one
   - close source-backed ART items only after a finalized Review Packet maps
     landed or explicitly accepted evidence to those items
3. If the request depends on fresh workspace-level truth, run
   `python3 scripts/check_remote_alignment.py --workspace-root /home/mfshaf7/projects --repo-name workspace-governance --refresh-remote`
   before relying on the local control-plane docs.
4. Before proposing a new control, workflow, validator, skill, product surface,
   or architecture capability, run `docs/recommendation-preflight.md` and state
   whether the posture is `reuse`, `extend`, `replace`, or `new`.
   - if the request is about AGENTS or skills, use
     `docs/instruction-and-skill-governance.md` and the
     `instruction-governance-auditor` workflow before editing source
5. Pick the owner repo from the contracts, not from convenience.
6. Check whether the task already has an `active` `dev-integration` profile and
   prefer that lane for fast workflow or API iteration before stage.
7. Check the product maturity before implying stage or prod flow.
   - if the request is a rehearsal, rollout drill, temporary prod bring-up, or
     restore-to-baseline exercise, classify the drill before implying scope:
     - `product-runtime-drill` when one governed product lane is under test
     - `active-stack-runtime-drill` when the current operator-critical
       mixed-lane stack must come up together and then return to the captured
       baseline
     - `environment-complete-runtime-drill` only when every admitted lane and
       product environment in scope is actually exercised
     - `lifecycle-control-drill` when the goal is to exercise lifecycle state
       controls rather than a full runtime bring-up
   - route those drill shapes to `platform-engineering` and the corresponding
     platform runbook or contract
   - do not default a broad stage/prod/restore request to OpenClaw-only just
     because OpenClaw has the most mature governed product promotion path
8. Route to the owner repo's `AGENTS.md` and `README.md`.
9. If the request changes more than one control plane, name the primary owner
   and the required secondary updates.
10. If the request spans multiple repos and one repo's validation or remote
   `main` state will gate another, use `cross-repo-sequencer`.
11. If the task is changing an operator-facing command family, request path,
   approval path, or status/help surface, use `operator-workflow-design`.

## Guardrails

- Do not route active work to retired repos.
- Do not skip an active `dev-integration` lane and jump straight to stage when
  the work is still in fast iteration.
- Do not invent a governed promotion path for products that do not have one.
- Do not treat a broad platform rehearsal as an OpenClaw-only workflow just
  because OpenClaw currently has the deepest governed product path.
- Do not hide meaningful accepted work in owner-repo maintenance just because
  it is plumbing.
- Do not propose a brand-new control surface before checking the existing skill
  inventory, repo-rule primary surfaces, dev-integration profile docs, and
  architecture/routing contracts.
- If the task introduces a new product, shared component, or control plane,
  stop and use the architecture discussion gate first.
