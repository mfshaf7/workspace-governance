# Workspace Root AGENTS

> Canonical source: `workspace-governance/workspace-root/AGENTS.md`
>
> This file is synced into `/home/mfshaf7/projects/AGENTS.md` by
> `workspace-governance/scripts/sync_workspace_root.py`.

This file is the workspace routing layer for `/home/mfshaf7/projects`.

It owns cross-repo routing, workspace-level governance expectations, and the
current owner map. It does not own product-specific incident lore or repo-local
implementation details.

For immediate architecture orientation in a new session, read
`/home/mfshaf7/projects/ARCHITECTURE.md` first. Use this file to route the
task after the system shape is clear.

## Default Perspective

Operate first as:

- enterprise architect
- cybersecurity architect
- senior lead auditor

That means:

- prefer durable ownership and control-plane clarity over local convenience
- distinguish documented control, implemented control, and validated operating
  control
- treat repeated operator pain as an architecture problem until proven
  otherwise
- preserve reviewability, attestation, rollback, and auditability

## Start Here

0. If this is a new workspace-level session, read:
   - `/home/mfshaf7/projects/ARCHITECTURE.md`
0.5 If workspace-level recommendations depend on fresh control-plane truth, run:
   - `python3 /home/mfshaf7/projects/workspace-governance/scripts/check_remote_alignment.py --workspace-root /home/mfshaf7/projects --repo-name workspace-governance --refresh-remote`
0.6 If a serious failure is being diagnosed, read:
   - `/home/mfshaf7/projects/workspace-governance/docs/troubleshooting-preflight.md`
0.7 Before doing meaningful work whose home is not already proven, classify it
   through:
   - `/home/mfshaf7/projects/workspace-governance/docs/work-home-routing-contract.md`
0.8 If a new workspace-level control, workflow, validator, skill, product
    surface, or architecture capability is being proposed, read:
   - `/home/mfshaf7/projects/workspace-governance/docs/recommendation-preflight.md`
1. Read the local repo `AGENTS.md`.
2. Read the local repo `README.md`.
3. Use this file only to route the task to the correct owner.
4. Use the workspace audit when repo inventory or workspace governance changed:
   - `/home/mfshaf7/projects/_workspace_tools/audit_workspace_layout.py`
5. When cross-repo ownership or vocabulary truth matters, use the machine-readable
   contracts in:
   - `/home/mfshaf7/projects/workspace-governance/contracts/`

## Current Owner Map

- `workspace-governance/`
  - owns workspace-root `README.md` and `AGENTS.md`, workspace contracts,
    generated governance artifacts, workspace audit tooling, and cross-repo
    routing rules
  - read first:
    - `workspace-governance/AGENTS.md`
    - `workspace-governance/README.md`
- `workspace-governance-control-fabric/`
  - owns runtime implementation for the Workspace Governance Control Fabric,
    including governance graph, validation planning, admission/readiness
    evaluation, receipts, ledger, and control-fabric API/worker/CLI surfaces
  - does not own workspace contracts, workspace-root guidance, platform
    deployment authority, security standards, or Workspace Delivery ART
    work-state truth
  - read first:
    - `workspace-governance-control-fabric/AGENTS.md`
    - `workspace-governance-control-fabric/README.md`
- `platform-engineering/`
  - owns shared platform structure, environment contracts, Argo-managed state,
    release governance, and product integration docs
  - if the task is product-specific inside this repo, route to
    `platform-engineering/products/<product>/AGENTS.md`
  - read first:
    - `platform-engineering/AGENTS.md`
    - `platform-engineering/README.md`
- `openclaw-runtime-distribution/`
  - owns the active OpenClaw runtime composition path, current packaged
    `host-control-openclaw-plugin`, and distribution-specific verification
  - read first:
    - `openclaw-runtime-distribution/AGENTS.md`
    - `openclaw-runtime-distribution/README.md`
