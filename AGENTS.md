# Workspace Governance Agent Notes

This repository owns the workspace-level control plane for
`/home/mfshaf7/projects`.

Keep it focused on cross-repo governance. Do not let it turn into another
delivery repo.

## Read First

- `README.md`
- `docs/codex-github-review-and-automation.md`
- `docs/recommendation-preflight.md`
- `docs/troubleshooting-preflight.md`
- `docs/delegated-execution.md`
- `docs/self-improvement-escalation.md`
- `workspace-root/ARCHITECTURE.md`
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
- after-action reviews, improvement-candidate triage, and self-improvement validation
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
- When workspace-level recommendations depend on fresh control-plane truth, run
  `python3 scripts/check_remote_alignment.py --workspace-root /home/mfshaf7/projects --repo-name workspace-governance --refresh-remote`
  first and say explicitly if the checkout is ahead, behind, or diverged from
  `origin/main`.
- When a request introduces a new product, shared component, control plane, or
  architecture-shaping feature, the first step is discussion and framing, not
  implementation.
- After changing `workspace-root/` or `scripts/audit_workspace_layout.py`, you
  must run `scripts/sync_workspace_root.py` before the work is complete.
- A workspace-root governance change is not complete until:
  - the canonical files are updated in this repo
  - the live workspace root has been re-synced
  - the sync and workspace audit both pass
- For meaningful git-tracked changes that are intended to land, use a repo
  branch and pull request with a meaningful summary instead of committing
  directly to `main`, unless the user explicitly asks for direct landing or the
  repo's documented workflow says otherwise.
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
- If a change creates or materially changes an operator-facing workflow,
  command family, request path, approval path, or other day-to-day operator
  procedure, the work is not complete until one primary operator instruction
  surface exists in the owning repo.
- If a serious failure or unexpected runtime behavior is being diagnosed, use
  `docs/troubleshooting-preflight.md` before deeper workaround analysis,
  redesign proposals, or code-level blame.
- If a meaningful repeated miss, operator callout, or active-work drift becomes
  visible, use `docs/self-improvement-escalation.md` before continuing normal
  execution.
- If work is going to use delegated execution, use
  `docs/delegated-execution.md` first and keep the main-agent-only authority,
  packet, write-scope, and journal rules intact.
- Contracts, templates, standards, and policy docs may support that workflow,
  but they do not replace the primary operator instruction surface.
- If the operator has to reconstruct the procedure from scattered policy,
  template, and standards files, the workflow is still incomplete.
- Workspace-level docs should point to the primary operator instruction
  surface, not force the operator to infer it from contract internals.
- Git-tracked docs outside `workspace-root/` must not use markdown navigation
  links to `/home/mfshaf7/projects/...`. Use repo-relative links for same-repo
  docs and web-safe links for cross-repo docs instead.
- AI may assist intake classification, but `decision_source: ai-suggested` is
  only valid when the entry carries governed-profile evidence from the approved
  `platform-engineering` model-profile registry and still records operator
  acceptance.
- If the owner model, product map, component map, or review/evidence model
  changes, update the affected files under `contracts/` and refresh
  `generated/` through `scripts/validate_cross_repo_truth.py --write-generated`.
- If the registered skill inventory changes, update `contracts/skills.yaml`,
  the owner repo skill source, rerun `scripts/install_skills.py`, and verify
  that the live installed skills under `~/.codex/skills` are back in sync.
- Skill-source changes affect future sessions only after the installed skill
  tree has been refreshed. Do not treat merged skill source alone as a complete
  runtime behavior change.
- If a broad workspace-level discussion is being resumed after a restart, check
  local `docs/archive/session-handoff-current.md` if it exists before assuming
  the chat thread is the only source of pending context.
- If a session is likely to restart while meaningful workspace-level pending
  items remain, create or refresh the single local-only handoff record at
  `docs/archive/session-handoff-current.md` before closing.
- Session handoffs are ignored local continuity state, not durable Git-tracked
  archive records.
- Keep zero or one session handoff at a time. Remove stale
  `docs/archive/session-handoff-*.md` records instead of accumulating dated
  files.
- Before telling the operator that a restart is safe or recommended, run an
  explicit restart-readiness check.
- If meaningful workspace-level local-only state remains, refresh the current
  handoff first and only then recommend the restart.
- If the workspace is being described as clean or restart-ready, require
  `python3 scripts/audit_branch_lifecycle.py --workspace-root /home/mfshaf7/projects --include-remote --check-clean`
  to pass before saying so.
- Remote non-`main` branches are only allowed when they back an open PR or
  have a documented exception in `contracts/exceptions.yaml`.
- Do not wait for the operator to ask whether a handoff should be written.
- This is required especially when:
  - the user is being told to restart so new skills or instructions will load
  - cross-repo architecture or workflow discussion remains intentionally
    deferred
  - there are explicit pending follow-ups that should survive chat reset
- If a workspace-level validator or audit reads remote `main` from another
  owner repo, sequence the dependent owner-repo merges first and land the
  control-plane repo last.
- If that sequence is violated, fix the merge order and rerun validation
  honestly. Do not represent a no-op rerun commit as the real fix.
