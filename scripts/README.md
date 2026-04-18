# Workspace Governance Scripts

- `audit_workspace_layout.py`
  - audits the active workspace repo inventory, Git SSH origin shape,
    workspace-root sync state, contract validity, live installed skill sync,
    generated artifact freshness, and cross-repo truth
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
- `install_skills.py`
  - installs or verifies the registered skills declared in `contracts/skills.yaml`
    from their owner repos into a Codex skill directory
  - tracks the workspace-managed live skill install manifest so stale managed
    skills do not silently linger in `~/.codex/skills`
- `scaffold_intake.py`
  - creates a new intake classification entry so a repo, product, or component
    is explicitly marked out-of-scope, proposed, or admitted before it joins
    the active contracts
- `record_after_action.py`
  - creates a scaffolded after-action review record under `reviews/after-action/`
- `record_improvement_candidate.py`
  - creates a scaffolded improvement-candidate record under
    `reviews/improvement-candidates/`
- `sync_workspace_root.py`
  - syncs the canonical files in this repo back into `/home/mfshaf7/projects`
- `validate_improvement_candidates.py`
  - validates that improvement candidates keep valid lifecycle, follow-up,
    closure references, and control references
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
  - validates that active repos still tell the same ownership truth and
    regenerates the resolved governance artifacts under `generated/`
- `validate_repo_structure.py`
  - validates that this repo keeps the expected governance structure
- `workspace_control_plane_summary.py`
  - runs a read-only control-plane summary covering remote freshness,
    workspace-root sync, skill sync, review-control compliance, stale-content
    drift, workspace audit, and self-improvement health
