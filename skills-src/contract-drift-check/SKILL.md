---
name: contract-drift-check
description: Use when reviewing workspace consistency, stale ownership language, cross-repo drift, or contract mismatch between active repos and the workspace governance model.
---

# Contract Drift Check

Use this skill when the task is an audit, review, or consistency check.

## Read First

- `contracts/README.md`
- `contracts/vocabulary.yaml`
- `contracts/repo-rules/`
- `scripts/README.md`

## Run

```bash
python3 scripts/validate_contracts.py --repo-root .
python3 scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --check-generated
python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects
python3 scripts/audit_stale_content.py --workspace-root /home/mfshaf7/projects
```

## Output

Report:

- contract model errors
- cross-repo ownership drift
- stale or retired language in active docs
- generated artifact drift

Prefer exact repo and file references over generic summary.
