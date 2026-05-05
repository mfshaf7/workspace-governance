# Workspace Architecture

> Canonical source: `workspace-governance/workspace-root/ARCHITECTURE.md`
>
> This file is synced into `/home/mfshaf7/projects/ARCHITECTURE.md` by
> `workspace-governance/scripts/sync_workspace_root.py`.

This file gives a new session the current system shape without forcing it to
reconstruct the workspace from every repo.

Use it first for workspace orientation. Then route into the owning repo.

## Current System Shape

The workspace currently has three durable authority planes, two active
governance runtime implementation components, plus one fast local iteration
lane:

- workspace governance
  - `workspace-governance/`
  - owns routing, contracts, workspace-root guidance, skills, audit tooling,
    intake classification, and self-improvement controls
- workspace governance control fabric
  - `workspace-governance-control-fabric/`
  - owns runtime implementation for governance graph, validation planning,
    admission/readiness evaluation, receipts, ledger, and control-fabric
    API/worker/CLI surfaces
  - consumes `workspace-governance` truth without owning contracts or
    workspace-root guidance
- context governance gateway
  - `context-governance-gateway/`
  - owns implementation for operational context admission, redaction,
    projection, model-safe/operator-safe packets, receipts, and local ledger
    behavior
  - service-mode runtime remains blocked behind proposed `dev-integration`,
    platform, and security admission gates
  - does not replace WGCF, OOS, platform release authority, security
    acceptance, or any governed AI access path
- shared platform and release authority
  - `platform-engineering/`
  - owns environment contracts, pinned SHAs and digests, Argo state, product
    integration docs, shared `dev-integration` runner, and governed promotion
    flow
- security governance
  - `security-architecture/`
  - owns trust-boundary architecture, security standards, review methodology,
    findings, and product security overlays
- fast local iteration lane
  - `dev-integration`
  - standardized in `workspace-governance`
  - runtime owned by `platform-engineering`
  - concrete profile owned by the workflow repo
  - local only, not governed rollout evidence

## Workspace Control-Plane Direction

The workspace control plane is no longer treated as a vague repo-local bundle.
The current target shape is explicit:

- `workspace-governance` remains the central control-plane repo
- `workspace-governance-control-fabric` is the admitted runtime implementation
  repo for the governance control fabric, not a replacement source of truth
- reusable governance-engine logic stays in canonical engine-owned sources
- tenant-instance state stays explicit instead of being absorbed into the
  engine layer
- runtime work stays sequenced behind an explicit governance-engine boundary,
  packaging model, compatibility boundary, and governed model-access contract

Primary source:

- [workspace-governance/docs/governance-engine-foundation.md](/home/mfshaf7/projects/workspace-governance/docs/governance-engine-foundation.md)

## Active Owner Repos

- `workspace-governance/`
  - workspace control plane
- `workspace-governance-control-fabric/`
  - governance runtime implementation fabric
- `context-governance-gateway/`
  - operational context admission implementation
- `platform-engineering/`
  - shared platform and release authority
- `security-architecture/`
  - security governance owner
- `openclaw-runtime-distribution/`
  - active OpenClaw runtime composition
- `openclaw-telegram-enhanced/`
  - canonical Telegram behavior and operator command UX
- `openclaw-host-bridge/`
  - canonical host enforcement and runtime attestation
- `operator-orchestration-service/`
  - active shared operator workflow service

Retired path:

- `openclaw-isolated-deployment/`
  - archival only
  - not part of the active governed model

## Product Maturity

- `openclaw`
  - fully governed
  - real `source -> runtime composition -> stage rehearsal -> readiness -> prod promotion` flow exists
  - highest real endpoint: governed prod
- `openproject`
  - platform-integrated
  - real runtime and operator procedures exist
  - does not yet have its own governed source-to-stage-to-prod path
  - highest real endpoint: platform-integrated runtime

## Current Product Paths

No single product should be treated as the workspace default. The current
product paths differ in maturity and purpose:

- OpenClaw
  - canonical source changes land in:
    - [openclaw-telegram-enhanced](/home/mfshaf7/projects/openclaw-telegram-enhanced/README.md)
    - [openclaw-host-bridge](/home/mfshaf7/projects/openclaw-host-bridge/README.md)
    - [openclaw-runtime-distribution/host-control-openclaw-plugin](/home/mfshaf7/projects/openclaw-runtime-distribution/host-control-openclaw-plugin)
  - [openclaw-runtime-distribution](/home/mfshaf7/projects/openclaw-runtime-distribution/README.md)
    assembles the governed runtime candidate
  - [platform-engineering/products/openclaw](/home/mfshaf7/projects/platform-engineering/products/openclaw/README.md)
    records approved SHAs and digests, stage verification, readiness, and prod
    promotion state
  - [security-architecture](/home/mfshaf7/projects/security-architecture/README.md)
    governs trust-boundary expectations and review
- OpenProject
  - platform runtime, access, and operator procedures live in
    [platform-engineering/products/openproject](/home/mfshaf7/projects/platform-engineering/products/openproject/README.md)
  - delivery execution truth lives in the
    [Workspace Delivery ART](/home/mfshaf7/projects/platform-engineering/products/openproject/delivery-art-contract.md)
  - [operator-orchestration-service](/home/mfshaf7/projects/operator-orchestration-service/README.md)
    owns the broker-backed delivery-control APIs and OpenProject workflow
    adapters

Important operating truth:

- `stage` is the governed rehearsal lane for products that have one
- `dev-integration` is the fast design lane
- stage is not the loose iteration lane

