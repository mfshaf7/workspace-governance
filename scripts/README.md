# Workspace Governance Scripts

- `audit_workspace_layout.py`
  - audits the active workspace repo inventory, Git SSH origin shape,
    workspace-root sync state, contract validity, live installed skill sync,
    generated artifact freshness, and cross-repo truth
- `audit_branch_lifecycle.py`
  - audits stale local branches, pinned worktree residue, and, with
    `--include-remote`, remote branches that do not back an open PR or a
    documented exception
  - `--check-clean` is the strict clean-state gate for restart-readiness and
    post-merge cleanup claims
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
- `validate_developer_integration.py`
  - validates the shared `dev-integration` lane contracts plus the registered
    repo-owned profile files and command paths
- `validate_review_coverage.py`
  - validates that active security-owned repos, components, and products have
    concrete baseline review coverage and non-stale review inventory metadata
- `validate_codex_review_controls.py`
  - validates that active repos keep repo-specific Codex review guidance,
    required GitHub control surfaces, PR-template evidence sections, and usable
    review-check workflows
- `validate_security_evidence.py`
  - runs the security-architecture evidence validator so stale assessment
    metadata and unlinked findings or risks fail at workspace level too
- `validate_security_change_record_lanes.py`
  - validates that repos with contract-declared security change-record lanes
    keep their README/AGENTS reference, policy file, PR workflow/template, and
    diff-aware validator intact
- `validate_contracts.py`
  - validates the machine-readable workspace contracts and repo rules against
    their schemas plus semantic checks
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
