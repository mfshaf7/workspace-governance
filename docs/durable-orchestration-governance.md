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
3. Build-admit the dev-integration profile, then route source implementation to
   OOS, Platform, and each activity owner. Build admission does not allow a
   runtime launch.
4. When operating evidence is required before normal activation, Platform may
   issue one expiring controlled-proof permit only after Security and the
   operator approve its exact scope.
5. Run only the permitted definition, revisions, artifacts, namespaces,
   identities, queues, scenarios, and actions. The profile remains
   `build-admitted`; ordinary self-serve actions remain denied.
6. Restore the captured exact baseline and preserve the proof result and owner
   receipts.
7. Obtain a separate post-proof Security decision on the operating evidence.
8. Activate the profile and one immutable definition version only after every
   normal admission gate passes.

`validation-readiness-run` is the safe runtime proof.
`delivery.refinement.apply` is the first business workflow. No Console,
Temporal, or owner-activity implementation may present either one as active
before admission evidence exists.

## Controlled Proof Boundary

The controlled-proof path solves first-runtime commissioning without weakening
normal activation:

- it is a `runtime-drill` with drill type `component-commissioning-proof`
- it is available only to a `build-admitted` profile
- it is operator-approved, Security-authorized, expiring, exact-scope, and
  limited to one run
- it binds exact source revisions and immutable runtime image and artifact
  digests as well as the permitted namespaces, identities, queues, definition
  versions, scenarios, and actions
- its permit follows
  [`../contracts/schemas/controlled-runtime-proof-authorization.schema.json`](../contracts/schemas/controlled-runtime-proof-authorization.schema.json)
- its pre-run authorization cannot be reused as post-run activation evidence
- exact-baseline restoration is required before the post-proof Security review
- it cannot run a business definition or create stage or production evidence

The permit is a separate bounded execution authority. It does not make normal
`up`, access, smoke, or workflow execution self-serve for a build-admitted
profile.

Schema validity is necessary but not sufficient. The future permit issuer and
executor must also compare the permit with the current orchestration allowlist,
verify its issue and expiry window, verify every source and runtime digest, and
fail closed when any stop condition is met. No such execution path is activated
by this contract change.

## Current Runtime Status

- adapter: `temporal`
- dev-integration profile: `temporal`
- contract status: `runtime-admission-review`
- profile lifecycle: `build-admitted`
- implementation allowed: bounded owner-repo source work only
- self-serve launch allowed: no
- normal workflow execution allowed: no
- controlled proof allowed: only after an exact permit is issued and accepted
- governed stage allowed: no
- production allowed: no

Build admission records completed Platform and Security review for source
implementation. It does not create or activate a runtime, admit a workflow
definition, or satisfy the later operating-evidence gates.

This source change defines the proof authority and permit schema. It does not
issue a permit or activate Temporal.

## Runtime Boundary

Temporal is a replaceable adapter behind OOS. It may appear in architecture,
platform, security, and technical diagnostics. It should not appear as the
business owner or as a direct dependency of normal domain UI.

Local dev-integration evidence proves fast integration only. It is not
governed stage or production evidence.