## Operator Workflow Surfaces

Primary operator-facing surfaces that already exist:

- workspace routing and governance
  - [AGENTS.md](/home/mfshaf7/projects/AGENTS.md)
  - [README.md](/home/mfshaf7/projects/README.md)
- shared `dev-integration` request and usage
  - [platform-engineering/docs/runbooks/dev-integration-profiles.md](https://github.com/mfshaf7/platform-engineering/blob/main/docs/runbooks/dev-integration-profiles.md)
- Telegram operator commands
  - [openclaw-telegram-enhanced/docs/operator-commands.md](/home/mfshaf7/projects/openclaw-telegram-enhanced/docs/operator-commands.md)
- OpenClaw runtime build and packaging
  - [openclaw-runtime-distribution/deployment/operator-build-procedure.md](/home/mfshaf7/projects/openclaw-runtime-distribution/deployment/operator-build-procedure.md)
- host bridge deployment
  - [openclaw-host-bridge/docs/host-deployment.md](/home/mfshaf7/projects/openclaw-host-bridge/docs/host-deployment.md)

## Broker And Idea Workflow

`operator-orchestration-service/` is an active part of the current control
plane. It is no longer just a proposal.

Current role:

- shared operator workflow service
- active workflows are broker-backed idea capture plus the internal accepted
  proposal handoff into the
  [OpenProject delivery ART plane](/home/mfshaf7/projects/platform-engineering/products/openproject/delivery-art-contract.md)
- Telegram `/idea` is a thin adapter to this broker
- OpenProject is the canonical backlog system for captured ideas and proposals
- active `dev-integration` profiles are `idea-workflow` and
  `accepted-idea-delivery`

Current non-goals:

- no autonomous governance decisions
- no direct mutation of active workspace contracts
- no pretending the broker already has a fully governed AI runtime path

## AI Governance Truth

The platform has a governed AI policy model, but the live governed invocation
path is still intentionally suspended.

Current state:

- model-profile registry exists in `platform-engineering/security/`
- the control-plane runtime foundation now requires an explicit model-access
  and audit contract before any governed AI runtime activation
- security review exists for governed intake-assist model profiles
- the reserved `intake-classifier-v1` profile is `suspended`
- operator approval is still required for intake, admission, approval, and
  promotion decisions

Do not describe a raw external model call as a governed AI control.

## Telegram And Codex Runtime Truth

The Telegram repo already contains Codex-adjacent runtime surfaces beyond plain
message formatting.

Current shape includes:

- `/platform` as a thin Telegram view over platform-owned truth
- `/idea` as a thin Telegram view over broker-owned workflow truth
- ACP/session binding support
- Telegram thread binding support for ACP and subagent-style session targets

That means a new session should treat `openclaw-telegram-enhanced/` as a real
operator interaction layer, not just a UI skin.

## Non-Obvious Rules

- the workspace root is not a Git repo
- canonical root files live in `workspace-governance/workspace-root/`
- the local root is materialized by `scripts/sync_workspace_root.py`
- live installed skills under `~/.codex/skills` are part of governed behavior
- `openclaw-isolated-deployment/` is retired
- OpenProject is canonical backlog truth for the idea/proposal flow
- Telegram must not own OpenProject credentials or broker-local workflow truth
- live environment drift is an environment problem first, then a backport task

## Read Next By Task

- workspace routing, repo ownership, or governance drift
  - [workspace-governance/README.md](/home/mfshaf7/projects/workspace-governance/README.md)
- governance graph, validation planning runtime, admission/readiness runtime,
  receipt ledger, or control-fabric API/worker/CLI implementation
  - [workspace-governance-control-fabric/README.md](/home/mfshaf7/projects/workspace-governance-control-fabric/README.md)
- operational context admission, model-safe/operator-safe context packets,
  context redaction, projection, receipts, or CGG Phase 1 local foundation
  - [context-governance-gateway/README.md](/home/mfshaf7/projects/context-governance-gateway/README.md)
- Codex GitHub review, PR flow, or read-only control-plane summary
  - [workspace-governance/docs/codex-github-review-and-automation.md](/home/mfshaf7/projects/workspace-governance/docs/codex-github-review-and-automation.md)
- platform, promotion flow, environments, or product integration
  - [platform-engineering/README.md](/home/mfshaf7/projects/platform-engineering/README.md)
- OpenProject runtime or delivery execution model
  - [platform-engineering/products/openproject/README.md](/home/mfshaf7/projects/platform-engineering/products/openproject/README.md)
- broker workflow contracts and runtime
  - [operator-orchestration-service/README.md](/home/mfshaf7/projects/operator-orchestration-service/README.md)
- OpenClaw runtime composition and packaging
  - [openclaw-runtime-distribution/README.md](/home/mfshaf7/projects/openclaw-runtime-distribution/README.md)
- OpenClaw governed release path
  - [platform-engineering/products/openclaw/README.md](/home/mfshaf7/projects/platform-engineering/products/openclaw/README.md)
- Telegram behavior or `/platform` and `/idea`
  - [openclaw-telegram-enhanced/README.md](/home/mfshaf7/projects/openclaw-telegram-enhanced/README.md)
- host-control or WSL/Windows bridge behavior
  - [openclaw-host-bridge/README.md](/home/mfshaf7/projects/openclaw-host-bridge/README.md)
- trust boundaries, AI governance, or security review posture
  - [security-architecture/README.md](/home/mfshaf7/projects/security-architecture/README.md)
