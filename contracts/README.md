# Workspace Governance Contracts

This directory is the source of truth for the workspace control-plane model.

Use these contracts to declare:

- which repos are active, retired, or governed differently
- which repos, products, or components are explicitly out-of-scope, proposed,
  or admitted before they join the active control plane
- which products and components exist
- which repo owns which long-lived responsibility
- which dependency and review relationships are allowed
- which evidence and change obligations apply
- which vocabulary is canonical and which terms are retired

## Contract Model

- `repos.yaml`
  - active and retired repos, lifecycle, ownership scope, and allowed
    authoritative references
- `intake-policy.yaml`
  - how new repos, products, and components are classified before they become
    part of the governed system
- `intake-register.yaml`
  - explicit intake decisions for new repos, products, and components that are
    out-of-scope, proposed, or admitted but not yet in the active contracts;
    the decision may come directly from the operator or from an AI suggestion
    that the operator then records
- `developer-integration-policy.yaml`
  - defines the shared `dev-integration` lane semantics, trigger guidance,
    forbidden targets, required actions, and required handoff artifacts
- `developer-integration-profiles.yaml`
  - registers the concrete repo-owned `dev-integration` profiles that may run
    on the shared local-k3s lane, including lifecycle, request record, and
    admission metadata
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

The intake layer is separate from `repo-rules/`. Use intake first to classify a
new entrant. Only create a repo rule when the repo is promoted into the active
governed set.

Repo rules may define:

- required ownership language in `README.md` and `AGENTS.md`
- required authoritative repo references
- required security-architecture artifacts, review checklist, and review-output
  scope for repos that cross security-relevant trust boundaries
- forbidden ownership or topology language
- additional stale-content patterns that should never reappear

`security_requirements.review_output_path` must point to a concrete dated
security review artifact, not a directory `README.md` placeholder.

Repo rules must not:

- redefine lifecycle semantics
- redefine central ownership truth from `repos.yaml`, `products.yaml`, or
  `components.yaml`
- carry ad hoc prose-only exceptions

Use `exceptions.yaml` for temporary waivers instead.

## Developer-Integration Profiles

`dev-integration` is a workspace-standardized fast local iteration lane.

It is:

- ungoverned for delivery
- contract-aligned for interfaces
- local-k3s based
- explicitly separated from governed `stage` and `prod`

The lane standard lives in this repo, but each concrete profile is owned in
the repo that owns the workflow being iterated.

The registered profiles in `developer-integration-profiles.yaml` must point to
a repo-local `profile.yaml` that defines:

- runtime shape
- source repos
- command paths
- session-manifest expectations
- stage handoff expectations

Profiles are not just binary present-or-missing entries anymore.

The shared lifecycle states are:

- `proposed`
  - request exists, but the profile is not yet self-serve launchable
- `active`
  - admitted and self-serve launchable on the shared runner
- `suspended`
  - previously admitted, temporarily blocked from normal launch
- `retired`
  - no longer part of the active self-serve catalog

Current model:

- the policy and lifecycle truth live in `workspace-governance`
- the current request surface adapter is OpenProject, but the contract stays
  generic by recording `request_record.system` and `request_record.ref`
- the shared runner must only launch profiles whose lifecycle is in
  `self_serve_statuses`
- a new profile request does not become launchable until platform acceptance is
  recorded and any flagged security review references are present

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
