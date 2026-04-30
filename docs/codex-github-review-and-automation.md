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

1. Choose the Landing Unit: the smallest source change that should be
   reviewed, merged, deployed, and rolled back together.
2. Create one repo branch for the Landing Unit, not one branch for every ART
   child item.
3. Update docs, contracts, or evidence in the owner repo at the same time as
   the code or workflow change.
4. Open a PR with the repo's required governance declaration, meaningful
   summary, and draft Review Packet coverage for the ART items it supports.
5. Fill the Review Packet with `open_pr` evidence, changed-surface
   explanations, tests, validations, rollback boundary, and item-level
   completion mapping.
6. Run `npm run art -- review-packet readiness <packet.json>` before merge.
   Do not merge while readiness fails; fix the same PR or explicitly split the
   Landing Unit.
7. Request Codex review manually with `@codex review` until the repo has
   stable automatic review enabled.
8. Resolve or explicitly acknowledge the findings in the PR before merge.
9. Merge only after readiness, repo-local checks, and required governance checks
   pass.
10. After merge, finalize the Review Packet with PR, commit, validation, and
   rollback evidence before closing covered source-backed ART items.
11. After closeout, retire the local branch, remote branch, and any temporary
   worktrees unless an open PR or a documented exception still requires them.

## Landing Units And Review Packets

A Landing Unit may cover one ART item, several child items, one Feature, or a
small cohesive Epic. It should split when the work has separate repo ownership,
review path, security impact, validation burden, deployment timing, or rollback
scope.

The Review Packet is the evidence bridge from Git or live work back to ART. It
records:

- covered ART items
- repo branches and PRs
- final commit SHAs or direct-land evidence
- validation results
- rollback scope
- live-only or non-source exceptions

Source-backed ART children should close only after a finalized Review Packet
covers them. Several children can close from the same packet. Analysis,
planning, risk handling, live verification, or ART metadata repair can close
with non-source evidence instead of merge evidence.

Pre-merge readiness is separate from post-merge finalization. Use `open_pr`
evidence and `npm run art -- review-packet readiness <packet.json>` while the
PR is still open. After merge, update the packet to `merged_pr`, add the merge
commit, and finalize it.

Direct-to-main landing is allowed only when the operator explicitly approves it
or the owning repo documents it. Record that exception in the Review Packet;
do not pretend it followed the PR path.

The Review Packet template lives at:

- `templates/review-packet/TEMPLATE.md`

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
- branch lifecycle hygiene, including stale remote branches that no longer back
  an open PR
- workspace audit
- deterministic improvement-signal audit
- improvement-candidate validity
- learning-closure validity

The summary is findings-only. It does not open PRs, change contracts, write
generated artifacts, or touch governed environments.

The branch lifecycle portion expects authenticated `gh` access so it can tell
an open-PR remote branch from stale remote residue.

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
