# Workspace Governance Scripts

- `audit_workspace_layout.py`
  - audits the active workspace repo inventory, repo guidance coverage, Git SSH
    origin shape, and workspace-root sync state
- `audit_stale_content.py`
  - audits active documentation for known retired script names, moved command
    paths, and obsolete guidance patterns that should no longer appear
- `sync_workspace_root.py`
  - syncs the canonical files in this repo back into `/home/mfshaf7/projects`
- `validate_repo_structure.py`
  - validates that this repo keeps the expected governance structure
