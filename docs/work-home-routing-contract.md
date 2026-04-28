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
4. `owner_repo_maintenance`
5. `new_business_or_architecture_idea`
6. `late_discovered_unclassified_work`

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

## Boundary With Later Doctrine

This contract defines the machine-readable routing model. Operator-facing
doctrine and AGENTS guidance should point at this contract, but that publication
step is separate from the contract definition work.
