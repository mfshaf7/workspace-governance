# Governance Control Fabric Operator Surface

## Purpose

Define the operator workflow shape for the future
`workspace-governance-control-fabric` runtime before implementation begins.

Machine-readable contract:

- [contracts/governance-control-fabric-operator-surface.yaml](../contracts/governance-control-fabric-operator-surface.yaml)

This surface exists so the control fabric is not implemented as a pile of
ad hoc validators, raw Git reads, or chat-only evidence. It must become a
bounded operator workflow that turns authority truth into receipts, decisions,
and audit events.

Validator and command inventory:

- [Governance Validator Catalog](governance-validator-catalog.md)

## Authority Split

The control fabric is an execution layer, not the policy source of truth.

- `workspace-governance` owns contracts, schemas, workspace-root guidance,
  routing rules, maturity rules, and generated governance artifacts.
- `workspace-governance-control-fabric` owns runtime implementation for
  validation planning, readiness evaluation, receipts, ledger events, API,
  worker, and CLI.
- `platform-engineering` owns approved deployment state, release gates, version
  pinning, promotion, and runtime adoption.
- `security-architecture` owns security standards, review criteria, findings,
  and security acceptance posture.
- `operator-orchestration-service` owns broker-backed workflow APIs,
  OpenProject adapters, ART writes, blockers, Review Packets, and completion
  evidence transport.

The fabric may read, normalize, plan, validate, evaluate, explain, and emit
receipts. It must not directly mutate upstream authority stores.

## Operator Flow

The minimum workflow has eight phases.

1. Discover status.
   - Confirm fabric health, configured source roots, source freshness, active
     profile, and latest ledger state.
2. Capture source snapshot.
   - Digest upstream authority refs before validation planning.
3. Plan validation.
   - Convert source truth and target scope into an explainable validation plan.
4. Execute validation.
   - Run the selected plan and emit bounded results, artifacts, receipt, and
     ledger event.
5. Inspect receipt.
   - Show the operator what passed, failed, was suppressed, and what action is
     required next.
6. Evaluate readiness.
   - Decide whether a workspace, repo, component, or operator surface is
     admitted, ready, denied, warned, or blocked under a profile.
7. Review ledger.
   - Show recent fabric-local events for audit and handoff.
8. Explain decision.
   - Explain one decision with authority refs, blocked controls, and escalation
     target.

Default output is compact. Full detail belongs in artifacts and receipts, not
in raw terminal dumps or memory-only closeout notes.

## Minimum CLI

The first implementation must preserve these command meanings even if some
commands are initially no-ops or local-only while service runtime is blocked:

```bash
wgcf status
wgcf sources snapshot --workspace-root <path>
wgcf plan --scope workspace|repo|component|operator-surface --target <id> --profile <profile>
wgcf run --plan <plan-id-or-file> --emit-receipt
wgcf inspect --receipt <receipt-id-or-path>
wgcf readiness --target workspace|repo:<name>|component:<name>|operator-surface:<id> --profile <profile>
wgcf ledger tail --limit <n>
wgcf explain --decision <decision-id>
```

The CLI should show a compact human-readable summary by default and provide
`--json` for automation. When full evidence exists, it should return receipt
and artifact references instead of printing raw validation output by default.

## Minimum API

The API is a future runtime integration surface, not day-one proof that a
service must be deployed immediately.

Required endpoint meanings:

- `GET /healthz`
- `GET /readyz`
- `GET /v1/status`
- `POST /v1/source-snapshots`
- `POST /v1/validation-plans`
- `POST /v1/validation-runs`
- `GET /v1/receipts/{receipt_id}`
- `POST /v1/readiness/evaluate`
- `GET /v1/ledger/events`
- `GET /v1/decisions/{decision_id}/explain`

No endpoint in the minimum surface mutates upstream authority. If a readiness
decision requires a contract change, ART mutation, platform decision, or
security review, the API emits the required route and evidence refs instead of
performing that mutation itself.

## Records

The fabric must treat these records as first-class outputs:

- `source-snapshot`
- `validation-plan`
- `validation-run`
- `control-receipt`
- `readiness-decision`
- `ledger-event`
- `authority-reference`
- `escalation-record`

Receipts are the operator-safe proof layer. Ledger events are the audit trail.
Neither replaces owner-repo PRs, ART completion evidence, security reviews, or
platform release records.

## Profiles

Initial profiles:

- `local-read-only`
  - default local posture for snapshots, validation plans, local checks,
    receipts, and ledger events
- `dev-integration`
  - future local-k3s posture after platform and security gates approve runtime
    service use
- `governed-stage`
  - future governed deployment posture requiring platform release authority and
    security review evidence before activation

Unknown authority, stale source snapshots, failed shadow parity, missing owner
boundaries, required security deltas, and platform release gates must block
readiness rather than pass best-effort.

## Blocker Handling

The fabric should produce an `escalation-record` when it cannot honestly
continue. Required blocker triggers are:

- `unknown-authority-source`
- `stale-source-snapshot`
- `shadow-parity-failed`
- `missing-owner-boundary`
- `security-delta-required`
- `platform-release-gate-required`

Active ART impacts must route through `operator-orchestration-service`.
Workspace authority gaps route through `workspace-governance`. Security deltas
route through `security-architecture`. Deployment or adoption gates route
through `platform-engineering`.

## Denied Behavior

The control fabric must not:

- mutate `workspace-governance` contracts directly
- mutate platform approved deployment state
- make security acceptance decisions
- mutate Delivery ART directly
- execute autonomous AI governance decisions
- hide raw validation output only in chat
- replace Review Packets for source-backed ART work
- treat compact output as full evidence

## Day-One Scope

Day one is allowed to be CLI-first and local-first. It should define source
snapshots, plans, receipts, decisions, and ledger shape before service runtime.

Day one must not build:

- dashboard
- always-on central service before security and platform approval
- replacement workspace-governance validators as the source of truth
- replacement OOS ART mutation or Review Packet surface
- custom LLM gateway or AI execution boundary
- platform deployment authority

## Sequencing

Runtime implementation should not start until:

- this contract and the runtime repo operator surface are merged
- #429 security delta review covers operator surface, receipt integrity, local
  ledger, and future API boundary
- implementation work in `workspace-governance-control-fabric` references this
  contract instead of redefining the workflow

The primary runtime operator surface is:

- [workspace-governance-control-fabric/docs/operations/operator-surface.md](https://github.com/mfshaf7/workspace-governance-control-fabric/blob/main/docs/operations/operator-surface.md)
