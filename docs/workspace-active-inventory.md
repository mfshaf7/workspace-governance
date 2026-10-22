# Workspace Active Inventory

Use this workflow after Workspace Intake has classified a repository, product,
or component as `admitted` and WGCF has returned readiness for the exact source
versions. Admission alone does not create an active inventory record.

The command prepares one reviewable source change. It removes the admitted
entry from `contracts/intake-register.yaml`, adds the matching record to
`contracts/repos.yaml`, `contracts/products.yaml`, or
`contracts/components.yaml`, and emits digest-bound preparation evidence. A
successful merged-authority receipt is produced later by OOS only after the
pull request is independently reviewed, merged, and read back from `main`.

## Inspect Current State

```bash
python3 scripts/workspace_inventory.py state --kind repo --name example-repo
```

The output provides the exact intake-register digest, target-inventory digest,
intake entry version and digest, and expected null active-record version needed
by the request and WGCF readiness artifacts.

## Prepare Promotion

Run from a non-default review branch:

```bash
python3 scripts/workspace_inventory.py apply \
  --request /path/to/promotion-request.json \
  --readiness /path/to/promotion-readiness.json \
  --output-dir /path/to/output
```

The request identifies one admitted intake entry, includes the complete typed
active record, binds current source digests, names the operator and approval
references, and uses a stable idempotency key. Readiness binds the exact request
and the same observed state.

The command fails before mutation when the entry is not admitted, any source
binding is stale, the active identity already exists, readiness is not `ready`,
the compatibility alias disagrees with posture or maturity, or the command is
run from `main`, `master`, or a detached head.

## Review And Completion

Promotion is a complete registration change, not merely two YAML files. All
Inventory kinds refresh the existing generated metadata family. A routine new
repository must have exact provider custody and the existing source-only
`covered-by-owner-repo` / `product-runtime-source` posture, without shared-control
or Security-binding authority. Its native owner transaction also derives the
minimal repo rule, the bounded source-owner routing index in the three root
documents, and conservative context/raw-output declarations. These declarations
keep raw model projection denied; they do not claim packet adoption, parity,
retirement eligibility, a CI toolchain, runtime activation or Security acceptance.
Shared/control owners and Security-bound registration require their explicit
reviewed source change; they cannot borrow this routine source-owner path.

The derived rule includes the existing active-repository pull-request review
policy: owner review guidance, CODEOWNERS, governance/advisory PR template and
a pull-request validation workflow. These are required surfaces, not passing
evidence. A valid application evidence profile alone does not satisfy them.
Missing controls use the existing trusted bootstrap before promotion, including
an admitted source-only owner still absent from Inventory. Optional bootstrap
CI does not waive the later active-Inventory review policy. Independent owner
policy and application source must not be overwritten to satisfy registration.

Only the exact generated index is registration data. Surrounding instructions,
existing core/custom repo rules and context policy remain reviewed controls.
OOS must publish and read back the complete owner-produced file set in one
source commit. Platform's record refresh validates that exact semantic boundary
with reviewed owner code rather than broadly allowing these control files.
The full contract model and cross-repo validation remain required before merge.
The local transaction stages/fsyncs all files and restores their original bytes
on a process exception; Git publication, not the local filesystem, provides the
durable multi-file boundary. Missing or drifted companions deny exact replay.

1. Run owner validation after the source change is prepared.
2. Open a pull request from the exact branch and review the exact head.
3. Merge through the repository provider. The command never merges its own work.
4. Let OOS read merged canonical truth and issue terminal merged-authority evidence.

The preparation receipt is not terminal success. WGCF and OOS artifacts support
the workflow but never replace merged Workspace Governance source authority.

## Routine Operation Boundary

Promotion and lifecycle commands share one activation boundary with Workspace
Intake. The canonical order, human gates, evidence requirements, rollback
units, and operator status states are defined in
[`workspace-intake-inventory-operation`](../contracts/workspace-intake-inventory-operation.yaml).