- `openclaw-telegram-enhanced/`
  - owns canonical Telegram behavior, routing, delivery, approvals, and
    Telegram tests
  - read first:
    - `openclaw-telegram-enhanced/AGENTS.md`
    - `openclaw-telegram-enhanced/README.md`
- `openclaw-host-bridge/`
  - owns canonical host enforcement, host policy, allowed roots, audit, export
    staging, and WSL/Windows bridge runtime behavior
  - read first:
    - `openclaw-host-bridge/AGENTS.md`
    - `openclaw-host-bridge/README.md`
- `security-architecture/`
  - owns security standards, trust-boundary architecture, review criteria,
    assessment evidence, and AI-governance posture
  - read first:
    - `security-architecture/AGENTS.md`
    - `security-architecture/README.md`
- `operator-orchestration-service/`
  - owns shared operator workflow APIs, broker-backed workflow orchestration,
    bounded AI-assist workflow orchestration, and OpenProject workflow adapters
  - read first:
    - `operator-orchestration-service/AGENTS.md`
    - `operator-orchestration-service/README.md`
- `openclaw-isolated-deployment/`
  - retired archival stub
  - do not route active work here unless the retirement decision is explicitly
    reversed

## First Classification

Before editing, classify the task into one of these buckets:

1. workspace governance or cross-repo owner-boundary issue
2. platform contract, GitOps, shared component, or promotion-flow issue
3. product integration or runtime composition issue
4. shared operator workflow service, broker, or OpenProject workflow adapter issue
5. Telegram behavior issue
6. host enforcement or WSL/Windows bridge issue
7. security or trust-boundary judgment
8. live environment drift under `~/.openclaw`, a running pod, or the host

That classification determines the owner.

Before executing meaningful work, also classify its work-tracking home through
`workspace-governance/docs/work-home-routing-contract.md`:

- accepted initiative work, blockers, risks, scope changes, and completion
  truth belong in the `Workspace Delivery ART`
- owner-repo-only maintenance belongs in the owner repo when it is outside an
  accepted initiative and does not affect shared workflow, platform, security,
  or workspace governance behavior
- new business or architecture ideas start in `Workspace Proposals` before
  decomposition
- repeated workflow misses or control failures are recorded as improvement
  candidates
- plumbing work is classified by impact, not by the word `plumbing`

Use the smallest home that preserves real owner, review, and validation
boundaries. If important work was already done without this classification,
reconcile it after discovery instead of pretending the skipped classification
did not happen.

## Architecture Discussion Gate

Before implementing, stop and discuss with the user first when the request
introduces any of these:

- a new product on the platform
- a new shared platform component or control plane
- a new ingress, gateway, service-mesh, or networking layer
- a new identity, secret-delivery, storage, messaging, or observability
  subsystem
- a new host-control capability or privileged execution path
- a feature with multiple plausible long-term architectures and no clear
  existing pattern

Examples include:

- introducing Envoy for `k3s`
- adding a new product beside the current governed product set
- introducing a new controller that changes delivery or runtime trust

In those cases, do not jump straight into implementation. First frame the
discussion around:

- target role in the architecture
- owner repo or control plane
- trust-boundary impact
- workflow maturity that would exist after the change
- operator surface, access path, and visibility model
- blocker and impediment handling, including whether the workflow records
  `remove`, `workaround`, `accept-risk`, or `defer` decisions with
  justification
- rollout and rollback shape

Only start implementation after that discussion narrows the target design.

## Routing Rules

- Cross-repo routing, workspace repo inventory, workspace-root guidance, and
  audit tooling belong in `workspace-governance/`.
- Governance graph, validation planner, admission/readiness runtime, receipt
  ledger implementation, and control-fabric API/worker/CLI surfaces belong in
  `workspace-governance-control-fabric/` after the governing contracts exist in
  `workspace-governance/`.
- Shared platform docs, Argo, Vault, observability, environment contracts,
  promotion flow, and product integration docs belong in
  `platform-engineering/`.
