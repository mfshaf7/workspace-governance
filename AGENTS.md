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
- workspace audit and sync tooling
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
- After changing `workspace-root/` or `scripts/audit_workspace_layout.py`, run
  `scripts/sync_workspace_root.py` so the live workspace root stays aligned.
- If the active repo inventory changes, update:
  - `workspace-root/README.md`
  - `workspace-root/AGENTS.md`
  - `scripts/audit_workspace_layout.py`
- If repo boundaries change, update the owning repo docs in the same work. This
  repo documents the boundary; it does not replace owner-repo documentation.
- Treat `openclaw-isolated-deployment/` as retired unless the retirement
  decision is deliberately reversed. Do not route active work there.

## Validation

Run these after structural changes:

```bash
python3 scripts/validate_repo_structure.py --repo-root .
python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects --check
python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects
python3 -m py_compile scripts/audit_workspace_layout.py scripts/sync_workspace_root.py scripts/validate_repo_structure.py
```
