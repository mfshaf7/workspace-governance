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
  - may also declare `security_review_subject: true` when a repo needs
    security review inventory coverage even though it does not use the normal
    security-binding pattern
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
- `delegation-policy.yaml`
  - defines the workspace-wide delegated-execution policy, eligibility gate,
    task classes, packet rules, and audit-journal expectations
- `self-improvement-policy.yaml`
  - defines the in-session self-improvement signal catalog, fail-closed runtime
    gate, and primary escalation surface
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
  source path; live installed skills under `~/.codex/skills` must stay
  aligned with this registry and source tree
- `governance-engine-foundation.yaml`
  - machine-readable definition of the governance-engine versus tenant-instance
    boundary, compatibility boundary, packaging model, and governed AI runtime
    sequencing prerequisites
- `governance-engine-boundary-map.yaml`
  - concrete path-level classification of engine-owned authoring surfaces,
    tenant-instance state, current coupling points, standalone packaging
    prerequisites, referenced external surfaces, and the generated boundary
    projection used during parity work
- `governance-engine-output-manifest.yaml`
  - machine-readable declaration of which outputs are materialized into the
    live workspace, live Codex skill root, and `generated/`, plus the emitter
    script that owns each output family
- `governance-engine-shadow-parity.yaml`
  - fail-closed parity checks and cutover gate for workspace-root, installed
    skills, generated artifacts, and stable entrypoints during integrated
    governance-engine work
- `governance-engine-extraction-gate.yaml`
  - threshold-based extraction decision contract with explicit hard gates,
    extraction-need signals, the current machine-recorded retain-versus-extract
    decision, non-goals, and bounded runtime readiness prerequisites after
    parity is proven
- `delivery-art-operator-path.yaml`
  - machine-readable definition of the canonical ART operator entrypoint,
    read hierarchy, guided closeout intents, fallback model, compatibility
    boundary, and success metrics

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
- security-significant path triggers that require a fresh security delta review
  and identify which review-inventory subjects must be refreshed
- forbidden ownership or topology language
- additional stale-content patterns that should never reappear

`security_requirements.review_output_path` must point to a concrete dated
security review artifact, not a directory `README.md` placeholder.

`security_requirements.delta_review_triggers` should describe the smallest real
change classes that cross a meaningful trust boundary. They are intentionally
path-based and machine-enforced so a repo can prove:

- which changes require a fresh security delta review
- which review areas are implicated
- which inventory subjects in `security-architecture/registers/review-inventory.yaml`
  must be refreshed in the same work

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
- testing posture
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
- persistent profiles must keep the shared `devint-smoke` action read-only
- if a workflow still needs mutating smoke, admit and use a separate
  disposable companion profile instead of writing test artifacts into the
  persistent working lane

This contract is governance truth, not the primary operator instruction
surface. If an operator needs to request or use a `dev-integration` profile,
the owning operator-facing runbook must say how to do it directly and link back
to these contracts only as supporting detail.

Current operator-facing runbook:

- [platform-engineering/docs/runbooks/dev-integration-profiles.md](https://github.com/mfshaf7/platform-engineering/blob/main/docs/runbooks/dev-integration-profiles.md)

## Improvement Candidates And After-Action Reviews

The self-improvement model now has three layers:

- machine-visible signal audit
- improvement candidates for fast triage
- after-action reviews for durable closure

Primary operator surface:

- `../docs/self-improvement-escalation.md`

That model is now regression-aware too:

- if a closed lesson regresses, the new candidate should explicitly link back
  to the earlier closed candidate or after-action with `regression_of`
- use trigger `closed-lesson-regression` for that record
- treat that as evidence that the earlier closure controls were too weak or too
  narrow, not as a vague unrelated new issue

Machine-visible signals are enforced through:

- repo-rule declared operator workflow surfaces
- `scripts/audit_improvement_signals.py`

Improvement candidates live under:

- `../reviews/improvement-candidates/`

Use them when a likely repeated miss or late discovery has been recognized, but
the durable control shape is not fully decided yet.

Validate them with:

- `scripts/validate_improvement_candidates.py`
- `scripts/audit_improvement_signals.py`

These are not the same thing as after-action reviews.

Candidates are the fast triage layer. After-actions are the governed closure
layer.

Troubleshooting doctrine is explicit too. Use
`../docs/troubleshooting-preflight.md` as the primary operator surface for
serious failure diagnosis. If a simpler root cause is discovered late because
the earlier preflight or live-truth layers were skipped, treat that as a
first-class self-improvement signal instead of normal debugging noise.

Delegated execution is explicit too. Use
`../docs/delegated-execution.md` as the primary operator surface for
workspace-wide sub-agent use, packet design, write-scope ownership, and
delegation-journal expectations.

Use an after-action directly when the lesson and control shape are already
clear enough to close or explicitly leave open with a real owner and due date.

Meaningful misses, late discoveries, or repeated operator pain should be
captured under `../reviews/after-action/`.

These records are not free-form notes. They are governed learning artifacts
that should either:

- stay explicitly open with an owner and due date, or
- close only when they link the durable control changes that actually landed

Use:

- `scripts/check_self_improvement_escalation.py`
- `scripts/record_after_action.py`
- `scripts/record_improvement_candidate.py`
- `scripts/validate_improvement_candidates.py`
- `scripts/audit_improvement_signals.py`
- `scripts/validate_learning_closure.py`

## Generated Artifacts

Resolved graphs and compiled rule sets belong in `../generated/`.

Do not hand-edit those files. Regenerate them through the validator and audit
scripts. The exact emitted file set is declared in
`governance-engine-output-manifest.yaml`.
