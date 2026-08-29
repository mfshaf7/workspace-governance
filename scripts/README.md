# Workspace Governance Scripts

- `audit_workspace_layout.py`
  - audits only active workspace repo presence, required repo guidance, Git SSH
    origin shape, session-handoff posture, and materialized workspace-root file
    parity
  - does not orchestrate contract, skill, cross-repo, security, or branch
    lifecycle validators
- `audit_branch_lifecycle.py`
  - audits stale local branches, pinned worktree residue, and, with
    `--include-remote`, remote branches that do not back an open PR or a
    documented exception
  - `--check-clean` also rejects dirty primary worktrees and is the source-state
    part of strict restart-readiness and post-merge cleanup certification
  - remote checks require authenticated `gh` access
- `audit_stale_content.py`
  - audits active documentation against the contract vocabulary and repo-rule
    forbidden ownership language
  - also fails active Git-tracked markdown docs outside `workspace-root/` when
    they use local filesystem navigation links to `/home/mfshaf7/projects/...`
- `check_remote_alignment.py`
  - checks whether local active repos are aligned, ahead, behind, or diverged
    from `origin/main`
  - use it as the remote-freshness preflight before trusting workspace-level
    control-plane guidance
- `contracts_lib.py`
  - shared YAML and generated-artifact loader for the governance scripts
  - also resolves the governance-engine output manifest so materialized and
    generated outputs are declared once instead of hard-coded in multiple scripts
- `project_lifecycle_contract.py`
  - focused semantic support for the product-neutral project lifecycle contract
  - validates owner uniqueness, state vectors, transition support, authority,
    typed envelopes, evidence, preconditions, recovery, and maturity claims
    through `validate_contracts.py`
- `repository_custody_contract.py`
  - validates repository custody owner references, action state transitions,
    evidence order, downstream owner boundaries, and disabled runtime maturity
    through `validate_contracts.py`
- `delivery_art_resource_retirement_contract.py`
  - focused semantic support for Delivery ART work-session resource manifests
    and terminal cleanup receipts
  - rejects unsafe paths, unowned deletion, false terminal outcomes, and receipt
    drift from the exact final manifest through `validate_contracts.py`
- `project_lifecycle_proof.py`
  - executes the registered lifecycle proof scenarios without a runtime or
    backend dependency
  - emits deterministic step receipts and generated JSON/Markdown baseline
    readiness reports
  - use `python3 scripts/project_lifecycle_proof.py --repo-root . --check` to
    detect stale reports or a failed scenario
- `agent_action_conformance.py`
  - invokes the exact merged WGCF evaluator and OOS enforcer sources through
    bounded adapters without exposing or activating a generic runtime path
  - emits compact digest-bound JSON and Markdown conformance reports for all
    declared action, replay, receipt, and audit cases
  - use `python3 scripts/agent_action_conformance.py --workspace-root .. --check`
    to rerun the integrated proof and detect stale reports
- `governance_engine_materializer.py`
  - shared materialization layer for workspace-root sync, managed live skill
    install, and generated governance artifacts
- `install_skills.py`
  - installs or verifies the registered skills declared in `contracts/skills.yaml`
    from their owner repos into a Codex skill directory
  - tracks the workspace-managed live skill install manifest so stale managed
    skills do not silently linger in `~/.codex/skills`
  - reads the live-skill emission boundary from
    `contracts/governance-engine-output-manifest.yaml`
  - keeps the stable skill-install entrypoint while delegating actual emission
    work to `governance_engine_materializer.py`
- `materialize_governance_engine_outputs.py`
  - explicit materializer entrypoint for the output families declared in
    `contracts/governance-engine-output-manifest.yaml`
  - covers live workspace-root sync, managed live skills, and generated
    governance artifacts through one shared implementation surface
- `validate_delegation_journal.py`
  - validates delegated-execution journal records, packet scope discipline,
    write-scope overlap, and required security-review references
- `scaffold_intake.py`
  - creates a new intake classification entry so a repo, product, or component
    is explicitly marked out-of-scope, proposed, or admitted before it joins
    the active contracts
  - when `--decision-source ai-suggested` is used, requires a validated
    `--ai-suggestion-file` produced by the governed client plus an explicit
    operator decision, acceptance state, identity, and timestamp before it can
    record workspace truth; one gateway decision can be applied only once
- `governed_intake_assist.py`
  - validates the active workspace, platform, and security-backed consumer
  boundary, invokes only the governed AI gateway, validates the bounded
    candidate response, and writes a local pre-acceptance artifact only under
    `.art/intake-assist/` without changing canonical workspace truth
- `record_after_action.py`
  - creates a scaffolded after-action review record under `reviews/after-action/`
- `record_improvement_candidate.py`
  - creates a scaffolded improvement-candidate record under
    `reviews/improvement-candidates/`
- `check_self_improvement_escalation.py`
  - evaluates whether a live self-improvement signal must pause normal work and
    immediately create a candidate
  - can also scaffold the candidate directly from the governed
    `self-improvement-policy` signal catalog
