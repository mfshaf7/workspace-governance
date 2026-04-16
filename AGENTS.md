# Workspace Governance Agent Notes

This repository owns the workspace-level control plane for
`/home/mfshaf7/projects`.

Keep it focused on cross-repo governance. Do not let it turn into another
delivery repo.

## Read First

- `README.md`
- `workspace-root/README.md`
- `workspace-root/AGENTS.md`
- `scripts/README.md`

## What This Repo Owns

- canonical workspace-root guidance
- machine-readable workspace contracts
- generated governance artifacts
- workspace-level skill source
- workspace audit and sync tooling
- stale-content audit rules for active docs
- repo inventory and cross-repo routing rules
- validation that the workspace-level control surface stays coherent

## What This Repo Does Not Own

- platform rollout logic
- product or component code
- product-specific runbooks
- security standards or review evidence

Route those changes back to the owner repos.

## Working Rules

- Edit the canonical files here, not the materialized root copies, unless you
  are doing short-lived incident containment.
- When a request introduces a new product, shared component, control plane, or
  architecture-shaping feature, the first step is discussion and framing, not
  implementation.
- After changing `workspace-root/` or `scripts/audit_workspace_layout.py`, you
  must run `scripts/sync_workspace_root.py` before the work is complete.
- A workspace-root governance change is not complete until:
  - the canonical files are updated in this repo
  - the live workspace root has been re-synced
  - the sync and workspace audit both pass
- If the active repo inventory changes, update:
  - `contracts/repos.yaml`
  - `contracts/repo-rules/`
  - `workspace-root/README.md`
  - `workspace-root/AGENTS.md`
  - `scripts/audit_workspace_layout.py`
- If the owner model, product map, component map, or review/evidence model
  changes, update the affected files under `contracts/` and refresh
  `generated/` through `scripts/validate_cross_repo_truth.py --write-generated`.
- If a component publishes an `interface_contract`, its declared
  `validation_command` must stay runnable from `scripts/validate_component_contracts.py`.
- If you retire a script name, move a workflow path, or change an ownership
  phrase that appears across repos, update `contracts/vocabulary.yaml` or the
  affected `contracts/repo-rules/*.yaml` so the stale wording is caught
  automatically next time.
- If repo boundaries change, update the owning repo docs in the same work. This
  repo documents the boundary; it does not replace owner-repo documentation.
- Treat `openclaw-isolated-deployment/` as retired unless the retirement
  decision is deliberately reversed. Do not route active work there.

## Validation

Run these after structural changes:

```bash
python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_repo_structure.py --repo-root .
python3 scripts/validate_contracts.py --repo-root .
python3 scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --write-generated
python3 scripts/validate_component_contracts.py --workspace-root /home/mfshaf7/projects
python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects --check
python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects
python3 scripts/audit_stale_content.py --workspace-root /home/mfshaf7/projects
python3 -m py_compile scripts/audit_workspace_layout.py scripts/audit_stale_content.py scripts/contracts_lib.py scripts/install_skills.py scripts/sync_workspace_root.py scripts/validate_component_contracts.py scripts/validate_contracts.py scripts/validate_cross_repo_truth.py scripts/validate_repo_structure.py
```
