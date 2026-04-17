# Workspace Governance

This repository is the cross-repo governance and routing layer for the
`/home/mfshaf7/projects` workspace.

It owns the canonical workspace-level guidance and audit tooling that are
materialized into the local workspace root for day-to-day operator use.

The workspace is multi-product. This repo should not drift into OpenClaw-only
language when the actual workspace governs shared platform services plus
multiple products.

It now also owns the machine-readable control-plane contracts that describe the
active repo map, product maturity, component inventory, dependency semantics,
review obligations, security-binding expectations, stale vocabulary, and the
after-action learning loop.

It also owns the intake layer that forces new repos, products, and components
to be explicitly classified as out-of-scope, proposed, or admitted before they
quietly drift into the governed system. The goal is not to govern everything.
The goal is to make the decision explicit before anything new becomes part of
the operator-facing control plane by accident.

## What This Repository Owns

- canonical source for the workspace-root `README.md` and `AGENTS.md`
- contract source under `contracts/`
- generated resolved governance artifacts under `generated/`
- workspace-level skill source under `skills-src/`
- governed after-action review records under `reviews/`
- workspace audit and sync tooling
- cross-repo owner-map and routing conventions
- workspace-level validation that the active repos remain aligned

## What This Repository Does Not Own

- platform manifests, Argo apps, or environment contracts
- product source, runtime packaging, or host-runtime implementation
- repo-local operator runbooks
- security standards or review outputs

Those stay in the owning repos:

- `platform-engineering/`
- `openclaw-runtime-distribution/`
- `openclaw-telegram-enhanced/`
- `openclaw-host-bridge/`
- `security-architecture/`

## Repository Layout

- `workspace-root/`
  - canonical copies of the files synced into `/home/mfshaf7/projects`
- `contracts/`
  - machine-readable repo, product, component, lifecycle, evidence, review, and
    vocabulary contracts plus intake policy and intake register
- `generated/`
  - resolved owner map, dependency graph, stale-content rules, and system map
- `skills-src/`
  - workspace-level skill source directories owned here
- `reviews/`
  - after-action records and learning-closure evidence
- `templates/`
  - scaffolds for new governance objects
- `scripts/`
  - audit, sync, and repo-structure validation helpers
- `.github/`
  - repo ownership and validation workflow metadata

## Operating Model

1. Edit the canonical files in this repo.
2. Sync them into the live workspace root.
3. Run repo-local validation.
4. Run the workspace audit against `/home/mfshaf7/projects`.
5. Reinstall or verify the registered skills if skill source or registry state
   changed.
6. Validate learning closure if after-action records or closure controls
   changed.
7. If repo ownership or routing changed, update the owning repo docs in the
   same work.

## Sync Model

The workspace root is not a Git repo, but local tools and future sessions still
read these paths directly:

- `/home/mfshaf7/projects/README.md`
- `/home/mfshaf7/projects/AGENTS.md`
- `/home/mfshaf7/projects/_workspace_tools/audit_workspace_layout.py`

This repo keeps the canonical copies in:

- `workspace-root/README.md`
- `workspace-root/AGENTS.md`
- `scripts/audit_workspace_layout.py`

Use `scripts/sync_workspace_root.py` to materialize the canonical files back
into the workspace root.

A workspace-governance change is not complete until that sync has been run and
the workspace audit passes against the live root.

## Validation

Run these from this repo:

```bash
python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_repo_structure.py --repo-root .
python3 scripts/validate_contracts.py --repo-root .
python3 scripts/validate_intake.py --workspace-root /home/mfshaf7/projects
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

## Read First

- [AGENTS.md](AGENTS.md)
- [contracts/README.md](contracts/README.md)
- [contracts/skills.yaml](contracts/skills.yaml)
- [reviews/after-action/README.md](reviews/after-action/README.md)
- [workspace-root/README.md](workspace-root/README.md)
- [workspace-root/AGENTS.md](workspace-root/AGENTS.md)
- [scripts/README.md](scripts/README.md)
