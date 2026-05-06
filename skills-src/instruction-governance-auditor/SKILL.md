---
name: instruction-governance-auditor
description: Use when reviewing, restructuring, creating, removing, or validating AGENTS.md files, Codex skills, installed skill state, or workspace instruction governance so guidance stays coherent with current contracts and runtime behavior.
---

# Instruction Governance Auditor

Use this before changing AGENTS files, skill source, skill registration, or
installed skill behavior.

## Read First

- `docs/instruction-and-skill-governance.md`
- `workspace-root/ARCHITECTURE.md`
- `workspace-root/AGENTS.md`
- `contracts/skills.yaml`
- `contracts/repos.yaml`
- `contracts/repo-rules/`

## Workflow

1. Prove remote freshness for `workspace-governance`.
2. Inventory active repo `AGENTS.md` files and registered skill sources.
3. Verify installed managed skills match registered source.
4. Classify each finding as `keep`, `extend`, `replace`, `remove`, or `new`.
5. Prefer extending an existing skill or primary operator surface before adding
   a new skill.
6. Keep AGENTS files short and authority-focused; move repeatable procedure to
   skills or primary operator docs.
7. If skill source or registration changes, reinstall skills and verify the
   live install.
8. If workspace-root files change, sync the root and verify the live root.
9. Validate contracts, cross-repo truth, Codex review controls, stale content,
   and workspace layout before closeout.

## Guardrails

- Do not treat source skill changes as complete until live installed skills are
  refreshed and checked.
- Do not leave stale normal-path instructions for direct Rails, raw OpenProject
  admin, or raw `kubectl exec ... node -e ...` ART work.
- Do not create a new skill just because guidance feels broad; first prove the
  existing skill inventory cannot cover it cleanly.
- Do not bury owner-boundary changes in AGENTS prose only; update the relevant
  machine-readable contracts too.
- Do not call the workspace clean unless the WGCF clean-state scope passes.