- Broad stage/prod rehearsal, temporary prod bring-up, and restore-to-baseline
  requests belong in `platform-engineering/`; classify them as
  `product-runtime-drill`, `active-stack-runtime-drill`,
  `environment-complete-runtime-drill`, or `lifecycle-control-drill` before
  execution, and do not default a broad platform rehearsal to OpenClaw-only
  just because OpenClaw has the most mature governed product promotion path.
- Shared operator workflow APIs, broker-backed workflow orchestration, bounded
  AI-assist workflow orchestration, and OpenProject workflow adapters belong in
  `operator-orchestration-service/`.
- OpenClaw runtime packaging and the active packaged
  `host-control-openclaw-plugin` belong in `openclaw-runtime-distribution/`.
- Telegram routing, buttons, media delivery, approvals, and Telegram-only UX
  belong in `openclaw-telegram-enhanced/`.
- Allowed roots, audit, export staging, and real host actions belong in
  `openclaw-host-bridge/`.
- Trust-boundary, auth, secrets, GitOps trust, AI-governance, and security
  review posture belong in `security-architecture/`.
- Live runtime drift is an environment problem first. Repair it if needed, then
  backport the durable fix to the owning repo.

## Workspace Governance Rules

- The workspace root is not a Git repo. The canonical source for its governance
  files now lives in `workspace-governance/`.
- For workspace-level Codex GitHub review, PR flow, and the read-only daily
  control-plane summary, use:
  - `/home/mfshaf7/projects/workspace-governance/docs/codex-github-review-and-automation.md`
- Do not hand-maintain long-lived edits directly in:
  - `/home/mfshaf7/projects/ARCHITECTURE.md`
  - `/home/mfshaf7/projects/README.md`
  - `/home/mfshaf7/projects/AGENTS.md`
  - `/home/mfshaf7/projects/_workspace_tools/audit_workspace_layout.py`
  Update the canonical files in `workspace-governance/` and sync them back.
- After any change to the canonical workspace-root governance files, sync the
  live root immediately with:
  - `python3 /home/mfshaf7/projects/workspace-governance/scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects`
- A workspace-governance change is not complete until the sync has been run and
  the workspace audit passes against the live root.
- For meaningful git-tracked repo changes that are intended to land, use a repo
  branch and pull request with a meaningful summary instead of committing
  directly to `main`, unless the user explicitly asks for direct landing or the
  repo's documented workflow says otherwise.
- Branch by Landing Unit, not by ART child and not automatically by Epic. A
  Landing Unit is the smallest source change that should be reviewed, merged,
  deployed, and rolled back together.
- Before creating a branch, opening a PR, or implementing source-backed ART
  work, record the Landing Unit Decision:
  `feature_single_landing_unit`, `child_isolated_landing_unit`,
  `non_source_child`, or `defer_decision_blocked`.
- Default to `feature_single_landing_unit` when same-Feature children share the
  same owner repo, review path, validation surface, deployment timing, security
  posture, and rollback boundary. Per-child PRs are the exception and require a
  real split reason.
- ART items track delivery state. Landing Units track source landing and
  rollback truth. Review Packets bind landed or explicitly accepted evidence
  back to one or more ART items.
- Source-backed ART children should not be marked `done` until a finalized
  Review Packet covers them with merged PR evidence, approved direct-land
  evidence, or equivalent durable source evidence. Multiple children may close
  from the same Review Packet.
- Before merging source-backed work, fetch the PR base and run the local
  command or command set that is CI-equivalent for the changed surface. When CI
  uses a base-aware validator, the local proof must use the same base-ref shape
  after fetching the base, such as `--against-ref origin/main`. Record the
  command, base ref, and result in the Review Packet validation evidence.
- Non-source ART items such as planning, risk disposition, live verification,
  or metadata repair close with the relevant non-source evidence instead of
  fake merge evidence.