Local source preparation and conformance remain baseline evidence. Routine
operation requires exact merged source, WGCF receipts, OOS recovery evidence,
the Console projection, Security acceptance, Platform composition, and the
composed operating receipt. No individual owner may infer `operating-ready`.

## Change An Active Record

Inspect the exact inventory and history bindings before preparing a change:

```bash
python3 scripts/workspace_inventory.py lifecycle-state \
  --kind repo \
  --name example-repo
```

Then run the requested lifecycle action from a non-default review branch:

```bash
python3 scripts/workspace_inventory.py lifecycle \
  --request /path/to/lifecycle-request.json \
  --readiness /path/to/lifecycle-readiness.json \
  --output-dir /path/to/output
```

The request may `update`, `suspend`, `restore`, or `retire` one repository,
product, or component. It binds the current inventory digest, append-only
history digest, record version and digest, posture, operator and approval
references, impact acknowledgements, and a stable idempotency key. A restore
also binds the latest suspension or retirement event.

Every accepted action preserves the record identity, increments its version,
and appends one event to `contracts/workspace-inventory-history.yaml`. Exact
replay returns the existing result without appending another event. Repository
retirement moves the complete record to `retired_repos`; restoration moves it
back to the active collection. Products and components remain in their current
collection with explicit posture.

Source-only lifecycle actions update the same rule, index and generated views.
Retirement retains the exact derived rule as history but removes active routing
and context coverage; restoration reinstates the denied-by-default declarations.
An independently customized rule or context policy requires explicit control
review instead of automatic replacement. No retirement fabricates CGG parity.
Existing core/control-owner posture changes also require their explicit routing
and policy review; readiness blocks the routine source-only route before a
write. Existing legacy identities and ordinary source work are not re-admitted.

Review, merge, and completion use the same boundary as promotion: validate the
prepared source, review the exact pull-request head, merge through the provider,
and let OOS reconcile merged canonical truth. The local preparation receipt is
not terminal success.

## Record Shape

Every v2 inventory record has an explicit identity, version, lineage, latest
mutation, and posture. Products additionally carry independent maturity.
`lifecycle` remains a temporary validated read alias so existing consumers can
migrate without an unsafe cross-repository flag day:

- repository and component: `lifecycle` equals `posture`
- product: `lifecycle` equals `maturity`

New consumers should use `posture` and `maturity` directly.

An explicit repository `provider_repository` binding is copied unchanged from
the admitted Intake record during promotion. Promotion cannot substitute or
invent another physical repository. Ordinary inventory updates preserve its
immutable `(provider, provider_repository_id)` pair; reviewed current `full_name`
coordinates may change after a real provider rename/transfer. Existing legacy
records without explicit provider coordinates remain valid. Neither this field,
promotion nor an App installation grants source credentials or activates a
runtime. Provider installation selection remains Platform authority.

Workspace layout validation uses an explicit GitHub provider binding's current
`full_name` for the canonical SSH origin. It does not infer that organization
repositories live under the personal account or that their local owner key
must equal the provider repository name. Unbound legacy owners keep their
existing personal-account origin rule; malformed explicit bindings fail closed.
This does not waive required repo rules, physical-owner guidance, review,
validation or the separate runtime/source-purpose boundaries.

## Migration

The one-time v1 migration preserves existing domain values and adds versioned,
digest-bound legacy lineage:

```bash
python3 scripts/workspace_inventory.py migrate \
  --source-ref git://workspace-governance/<commit> \
  --recorded-at <ISO-8601-date-time> \
  --output /path/to/migration-report.json
```

All target inventories validate before replacement. Re-running the command on
v2 data is a no-op.

## Prohibited Shortcuts

- no direct write to `main`
- no automatic merge
- no promotion from `proposed` or `out-of-scope`
- no overlap between intake and active inventory
- no hard delete
- no stale lifecycle or history overwrite
- no hidden restoration or history rewrite
- no runtime, release, security, or product-maturity activation by promotion
