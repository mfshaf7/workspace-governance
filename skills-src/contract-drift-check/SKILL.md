---
name: contract-drift-check
description: Use when reviewing workspace consistency, stale ownership language, cross-repo drift, or contract mismatch between active repos and the workspace governance model.
---

# Contract Drift Check

Use this skill when the task is an audit, review, or consistency check.

## Read First

- `workspace-root/ARCHITECTURE.md`
- `contracts/README.md`
- `contracts/vocabulary.yaml`
- `contracts/repo-rules/`
- `contracts/skills.yaml`
- `docs/instruction-and-skill-governance.md`
- `scripts/README.md`

## Run

```bash
python3 scripts/validate_contracts.py --repo-root .
python3 scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --check-generated
python3 scripts/validate_codex_review_controls.py --workspace-root /home/mfshaf7/projects
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects --check
python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects
python3 scripts/audit_stale_content.py --workspace-root /home/mfshaf7/projects
```

If the workspace is being described as clean or restart-ready, also require the
WGCF clean-state scope to pass:

```bash
wgcf catalog check --workspace-root /home/mfshaf7/projects --scope authority:workspace-clean-state --profile dev-integration --tier scoped --operator-approved
```

## Output

Report:

- contract model errors
- cross-repo ownership drift
- stale or retired language in active docs
- generated artifact drift
- Codex review-control drift
- installed skill drift
- AGENTS or skill guidance that contradicts current WGCF, CGG, OOS, or ART
  operator-path contracts

Prefer exact repo and file references over generic summary.