- A Feature or Epic may close only when every child is covered by a finalized
  Review Packet or explicitly marked as non-source evidence only.
- If the registered skill inventory or any workspace-owned skill source
  changes, the work is not complete until the live installed skills under
  `~/.codex/skills` are refreshed and the workspace audit confirms they are in
  sync.
- Skill-source changes affect future sessions only after that install step.
- If a restart is likely while meaningful workspace-level pending items remain,
  create or refresh the single local-only
  `workspace-governance/docs/archive/session-handoff-current.md` record before
  closing the session.
- Session handoffs are ignored local continuity state, not durable Git-tracked
  archive records.
- Keep zero or one session handoff at a time. Remove stale
  `workspace-governance/docs/archive/session-handoff-*.md` records instead of
  accumulating dated files.
- Before telling the operator that a restart is safe or recommended, run an
  explicit restart-readiness check.
- If meaningful workspace-level local-only state remains, refresh the current
  handoff first and only then recommend the restart.
- If the workspace is being described as clean or restart-ready, require the
  WGCF clean-state scope to pass before saying so:
  - `wgcf catalog check --workspace-root /home/mfshaf7/projects --scope authority:workspace-clean-state --profile dev-integration --tier scoped --operator-approved`
- Direct branch-lifecycle or workspace-layout validator commands are rollback
  paths after #536. If WGCF cannot run them, record the blocker or defect before
  using the direct command as evidence.
- Remote non-`main` branches are only allowed when they back an open PR or
  have a documented exception in `workspace-governance/contracts/exceptions.yaml`.
- Do not wait for the operator to ask whether a handoff should be written.
- If the repo inventory, owner map, or routing model changes, update:
  - `workspace-governance/contracts/repos.yaml`
  - `workspace-governance/contracts/intake-register.yaml` when the entrant is
    only out-of-scope, proposed, or admitted
  - `workspace-governance/contracts/repo-rules/`
  - `workspace-governance/workspace-root/README.md`
  - `workspace-governance/workspace-root/AGENTS.md`
  - `workspace-governance/scripts/audit_workspace_layout.py`
- If a retired path, repo, or operator command must never reappear in active
  guidance, update `workspace-governance/contracts/vocabulary.yaml` or the
  affected `workspace-governance/contracts/repo-rules/*.yaml` in the same work.
- If a repo boundary changes, update the owning repo docs in the same work.
- If a workspace-level validator or audit depends on another repo's remote
  `main`, sequence the dependency repo merges first and land the dependent
  control-plane change after them.
- If multiple repos are landing through PRs, make the merge order explicit and
  do not treat local commits, background pushes, or unreviewed direct-to-`main`
  landings as complete.
- New repos, products, and components must be classified through the intake
  layer before they become part of the governed active model. Not everything
  must be governed, but everything new must be classified.
- `dev-integration` is the fast local iteration lane. It is standardized at
  the workspace layer, but it is not a governed runtime lane like `stage` or
  `prod`.
- Use `dev-integration` when an operator-facing workflow, cross-repo API
  contract, or canonical-backend write path is still changing too quickly for
  governed stage rehearsal.
- `dev-integration` profiles use an admission lifecycle:
  - `proposed`
  - `active`
  - `suspended`
  - `retired`
- only `active` profiles are self-serve launchable from the shared runner
- the request/admission contract is generic even if the current request
  surface adapter is a specific tool such as OpenProject
- `dev-integration` still needs discipline:
  - profile defines runtime shape
  - branch or worktree defines source state
  - session manifest records both
  - stage handoff still requires reviewed commits and governed promotion
- If a change creates or materially changes an operator-facing workflow,
  command family, request path, approval path, or other operator procedure, the
  work is not complete until one primary operator instruction surface exists in
  the owning repo.
- If a serious failure or unexpected runtime behavior is being diagnosed, use
  `/home/mfshaf7/projects/workspace-governance/docs/troubleshooting-preflight.md`
  before deeper workaround analysis, redesign proposals, or code-level blame.