- If work spans multiple repos and is meant to land through PRs, state the PR
  merge order explicitly while the work is in flight and do not leave the
  branch/PR plan only in chat memory.
- If a major miss, late discovery, or repeated workflow problem is uncovered,
  do not jump straight from chat to after-action closure.
- Record or update an improvement candidate under
  `reviews/improvement-candidates/` as soon as the signal is real.
- If the user explicitly says something is a repeated mistake, that is a
  mandatory candidate signal.
- If the user calls the work half-baked, incomplete, or says the miss should
  have been caught already, treat that as the same class of mandatory
  self-improvement signal.
- Improvement candidate capture should be automatic once the signal is real.
- If active work becomes half-finished at the planning, control, or completion
  layer, record or update the improvement candidate before continuing normal
  execution.
- If a simpler root cause is discovered late because earlier troubleshooting
  layers were skipped, treat that as a mandatory self-improvement signal and
  route it through the improvement-candidate layer.
- If a lesson that was already treated as closed regresses in active work,
  record the new candidate as a regression and link it to the earlier closed
  candidate or after-action. Do not treat it as an unrelated new miss.
- After creating or editing any structured governance record, run:
  - `python3 scripts/validate_structured_record.py <record-path> --workspace-root /home/mfshaf7/projects`
  before continuing normal work. This applies to improvement candidates,
  after-actions, delegation journals, workspace contracts, and owner-repo
  change records.
- If an owner-repo change record declares `security_evidence`, that preflight
  must also prove the generated `security-architecture` change-record index is
  current before closure or merge sequencing continues.
- Do not automatically implement the durable fix just because the candidate
  exists.
- After recording the candidate, propose the best fix shape, justify why that
  fix is the best option, and wait for operator approval before landing the
  control change.
- If the lesson and control shape are already clear, record the after-action
  too and close the candidate through the linked review or direct controls.
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

## Review guidelines

For Codex GitHub review, treat the following as `P1` when they plausibly
regress the workspace control plane:

- contract drift, generated artifact drift, or repo-rule drift that leaves the
  machine-readable workspace model out of sync with active repo behavior
- workspace-root sync or architecture-bootstrap regressions that would make a
  new session read stale control-plane guidance
- live installed skills or managed-skill sync drift after `skills-src/` or
  `contracts/skills.yaml` changes
- missing improvement candidate, after-action, or durable control updates after
  a repeated mistake or deterministic review/control failure
- branch lifecycle control regressions that would let stale local branches,
  pinned worktrees, or remote branches without an open PR linger after merge or
  while a clean-state claim is being made
- Codex review-control regressions that remove repo-specific review guidance,
  PR evidence surfaces, or validation coverage from active repos

## Validation

Run these after structural changes:

```bash
python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_repo_structure.py --repo-root .
python3 scripts/validate_contracts.py --repo-root .
python3 scripts/validate_delegation_journal.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_intake.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_developer_integration.py --repo-root . --workspace-root /home/mfshaf7/projects
python3 scripts/validate_improvement_candidates.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_structured_record.py reviews/improvement-candidates/<record>.yaml --workspace-root /home/mfshaf7/projects
python3 scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --write-generated
python3 scripts/validate_security_bindings.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_component_contracts.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_review_coverage.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_security_change_record_lanes.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_codex_review_controls.py --workspace-root /home/mfshaf7/projects
python3 scripts/audit_improvement_signals.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_learning_closure.py --workspace-root /home/mfshaf7/projects
python3 scripts/audit_branch_lifecycle.py --workspace-root /home/mfshaf7/projects
python3 scripts/audit_branch_lifecycle.py --workspace-root /home/mfshaf7/projects --include-remote
python3 scripts/audit_branch_lifecycle.py --workspace-root /home/mfshaf7/projects --include-remote --check-clean
python3 scripts/workspace_control_plane_summary.py --workspace-root /home/mfshaf7/projects --refresh-remote
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects --check
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects --target-root /tmp/workspace-skills
python3 scripts/install_skills.py --workspace-root /home/mfshaf7/projects --target-root /tmp/workspace-skills --check
python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects --check
python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects
python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects --check-clean
python3 scripts/audit_stale_content.py --workspace-root /home/mfshaf7/projects
python3 -m py_compile scripts/audit_branch_lifecycle.py scripts/audit_workspace_layout.py scripts/audit_stale_content.py scripts/audit_improvement_signals.py scripts/check_remote_alignment.py scripts/contracts_lib.py scripts/install_skills.py scripts/record_after_action.py scripts/record_improvement_candidate.py scripts/scaffold_intake.py scripts/sync_workspace_root.py scripts/validate_codex_review_controls.py scripts/validate_component_contracts.py scripts/validate_contracts.py scripts/validate_cross_repo_truth.py scripts/validate_developer_integration.py scripts/validate_improvement_candidates.py scripts/validate_intake.py scripts/validate_learning_closure.py scripts/validate_repo_structure.py scripts/validate_review_coverage.py scripts/validate_security_bindings.py scripts/validate_security_change_record_lanes.py scripts/validate_structured_record.py scripts/workspace_control_plane_summary.py
```
