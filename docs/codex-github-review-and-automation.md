# Codex GitHub Review And Automation

This is the primary operator surface for workspace-level Codex GitHub review,
PR flow, and the read-only daily control-plane summary.

Use this procedure when you want workspace changes to be reviewable,
machine-checked, and repeatable instead of reconstructed from chat.

## Scope

This procedure covers:

- repo-level Codex GitHub review expectations
- the required PR flow for meaningful git-tracked changes
- the read-only workspace control-plane summary
- how repeated review/control failures feed the self-improvement loop

This procedure does not create a new governed AI runtime path and does not
replace owner-repo runbooks.

## Preflight

Before relying on workspace-level guidance, verify the local
`workspace-governance` checkout against `origin/main`:

```bash
python3 scripts/check_remote_alignment.py --workspace-root /home/mfshaf7/projects --repo-name workspace-governance --refresh-remote
```

If the checkout is behind or diverged, update the local repo before treating
the workspace control plane as fresh truth.

If the checkout is ahead on a feature branch, say that explicitly in the work
summary or PR because future sessions are no longer reading plain `main`.

## Repo Preparation Model

Codex GitHub review is only high-signal after each active repo has:

- repo-specific `## Review guidelines` in the relevant `AGENTS.md`
- `CODEOWNERS`
- a PR template that captures governance evidence and Codex review status
- a validation workflow that can be used as a required status check

Those controls are validated from `workspace-governance` by:

```bash
python3 scripts/validate_codex_review_controls.py --workspace-root /home/mfshaf7/projects
```

## Standard PR Flow

1. Create a repo branch for the meaningful change.
2. Update docs, contracts, or evidence in the owner repo at the same time as
   the code or workflow change.
3. Open a PR with the repo's required governance declaration and meaningful
   summary.
4. Request Codex review manually with `@codex review` until the repo has
   stable automatic review enabled.
5. Resolve or explicitly acknowledge the findings in the PR before merge.
6. Merge only after the repo-local checks and required governance checks pass.

## Codex GitHub Review Setup

The repo-owned controls live in Git. The Codex repo toggle does not.

Per active repo, turn on the Codex GitHub integration and enable:

- `Code review`
- `Automatic reviews` after the manual rollout is producing useful findings

Use a manual kickoff comment such as:

```text
@codex review for security regressions, owner-boundary drift, missing validation, and missing governance evidence
```

The repo-specific `## Review guidelines` teach Codex which workflow and control
regressions should be treated as `P1`.

## Read-Only Control-Plane Summary

Use the read-only summary to check workspace control-plane health without
mutating contracts, repos, or environments:

```bash
python3 scripts/workspace_control_plane_summary.py --workspace-root /home/mfshaf7/projects --refresh-remote
```

The summary checks:

- remote freshness for the local `workspace-governance` control plane
- workspace-root sync state
- live skill install sync
- Codex review-control compliance
- stale-content drift
- workspace audit
- deterministic improvement-signal audit
- improvement-candidate validity
- learning-closure validity

The summary is findings-only. It does not open PRs, change contracts, write
generated artifacts, or touch governed environments.

## Self-Improvement Route

If the control-plane summary or repo review controls uncover a repeated failure
class, update the improvement system instead of leaving the lesson in chat.

Use:

```bash
python3 scripts/record_improvement_candidate.py --workspace-root /home/mfshaf7/projects --slug <candidate-slug>
```

Then validate the learning layers:

```bash
python3 scripts/validate_improvement_candidates.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_learning_closure.py --workspace-root /home/mfshaf7/projects
```

## Out Of Scope

This wave does not include:

- a new governed AI runtime path
- broad new skill creation beyond startup-skill wiring
- new control planes
- write-capable automation
- pretending OpenProject already has its own governed promotion flow
