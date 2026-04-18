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
- registered repo-owned skill inventory
- workspace audit and sync tooling
- after-action reviews and learning-closure validation
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
  - `contracts/intake-register.yaml` when a new entrant is still out-of-scope,
    proposed, or admitted instead of fully active
  - `contracts/repo-rules/`
  - `workspace-root/README.md`
  - `workspace-root/AGENTS.md`
  - `scripts/audit_workspace_layout.py`
- New repos, products, and components must be classified through the intake
  layer first. Do not silently let them appear in the workspace and only wire
  them into governance later.
- `dev-integration` is a workspace-standardized fast-iteration lane, not a
  governed delivery lane. Use it when operator-facing workflow design,
  cross-repo API iteration, or canonical-backend write paths are still moving
  too quickly for governed stage rehearsal.
- `dev-integration` profiles now have an admission lifecycle:
  - `proposed`
  - `active`
  - `suspended`
  - `retired`
- only `active` profiles are self-serve launchable from the shared runner
- the profile request/admission model stays generic here, even if the current
  request surface adapter is OpenProject
- The lane standard lives here, but the runtime is not owned here:
  - `workspace-governance` owns the standard and handoff rules
  - `platform-engineering` owns the shared local-k3s runner
  - the owner repo owns its concrete profile
- `dev-integration` profiles must capture both runtime shape and source state.
  Profiles define the environment. Branches or worktrees define which local
  repo state is mounted into that environment. The session manifest must record
  both.
- AI may assist intake classification, but `decision_source: ai-suggested` is
  only valid when the entry carries governed-profile evidence from the approved
  `platform-engineering` model-profile registry and still records operator
  acceptance.
- If the owner model, product map, component map, or review/evidence model
  changes, update the affected files under `contracts/` and refresh
  `generated/` through `scripts/validate_cross_repo_truth.py --write-generated`.
- If the registered skill inventory changes, update `contracts/skills.yaml`,
  the owner repo skill source, and rerun `scripts/install_skills.py`.
- If a major miss, late discovery, or repeated workflow problem is uncovered,
  record an after-action under `reviews/after-action/` and either close it with
  linked durable controls or leave it explicitly open with owner and due date.
- Do not treat conversational hindsight as a durable fix. Repeated failure
  classes should leave behind a real control change such as a validator, skill
  update, contract update, workflow update, runbook, or test.
- Repos that declare `requires_security_bindings: true` in `contracts/repos.yaml`
  must keep concrete `security-architecture` artifact references, review
  checklist references, and review-output scope references in their root docs.
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
python3 scripts/validate_intake.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_developer_integration.py --repo-root . --workspace-root /home/mfshaf7/projects
python3 scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --write-generated
python3 scripts/validate_security_bindings.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_component_contracts.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_learning_closure.py --workspace-root /home/mfshaf7/projects
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects --target-root /tmp/workspace-skills
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects --target-root /tmp/workspace-skills --check
python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects --check
python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects
python3 scripts/audit_stale_content.py --workspace-root /home/mfshaf7/projects
python3 -m py_compile scripts/audit_workspace_layout.py scripts/audit_stale_content.py scripts/contracts_lib.py scripts/install_skills.py scripts/record_after_action.py scripts/scaffold_intake.py scripts/sync_workspace_root.py scripts/validate_component_contracts.py scripts/validate_contracts.py scripts/validate_cross_repo_truth.py scripts/validate_intake.py scripts/validate_learning_closure.py scripts/validate_repo_structure.py scripts/validate_security_bindings.py
```
