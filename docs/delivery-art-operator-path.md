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

## Initiative Architecture Preflight

Before source implementation begins for an architecture-shaping initiative,
cross-repo protocol, or control-plane change, reconstruct the whole initiative
once. Do not start from one child item and discover the architecture through
successive implementation reviews.

The preflight must use authoritative ART and merged owner-repo truth to produce
one bounded architecture packet containing:

- the complete descendant and owner map
- the dependency and merge sequence
- the lifecycle and state model
- the authorization, session, scenario, and execution model
- evidence and owner-receipt handoffs
- runtime boundaries and prohibited actions
- rollback, cleanup, and terminal completion conditions
- contradictions and unresolved decisions
- the positive and negative conformance cases that later implementation must
  prove, including the required fidelity class for each case

Discuss that packet with the operator and lock the execution sequence before
child implementation starts. The only valid outcomes are `architecture-ready`
or
`blocked-pending-architecture-decision`. Reopen the preflight if an owner
boundary, protocol, lifecycle, or evidence handoff materially changes.

The descendant owner map and dependency DAG must cover the same declared work
items. Parent links form a rooted acyclic forest, every edge endpoint resolves,
and the source snapshot contains exactly one revision for every declared owner
repo. Dependency relations have explicit precedence: the target precedes the
source for `depends_on`; the source precedes the target for `blocks` and
`must_merge_before`. Cross-repo edges must be honored by `merge_order`, and
every lifecycle transition endpoint must be a declared lifecycle state. These
invariants are semantic checks in addition to JSON Schema shape.

Every architecture packet records whether it changes a cross-repo protocol and
why. When protocol conformance applies, the packet must include every mandated
dimension in its executable conformance plan. It must cover command acknowledgement,
deterministic identity and idempotency, state-mutation ordering, retry, cancel,
replay and recovery semantics, bounded failure mapping, authorization integrity,
session and scenario-execution binding, complete owner receipts, immutable
restore evidence, lifecycle matrices, cross-artifact timelines, and shared
validator compatibility.

Architecture readiness proves that this plan is complete and operator-approved;
it does not pretend implementation tests have already run. Applicable positive
and negative cases must pass before `merge-ready`, using the fidelity needed for
the claim. Each case names the dimensions it proves, required plans cover every
declared dimension, and every mandated protocol dimension has positive and
negative `merge-ready` cases. Every covered work item must also have positive
and negative `merge-ready` cases, so one item cannot carry protocol proof for a
different item that defers its own cases until operating readiness. A synthetic
resolver may support unit tests, but it cannot prove a claim about real Git
history. The packet therefore declares the exact applicable dimensions for each
work item. Every declared `(work item, dimension)` pair needs positive and
negative merge-ready cases. Git-causality claims separately name their work
items and dimensions, and each such pair requires positive and negative
`real-git` cases.

The machine schema is
[`delivery-art-architecture-packet.schema.json`](../contracts/schemas/delivery-art-architecture-packet.schema.json).

## Readiness Levels

ART readiness is four separate decisions, not one overloaded `ready` flag:

1. `architecture-ready`: design, ownership, execution sequence, boundaries,
   and conformance plan are explicit and operator-approved.
2. `implementation-ready`: one Landing Unit is bound to exact ART and owner-repo
   source truth through a durable work-start record.
3. `merge-ready`: the exact open-PR source head, or an explicitly authorized
   direct-land head, has passing applicable tests, validations, acceptance
   mapping, and a concrete rollback boundary.
4. `operating-ready`: merged or explicitly accepted evidence is finalized,
   content-addressed, durably stored, and includes any live, runtime, security,
   or restore proof required by the change class.

Each decision is bound to a source snapshot and scope fingerprint. The
architecture fingerprint is recomputed from Delivery scope, covered work,
source snapshot, architecture, conformance plan, and decision status. The
work-start fingerprint is recomputed from Delivery scope, covered work,
Landing Unit, architecture binding, source snapshot, and the complete
invalidation set. Operator-provided arbitrary digests are invalid. A material
ART dependency, owner boundary, base revision, architecture decision, or
validation obligation change invalidates the affected later decision instead
of silently mutating earlier evidence.

The contract and schemas define this target now. Runtime enforcement remains
pending the owner-repo work and initiative `698` dogfood listed in the machine
contract. Until those items land, use the existing OOS operator commands and
Review Packet v1 path; do not claim that a new work-start command or Review
Packet v2 persistence path already exists.

The machine contract also carries a proof-obligation registry. Every Boolean
claim under readiness rules, work-start, evidence integrity, and architecture
preflight is mapped exactly once as:

- `active-local`, with an executed positive and negative validation case
- `pending-owner`, with its activation ART item
- `doctrine`, with an explicit rationale and no false runtime proof

Adding a true claim without that mapping, mapping one claim twice, or naming a
validation case that did not execute fails the contract validator.

## Work-Start Gate

