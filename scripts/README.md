# Workspace Governance Scripts

- `audit_workspace_layout.py`
  - audits the active workspace repo inventory, Git SSH origin shape,
    workspace-root sync state, contract validity, generated artifact freshness,
    and cross-repo truth
- `audit_stale_content.py`
  - audits active documentation against the contract vocabulary and repo-rule
    forbidden ownership language
- `contracts_lib.py`
  - shared YAML and generated-artifact loader for the governance scripts
- `install_skills.py`
  - installs or verifies the workspace-level skills under `skills-src/`
- `sync_workspace_root.py`
  - syncs the canonical files in this repo back into `/home/mfshaf7/projects`
- `validate_contracts.py`
  - validates the machine-readable workspace contracts and repo rules against
    their schemas plus semantic checks
- `validate_component_contracts.py`
  - executes the component-level interface validation commands declared in
    `contracts/components.yaml` across the local workspace
- `validate_security_bindings.py`
  - validates that repos with security-relevant trust boundaries point at
    concrete `security-architecture` artifacts, checklist scope, and review
    output scope
- `validate_cross_repo_truth.py`
  - validates that active repos still tell the same ownership truth and
    regenerates the resolved governance artifacts under `generated/`
- `validate_repo_structure.py`
  - validates that this repo keeps the expected governance structure
