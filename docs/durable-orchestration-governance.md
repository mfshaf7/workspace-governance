# Durable Orchestration Governance

This is the primary workspace instruction surface for deciding whether a
workflow needs durable execution and routing its implementation.

The machine-readable authority is
[`../contracts/durable-orchestration.yaml`](../contracts/durable-orchestration.yaml).

## Default Decision

Keep execution synchronous unless the accepted command needs restart survival,
multiple recoverable side effects, a wait beyond one request, controlled retry
or timeout, compensation, durable controls, or correlated evidence across
multiple execution owners.

Visual workflow depth, a wizard, logs, or a persisted domain record do not by
themselves justify durable orchestration.

## Owner Route

- `workspace-governance` owns the cross-repo contract and admission rules.
- `operator-orchestration-service` owns definitions, requests, run controls,
  aggregate projection, correlation, and final receipts.
- `platform-engineering` owns the Temporal runtime and its lifecycle.
- domain and shared-component repos own their bounded business intent or
  activities.
- `security-architecture` owns trust-boundary acceptance.
- `governance-operations-console` prepares approved intent and projects OOS
  state; it never calls Temporal directly.

## Required Sequence

1. Classify the use case as `synchronous`, `conditional`,
   `durable-candidate`, or `admitted-durable`.
2. For a durable candidate, complete the definition contract before source
   implementation.
3. Route implementation to OOS and activity work to each activity owner.
4. Admit a dev-integration profile and complete Platform and Security review.
5. Prove deterministic replay, idempotency, failure handling, controls,
   source projection, receipts, suspension, and rollback.
6. Activate one immutable definition version only after every admission gate
   passes.

`validation-readiness-run` is the safe runtime proof.
`delivery.refinement.apply` is the first business workflow. No Console,
Temporal, or owner-activity implementation may present either one as active
before admission evidence exists.

## Current Runtime Status

- adapter: `temporal`
- dev-integration profile: `temporal`
- contract status: `runtime-admission-review`
- profile lifecycle: `build-admitted`
- implementation allowed: bounded owner-repo source work only
- self-serve launch allowed: no
- workflow execution allowed: no
- governed stage allowed: no
- production allowed: no

Build admission records completed Platform and Security review for source
implementation. It does not create or activate a runtime, admit a workflow
definition, or satisfy the later operating-evidence gates.

## Runtime Boundary

Temporal is a replaceable adapter behind OOS. It may appear in architecture,
platform, security, and technical diagnostics. It should not appear as the
business owner or as a direct dependency of normal domain UI.

Local dev-integration evidence proves fast integration only. It is not
governed stage or production evidence.