Before creating a branch or editing source, the target OOS path will persist a
[`delivery-art-work-start-record`](../contracts/schemas/delivery-art-work-start-record.schema.json)
that records:

- the covered ART items and explicit Landing Unit Decision
- a concrete split reason for `child_isolated_landing_unit`
- owner repos, branch plan, exact base refs, and exact base commits
- the architecture packet ref and digest when preflight applies
- a planned Review Packet ref
- the scoped ART/source snapshot, fingerprint, and invalidation inputs
- the operator decision and resulting implementation readiness

For a source-backed Landing Unit, owner repos, branch-plan repos, and source
snapshot repos must be the same set. Each planned base ref and base commit must
also equal the corresponding captured source revision. Schema shape validation
alone is insufficient for these dynamic cross-record comparisons, so the
contract validator applies the semantic binding as a separate required check.
Durable work-start or blocked records must also record `persisted_at`; durable
custody without a persistence timestamp is invalid.

The invalidation input list is a complete machine set, not an operator-selected
subset. Every work-start record carries all five declared change classes so a
later ART, ownership, source, architecture, validation, or security change
forces reevaluation instead of silently relying on stale readiness.

When architecture is required but its decision is unresolved, the work-start
record remains durable with architecture readiness `blocked` and overall
readiness `blocked`. It must not invent a packet ref or claim
`implementation-ready`. Once the architecture decision is ready, a fresh
work-start evaluation binds its packet ref and digest before source work.
Those refs follow the architecture substate even when a separate blocker keeps
overall work-start readiness blocked: `architecture-ready` requires both refs,
while `blocked` and `not-required` require both to remain null.

Read snapshots may be cached to keep preparation fast. A final mutation must
refresh the target item and dependency subset. The intended cold work-start
budget is five seconds, the warm budget is two seconds, and local schema
validation should remain under 250 milliseconds. These are target budgets until
dogfood turns them into measured operating controls.

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

Approved direct landing is an exception path, not timeless authority. Its
`direct-land` exception must carry an expiry and remain valid through the
packet's readiness evaluation and finalization. An expired or non-expiring
exception cannot authorize a finalized direct-land packet, and direct-land
evidence cannot simultaneously claim a pull-request URL.

Before merging source-backed work, create or refresh the local draft Review
Packet. For the normal PR path it uses `open_pr` evidence and includes the PR
URL, changed-surface explanations, tests, validations, rollback boundary, and
item-level completion mapping. Fetch the PR base and run the local command or
command set that is CI-equivalent for the changed surface. If required CI uses
a base-aware validator, use the same base-ref shape after fetching the base,
such as `--against-ref origin/main`. Every passing result records the exact
repo/head revisions it proves; a stale or partial source-revision set is not
passing evidence. Then run:

```bash
npm run art -- review-packet readiness <packet.json>
```

Passing readiness persists a content-addressed `merge-ready` Review Packet.
That artifact is the immutable reviewed predecessor, not a local file that can
be rewritten after merge. Merge only after it exists. If readiness fails, fix
the same PR or split the Landing Unit; do not merge first and repair the
evidence later. After merge, build the final packet from that predecessor, set
the evidence kind to `merged_pr`, add the merge commit and any later evidence,
and preserve every earlier source, result, mapping, and exception fact.
Finalize only after the operating-readiness receipt resolves, then use the
final packet digest in ART completion evidence.

Review Packet v2 replaces prose result lines with structured evidence. Every
test and validation records its command, fidelity class, result, summary, and
evidence refs. `fail` blocks merge readiness. `not_applicable` requires both a
reason and an authority ref. `Attached artifact` is a reference, not a passing
result, and prefixes such as `PASS:`, `FAIL:`, and `CHECK:` are not evidence
types.

The acceptance mapping must contain exactly one mapping for every declared
covered work item. Mapping references must resolve to globally unique evidence
ids in that packet. These are packet-level semantic invariants in addition to
the JSON Schema shape, and partial coverage or unknown references fail
readiness.

For source-backed packets, repository evidence is unique per repo and every
declared changed surface must resolve to a file in that repo's exact
`changed_files` list. This prevents a packet from presenting acceptance
evidence for source outside its declared landing boundary.

Readiness references are not opaque labels. A work-start record resolves its
architecture packet; a Review Packet resolves its work-start record and that
record's architecture packet. The resolved chain must preserve Delivery id,
work-item coverage, Landing Unit decision, owner and branch plan, exact base
revisions, scope fingerprint, and architecture decision. Architecture
conformance cases declare the work items they apply to. Every case applicable
to the packet's work-item and readiness scope must have a passing evidence
result at the planned fidelity. A required conformance plan covers every
architecture work item and every declared dimension with executable cases. A
child cannot advance merely because its tests were omitted from the plan or
deferred beyond that child's current readiness gate.

