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

1. Run owner validation after the source change is prepared.
2. Open a pull request from the exact branch and review the exact head.
3. Merge through the repository provider. The command never merges its own work.
4. Let OOS read merged canonical truth and issue terminal merged-authority evidence.

The preparation receipt is not terminal success. WGCF and OOS artifacts support
the workflow but never replace merged Workspace Governance source authority.

## Record Shape

Every v2 inventory record has an explicit identity, version, lineage, latest
mutation, and posture. Products additionally carry independent maturity.
`lifecycle` remains a temporary validated read alias so existing consumers can
migrate without an unsafe cross-repository flag day:

- repository and component: `lifecycle` equals `posture`
- product: `lifecycle` equals `maturity`

New consumers should use `posture` and `maturity` directly.

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
- no runtime, release, security, or product-maturity activation by promotion
