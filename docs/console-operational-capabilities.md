# Console Operational Capability Contract

This is the primary Workspace Governance surface for deciding whether the
Governance Operations Console has a complete idea-to-product plan and whether
one capability is genuinely available in live operation.

The machine-readable authority is
[`contracts/console-operational-capabilities.yaml`](../contracts/console-operational-capabilities.yaml).
The generated review view is
[`generated/console-operational-capabilities.json`](../generated/console-operational-capabilities.json).

The [Epic1275 qualification record](../reports/console-journey-1275-qualification.md)
binds the completed real application journey to actual owner receipts and its
explicit scope and recovery limits.

## What The Contract Prevents

Three facts must never be collapsed into one claim:

- a capability is defined in a contract
- source implementing that capability exists
- a live runtime can execute it against its canonical authority

A fixture, Storybook story, or disconnected preview may prove presentation and
interaction behavior. It cannot prove live availability or completion. Live
mode must use owner-backed state and fail visibly when that owner is
unavailable; it must not substitute fixture data.

## Capability Status

Every status projection keeps five independent dimensions:

- contract state
- implementation state
- runtime state
- evidence state
- demonstration source

Only the `operational-live` profile is terminal capability evidence. It means
the contract is defined, implementation exists, the runtime is available,
evidence is validated, and the demonstration source is the live authority.
`planned`, `implemented-uncommissioned`, fixture, disconnected-preview, and
degraded profiles remain truthful non-terminal postures.

The contract also records one dated operating observation for every capability.
That observation is not inferred from feature presence: it names the exact
five-dimensional profile seen in the local `dev-integration` composition and
cites the source packet that captured the audit. A dependency may be reused
only when fresh authority evidence still resolves it as `operational-live`.
Missing or stale evidence makes it non-reusable; it does not inherit the last
successful claim.

## Plan Completeness

An idea-to-product plan is complete only when every ordered journey stage has:

- a canonical authority reference and workflow owner
- a Console read model and explicit operator intents
- lifecycle, failure, and recovery states
- positive, negative, and terminal proof obligations
- accepted activation work and current authority references

The required journey is idea and proposal, prototype incubation, Delivery ART
planning, architecture decision, repository custody, source realization,
exact-head human review, distinct Security acceptance, governed source merge,
Workspace Intake and Active Inventory, runtime and release, Product Portfolio,
and interruption recovery and audit.

Repository custody is explicit because a new-product journey cannot enter
source realization until the real repository, provider policy, dedicated
credential, reconciliation, revocation, and rollback path are operational. A
contract-only or uncommissioned adapter is therefore visible as
`implemented-uncommissioned`, not silently treated as reusable infrastructure.

The Console remains an adapter. OOS owns durable cross-domain orchestration,
domain owners retain canonical state, WGCF evaluates and stores bounded
governance evidence, Security decides trust acceptance, Platform owns runtime
composition, Git owns source truth, and OpenProject owns proposal and Delivery
ART work state.

## Primary Operator Journey

Use the Console as the normal workplace. Read current owner state, review the
explicit decision, apply once, and retain the returned request, operation and
receipt. CLI and host tools remain engineering diagnostic and recovery paths;
they do not replace a missing Console business transition.

The qualified acceptance route is the public-source, browser-local Little List
application: Proposal1305, Prototype `proposal-1305`, Delivery1306 and source
owner `console-todo-1275`. Story1298 records the completed actual journey. Gary
authors source; the accountable human reviews the exact head. The local model
may advise planning metadata; it does not supply source quality, Security
acceptance or merge authority. This observation does not admit private client
source, hostile source, public hosting or stage/prod release. Each project keeps
its own access, validation and runtime decisions.

| Step | Console action and required owner result |
| --- | --- |
| Idea and route | In Proposal, capture and qualify the actual idea. Choose Prototype when exploration or a demonstrable design is needed, or direct Delivery when accepted work is ready for delivery planning. Retain one proposal and its canonical history. |
| Incubation | Open the proposal's canonical Prototype record and run Landing. Review project shape, owner, tools and preview need. Use source-authoring and Preview Runtime when applicable; seeded application data cannot stand in for a working app. |
| Repository | Use Repository's proposal gate, custody, provisioning and owner setup controls. Confirm provider account, repository identity, visibility, installation scope and receipt. An existing owner reuses its actual repository. |
| Planning | Continue the original transition into Delivery. Work Design frames the full scope; Refinement records the actual hierarchy and PI commitment. Plan every owner, evidence handoff and independent review before source starts. Earned value remains separate from planned value. |
| Architecture | Use the Architecture Packet workflow when required. Inspect and reuse the current durable packet. A bounded ordinary product change may explicitly select Not required. A recovery, commit or historical receipt alone does not justify another packet version. |
| Source | In Delivery → Execution, Open Work Item and enter the exact source item. Prepare Session; review its Landing Unit, branch and rollback boundary. Prepare and approve its exact source scope, start the session, then use the returned workspace, continue, review, merge and close actions. |
| Review | Gary authors and publishes. The delegated human approves the exact current PR head; the distinct Security authority accepts exact source when required. Candidate source must exist before exact-source acceptance. OOS retains merge-ready custody before the Console merge action. |
| Ownership | Complete the original Prototype graduation and owner readback. Workspace Registry provides Proposed review, admitted Intake and Active Inventory. Retain source and product identities independently; source merge does not itself admit a product. |
| Runtime | Follow the selected project route. Source-only outcomes need no invented deployment. Browser-local apps can use admitted Preview Runtime. APIs, workers and evolving integrations use their admitted dev-integration profile; stage/prod remain separate owner decisions. Verify actual application behavior. |
| Publication | Open the real product in Portfolio. Review the merged manifest, source revision, lifecycle evidence, Security decision, audience and publication version. Apply once and retain the original owner receipt. Do not invent a requirement to close the parent ART Epic before publication. |
| Completion | Use Non-source completion for actual evidence-only outcomes. For a PI Objective, explicitly record earned actual value and native outcome, then separately confirm completion. Source work uses its existing finalized Review Packet and Close Landing Unit. |
| Parents | Reconcile a completed parent after terminal child coverage. Epics use Inspect Closeout: review completion, Demo, Inspect & Adapt and exact impact, then apply the native guided operation. An admitted product uses existing-product change rather than duplicate Intake. |

