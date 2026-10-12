# Product Publication

## Purpose

Product Publication is the governed path for listing an operational product in
the workspace portfolio. It converts exact product-owner lifecycle evidence
into a separate publication decision and terminal receipt.

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

1. The product owner commits a product-owned manifest at an exact Git revision.
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

## Product-Owner Manifest

The product owner keeps the manifest in its own repository. A manifest must
identify:

- the canonical `product:<name>` and exact Workspace Governance product-record
  version;
- the inventory classification and lifecycle state;
- whether the submitting repo is the inventory's runtime owner or a declared
  source owner;
- a full owner commit plus every supporting source reference;
- all five lifecycle axes and the durable evidence references supporting them.

The manifest is evidence, not a mutation request. Its `publication_posture`
describes current owner-observed truth. The publication packet separately asks
for a governed change from that posture.

Validate an owner manifest before submitting it:

```bash
python3 scripts/product_publication_contract.py \
  --manifest <owner-repo>/<manifest.json> \
  --observed-owner-revision <current-full-owner-commit>
```

The validator rejects unknown products, mismatched product versions,
unauthorized owner repos, non-commit revisions, inventory classification or
lifecycle drift, missing lifecycle axes, and impossible lifecycle/publication
combinations.

## Publication Packet

The orchestrated packet binds one exact owner manifest to:

- one request and idempotency key;
- the current publication version and previous receipt, when one exists;
- one action: `publish`, `update`, `unpublish`, or `archive`;
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
  --observed-owner-revision <current-full-owner-commit> \
  --packet <publication-packet.json>
```

Reusing an idempotency key is valid only for the same request identity and
request digest. A different request under the same key is a conflict and must
fail closed. The expected publication version must match the previous terminal
receipt; initial publication starts at version zero with no previous receipt.

## Terminal Receipt

The terminal receipt binds the exact packet, request digest, manifest digest,
product identity, result, and publication version. A successful result advances
the expected version exactly once and reports the requested target posture.
Rejected or failed results cannot claim an applied version or posture.

Validate all three artifacts together:

```bash
python3 scripts/product_publication_contract.py \
  --manifest <owner-repo>/<manifest.json> \
  --observed-owner-revision <current-full-owner-commit> \
  --packet <publication-packet.json> \
  --receipt <terminal-receipt.json>
```

## Fail-Closed Boundaries

Do not publish when any of these are true:

- the product is absent from the active Workspace Governance inventory;
- the manifest owner, revision, classification, lifecycle state, or product
  record version does not match authority truth;
- a listed posture lacks operational phase, durable source custody, or valid
  release posture;
- the audience, listing scope, or access class contradicts the target posture;
- an operator, readiness, or Security authority reference is missing or uses a
  different owner namespace;
- an idempotency replay conflicts with earlier request content;
- the packet attempts to grant authority owned by another control plane.

Console fixtures and display state may be used for UI development, but they are
never publication evidence and cannot be promoted into the portfolio without
the owner manifest, governed packet, and terminal receipt.
