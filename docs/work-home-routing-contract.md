# Work-Home Routing Contract

This document explains the proportional work-home contract declared in
[`contracts/work-home-routing.yaml`](../contracts/work-home-routing.yaml).

The purpose is to prevent two opposite failures:

- meaningful accepted work being done without an ART home
- low-risk owner-repo maintenance being forced into unnecessary ART structure

The contract is intentionally about classification before execution. It does
not replace owner-repo change records, security evidence, or ART completion
evidence.

## Systems Of Record

- Workspace Delivery ART is the work-state home for accepted initiative work,
  blocker state, risk state, scope changes, and completion truth.
- Owner repos are the implementation home for code, docs, runtime artifacts,
  tests, repo-local change records, and review evidence.
- Workspace Proposals is the intake home for new ideas that are not accepted
  into delivery yet.
- Improvement candidates are the learning home for repeated workflow misses or
  control failures.

These records are not redundant. They answer different questions.

## Classification Order

Use the contract's `classification_order` before execution:

1. `active_incident_or_blocker`
2. `active_art_slice`
3. `meaningful_same_initiative_expansion`
4. `platform_or_workflow_plumbing`
5. `owner_repo_maintenance`
6. `new_business_or_architecture_idea`
7. `late_discovered_unclassified_work`

The order matters. A live blocker must be recorded before adjacent mutation
continues. Accepted initiative work must stay in ART even when it feels like
plumbing. Pure owner-repo maintenance should not create ART noise.

## Proportionality Rule

Use the smallest home that still preserves real owner, review, and validation
boundaries.

- Absorb a tiny same-slice correction into the active ART item and mention it
  in completion evidence.
- Create a new ART child when the work has a distinct scope, owner repo,
  review path, risk, blocker, or validation proof.
- Use owner-repo-only tracking when the work is local maintenance outside an
  accepted initiative and does not affect shared workflow, platform, security,
  or workspace governance behavior.
- Use Workspace Proposals before decomposing a new business or architecture
  idea.

## Landing Units And Review Packets

ART decomposition, Git branches, and completion evidence are related, but they
are not one-to-one.

- An ART item tracks delivery intent, work state, blockers, risks, and
  completion truth.
- A Landing Unit tracks the source change that should be reviewed, merged,
  deployed, and rolled back together.
- A Review Packet binds landed or explicitly accepted evidence back to one or
  more ART items.

Branch by Landing Unit, not by ART child and not automatically by Epic. One
Landing Unit can cover one story, several stories, a Feature, or a small
cohesive Epic when review and rollback boundaries are shared. Split the Landing
Unit when the work crosses repos, owners, security posture, validation burden,
or rollback boundaries.

Security-evidenced owner-repo change records create a dependent security
landing unit. If a change record declares `security_evidence`, the generated
`security-architecture/registers/security-change-record-index.yaml` update must
be checked and landed in the cross-repo sequence before workspace closure is
claimed clean.

Source-backed ART children should not be marked `done` until they are covered
by a finalized Review Packet with merged PR evidence, approved direct-land
evidence, or an equivalent durable landing record. Multiple children may close
from the same Review Packet. Non-source children, such as planning, risk
disposition, live verification, or metadata repair, close with the relevant
non-source evidence instead of fake merge evidence.

For long-running work, push an early draft PR when useful for backup, CI, or
review visibility. That does not make the work done. It remains open until the
Landing Unit is landed or the operator explicitly accepts a direct-land or
non-source exception.

For source-backed work, create or refresh the draft Review Packet while the PR
is still open. It must carry `landing_unit.evidence_kind: open_pr`, the PR URL,
concrete changed-surface explanations, test and validation evidence, rollback
boundary, and one completion mapping per covered ART item. Then run:

```bash
npm run art -- review-packet readiness <packet.json>
```

Do this after the PR is open and before it is merged. A readiness failure means
the Landing Unit is not ready to merge; fix the same PR or deliberately split
the Landing Unit instead of planning a corrective PR after merge.

After merge, change the packet to `merged_pr`, add the merge commit, finalize
the packet, and use the finalized digest in ART completion evidence.

Parent closeout must prove coverage, not duplicate every child record. A
Feature or Epic can close only when every child is covered by a finalized Review
Packet or explicitly marked as non-source evidence only.

Use [`templates/review-packet/TEMPLATE.md`](../templates/review-packet/TEMPLATE.md)
when a packet needs a durable artifact outside the ART completion note.

