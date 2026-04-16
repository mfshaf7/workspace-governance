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
and the workspace audit script.

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

## Start Here

- Workspace routing: [AGENTS.md](/home/mfshaf7/projects/AGENTS.md)
- Workspace governance repo: [workspace-governance/README.md](/home/mfshaf7/projects/workspace-governance/README.md)
- Workspace audit: [_workspace_tools/audit_workspace_layout.py](/home/mfshaf7/projects/_workspace_tools/audit_workspace_layout.py)
- Platform authority: [platform-engineering/README.md](/home/mfshaf7/projects/platform-engineering/README.md)
- OpenClaw platform model: [platform-engineering/products/openclaw/architecture-and-owner-model.md](/home/mfshaf7/projects/platform-engineering/products/openclaw/architecture-and-owner-model.md)
- OpenProject platform model: [platform-engineering/products/openproject/README.md](/home/mfshaf7/projects/platform-engineering/products/openproject/README.md)
- Active OpenClaw runtime composition: [openclaw-runtime-distribution/README.md](/home/mfshaf7/projects/openclaw-runtime-distribution/README.md)
- Canonical Telegram source: [openclaw-telegram-enhanced/README.md](/home/mfshaf7/projects/openclaw-telegram-enhanced/README.md)
- Canonical host bridge: [openclaw-host-bridge/README.md](/home/mfshaf7/projects/openclaw-host-bridge/README.md)
- Security governance: [security-architecture/README.md](/home/mfshaf7/projects/security-architecture/README.md)
