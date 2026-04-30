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

Do not mark source-backed ART children `done` just because code exists on a
branch. Keep them open with work notes such as `implemented pending landing`
until the finalized Review Packet provides merged PR evidence, approved
direct-land evidence, or equivalent durable source evidence.

Non-source work, such as risk disposition, live verification, planning, or ART
metadata repair, closes with non-source evidence and should not invent merge
evidence.

Feature and Epic closeout must verify coverage: every child is either covered
by a finalized Review Packet or explicitly marked as non-source evidence only.

## Read Hierarchy

Use this order:

1. `npm run art -- bootstrap`
   - resume the active ART lane and assignable principals
2. `npm run art -- workflow-health`
   - confirm roadmap and PM² projection health
3. `npm run art -- initiative planning <delivery-id>`
   - identify the active committed front when the next item is not already known
4. `npm run art -- item continuation <work-item-id>`
   - resume one concrete leaf item
5. `npm run art -- initiative review-pack <delivery-id>`
   - inspect initiative review readiness, stale-open candidates, and closeout posture

## Guided Write Intents

Normal guided write paths are:

- `npm run art -- item blocker <work-item-id> <payload.json>`
- `npm run art -- initiative planning-repair <delivery-id> <payload.json>`
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

After any ART mutation that can change OpenProject roadmap `version`
projection, projection reconciliation is part of the workflow rather than an
exceptional repair. Run platform view sync with the proven active ART runtime
context before treating the quality gate as final. This applies to:

- assigning, clearing, or retargeting `Target PI`
- carryover, decommit, parking, retirement, or completion
- status changes that move work between backlog, committed, active, done,
  parked, or retired roadmap buckets
- platform-admin repair that changes expected roadmap placement

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
- workflow health is one command
- initiative review readiness is one command
- planning repair is one guided write path
- blocker management is one guided write path
- item completion and stale-open close each have one guided write path
- initiative closeout is one guided write path
- normal ART sessions do not use direct Rails query
- normal ART sessions do not use raw pod exec plus ad hoc node one-liners

## Related References

- [operator-orchestration-service delivery operator surface](https://github.com/mfshaf7/operator-orchestration-service/blob/main/docs/operations/delivery-workflow-operator-surface.md)
- [platform-engineering OpenProject start-delivery-initiative](https://github.com/mfshaf7/platform-engineering/blob/main/products/openproject/runbooks/start-delivery-initiative.md)
- [platform-engineering OpenProject workflow health](https://github.com/mfshaf7/platform-engineering/blob/main/products/openproject/runbooks/check-delivery-art-workflow-health.md)
- [platform-engineering OpenProject admin boundary](https://github.com/mfshaf7/platform-engineering/blob/main/products/openproject/runbooks/openproject-platform-admin-surface.md)