A finalized source Review Packet also resolves the durable merge-ready packet
named by `custody.supersedes`. The predecessor must be earlier, durable, of the
same packet and Delivery scope, and its reviewed source/evidence facts must
remain present. The final packet may add merge and operating evidence; it may
not rewrite what was reviewed. Supersession is walked as a complete chain, so
cycles and non-strict persistence order fail even when each immediate ref looks
well formed.

WGCF can issue receipts for all four readiness levels. Architecture,
implementation, and merge receipts bind the exact durable source artifact by
its content digest. Operating readiness is intentionally different: the final
packet's `readiness.subject_digest` is recomputed over packet content excluding
custody, integrity, `finalized_at`, `readiness.evaluated_at`, receipt refs, and
that digest field. The remaining projection binds the final semantic content
before receipt issuance without committing timestamps that do not exist yet.
WGCF then evaluates and persists the receipt, the packet copies the receipt's
evaluation time, finalizes no earlier than receipt persistence, and finally
persists its own content-addressed artifact. The receipt resolver still
requires the exact subject artifact and matching Delivery, covered work,
readiness level, chronology, and digest.

Each receipt referenced by a finalized packet must resolve by URI and content
digest, bind the same packet id and readiness-subject digest, carry a `ready`
outcome that permits mutation, and be durably persisted before the final
packet. This local validation proves receipt structure and subject binding;
trusted WGCF service identity remains target owner work under `803` and the
security gate under `805`.

An architecture decision and its durable attachment must exist before the
work-start evaluation that consumes it. The durable work-start attachment must
exist before a Review Packet is created. Internally valid future evidence
cannot satisfy an earlier readiness decision.

When an append-only correction declares `custody.supersedes`, that reference
must resolve to an earlier durable artifact of the same type and Delivery
initiative. A self-reference or an invented prior digest is not a correction.

Validate any supplied target-contract artifact locally with:

```bash
python3 scripts/validate_delivery_art_artifact.py <artifact.json> --repo-root . \
  --dependency-artifact <referenced-artifact.json>
```

Repeat `--dependency-artifact` until the referenced dependency closure is
complete. An architecture packet has no dependency argument. A work-start
record needs its architecture packet. A merge-ready Review Packet needs both.
A readiness receipt needs its exact subject artifact plus that subject's
dependency closure. An operating-readiness receipt therefore needs the final
packet, its merge-ready predecessor, work-start record, and architecture
packet. A finalized source Review Packet needs its durable merge-ready
predecessor and readiness receipt in addition to the earlier source artifacts:

```bash
python3 scripts/validate_delivery_art_artifact.py <finalized-packet.json> --repo-root . \
  --dependency-artifact <architecture-packet.json> \
  --dependency-artifact <work-start-record.json> \
  --dependency-artifact <merge-ready-packet.json> \
  --dependency-artifact <readiness-receipt.json>
```

This entrypoint validates schema shape, dynamic repo/graph/acceptance bindings,
exact evidence source heads, resolved cross-artifact continuity, applicable
conformance cases, and content integrity. OOS work item `802` must resolve the
same durable dependencies on the active runtime path before Review Packet v2
is declared implemented.

The v2 schema is
[`delivery-art-review-packet.schema.json`](../contracts/schemas/delivery-art-review-packet.schema.json).
It remains a target contract until OOS work item `802` implements and activates
the migration from the current runtime schema version.

Draft artifacts remain local and reviewable, carry no persistence timestamp,
and do not claim durable custody. Once an architecture decision, work-start
evaluation, or merge-ready/final Review Packet is recorded, OOS owns durable
custody by attaching content-addressed JSON to the initiative Epic. Corrections
append a superseding artifact; they do not replace prior evidence. Every
durable architecture, work-start, merge-ready, and finalized Review Packet
records when it was persisted.

WGCF stores content-addressed readiness receipts and exact source-artifact
bindings, not duplicate source artifacts. The same receipt schema covers
architecture, implementation, merge, and operating readiness; only the
operating receipt uses the cycle-safe Review Packet readiness-subject digest.
The receipt schema is
[`delivery-art-readiness-receipt.schema.json`](../contracts/schemas/delivery-art-readiness-receipt.schema.json).
Artifact digests use the integer-only RFC 8785 canonical domain and SHA-256
over artifact content, excluding custody metadata and the digest field itself.

The accepted canonical input domain contains unique JSON object keys, Unicode
scalar values, and integral numbers only; duplicate keys, floating-point
spellings such as `1.0`, and lone UTF-16 surrogates are rejected before
hashing. Artifact lifecycle timestamps are chronological:
source capture precedes architecture decisions and work-start evaluation,
packet creation precedes evaluation and finalization, and durable persistence
does not precede the decision it stores.

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
evidence. A `non_source_child` may remain `pending` while its packet is a draft,
but it may finalize only with `non_source_evidence` and no repository, branch,
pull-request, or merge evidence. Source-backed Landing Units cannot use
`non_source_evidence`.

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