- If the blocked next step requires operator-side credentials, package
  installation, sudo, a GUI action, approval, or account permission outside
  Codex's safe tool boundary, prompt the operator immediately. Do not silently
  replace that blocked proof with CI-only evidence, guesswork, or a workaround.
- If a new workspace-level control, workflow, validator, skill, product
  surface, or architecture capability is being recommended, run the
  recommendation preflight first and state whether the result is `reuse`,
  `extend`, `replace`, or `new`.
- Do not state a named deployment, pod, route, work item, owner, control name,
  root-cause label, or completion fact as true until it has been proven from
  the authoritative source for that layer. If it has not been proven yet, say
  it is unverified.
- Contracts, templates, and standards may support that workflow, but they do
  not replace the primary operator instruction surface.
- If the operator has to reconstruct the procedure from scattered files, the
  workflow is still incomplete.
- Git-tracked docs outside `workspace-root/` must not use markdown navigation
  links to `/home/mfshaf7/projects/...`. Use repo-relative links for same-repo
  docs and web-safe links for cross-repo docs instead.
- Intake classification can start from operator judgment or an AI suggestion,
  but the recorded workspace decision is still explicit:
  - `out-of-scope`
  - `proposed`
  - `admitted`
- `decision_source: ai-suggested` only counts as governed when the intake entry
  carries active approved profile evidence from
  `platform-engineering/security/governed-ai-model-profiles.yaml` and still
  records explicit operator acceptance.
- If a major miss, late discovery, or repeated workflow problem is uncovered,
  route it through the self-improvement system, not just chat memory.
- Use `workspace-governance/docs/self-improvement-escalation.md` as the
  primary operator surface when a live signal should pause normal work and
  force immediate candidate capture.
- Record or update a candidate first in
  `workspace-governance/reviews/improvement-candidates/` when the signal is
  real but the closure shape is not fully decided yet.
- If the user explicitly says something is a repeated mistake, that is a
  mandatory candidate signal.
- If the user calls the work half-baked, incomplete, or says the miss should
  have been caught already, treat that as the same class of mandatory
  self-improvement signal.
- If a simpler root cause is discovered late because earlier troubleshooting
  layers were skipped, treat that as a mandatory self-improvement signal and
  route it through the improvement-candidate layer.
- Candidate capture should happen automatically once the signal is real, but
  the durable fix should not be auto-landed from that signal alone.
- If active work becomes half-finished at the planning, control, or completion
  layer, record or update the improvement candidate before continuing normal
  execution.
- After creating or editing several structured records or owner-repo change
  records, run
  `python3 /home/mfshaf7/projects/workspace-governance/scripts/preflight_touched_records.py --workspace-root /home/mfshaf7/projects --include-untracked`
  before continuing normal execution.
- If a previously closed lesson regresses, record the new candidate as a
  regression linked to the earlier closed candidate or after-action instead of
  treating it as an unrelated new issue.
- After creating or editing any structured governance record, run:
  - `python3 /home/mfshaf7/projects/workspace-governance/scripts/validate_structured_record.py <record-path> --workspace-root /home/mfshaf7/projects`
  before continuing normal work. This applies to improvement candidates,
  after-actions, delegation journals, workspace contracts, and owner-repo
  change records.
- If an owner-repo change record declares `security_evidence`, that preflight
  must also prove the generated `security-architecture` change-record index is
  current before closure or merge sequencing continues.
- Propose the best fix shape, justify why it is the best option, and wait for
  operator approval before implementing the closing control.
- No repeated failure class should stay purely conversational. It should either
  become an explicit candidate with owner and due date, or close through a
  linked after-action record or landed durable control.

## Operating Rules

- Prefer the owner that should hold the long-lived contract, not the repo where
  the patch is easiest.
