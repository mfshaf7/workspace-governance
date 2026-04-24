# Governance Engine Foundation

## Purpose

Define the current target shape for the governed enterprise AI agent control
plane so the workspace can separate reusable governance-engine logic from
tenant-instance state without breaking the current operator surface.

This document is the primary architectural surface for:

- the governance-engine versus tenant-instance boundary
- the compatibility boundary that keeps today's `AGENTS.md`, skills, and
  script entrypoints stable during migration
- the shadow-parity path for introducing a central governance engine
- the enterprise control-plane packaging model
- the governed AI runtime foundation and its sequencing rules

## Current Direction

`workspace-governance` is still the active workspace control plane today, but it
currently carries both:

- reusable governance-engine logic
- tenant-instance state for this specific workspace

The next architecture step is not a rewrite. It is a controlled separation that
keeps the current operator experience working while making the reusable engine
boundary explicit.

## Governance-Engine Boundary

### Shared Engine Authoring Layer

The following surfaces are the reusable governance-engine authoring layer:

- `workspace-root/`
  - canonical workspace bootstrap and routing guidance
- `contracts/`
  - lifecycle, routing, evidence, intake, and policy truth
- `skills-src/`
  - canonical instruction source for workspace-managed skills
- `scripts/`
  - sync, install, validation, audit, and generated-artifact orchestration
- `generated/`
  - derived control-plane outputs, never hand-authored

These are engine-level concerns because they define how the workspace is
classified, routed, audited, and corrected.

### Tenant-Instance State

The following surfaces stay tenant-instance specific even when the engine split
is explicit:

- `contracts/intake-register.yaml`
  - local classification decisions for this workspace
- `contracts/developer-integration-profiles.yaml`
  - admitted local iteration lanes and their profile state
- `contracts/exceptions.yaml`
  - time-bounded local waivers
- owner-repo operator workflows and runtime docs
  - implementation-local procedures stay with the owning repo
- security review outputs
  - review records stay with `security-architecture` and the reviewed owner
    repo, not in a generated workspace copy

The reusable engine may validate or consume this state, but it must not erase
the distinction between shared policy logic and local admitted state.

## Compatibility Boundary

The migration must preserve the current authoring model and operator entry
surface.

### Non-Break Constraints

- `AGENTS.md`, skills, contracts, and repo rules remain the authoring layer
- the generated workspace root remains materialized from canonical sources
- current script entrypoints remain stable while the engine split is introduced
- repo-owned operator workflows stay in the owning repo
- existing audits and validators continue to work during migration

### Stable Entry Points

The following entrypoints must remain stable through the split:

- `workspace-root/AGENTS.md`
- `workspace-root/README.md`
- `workspace-root/ARCHITECTURE.md`
- `scripts/sync_workspace_root.py`
- `scripts/install_skills.py`
- `scripts/validate_contracts.py`
- `scripts/audit_workspace_layout.py`

If one of these needs to change, it should change behind compatibility shims and
only after the replacement path is already documented and validated.

## Shadow-Parity Path

The governance engine should be introduced through shadow parity, not a
cut-over rewrite.

### Required Phases

1. Author in the current canonical engine-owned sources.
2. Materialize the tenant-instance outputs from those sources without changing
   current behavior.
3. Compare the emitted outputs against the live workspace copies and installed
   skill state.
4. Record parity gaps explicitly before any cutover.
5. Cut over only after parity reads clean and operator-facing entrypoints stay
   stable.

### Required Evidence

- the materialized workspace root still matches the canonical sources
- the live installed skills still match `contracts/skills.yaml`
- owner-repo operator surfaces still point at the same primary procedures
- validation output proves no control-plane truth was duplicated or lost

## Enterprise Control-Plane Packaging Model

### Central Repo

`workspace-governance` remains the central control-plane repo for:

- shared routing truth
- workspace-root bootstrap truth
- machine-readable contracts
- workspace-managed skills
- sync, audit, and validation logic

### Generated Repo-Local Wiring

Repo-local wiring should stay thin and generated or contract-driven where
possible:

- materialized workspace-root bootstrap files
- live installed skill tree under `~/.codex/skills`
- repo-rule driven validation expectations
- generated resolved control-plane artifacts under `generated/`

Repo-local wiring is not the place to re-author central routing or policy
truth.

### Seam-Only Local Validation

Repo-local custom validation is allowed only at true seams:

- product runtime behavior
- component interface contracts
- packaging and build-tooling constraints
- repo-local protocol or artifact formats

Repo-local validation must not duplicate:

- central owner or routing truth
- central lifecycle or intake semantics
- governed AI model policy
- cross-repo evidence or review obligations

## Governed AI Runtime Foundation

### Instruction Bundle Model

The instruction bundle remains layered instead of collapsing into one generated
runtime artifact:

- `AGENTS.md`
  - repo and workspace bootstrap instructions
- `skills-src/`
  - repo-owned instruction logic
- `contracts/skills.yaml`
  - workspace-managed skill registry and ownership
- `contracts/repo-rules/*.yaml`
  - repo-specific control expectations

The future governed runtime may package or materialize these layers, but it
must not replace them as the source of truth.

### Model Access And Audit Contract

The governed AI runtime foundation depends on a separate reviewed model-access
contract:

- approved profile registry:
  - `platform-engineering/security/governed-ai-model-profiles.yaml`
- governed access standard:
  - `platform-engineering/docs/standards/governed-ai-access-model.md`
- security baseline:
  - `security-architecture/docs/standards/ai-security-and-governance.md`

Required controls for any governed model path:

- approved profile plus governed invocation path
- workload caller identity distinct from operator acceptance identity
- structured output contract for governance assistance
- explicit human approval for governance decisions
- attributable audit emission
- no direct provider credentials inside governed product or operator-assist
  workloads

### Runtime Sequencing

The runtime track stays blocked until all of these are explicit:

- governance-engine boundary
- compatibility boundary
- shadow-parity path
- packaging model
- governed model-access and audit contract

That keeps runtime work behind real control-plane truth instead of letting a
future agent runtime define the governance model by accident.