- `sync_workspace_root.py`
  - syncs the canonical files in this repo back into `/home/mfshaf7/projects`
  - reads the workspace-root emission map from
    `contracts/governance-engine-output-manifest.yaml`
  - keeps the stable sync entrypoint while delegating actual file emission to
    `governance_engine_materializer.py`
- `validate_improvement_candidates.py`
  - validates that improvement candidates keep valid lifecycle, follow-up,
    closure references, and control references
- `validate_structured_record.py`
  - validates one touched structured governance record immediately and then
    delegates to the owning full validator
  - use it after editing improvement candidates, after-actions, delegation
    journals, workspace contracts, or owner-repo change records
  - when an owner-repo change record declares `security_evidence`, it also
    requires the generated `security-architecture` change-record index to be
    current before the record preflight can pass
- `preflight_touched_records.py`
  - scans changed or explicit paths for structured governance records and
    owner-repo change records, then runs `validate_structured_record.py` on
    every match
  - use it after editing multiple records or when you need to prove no touched
    record was skipped
- `audit_improvement_signals.py`
  - audits machine-visible self-improvement signals such as missing declared
    primary operator workflow surfaces across active repos
- `validate_learning_closure.py`
  - validates that after-action reviews either link real durable controls or
    stay explicitly open with owner and due date
- `validate_intake.py`
  - validates the intake register, explicit out-of-scope/proposed/admitted
    classifications, and the rule that new git repos at the workspace root
    must be classified before they become part of the governed system
  - also validates that any AI-suggested intake entry is backed by the
    workspace governed-intake-assist contract, platform governed-AI contracts,
    active profile policy, and explicit operator acceptance
- `validate_developer_integration.py`
  - validates the shared `dev-integration` lane contracts plus the registered
    repo-owned profile files and command paths
  - requires pinned Security review commits to be landed on `origin/main`, then
    resolves the referenced file from that commit and verifies its exact-byte
    SHA-256 instead of trusting mutable checkout content
- `validate_review_coverage.py`
  - validates that active security-owned repos, components, and products have
    concrete baseline review coverage and non-stale review inventory metadata
- `validate_pull_request_controls.py`
  - validates that active repos keep provider-neutral review guidance,
    required GitHub control surfaces, PR-template evidence sections, bounded
    optional advisory-review disposition, and usable review-check workflows
- `validate_security_evidence.py`
  - runs the security-architecture evidence validator so stale assessment
    metadata and unlinked findings or risks fail at workspace level too
- `validate_security_change_record_lanes.py`
  - validates that repos with contract-declared security change-record lanes
    keep their README/AGENTS reference, policy file, PR workflow/template, and
    diff-aware validator intact
  - also verifies the lane's `TEMPLATE.md` carries the same required closure
    headings as real change records so scaffolding cannot teach a stale record
    shape
- `validate_contracts.py`
  - validates the machine-readable workspace contracts and repo rules against
    their schemas plus semantic checks
  - validates Delivery ART architecture, work-start, Review Packet v2, and
    readiness-receipt fixtures plus the claim-to-proof registry; locally active
    claims require executed positive and negative cases while pending owner
    controls remain explicitly linked to their ART activation work
- `validate_delivery_art_artifact.py`
  - validates one operator-supplied architecture packet, work-start record,
    Review Packet, or readiness receipt against its JSON Schema, cross-field
    semantic bindings, resolved dependency artifacts, applicable architecture
    conformance cases, and declared content digest
  - repeat `--dependency-artifact <path>` until the dependency closure is
    complete; every readiness receipt requires its exact subject artifact, and
    a finalized source Review Packet requires its architecture packet,
    work-start record, durable merge-ready predecessor, and readiness receipt
  - use this contract-authority entrypoint for local artifact review until OOS
    work item `802` activates equivalent runtime validation
- `validate_component_contracts.py`
  - executes the component-level interface validation commands declared in
    `contracts/components.yaml` across the local workspace
- `validate_security_bindings.py`
  - validates that repos with security-relevant trust boundaries point at
    concrete `security-architecture` artifacts, checklist scope, and dated
    review output artifacts instead of directory-level placeholders
- `validate_cross_repo_truth.py`
  - validates that active repos still tell the same ownership truth, that the
    canonical `workspace-root/` bootstrap sections cover the full active repo
    inventory, that `security-architecture` keeps security-view and platform
    inventory coverage for active security-owned components, and regenerates
    the resolved governance artifacts declared in
    `contracts/governance-engine-output-manifest.yaml`
  - now uses the shared materializer layer for generated artifact write/check
    instead of carrying its own duplicate output-emission logic
- `validate_repo_structure.py`
  - validates that this repo keeps the expected governance structure
- `workspace_control_plane_summary.py`
  - runs a read-only control-plane summary covering remote freshness,
    workspace-root sync, skill sync, review-control compliance, stale-content
    drift, branch lifecycle hygiene, workspace audit, and self-improvement
    health
