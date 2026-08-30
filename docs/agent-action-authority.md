# Agent Action Authority

This is the primary workspace operator surface for classifying and authorizing
AI-assisted actions that cross owner or workflow boundaries.

The canonical machine-readable contract is
[contracts/agent-action-authority.yaml](../contracts/agent-action-authority.yaml).

## Core Rule

Agent identity records attribution. It does not grant authority.

An action is eligible only when the accountable operator, authenticated caller,
admitted workflow, action class, exact target, current source version, current
policy decision, and any required approval all agree. Owner-repo business rules
remain authoritative for the final operation.

## Action Classes

| Class | Purpose | Canonical mutation | Approval |
| --- | --- | --- | --- |
| `read` | Read admitted state through an owner-approved path. | No | Not required |
| `advise` | Produce model-assisted guidance from governed context. | No | Not required |
| `draft` | Produce a noncanonical change candidate for operator review. | No | Operator accepts the output before any later mutation request |
| `mutate` | Ask an admitted owner workflow to change canonical state. | Yes | Exact operator approval is required before owner invocation |

Do not upgrade an `advise` or `draft` result into mutation authority. A later
mutation is a new bound request with a current source version and approval.

## Authority Sequence

1. Classify the requested action as `read`, `advise`, `draft`, or `mutate`.
2. Bind the operator, caller workload, logical agent, workflow execution,
   target, source version, intent digest, context receipts, and idempotency key
   in an `agent_action_request`.
3. Ask Workspace Governance Control Fabric to evaluate that exact request.
4. Continue only when the returned policy decision is current and every binding
   still matches.
5. For `mutate`, verify the exact operator approval before calling the admitted
   owner workflow.
6. Let the owner adapter enforce business eligibility and emit an owner receipt
   when it is invoked.
7. Emit one terminal action receipt for success, denial, failure, or
   cancellation.

## Receipt Boundaries

- Workspace Governance Control Fabric owns policy decisions.
- Operator Orchestration Service owns shared-workflow action receipts.
- The domain owner emits the owner receipt for an invoked owner action.
- Security Architecture owns final security acceptance.

Receipts carry digest-bound references, reason codes, versions, and outcomes.
They do not carry raw context, raw model output, credentials, or secret
material.

## Fail-Closed Conditions

Deny or stop the action when any of these is true:

- the caller, operator session, agent instance, or workflow execution differs
  from the evaluated request
- the target or source version changed
- the decision or approval expired
- mutation approval is absent or points at another request
- the idempotency key was already consumed for a different intent
- the owner workflow is not admitted or rejects business eligibility
- a required context, decision, action, owner, or audit receipt is missing
- a caller tries to use direct model-provider or owner-backend access

## Current Activation Boundary

The contract and schemas are the active foundation. Shared runtime mutation is
not active yet. Runtime activation remains blocked until the policy evaluator,
workflow enforcement, integrated conformance, and Security acceptance outcomes
listed in the canonical contract are complete.

The Governance Operations Console may display safe posture and submit requests
to admitted server workflows. It does not authorize actions and must not trust
its current local or synthetic identity as shared authority.

## Integrated Conformance

The bounded local proof is declared in
[contracts/agent-action-conformance.yaml](../contracts/agent-action-conformance.yaml)
and rendered in
[reports/agent-action-conformance.md](../reports/agent-action-conformance.md).
It invokes the exact merged WGCF evaluator and OOS enforcer source revisions,
uses a synthetic owner adapter, and records only digest-bound decision and
receipt references. It does not activate shared runtime behavior or mutate a
canonical backend.

The proof materializes each pinned revision from Git history and verifies that
it remains an ancestor of that owner repo's canonical `main`. Unrelated later
merges therefore do not rewrite or invalidate the approved proof source.

Run or verify it from the workspace root with:

```bash
python3 workspace-governance/scripts/agent_action_conformance.py \
  --workspace-root /home/mfshaf7/projects --check
```
