# Workspace Governance Contracts

This directory is the source of truth for the workspace control-plane model.

Use these contracts to declare:

- which repos are active, retired, or governed differently
- which products and components exist
- which repo owns which long-lived responsibility
- which dependency and review relationships are allowed
- which evidence and change obligations apply
- which vocabulary is canonical and which terms are retired

## Contract Model

- `repos.yaml`
  - active and retired repos, lifecycle, ownership scope, and allowed
    authoritative references
- `products.yaml`
  - product maturity, owning repos, and delivery model
- `components.yaml`
  - shared and product-linked components, operator surface, owner repo, and
    any published interface contract path plus validation entrypoint
- `task-types.yaml`
  - workspace-level routing and discussion gates by task type
- `lifecycle.yaml`
  - allowed lifecycle states for repos, products, and components
- `dependency-types.yaml`
  - approved cross-repo dependency semantics
- `change-classes.yaml`
  - durable change categories used for routing and evidence
- `failure-taxonomy.yaml`
  - reusable failure classes for after-action review and learning closure
- `improvement-triggers.yaml`
  - triggers that decide when an after-action review is expected and which
    kinds of durable controls usually close it
- `evidence-obligations.yaml`
  - required evidence for each change class
- `review-obligations.yaml`
  - required review routes and security involvement by impact
- `vocabulary.yaml`
  - canonical and retired terms used by stale-content and drift checks
- `exceptions.yaml`
  - time-bounded waivers with owner, rationale, and expiry
- `validation-matrix.yaml`
  - which validator or audit enforces which contract surface
- `skills.yaml`
  - registered workspace and repo-owned skills, their owner repo, and their
    source path

## Repo Rules

`repo-rules/*.yaml` extends the shared contracts for one active repo at a time.

Repo rules may define:

- required ownership language in `README.md` and `AGENTS.md`
- required authoritative repo references
- required security-architecture artifacts, review checklist, and review-output
  scope for repos that cross security-relevant trust boundaries
- forbidden ownership or topology language
- additional stale-content patterns that should never reappear

Repo rules must not:

- redefine lifecycle semantics
- redefine central ownership truth from `repos.yaml`, `products.yaml`, or
  `components.yaml`
- carry ad hoc prose-only exceptions

Use `exceptions.yaml` for temporary waivers instead.

## After-Action Reviews

Meaningful misses, late discoveries, or repeated operator pain should be
captured under `../reviews/after-action/`.

These records are not free-form notes. They are governed learning artifacts
that should either:

- stay explicitly open with an owner and due date, or
- close only when they link the durable control changes that actually landed

Use:

- `scripts/record_after_action.py`
- `scripts/validate_learning_closure.py`

## Generated Artifacts

Resolved graphs and compiled rule sets belong in `../generated/`.

Do not hand-edit those files. Regenerate them through the validator and audit
scripts.