## Plumbing Work

Plumbing is classified by impact, not by name.

Examples:

- Fixing the platform observability stack is platform plumbing. If it is part
  of an accepted initiative, it needs an ART item with `platform-engineering`
  as owner. If it is not accepted yet, it starts in Workspace Proposals or
  architecture discussion.
- Fixing a broker ART adapter during active #362 work is same-initiative
  expansion. It should become a Defect or User story under the active ART
  Feature before adjacent work continues.
- Fixing a small typo in one README outside accepted work is owner-repo
  maintenance. A normal owner-repo PR is enough unless the repo rules require
  extra evidence.

When plumbing is proposed because an existing workflow appears insufficient,
run the recommendation preflight first:

- [recommendation-preflight.md](recommendation-preflight.md)

That preflight decides whether the right posture is `reuse`, `extend`,
`replace`, or `new` before another control surface is invented.

## Dev-Integration Live Misses

When a workflow has an active `dev-integration` profile and a failure appears
only after local proof, do not keep patching in the live/shared runtime by
default.

Use `contracts/developer-integration-policy.yaml` `live_miss_escalation` to
choose one of three routes:

- return to `dev-integration` when workflow shape, operator inputs, or backend
  write semantics are still changing and the profile can reproduce the issue
- route to the platform or backend boundary when local workflow proof already
  passed and the remaining failure is identity, networking, persistence, form
  writability, or platform projection behavior
- continue governed rehearsal only when reviewed commits and handoff evidence
  exist and blocker, defect, or risk state has been recorded where needed

## Late Discovery

If a human operator or agent already performed important work without applying
the contract, do not throw away the change and do not pretend the miss did not
happen.

Reconcile it by applying the same classes after discovery:

- attach it to the active ART item if it is truly same-slice
- create a compensating ART item if it has independent scope or evidence
- route it as owner-repo maintenance if it is outside accepted ART work
- record an improvement candidate if the missed classification is a repeated
  control failure

Late reconciliation preserves useful work while still making the skipped
classification visible.

## Backfill And Bypass Reconciliation

Backfill is selective and evidence-driven. Do not recreate all historical work
as ART items just because the rule now exists.

Mandatory reconciliation applies when late-discovered work affects:

- the active initiative
- an active blocker or risk
- source or runtime state needed for current completion
- security posture or auditability
- a repeated control miss

Closed historical work is reconciled only when it is needed to explain current
state, security evidence, auditability, or an active follow-up.

Human/operator bypass is allowed as urgent containment when the system is down
or safety would be worse if work waited for full routing. That bypass is not a
normal delivery path. Reconcile it before adjacent planned ART mutation
continues when the bypass affects scope, blocker state, risk state, security
posture, or completion evidence.

Use these resolution paths:

- `attach_to_active_item`: same-slice work with the same owner and validation
  boundary; record it in the active item's evidence.
- `create_compensating_art_item`: independent scope, owner repo, review path,
  blocker, risk, validation proof, or completion evidence; create or use the
  smallest honest ART item.
- `route_owner_repo_maintenance`: local maintenance outside accepted ART scope;
  keep it in the owner repo with normal validation and PR evidence.
- `create_workspace_proposal`: new business or architecture work not yet
  accepted; route it to intake before execution decomposition.
- `record_improvement_candidate`: repeated, operator-called-out, or
  machine-visible missed gate; capture the control failure with owner and due
  date.
- `open_defect_or_risk`: active broken-control or exposure state; record the
  blocker, defect, or risk before continuing adjacent mutation.

Every reconciliation decision should record:

- when it was discovered
- who discovered it
- who or what made the original change
- what changed
- authoritative evidence refs
- classification result
- selected resolution path
- owner repo
- ART, proposal, candidate, defect, or risk refs
- whether security or risk review is needed
- operator acceptance when required

Forbidden outcomes:

- backdating ART or pretending approval existed before it did
- discarding useful work solely because classification was late
- hiding accepted initiative work in an owner-repo-only note
- closing active work while known unclassified work still affects scope, risk,
  blocker state, or completion evidence
- treating urgent human bypass as normal process instead of reconciling it

## Boundary With Later Doctrine

This contract defines the machine-readable routing model. Operator-facing
doctrine and AGENTS guidance should point at this contract, but that publication
step is separate from the contract definition work.
