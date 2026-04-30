# Governance Validator Catalog

## Purpose

The governance validator catalog is the source-owned inventory for current
workspace validators, audits, materializers, scaffolding commands, and external
operator command surfaces.

Machine-readable contract:

- [contracts/governance-validator-catalog.yaml](../contracts/governance-validator-catalog.yaml)

This catalog exists so `workspace-governance-control-fabric` can plan and
receipt validation without guessing from chat history, broad README command
lists, or raw terminal output.

## Authority Split

`workspace-governance` owns the catalog. It decides which command exists, which
repo owns it, which safety class applies, which profile may run it, and whether
it may ever be retired.

`workspace-governance-control-fabric` consumes the catalog. It may snapshot,
plan, invoke allowed checks, cache results, store artifacts, emit receipts, and
explain readiness decisions. It must not redefine catalog truth locally.

`operator-orchestration-service` remains the only Delivery ART mutation
authority. WGCF can produce ART recommendations and receipt references, but OOS
performs the ART write.

`platform-engineering` owns runtime and deployment command surfaces such as
OpenProject quality checks, projection sync, dev-integration runner commands,
and Kubernetes access.

`security-architecture` owns security review acceptance. WGCF may surface
required security evidence and missing review posture, but it does not approve
security risk.

## Safety Classes

The catalog classifies every command before WGCF can use it:

- `local-read-only`: reads repo-local files and emits bounded output.
- `workspace-cross-repo-read`: reads sibling repos or generated workspace state.
- `remote-read`: reads GitHub or other network-backed state.
- `live-runtime-read`: reads live broker, platform, or Kubernetes runtime state.
- `materialized-output-write`: writes generated or live materialized outputs.
- `structured-record-write`: creates or updates governance records.
- `authority-mutation`: mutates an upstream authority store.

Only read-only classes are eligible for default WGCF plans. Anything that
writes materialized outputs, writes structured records, touches live runtime, or
mutates authority requires an explicit profile gate and operator intent.

## WGCF Invocation Rules

WGCF must use the catalog in this order:

1. Load the catalog from `workspace-governance`.
2. Resolve requested scope to catalog entries.
3. Reject unknown commands or unknown safety classes.
4. Apply profile gating before execution.
5. Plan selected, suppressed, blocked, stale, waived, and external-owner checks
   distinctly.
6. Capture raw output as artifact references when retention is required.
7. Emit compact receipts and ledger events instead of raw output dumps.

The default is deny-by-absence. A command that is not in the catalog is not a
valid WGCF execution target.

## Retirement Rule

No direct validator path may be removed because WGCF exists. Retirement needs:

- shadow parity between direct command output and WGCF receipt posture
- rollback path
- replacement receipt evidence
- explicit ART or owner-repo closeout evidence

Until that exists, direct commands stay as compatibility entrypoints.

## Current Boundaries

The catalog intentionally includes both local scripts and external command
families. This is required because current operator validation spans:

- workspace-governance Python validators and audits
- OOS `npm run art` and `npm run api:probe`
- platform OpenProject quality and projection commands
- platform dev-integration runner commands
- GitHub CLI state reads and PR/workflow operations
- Kubernetes runtime diagnostics
- future `wgcf` command surfaces

The goal is not to move ownership of those commands into WGCF. The goal is to
let WGCF decide what can be invoked, under which profile, and how the evidence
is compacted and receipted.
