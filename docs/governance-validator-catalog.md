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

## Admission Rules For New Repos And Components

The intake layer now treats validation behavior as part of admission, not as a
cleanup task after a repo or component is already active.

Every active repo and active component must declare:

- `posture`: whether the subject owns catalog truth, consumes WGCF runtime
  truth, is profile-gated external validation, is covered by owner-repo
  validation, or is interface-contract backed.
- `wgcf_graph_role`: how WGCF should represent the subject in the governance
  graph.
- `catalog_refs`: the validator catalog entries that prove or inspect the
  subject.
- `notes`: the operator-readable rationale for the posture.

The same `validation_behavior` shape is required for proposed or admitted
repos and components in the intake register. If that field is missing, the
intake validator must fail before the entrant can silently become part of the
governed workspace model.

This is intentionally strict at the contract boundary. It prevents a new
component from landing first and only later asking "which validator owns this?"
WGCF can then plan from declared graph participation instead of guessing from
repo names, terminal history, or broad command lists.

## Retirement Rule

No direct validator path may be removed because WGCF exists. Retirement needs:

- shadow parity between direct command output and WGCF receipt posture
- rollback path
- replacement receipt evidence
- explicit ART or owner-repo closeout evidence

Until that exists, direct commands stay as compatibility entrypoints.

The machine-readable `retirement_register` groups entries by ownership and
replacement posture. It distinguishes:

- direct validators that may retire only after shadow parity
- remote-read audits that need explicit profile identity and cache behavior
- materializers and record writers that remain explicit write surfaces
- OOS ART mutation surfaces that WGCF must never replace
- platform runtime commands that stay platform-owned
- GitHub and Kubernetes mutation surfaces that stay recommendation-only for
  WGCF

Every catalog entry must appear in that retirement register. Missing coverage
is a contract validation failure.

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