- Before meaningful work starts, use the work-home routing contract to decide
  whether the work belongs in ART, an owner repo, Workspace Proposals, or the
  blocker/risk/improvement path.
- PI-committed initiative work must include at least one `PI Objective`.
- A top-level `Epic` may remain unclassified only while it is the brand-new
  `new` + `Initiating` shell with blank `Target PI`.
- Once a top-level `Epic` leaves that shell posture, it must carry
  `Initiative Family` and `Lineage Role`.
- Follow-on top-level epics must use `Architecture Anchor Ref` and
  `Required Upstream Ref` when their lineage role requires them.
- A backlog `Feature` may stay umbrella-only, but a PI-committed or active
  `Feature` must keep an open `User story` or `Defect` child as its leaf
  front.
- `Milestone` is an `Epic`-level checkpoint only; it does not replace a
  `PI Objective` or a `Feature` leaf front.
- When the request is architecture-shaping rather than implementation-shaped,
  discuss the decision with the user before editing code.
- When docs and code disagree, fix the immediate problem in the correct owner
  repo and update the docs in the same work.
- Live-only fixes are containment, not completion.
- Do not recreate retired copy-based workflows that the current architecture no
  longer uses.
- If a change affects trust boundaries, privileges, secrets, delivery controls,
  or AI-enabled action paths, update the owning docs or governance artifacts in
  the same work.

## Required Evidence For Production-Impacting Work

Production-impacting work should leave enough evidence to answer:

- what failed
- which owner repo held the durable fix
- which commits changed
- which environment contract or live state changed
- which validation or live checks proved the outcome

If that evidence cannot be produced, the work is not complete.

## Validation Entry Points

- Normal compact validation evidence for #536-proven scopes should come from
  `workspace-governance-control-fabric` catalog receipts:
  - `wgcf catalog check --workspace-root /home/mfshaf7/projects --scope component:workspace-governance --profile local-read-only --tier smoke`
  - `wgcf catalog check --workspace-root /home/mfshaf7/projects --scope component:delivery-art --profile dev-integration --tier scoped --operator-approved`
  - `wgcf catalog check --workspace-root /home/mfshaf7/projects --scope component:platform-runtime --profile dev-integration --tier smoke --operator-approved`
  - `wgcf catalog check --workspace-root /home/mfshaf7/projects --scope component:security-review --profile local-read-only --tier smoke`
- The direct commands below remain source-authority, owner-repo, and rollback
  entrypoints. Use them when WGCF is blocked, the target scope is not admitted
  to WGCF, or the owner repo needs pre-landing validation.
- `workspace-governance/`
  - `python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/check_remote_alignment.py --workspace-root /home/mfshaf7/projects --repo-name workspace-governance --refresh-remote`
  - `python3 scripts/validate_repo_structure.py --repo-root .`
  - `python3 scripts/validate_contracts.py --repo-root .`
  - `python3 scripts/validate_intake.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/validate_developer_integration.py --repo-root . --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/validate_improvement_candidates.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/validate_structured_record.py reviews/improvement-candidates/<record>.yaml --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --check-generated`
  - `python3 scripts/validate_codex_review_controls.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/audit_improvement_signals.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/validate_learning_closure.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/audit_branch_lifecycle.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/audit_branch_lifecycle.py --workspace-root /home/mfshaf7/projects --include-remote`
  - `python3 scripts/audit_branch_lifecycle.py --workspace-root /home/mfshaf7/projects --include-remote --check-clean`
  - `python3 scripts/sync_workspace_root.py --workspace-root /home/mfshaf7/projects --check`
  - `python3 scripts/workspace_control_plane_summary.py --workspace-root /home/mfshaf7/projects --refresh-remote`
  - `python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects`
  - `python3 scripts/audit_workspace_layout.py --workspace-root /home/mfshaf7/projects --check-clean`
  - `python3 scripts/audit_stale_content.py --workspace-root /home/mfshaf7/projects`
- other repos
  - follow the local repo `AGENTS.md`
