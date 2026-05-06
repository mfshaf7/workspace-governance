# Delivery ART Operator Path

## Purpose

Define the workspace-level governance shape for the normal `Workspace Delivery
ART` operator workflow.

This is not the primary route-by-route operator runbook. That remains the
broker-owned surface in
[`operator-orchestration-service`](https://github.com/mfshaf7/operator-orchestration-service/blob/main/docs/operations/delivery-workflow-operator-surface.md).

This document governs the cross-repo boundary instead:

- which entrypoint is canonical
- which reads come first
- which writes are guided intents
- when fallback is allowed
- what success looks like

Machine-readable companion contract:

- [contracts/delivery-art-operator-path.yaml](../contracts/delivery-art-operator-path.yaml)

## Canonical Entrypoint

Normal ART work should start from the broker CLI:

```bash
cd /home/mfshaf7/projects/operator-orchestration-service
npm run art -- bootstrap
```

That means:

- the broker owns the normal ART read and write path
- normal sessions do not start from direct Rails query
- normal sessions do not start from raw `kubectl exec ... node -e ...`

When accepted work is first entering `Workspace Delivery ART`, use the
OpenProject start-here planning surface first:

- [platform-engineering OpenProject start-delivery-initiative](https://github.com/mfshaf7/platform-engineering/blob/main/products/openproject/runbooks/start-delivery-initiative.md)

## Work-Home Classification

Before doing meaningful work that is not already covered by the active ART
item, classify its home through the workspace work-home routing contract:

- [workspace-governance work-home routing contract](work-home-routing-contract.md)

Use that contract before execution, not as a retrospective clean-up step.

The normal decisions are:

- keep accepted initiative work, blockers, risks, scope changes, and
  completion truth in `Workspace Delivery ART`
- absorb a tiny same-slice correction into the active item and record it in
  completion evidence
- create a new ART child when the work has a distinct owner repo, scope,
  review path, risk, blocker, or validation proof
- use owner-repo tracking only for local maintenance outside accepted ART work
- use `Workspace Proposals` before decomposing a new business or architecture
  idea
- record an improvement candidate when the missed classification is a repeated
  control failure

Plumbing work is classified by impact, not by name. Platform observability
plumbing, broker ART adapter repair, security-review plumbing, and
workspace-control plumbing can land in different homes depending on whether
they are accepted initiative work, owner-repo maintenance, or a new idea.

If important work was already done without classification, reconcile it after
discovery. Do not throw away useful work, and do not leave the skipped
classification invisible.

## Landing Evidence

Do not treat ART child items, Git branches, and merge evidence as one-to-one.

- ART decomposition tracks delivery state.
- Landing Units track source review, merge, deployment, and rollback state.
- Review Packets bind landed or accepted evidence back to one or more ART
  items.

For source-backed work, choose a Landing Unit before implementation. One
Landing Unit can cover several ART children when they share the same review and
rollback boundary. Several Landing Units can exist under one Feature or Epic
when owner repo, validation, security, deployment, or rollback boundaries
differ.

Before creating a branch or implementing source-backed work, record the
Landing Unit Decision:

- `feature_single_landing_unit`: one branch, one PR, and one Review Packet for
  the active Feature's covered source-backed children.
- `child_isolated_landing_unit`: one child needs an independent source landing;
  record the concrete split reason before branching.
- `non_source_child`: close with non-source evidence and no fake branch or PR.
- `defer_decision_blocked`: stop and gather the missing ART/repo context before
  source work continues.

Default to `feature_single_landing_unit` when same-Feature children share the
same owner repo, rollback boundary, validation surface, deployment timing, and
security posture. A per-child PR is an exception that needs a real split reason,
not the default working model.

Do not mark source-backed ART children `done` just because code exists on a
branch. Keep them open with work notes such as `implemented pending landing`
until the finalized Review Packet provides merged PR evidence, approved
direct-land evidence, or equivalent durable source evidence.

Before merging source-backed work, create or refresh the draft Review Packet
while the PR is still open. The packet must use `open_pr` evidence and include
the PR URL, changed-surface explanations, tests, validations, rollback
boundary, and item-level completion mapping. Fetch the PR base and run the
local command or command set that is CI-equivalent for the changed surface. If
required CI uses a base-aware validator, use the same base-ref shape after
fetching the base, such as `--against-ref origin/main`. Record the command,
base ref, and result in validation evidence. Then run:

```bash
npm run art -- review-packet readiness <packet.json>
```

Merge only after readiness passes. If it fails, fix the same PR or split the
Landing Unit; do not merge first and repair the evidence later. After merge,
set the packet to `merged_pr`, add the merge commit, finalize it, and use the
final digest in ART completion evidence.

Generated ART payloads, Review Packets, and completion evidence files must stay
reviewable. Edit them through a patchable diff path such as `apply_patch` or an
equivalent reviewed file patch, then rerun the relevant broker preflight before
using the payload. Do not make final evidence edits through ad hoc heredocs,
raw shell redirection, or one-off overwrites unless the generator itself is the
reviewed control.

If CI-equivalent proof cannot run because it needs operator-side credentials,
package installation, sudo, a GUI action, approval, or account permission,
prompt the operator immediately. Do not use GitHub CI as the first proof unless
the operator explicitly accepts that blocker or exception.

Non-source work, such as risk disposition, live verification, planning, or ART
metadata repair, closes with non-source evidence and should not invent merge
evidence.

Feature and Epic closeout must verify coverage: every child is either covered
by a finalized Review Packet or explicitly marked as non-source evidence only.

## Optimized Read Hierarchy

Use this order for normal active ART work:

1. `npm run art -- bootstrap`
   - resume the active ART lane and assignable principals at the start of a
     local session
2. `npm run art -- initiative active-session <delivery-id>`
   - resume a known active initiative with bounded front state, quality drift,
     stale-open candidates, closeout readiness, and full-output refs
3. `npm run art -- item continuation <work-item-id>`
   - resume one concrete leaf item before implementation work starts
4. `npm run art -- item evidence-packet <work-item-id>`
   - inspect one work item's evidence posture without rereading raw
     descriptions or the full initiative tree
5. `npm run art -- initiative evidence-packet <delivery-id>`
   - inspect initiative-level evidence posture without reopening raw
     descriptions, PRs, and validation logs
6. `npm run art -- review-packet evidence-packet <packet.json>`
   - inspect one Review Packet's coverage and evidence posture before using it
     for closeout

Use `npm run art -- workflow-health` when roadmap, PM² projection, or broker
health is the question. Use `npm run art -- initiative planning <delivery-id>`
when the active front is unknown or planning state must be repaired. Use
`npm run art -- initiative review-pack <delivery-id>` for initiative review,
stale-open, or final closeout posture.

## 90 Percent Optimized Path

ART #650 records the accepted optimization target for reducing repeated ART
reads, manual evidence reconstruction, and large raw-output projection.

The operator path is now active for the OOS-owned broker surfaces that were
implemented and dogfooded through #650:

- active-session packet: one bounded broker packet for active front, quality
  drift, stale-open candidates, closeout readiness, and full-output refs
- evidence packet: compact work-item, initiative, and Review Packet evidence
  reads without reopening raw descriptions, PRs, and validation logs
- Review Packet workflow: draft, validate, readiness, evidence-packet, and
  finalize commands for source-backed completion evidence
- landing-unit status, dry-run, and submit: one Review Packet driven workflow
  for child completion, parent stale-open readiness, generated-payload
  preflight, WGCF readiness receipts, and projection checkpoint handling
- optional CGG packet refs: `ART_CGG_PACKETING=enabled` can add packet refs and
  digests for oversized ART CLI output while preserving the `.art/outputs`
  local artifact path

First dogfood measurement:

- older active-front evidence read: `npm run art -- initiative
  execution-summary 650 --json` produced 65,648 bytes
- optimized active-front read: `npm run art -- initiative active-session 650
  --json` produced 9,162 bytes
- measured reduction for that read path: 86%
- same dogfood run closed #668 through `landing-unit status`, `landing-unit
  dry-run`, and `landing-unit submit` with generated payload preflight valid,
  WGCF receipt `art-readiness-receipt:f5ae7cd83f2b73fa7b995370`, and clean
  projection state

The target is not complete for every context source yet. The remaining
optimization work is to replace repeated validator discovery with WGCF
validation-plan receipts and make CGG packet projection the normal path for
oversized ART, CI, terminal, and runtime output. Until that lands, raw large
output should stay behind `.art/outputs` refs or CGG packet refs instead of
being copied into operator or model context.

## Guided Write Intents

Normal guided write paths are:

- `npm run art -- item blocker <work-item-id> <payload.json>`
- `npm run art -- initiative planning-repair <delivery-id> <payload.json>`
- `npm run art -- review-packet draft <delivery-id> <output.json> <work-item-id...> [--repo-root <path>...]`
- `npm run art -- review-packet validate <packet.json>`
- `npm run art -- review-packet readiness <packet.json>`
- `npm run art -- review-packet finalize <packet.json>`
- `npm run art -- landing-unit status <packet.json>`
- `npm run art -- landing-unit dry-run <packet.json>`
- `npm run art -- landing-unit submit <packet.json>`
- `npm run art -- item complete <work-item-id> <payload.json>`
- `npm run art -- item stale-open-close <work-item-id> <payload.json>`
- `npm run art -- initiative close <delivery-id> <payload.json>`
- `npm run art -- scaffold item-complete <work-item-id> <output.json> [repo-root...]`
- `npm run art -- scaffold initiative-close <delivery-id> <output.json> [repo-root...]`

These exist so the operator does not have to reconstruct multi-step ART writes
from low-level broker calls.

When the active next step cannot proceed, use the blocker workflow before
continuing adjacent ART mutation:

- state the exact blocker on the affected work item
- open a real `Defect` when the blocker is caused by a live system or workflow
  control bug
- open a `Risk` when the exposure is broader than one blocked item
- clear the blocker only through the bounded blocker path, not by generic
  status edits

When a new defect is discovered while active ART work is already moving,
contain the immediate drift or live issue first, then classify the defect before
implementation:

- `immediate_blocker`: safe continuation is impossible because quality remains
  unhealthy, the next mutation would corrupt state, evidence cannot be trusted,
  the runtime path is down, or an open security/trust exposure exists.
- `deferred_defect`: containment restored safe continuation; record the defect
  or follow-up and continue the active committed front.
- `absorbed_same_slice_fix`: the defect has the same cause, owner, validation,
  review, and rollback boundary as the active Landing Unit.
- `risk`: the exposure is broader than one work item or needs ROAM handling.

Do not context-switch into an unplanned defect fix after containment unless the
classification is `immediate_blocker` or the operator explicitly approves
absorbing the fix into the current slice.

## Fallback Model

Normal rule:

- use broker CLI or broker HTTP routes for ART work
- do not use direct Rails query for normal ART work
- do not use raw pod exec plus ad hoc node one-liners for normal ART work

Fallback is allowed only when the broker runtime or compatible OpenProject
projection is unhealthy.

Do not turn a wrapper or tooling failure into a named root cause until live
truth proves it. A deployment name, pod name, route, work item, owner, or
control name used in an operator update or completion record must come from the
authoritative source for that layer, or be explicitly marked as unverified.

If broker runtime is unavailable:

1. restore the lane through the OpenProject and broker runtime runbooks
2. use the OpenProject platform-admin surface only for runtime, board, or
   projection repair
3. return to the broker path for ART mutation

If roadmap or PM² projection drift is suspected:

1. `npm run art -- workflow-health`
2. `make openproject-check-delivery-art-quality ...`
3. `make openproject-sync-delivery-art-views ...` only when the projection
   itself is the problem

After any ART mutation that returns
`roadmap_version_projection.status=external_reconciler_required`, projection
reconciliation is a broker-visible checkpoint rather than a per-mutation sync
reflex.

Use this sequence:

1. inspect `npm run art -- projection status`
2. batch only related same-burst closeouts while dirty state is visible
3. run `npm run art -- projection sync --pi-names "<known-pis>" --target-epic-id <epic-id> --quality`
   before treating roadmap projection health or scoped quality as final

Do not defer dirty projection sync until the whole Epic is finished. Run it at
parent closeout, final evidence, or roadmap/quality checkpoints.

## Compatibility Boundary

Broker-owned normal ART surfaces:

- session bootstrap and workflow health
- initiative reads, planning, and review readiness
- initiative writes, planning repair, and closeout
- work-item reads, writes, and closeout
- closeout scaffolding helpers

OpenProject platform-admin only:

- bootstrap and schema provisioning
- board and roadmap projection repair
- one-time normalization after contract changes
- service identity provisioning
- clean-start, backup, restore, and uninstall controls

## Success Metrics

The operator path is only considered complete when all of these are true:

- ART lane bootstrap is one command
- active initiative resume is one bounded active-session packet
- workflow health is one command when health is the question
- initiative evidence posture is one bounded evidence packet
- Review Packet readiness and finalization are one command family
- planning repair is one guided write path
- blocker management is one guided write path
- landing-unit child completion, parent closeout candidates, generated payload
  preflight, WGCF receipts, and projection checkpoint are one guided command
  family
- direct item completion and stale-open close remain bounded fallback write
  paths for non-Review Packet closure
- initiative closeout is one guided write path
- normal ART sessions do not use direct Rails query
- normal ART sessions do not use raw pod exec plus ad hoc node one-liners

## Related References

- [operator-orchestration-service delivery operator surface](https://github.com/mfshaf7/operator-orchestration-service/blob/main/docs/operations/delivery-workflow-operator-surface.md)
- [platform-engineering OpenProject start-delivery-initiative](https://github.com/mfshaf7/platform-engineering/blob/main/products/openproject/runbooks/start-delivery-initiative.md)
- [platform-engineering OpenProject workflow health](https://github.com/mfshaf7/platform-engineering/blob/main/products/openproject/runbooks/check-delivery-art-workflow-health.md)
- [platform-engineering OpenProject admin boundary](https://github.com/mfshaf7/platform-engineering/blob/main/products/openproject/runbooks/openproject-platform-admin-surface.md)
