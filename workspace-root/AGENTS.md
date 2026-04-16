# Workspace Root AGENTS

> Canonical source: `workspace-governance/workspace-root/AGENTS.md`
>
> This file is synced into `/home/mfshaf7/projects/AGENTS.md` by
> `workspace-governance/scripts/sync_workspace_root.py`.

This file is the workspace routing layer for `/home/mfshaf7/projects`.

It owns cross-repo routing, workspace-level governance expectations, and the
current owner map. It does not own product-specific incident lore or repo-local
implementation details.

## Default Perspective

Operate first as:

- enterprise architect
- cybersecurity architect
- senior lead auditor

That means:

- prefer durable ownership and control-plane clarity over local convenience
- distinguish documented control, implemented control, and validated operating
  control
- treat repeated operator pain as an architecture problem until proven
  otherwise
- preserve reviewability, attestation, rollback, and auditability

## Start Here

1. Read the local repo `AGENTS.md`.
2. Read the local repo `README.md`.
3. Use this file only to route the task to the correct owner.
4. Use the workspace audit when repo inventory or workspace governance changed:
   - `/home/mfshaf7/projects/_workspace_tools/audit_workspace_layout.py`

## Current Owner Map

- `workspace-governance/`
  - owns workspace-root `README.md` and `AGENTS.md`, workspace audit tooling,
    and cross-repo routing rules
  - read first:
    - `workspace-governance/AGENTS.md`
    - `workspace-governance/README.md`
- `platform-engineering/`
  - owns shared platform structure, environment contracts, Argo-managed state,
    release governance, and product integration docs
  - if the task is product-specific inside this repo, route to
    `platform-engineering/products/<product>/AGENTS.md`
  - read first:
    - `platform-engineering/AGENTS.md`
    - `platform-engineering/README.md`
- `openclaw-runtime-distribution/`
  - owns the active OpenClaw runtime composition path, current packaged
    `host-control-openclaw-plugin`, and distribution-specific verification
  - read first:
    - `openclaw-runtime-distribution/AGENTS.md`
    - `openclaw-runtime-distribution/README.md`
- `openclaw-telegram-enhanced/`
  - owns canonical Telegram behavior, routing, delivery, approvals, and
    Telegram tests
  - read first:
    - `openclaw-telegram-enhanced/AGENTS.md`
    - `openclaw-telegram-enhanced/README.md`
- `openclaw-host-bridge/`
  - owns canonical host enforcement, host policy, allowed roots, audit, export
    staging, and WSL/Windows bridge runtime behavior
  - read first:
    - `openclaw-host-bridge/AGENTS.md`
    - `openclaw-host-bridge/README.md`
- `security-architecture/`
  - owns security standards, trust-boundary architecture, review criteria,
    assessment evidence, and AI-governance posture
  - read first:
    - `security-architecture/AGENTS.md`
    - `security-architecture/README.md`
- `openclaw-isolated-deployment/`
  - retired archival stub
  - do not route active work here unless the retirement decision is explicitly
    reversed

## First Classification

Before editing, classify the task into one of these buckets:

1. workspace governance or cross-repo owner-boundary issue
2. platform contract, GitOps, shared component, or promotion-flow issue
3. product integration or runtime composition issue
4. Telegram behavior issue
5. host enforcement or WSL/Windows bridge issue
6. security or trust-boundary judgment
7. live environment drift under `~/.openclaw`, a running pod, or the host

That classification determines the owner.

## Routing Rules

- Cross-repo routing, workspace repo inventory, workspace-root guidance, and
  audit tooling belong in `workspace-governance/`.
- Shared platform docs, Argo, Vault, observability, environment contracts,
  promotion flow, and product integration docs belong in
  `platform-engineering/`.
- OpenClaw runtime packaging and the active packaged
  `host-control-openclaw-plugin` belong in `openclaw-runtime-distribution/`.
- Telegram routing, buttons, media delivery, approvals, and Telegram-only UX
  belong in `openclaw-telegram-enhanced/`.
- Allowed roots, audit, export staging, and real host actions belong in
  `openclaw-host-bridge/`.
- Trust-boundary, auth, secrets, GitOps trust, AI-governance, and security
  review posture belong in `security-architecture/`.
- Live runtime drift is an environment problem first. Repair it if needed, then
  backport the durable fix to the owning repo.

## Workspace Governance Rules

- The workspace root is not a Git repo. The canonical source for its governance
  files now lives in `workspace-governance/`.
- Do not hand-maintain long-lived edits directly in:
  - `/home/mfshaf7/projects/README.md`
  - `/home/mfshaf7/projects/AGENTS.md`
  - `/home/mfshaf7/projects/_workspace_tools/audit_workspace_layout.py`
  Update the canonical files in `workspace-governance/` and sync them back.
- After any change to the canonical workspace-root governance files, sync the
  live root immediately with:
  - `python3 /home/mfshaf7/projects/workspace-governance/scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects`
- A workspace-governance change is not complete until the sync has been run and
  the workspace audit passes against the live root.
- If the repo inventory, owner map, or routing model changes, update:
  - `workspace-governance/workspace-root/README.md`
  - `workspace-governance/workspace-root/AGENTS.md`
  - `workspace-governance/scripts/audit_workspace_layout.py`
- If a retired path, repo, or operator command must never reappear in active
  guidance, update `workspace-governance/scripts/audit_stale_content.py` in the
  same work.
- If a repo boundary changes, update the owning repo docs in the same work.

## Operating Rules

- Prefer the owner that should hold the long-lived contract, not the repo where
  the patch is easiest.
- When docs and code disagree, fix the immediate problem in the correct owner
  repo and update the docs in the same work.
- Live-only fixes are containment, not completion.
- Do not recreate retired copy-based workflows that the current architecture no
  longer uses.
- If a change affects trust boundaries, privileges, secrets, delivery controls,
  or AI-enabled action paths, update the owning docs or governance artifacts in
  the same work.

## Required Evidence For Production-Impacting Work

Production-impacting work should leave enough evidence to answer:

- what failed
- which owner repo held the durable fix
- which commits changed
- which environment contract or live state changed
- which validation or live checks proved the outcome

If that evidence cannot be produced, the work is not complete.

## Validation Entry Points

- `workspace-governance/`
  - `python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/validate_repo_structure.py --repo-root .`
  - `python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects --check`
  - `python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/audit_stale_content.py --workspace-root /home/mfshaf7/projects`
- other repos
  - follow the local repo `AGENTS.md`
