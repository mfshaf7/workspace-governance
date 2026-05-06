# Instruction and Skill Governance

This is the primary operator surface for changing workspace `AGENTS.md` files
and registered Codex skills.

The goal is to keep runtime instruction behavior coherent, fast, and aligned
with the current control-plane state. Do not treat AGENTS and skills as loose
notes. They are active operator controls.

## Authority Model

- `workspace-governance` owns workspace-root guidance, workspace-level skill
  source, the registered skill inventory, sync tooling, install tooling, and
  validation of the workspace instruction surface.
- Repo-local `AGENTS.md` files own repo boundary, high-risk review posture, and
  the minimum local reading path for that repo.
- Owner repos may own repo-specific skill source when the skill is domain
  specific, but registration and installation still flow through
  `workspace-governance/contracts/skills.yaml`.
- `~/.codex/skills` is live runtime state. Source changes are not effective for
  future sessions until installed skills are refreshed and verified.

## Shape Rules

- Keep root `AGENTS.md` focused on routing, owner boundaries, hard gates, and
  validation entrypoints.
- Keep repo-local `AGENTS.md` focused on repo ownership, non-ownership,
  primary surfaces, review risks, and validation commands.
- Put detailed repeatable procedure in a primary operator doc or a skill, not
  as duplicated long-form guidance across many AGENTS files.
- Skills should be triggerable workflows. They should be concise, specific, and
  only load detailed references when needed.
- If a skill grows beyond one coherent workflow, split it or move detailed
  variants into a referenced doc.

## Required Audit Before Changing

Before editing AGENTS or skills:

1. Prove fresh workspace-control truth:
   `python3 scripts/check_remote_alignment.py --workspace-root /home/mfshaf7/projects --repo-name workspace-governance --refresh-remote`
2. Read:
   - `workspace-root/ARCHITECTURE.md`
   - `workspace-root/AGENTS.md`
   - `contracts/skills.yaml`
   - `contracts/repos.yaml`
   - `contracts/repo-rules/`
   - this document
3. Inventory active guidance:
   - every active repo `AGENTS.md`
   - every registered skill source
   - installed managed skills under `~/.codex/skills`
4. Classify each finding:
   - `keep`: still correct and useful
   - `extend`: correct owner, missing current coverage
   - `replace`: active guidance is wrong, stale, or contradictory
   - `remove`: obsolete, duplicated, or belongs in history only
   - `new`: no existing AGENTS rule, doc, or skill covers the need

Do not create a new skill before proving why an existing skill or primary
operator surface cannot be extended.

## Hard Drift Checks

Treat these as blocking findings:

- root guidance disagrees with repo-local ownership
- installed skill differs from registered source
- skill source changed but `contracts/skills.yaml` was not updated when needed
- root `AGENTS.md`, `README.md`, or `ARCHITECTURE.md` was edited directly
  instead of through `workspace-governance/workspace-root/`
- current guidance says to use direct Rails, raw OpenProject admin paths, or
  raw `kubectl exec ... node -e ...` as the normal ART path
- CGG is described as a WGCF, OOS, platform, security, or LLM-gateway
  replacement
- WGCF is described as an ART mutation authority, security acceptance owner, or
  platform release authority
- `dev-integration` is described as governed stage or production evidence
- retired repos or commands appear in active routing guidance

## Validation

After changing AGENTS, skill source, or skill inventory, run the applicable
checks before closeout:

```bash
python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_repo_structure.py --repo-root .
python3 scripts/validate_contracts.py --repo-root .
python3 scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --write-generated
python3 scripts/validate_codex_review_controls.py --workspace-root /home/mfshaf7/projects
python3 scripts/audit_stale_content.py --workspace-root /home/mfshaf7/projects
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects --check
python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects
```

If the workspace is described as clean or restart-ready, the WGCF clean-state
scope must also pass:

```bash
wgcf catalog check --workspace-root /home/mfshaf7/projects --scope authority:workspace-clean-state --profile dev-integration --tier scoped --operator-approved
```

Use the direct branch-layout validators only as rollback/source-authority
entrypoints when WGCF is blocked or the scope is not admitted to WGCF.
