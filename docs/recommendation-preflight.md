# Recommendation Preflight

Use this preflight before proposing a new workspace-level control, workflow,
validator, skill, product surface, or architecture capability.

The purpose is to prevent redundant or shallow recommendations caused by
under-reading controls that already exist.

## When To Run

Run this when a request asks for:

- a broad plan or architecture direction
- a new control, workflow, validator, skill, or operator surface
- a replacement for an existing process
- a claim that "we need a new way" to handle an already governed area

For a small implementation detail inside one known owner repo, use the repo's
normal guidance instead.

## Required Checks

1. Prove remote freshness when workspace control truth matters:

```bash
python3 scripts/check_remote_alignment.py --workspace-root /home/mfshaf7/projects --repo-name workspace-governance --refresh-remote
```

2. Read the current architecture and routing surface:

- `workspace-root/ARCHITECTURE.md`
- `workspace-root/AGENTS.md`
- `docs/work-home-routing-contract.md`

3. Check machine-readable control inventory:

- `contracts/repos.yaml`
- `contracts/components.yaml`
- `contracts/products.yaml`
- `contracts/repo-rules/`
- `contracts/skills.yaml`
- `contracts/developer-integration-profiles.yaml`

4. Check existing operator surfaces before inventing a new one:

- repo-local `AGENTS.md`
- repo-local `README.md`
- primary operator surfaces declared in `contracts/repo-rules/`
- active `dev-integration` profile READMEs when the request involves fast
  workflow or API iteration

5. Check whether the request is already covered by a skill:

```bash
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects --check
```

6. State the recommendation posture explicitly:

- `reuse`: an existing control already covers the need
- `extend`: an existing control is the right owner but needs more coverage
- `replace`: the existing control is wrong or obsolete
- `new`: no existing owner/control fits

Do not recommend `new` without naming the checked existing controls and why
they are insufficient.

## Output Shape

The recommendation should include:

- owner repo
- existing controls checked
- chosen posture: `reuse`, `extend`, `replace`, or `new`
- work-home classification
- validation or evidence required before the recommendation can be treated as
  implemented
