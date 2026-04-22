# Delegated Execution

This is the primary operator surface for workspace-wide delegated execution.

Use it when the main agent wants bounded sub-agents to accelerate delivery
without giving up work-state, security, or proof discipline.

## Purpose

Delegated execution is a governed capability, not an excuse to let parallel
workers improvise scope.

The durable model is:

- `workspace-governance` owns policy
- the main agent owns orchestration authority
- delegated workers own bounded execution only
- audit records prove who was delegated what and how the result was integrated

## Authority Split

The main agent always retains:

- work-system mutation
- live environment mutation
- security decision closure
- final proof
- final completion
- PI replanning
- change classification and scope routing

Delegated workers may own:

- bounded repo-local implementation
- tests
- docs or change records
- read-only exploration

Delegated workers do not own workflow authority.

## Eligibility Gate

Do not delegate until all of these are true:

1. The work is already classified in the current system of record or is an
   explicitly bounded local support task.
2. Scope and evidence expectations are clear enough to delegate safely.
3. The main agent has confirmed that no unresolved blocker prevents the
   delegated slice.
4. Disjoint write scope is declared before delegation starts.
5. Each delegated packet declares expected outputs and forbidden actions.

For ART-backed delivery, the main agent should start from the ART first and
keep the active front honest before any spawn.

## Task Classes

Current governed task classes live in
[contracts/delegation-policy.yaml](../contracts/delegation-policy.yaml).

The important operating distinction is:

- `repo-local-implementation`
  - bounded local repo work
- `cross-repo-delivery`
  - one feature or fix spanning multiple repos with main-agent integration
- `security-significant-delivery`
  - delegated implementation that changes trust boundaries, identity, secrets,
    privileged runtime, or AI-shaped action paths
- `live-control`
  - ART, dev-integration, stage, prod, or other live control-plane mutation

`live-control` does not delegate.

## Delegation Packet

Every delegated write must have a packet. The canonical shape is:

- `work_item_ref`
- `summary`
- `owner_repo`
- `allowed_write_paths`
- `expected_outputs`
- `proof_expectation`
- `forbidden_actions`

Use the template in
[templates/delegation-packet/TEMPLATE.yaml](../templates/delegation-packet/TEMPLATE.yaml)
when drafting a new packet.

## Audit Journal

Every delegated write and every security-significant delegated run must leave a
journal record under
[reviews/delegation-journal/](../reviews/delegation-journal/).

The journal record must capture:

- the work item and task class
- what the main agent retained
- each delegated packet
- declared write scope
- integration outcome
- security review reference when required

Validate journal records with:

```bash
python3 scripts/validate_delegation_journal.py --workspace-root /home/mfshaf7/projects
```

## Scope Discovery

If a delegated worker finds more work than expected:

- tiny in-scope follow-up:
  - absorb it into the active item only when it does not change planning
    meaning
- meaningful in-scope follow-up:
  - create or update the work record first
- out-of-scope work:
  - route it to the owner repo, intake, or improvement layer as appropriate

The delegated worker may discover scope. The main agent still classifies it.

## Security

Security-significant delegated work still routes through
`security-architecture`.

Delegated workers may implement a bounded security-significant slice, but the
main agent still owns:

- delta-review closure
- risk acceptance judgment
- final decision about whether the change can land

## Self-Improvement

Delegation mistakes are not normal noise.

If delegated work:

- overlaps write scope
- mutates live control surfaces
- creates uncovered work that is left out of the work system
- or bypasses main-agent proof or closure

route that miss through the self-improvement system.

Primary operator surface:

- `docs/self-improvement-escalation.md`
