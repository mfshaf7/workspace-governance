# Product Publication

## Purpose

Product Publication is the governed path for listing and maintaining an
operational product in the workspace portfolio. It converts exact
product-owner lifecycle evidence into a separate publication decision and
terminal receipt.

Publication does not create a product, activate a runtime, approve a release,
accept security risk, or transfer source custody. Those decisions remain with
their existing owners.

The machine-readable authority is
[the product-publication contract](../contracts/product-publication.yaml).
The active product classification and owner bindings remain in
[the product inventory](../contracts/products.yaml), while lifecycle states and
transitions remain in
[the project-lifecycle contract](../contracts/project-lifecycle.yaml).

## Owner Sequence

The workflow preserves six owner boundaries:

1. The product owner binds an exact product-source revision in a product-owned
   manifest, then commits that manifest at a separate exact manifest revision.
2. Workspace Governance supplies vocabulary and artifact contracts; it does not
   fabricate owner evidence.
3. Workspace Governance Control Fabric evaluates the exact manifest and emits
   publication-readiness evidence.
4. Operator Orchestration Service binds the operator decision, idempotency key,
   manifest digest, authority references, and terminal owner receipt.
5. Governance Operations Console projects the accepted record; it is not the
   publication authority.
6. Security Architecture and Platform Engineering retain their independent
   exact-revision review and activation responsibilities when the requested
   audience or operating posture requires them.

Workspace Inventory remains the lifecycle authority. Publication consumes its
exact append-only lifecycle receipt and history event; publication never
creates, retires, restores, or rewrites the product inventory record.

## Product-Owner Manifest

The product owner keeps the manifest in its own repository. A manifest must
identify:

- the canonical `product:<name>` and exact Workspace Governance product-record
  version;
- the inventory classification and lifecycle state;
- whether the submitting repo is the inventory's runtime owner or a declared
  source owner;
- a full product-source commit plus every supporting source reference;
- all five lifecycle axes and the durable evidence references supporting them.

`owner_revision` is the product source snapshot described by the manifest. It
is not the later commit that adds the manifest, because a file cannot contain
the hash of the commit that contains itself. WGCF readiness evidence separately
binds the manifest commit, proves that it descends from `owner_revision`, and
proves that the committed manifest digest equals the submitted manifest digest.

The manifest is evidence, not a mutation request. Its `publication_posture`
describes current owner-observed truth. The publication packet separately asks
for a governed change from that posture.

Schema-v2 manifests additionally bind the latest Workspace Inventory lifecycle
receipt, immutable history event, prior event, and resulting record version,
digest, and posture. Those references must describe the same active product
record as the manifest. A restoration manifest binds an owner `restore` event,
the prior suspension or retirement event, an `active` lifecycle state, and the
safe owner-observed `unlisted` publication posture.

Validate an owner manifest before submitting it:

```bash
python3 scripts/product_publication_contract.py \
  --manifest <owner-repo>/<manifest.json> \
  --observed-owner-revision <product-source-snapshot-commit>
```

The validator rejects unknown products, mismatched product versions,
unauthorized owner repos, non-commit revisions, inventory classification or
lifecycle drift, missing lifecycle axes, and impossible lifecycle/publication
combinations.

## Publication Packet

The orchestrated packet binds one exact owner manifest to:

- one request and idempotency key;
- the current publication version and previous receipt, when one exists;
- one action: `publish`, `update`, `unpublish`, `archive`, or schema-v2
  `restore`;
- one target posture and its fixed listing-scope, audience, and access-class
  tuple;
- the operator decision, WGCF readiness receipt, and Security decision;
- explicit `false` values for source, runtime, release, security, and lifecycle
  authority grants.

The supported target tuples are fixed:

| Posture | Listing scope | Audience | Access class |
| --- | --- | --- | --- |
| `unlisted` | none | none | none |
| `internal` | `workspace-portfolio` | `workspace-operators` | `workspace-authenticated` |
| `client` | `client-portfolio` | `authorized-clients` | `client-authorized` |
| `public` | `public-catalog` | `public` | `public-anonymous` |
| `archived` | `historical-archive` | `historical` | `historical-read-only` |

Validate the complete binding when a packet is available:

```bash
python3 scripts/product_publication_contract.py \
  --manifest <owner-repo>/<manifest.json> \
  --observed-owner-revision <product-source-snapshot-commit> \
  --packet <publication-packet.json>
```

Reusing an idempotency key is valid only for the same request identity and
request digest. A different request under the same key is a conflict and must
fail closed. The expected publication version must match the previous terminal
receipt; initial publication starts at version zero with no previous receipt.

## Retirement And Restoration

Retirement and publication archive remain separate ordered decisions:

1. The product owner retires the product through Workspace Inventory, which
   appends the immutable owner lifecycle event.
2. Publication is first moved to `unlisted` when needed.
3. `archive` may then move only `unlisted` to `archived` using retired owner
   evidence.
4. A later product restoration first runs through Workspace Inventory and
   appends an owner `restore` event.
5. Publication `restore` binds that exact owner receipt and history event plus
   the exact previous archived publication receipt, and moves only `archived`
   to `unlisted`.

Restoration never moves directly to `internal`, `client`, or `public`. A later
publication action must independently re-evaluate the current owner manifest,
readiness evidence, Security decision, expected version, and requested audience.
It also does not restore a runtime, release, repository, access grant, or
Security acceptance.

## Terminal Receipt

The terminal receipt binds the exact packet, request digest, manifest digest,
product identity, result, and publication version. Schema-v2 receipts also
preserve the exact previous publication receipt and owner lifecycle receipt and
history event from the packet. A successful result advances the expected
version exactly once and reports the requested target posture without rewriting
earlier history. Rejected or failed results cannot claim an applied version or
posture.

Validate all three artifacts together:

```bash
python3 scripts/product_publication_contract.py \
  --manifest <owner-repo>/<manifest.json> \
  --observed-owner-revision <product-source-snapshot-commit> \
  --packet <publication-packet.json> \
  --receipt <terminal-receipt.json>
```

## Fail-Closed Boundaries

Do not publish when any of these are true:

- the product is absent from the active Workspace Governance inventory;
- the manifest owner, revision, classification, lifecycle state, or product
  record version does not match authority truth;
- the committed manifest revision does not descend from the product-source
  revision or its manifest digest differs from the submitted artifact;
- a listed posture lacks operational phase, durable source custody, or valid
  release posture;
- the audience, listing scope, or access class contradicts the target posture;
- an operator, readiness, or Security authority reference is missing or uses a
  different owner namespace;
- an idempotency replay conflicts with earlier request content;
- schema-v2 lifecycle receipt or history references differ from the bound owner
  manifest;
- restoration lacks an exact owner restore event, prior lifecycle event, or
  archived publication receipt;
- restoration targets any posture other than `unlisted`;
- the packet attempts to grant authority owned by another control plane.

Console fixtures and display state may be used for UI development, but they are
never publication evidence and cannot be promoted into the portfolio without
the owner manifest, governed packet, and terminal receipt.