Detailed owner procedures remain linked from this one connected route:

- [Repository custody](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/repository-custody-live-integration.md),
  [provisioning](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/repository-provisioning-live-integration.md)
  and [owner setup](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/repository-owner-setup.md).
- [Prototype Landing](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/prototype-landing-live-integration.md),
  [source authoring](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/prototype-source-authoring.md),
  [Preview Runtime](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/prototype-preview-runtime-live-integration.md)
  and [graduation/closure](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/prototype-closure-live-integration.md).
- [Delivery work sessions and evidence-only completion](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/delivery-execution-work-sessions.md),
  [plan changes](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/delivery-change-control-live-integration.md)
  and [Epic closeout](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/delivery-closeout-live-integration.md).
- [Workspace Intake and Inventory](https://github.com/mfshaf7/governance-operations-console/blob/main/docs/product/workspace-intake-live-integration.md)
  and [product publication](product-publication.md).

## Project Shape And Evidence

A document or library, browser-local app and service with a database need
different owner checks and runtime choices. Repository bootstrap makes CI an
explicit choice; the demo is not a universal CI or deployment template.
Required evidence follows the selected owner profile and accepted plan.

Before implementation, compare the whole initiative's ordered source work,
human decisions, evidence-kind/fidelity coverage and terminal outcome. Read
completion narratives alongside machine-readable start/close dependencies.
A narrative must not require a later child to finish before its prerequisite
can close. Resolve that contradiction in the existing plan and owner scope.
Native configured-path preflight exposes current narrative blockers and
accepted-base evidence coverage before source start. Do not replace that
whole-plan review with a sequence of child-local repairs.

Board counters, status badges and successful owner unit tests do not prove a
whole journey. Source CI proves source; a Security reader proves admission or
conformance; an actual owner operation and canonical receipt prove operation.
Keep those distinctions in the capability observation. The acceptance app's
finalized packet records nine unit and seven serial browser cases, including
storage-denial and corrupt-storage behavior. Synthetic inputs remain labeled
as such; they do not establish a live owner handoff.

## Interruption, Rejection And Rollback

For a lost or timed-out response, retain the original request and intent and
read that owner result before another write. Reopen the same work item and use
Recover original source scope or the existing resume/read action. Inspect its
operation and receipt. An unavailable response does not prove owner rejection.
Do not repeat provisioning, admission, publication, source start or completion
because a local modal was lost.

For explicit rejection, inspect both the rejected command and current canonical
revision. Correct the rejected input, review the changed decision and follow
the owner action. Completion summaries are paragraphs; changed surfaces are
explained flat bullets; test/validation fields use their native prefixes.
Optional Residual Follow-Up also requires flat bullets. Include every entered
optional field in an engineering preflight. Inspect the current modal and any
discard confirmation before issuing the next action.

Normal source closeout retires only its owned resources and revokes its exact
scope. Revert a merged owner Landing Unit through its reviewed source path;
stop a preview through its original owner control; restore a composed runtime
through Platform's existing rollback procedure. Keep ART, Git, Security, denial,
operating and owner-receipt history. A later attempt cannot rewrite earlier
evidence or inherit an unproven success receipt.

## Final Acceptance And Restart

Final acceptance needs current child/evidence coverage, earned PI review,
native Epic demo and inspection review, primary guidance and exact source
cleanup. Source work needs finalized packets; non-source outcomes need actual
owner proof. Closing the app Epic does not itself close the system initiative.

After a security-evidenced owner merge, run existing structured-record preflight
and generated Security-index validation before adjacent closure. Land the
dependent index update after the owner record exists on remote main. Use this
existing rejection and procedure rather than invent another lifecycle action.
Refresh composed exact-source admission when changed paths exceed its reviewed
record-only allowance.

After source cleanup, obtain the existing WGCF `authority:workspace-clean-state`
receipt. Preserve dirty or unique work and record its disposition before a
cleanliness claim. Keep the single local continuity handoff current while
meaningful pending state remains. Restart readiness also needs the accepted
complete composition, current credential/provider bindings and owner readback;
a historical source check is insufficient.

## Validation

Run:

```bash
python3 scripts/validate_contracts.py --repo-root .
python3 -m unittest tests.test_console_operational_capabilities
python3 scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --check-generated
```

The first command validates the schema and semantic separation rules. The unit
tests exercise positive and negative cases. The generated-view check proves
that the compact operator review view still matches the canonical contract.
