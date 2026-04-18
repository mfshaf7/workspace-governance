# Projects Workspace

> Canonical source: `workspace-governance/workspace-root/README.md`
>
> This file is synced into `/home/mfshaf7/projects/README.md` by
> `workspace-governance/scripts/sync_workspace_root.py`.

This workspace is the operator-facing multi-repo source of truth for the
current platform and product stack.

Treat it as a governed system, not a loose folder of related repos.

## Active Repository Roles

| Repository | Current role | Owns | Does not own |
| --- | --- | --- | --- |
| `workspace-governance/` | Workspace control plane | workspace-root guidance, cross-repo routing, workspace audit tooling | platform rollout, product delivery, security standards |
| `platform-engineering/` | Release and platform authority | environment contracts, pinned SHAs, image digests, Argo state, shared component docs, product integration runbooks | Telegram behavior, bridge implementation, security governance |
| `openclaw-runtime-distribution/` | Active OpenClaw runtime composition | bundled runtime assembly, packaging checks, active `host-control-openclaw-plugin` package, runtime-required workspace templates | environment approval, Argo state, host runtime policy |
| `openclaw-telegram-enhanced/` | Canonical Telegram source | Telegram UX, routing, approvals, media delivery behavior, Telegram-specific tests | host enforcement, platform rollout, security governance |
| `openclaw-host-bridge/` | Canonical host enforcement runtime | allowed roots, typed host operations, audit logs, staging, host-side health and attestation, WSL/Windows bridge behavior | Telegram UX, image composition, GitOps rollout |
| `security-architecture/` | Security governance owner | standards, trust-boundary judgment, review methodology, findings, ADRs, remediation direction | rollout implementation, product packaging, operator runbooks |

## Retired Repository

- `openclaw-isolated-deployment/`
  - retired to an archival stub
  - not part of the current governed build, promotion, or owner-routing model

## Current OpenClaw Control Flow

1. Source behavior changes land in the canonical owner repo:
   - `openclaw-telegram-enhanced/`
   - `openclaw-host-bridge/`
   - `openclaw-runtime-distribution/host-control-openclaw-plugin/`
2. `openclaw-runtime-distribution/` assembles the governed runtime candidate.
3. `platform-engineering/products/openclaw/` records the approved source SHAs
   and image digest for `stage` or `prod`.
4. Argo reconciles the approved environment state into the live cluster.
5. Host-control requests cross the runtime boundary:
   - gateway
   - packaged plugin
   - `openclaw-host-bridge`
   - WSL/Windows host
6. `security-architecture/` governs trust-boundary, control, and review
   expectations across the stack.

## Current Product Surfaces

- OpenClaw
  - product integration, runbooks, and release workflow:
    [platform-engineering/products/openclaw/README.md](/home/mfshaf7/projects/platform-engineering/products/openclaw/README.md)
- OpenProject
  - product integration, access, and operations guidance:
    [platform-engineering/products/openproject/README.md](/home/mfshaf7/projects/platform-engineering/products/openproject/README.md)

## Workspace Governance And Audit

`workspace-governance/` owns the canonical copies of the workspace-root files
plus the machine-readable contract model that defines the active repo map,
product maturity, component inventory, vocabulary, and cross-repo routing
rules. It also owns the self-improvement loop that now includes:

- machine-visible signal audit
- improvement-candidate triage
- after-action closure

It also owns the intake gate. New repos, products, and components are supposed
to be classified first:

- `out-of-scope`
- `proposed`
- `admitted`

before they quietly become part of the governed active model.

AI may assist intake classification later, but that suggestion only counts as
governed when it references an active approved model profile from
`platform-engineering` and the operator still records explicit acceptance.

The workspace also defines a `dev-integration` lane for fast local iteration.
Use it when operator-facing workflow design or cross-repo API work is still
changing too quickly for governed stage rehearsal. It is standardized at the
workspace level, but it is not a governed delivery lane:

- `workspace-governance` defines when to use it and what it must never touch
- `platform-engineering` owns the shared local-k3s runner
- the owner repo supplies the concrete profile
- local branch, worktree, and dirty-state inputs are allowed there
- stage still requires reviewed commits and the normal governed path

`dev-integration` profiles also have a lifecycle now:

- `proposed`
- `active`
- `suspended`
- `retired`

Only `active` profiles are self-serve launchable from the shared runner. The
request/admission model is generic at the workspace layer, even if the current
request surface adapter is a specific tool such as OpenProject.

For operator-facing workflow changes, one clear operator instruction surface is
required in the owning repo. Supporting contracts, templates, and standards do
not count as the primary procedure by themselves. For `dev-integration`,
operators should use the shared runbook in
[platform-engineering/docs/runbooks/dev-integration-profiles.md](https://github.com/mfshaf7/platform-engineering/blob/main/docs/runbooks/dev-integration-profiles.md).

The same principle now applies to self-improvement. Do not wait for a later
retrospective if a repeated miss is already obvious. If the user explicitly
calls out a repeated mistake, or if the machine-visible audit detects a doctrine
or completion gap, that should create or update an improvement candidate first.
Only then should the system decide whether the lesson needs a full after-action
review.

The root copies remain materialized in `/home/mfshaf7/projects` because local
tooling and future sessions read those entrypoints directly.

Supported audit entrypoint:

```bash
python3 /home/mfshaf7/projects/_workspace_tools/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects
```

Supported stale-content audit entrypoint:

```bash
python3 /home/mfshaf7/projects/workspace-governance/scripts/audit_stale_content.py --workspace-root /home/mfshaf7/projects
```

Supported contract validation entrypoints:

```bash
python3 /home/mfshaf7/projects/workspace-governance/scripts/validate_contracts.py --repo-root /home/mfshaf7/projects/workspace-governance
python3 /home/mfshaf7/projects/workspace-governance/scripts/validate_intake.py --workspace-root /home/mfshaf7/projects
python3 /home/mfshaf7/projects/workspace-governance/scripts/validate_developer_integration.py --repo-root /home/mfshaf7/projects/workspace-governance --workspace-root /home/mfshaf7/projects
python3 /home/mfshaf7/projects/workspace-governance/scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --check-generated
```

Supported learning-closure validation entrypoint:

```bash
python3 /home/mfshaf7/projects/workspace-governance/scripts/validate_learning_closure.py --workspace-root /home/mfshaf7/projects
```

Supported improvement-candidate validation entrypoint:

```bash
python3 /home/mfshaf7/projects/workspace-governance/scripts/validate_improvement_candidates.py --workspace-root /home/mfshaf7/projects
```

Supported proactive signal audit entrypoint:

```bash
python3 /home/mfshaf7/projects/workspace-governance/scripts/audit_improvement_signals.py --workspace-root /home/mfshaf7/projects
```

## Start Here

- Workspace routing: [AGENTS.md](/home/mfshaf7/projects/AGENTS.md)
- Workspace governance repo: [workspace-governance/README.md](/home/mfshaf7/projects/workspace-governance/README.md)
- Workspace contracts: [workspace-governance/contracts/README.md](/home/mfshaf7/projects/workspace-governance/contracts/README.md)
- Workspace audit: [_workspace_tools/audit_workspace_layout.py](/home/mfshaf7/projects/_workspace_tools/audit_workspace_layout.py)
- Platform authority: [platform-engineering/README.md](/home/mfshaf7/projects/platform-engineering/README.md)
- Dev-integration request and usage: [platform-engineering/docs/runbooks/dev-integration-profiles.md](https://github.com/mfshaf7/platform-engineering/blob/main/docs/runbooks/dev-integration-profiles.md)
- OpenClaw platform model: [platform-engineering/products/openclaw/architecture-and-owner-model.md](/home/mfshaf7/projects/platform-engineering/products/openclaw/architecture-and-owner-model.md)
- OpenProject platform model: [platform-engineering/products/openproject/README.md](/home/mfshaf7/projects/platform-engineering/products/openproject/README.md)
- Active OpenClaw runtime composition: [openclaw-runtime-distribution/README.md](/home/mfshaf7/projects/openclaw-runtime-distribution/README.md)
- Canonical Telegram source: [openclaw-telegram-enhanced/README.md](/home/mfshaf7/projects/openclaw-telegram-enhanced/README.md)
- Canonical host bridge: [openclaw-host-bridge/README.md](/home/mfshaf7/projects/openclaw-host-bridge/README.md)
- Security governance: [security-architecture/README.md](/home/mfshaf7/projects/security-architecture/README.md)
