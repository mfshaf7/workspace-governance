# Agent Action Authority

This is the primary workspace operator surface for classifying and authorizing
AI-assisted actions that cross owner or workflow boundaries.

The canonical machine-readable contracts are:

- [agent-action-authority.yaml](../contracts/agent-action-authority.yaml) for
  generic `read`, `advise`, `draft`, and `mutate` authority
- [agent-source-implementation.yaml](../contracts/agent-source-implementation.yaml)
  for governed source authorship under that authority model

## Core Rule

Agent identity records attribution. It does not grant authority.

An action is eligible only when the accountable operator, authenticated caller,
admitted workflow, action class, exact target, current source version, current
policy decision, and any required approval all agree. Owner-repo business rules
remain authoritative for the final operation.

## Source Implementation Identity

Source implementation uses a distinct identity so authorship can be reviewed
independently from human approval. The first registered source implementor is:

- display name: `Agent Gary`
- logical agent id: `agent-gary`
- role: source implementor
- provider principal: `mfshaf7-agent-gary[bot]`
- Git author: `Agent Gary` using the GitHub-recognized App bot noreply address
- current state: contract defined, not normally active

Future logical AI-agent display names use `Agent <Name>` and machine ids use
`agent-<name>`. Human users, service workloads, model providers, and backend
executors do not use this naming class.

The authority split is strict:

| Principal | Responsibility |
| --- | --- |
| Human operator | Accountable reviewer, approver, and merger |
| Agent Gary | Attributed branch author and pusher |
| Operator Orchestration Service | Admitted workflow coordinator and receipt owner |
| GitHub App installation | Authenticated source transport only |
| Platform Engineering | Credential custodian and short-lived token issuer |

Agent Gary may author and push an exact non-default review branch and open or
update its pull request. Agent Gary cannot approve or merge that pull request,
push the default branch, administer a repository, modify repository rules,
broaden installation scope, or use the operator's GitHub credential as a
fallback.

## Source Session Binding

Before a credential is issued or a branch is pushed, every governed source
session binds:

- logical agent id and provider installation id
- provider principal and exact Git author name and email
- exact Landing Unit, owner repo, and repository id
- branch and fetched base
- token expiry
- intended human reviewer id

Completion evidence then binds the pushed head, the exact head reviewed by the
human operator, and the merged head read back from the source provider.

The provider installation is selected-repository only. Its minimum permissions
are Metadata read, Contents write, Pull requests write, and Checks read.
Evidence records the bindings and durable references, never private keys,
installation tokens, or other secret values.

The Git author identity must resolve to the bound provider principal. A local
or otherwise unattributed email is not acceptable because repository policy
cannot distinguish it from unowned source and may require an impossible extra
human approval.

Agent authorship is not independent review. A source Landing Unit is not
complete until the human operator reviews the exact pushed head, explicitly
authorizes the merge, and the merged head is read back and reconciled.

## First Identity Bootstrap

The first source identity has a bounded bootstrap because the normal OOS token
consumer cannot activate until the identity contract, Security review, and
Platform commissioning have landed in order. The operator-approved bootstrap
is bound to the current Delivery architecture packet and work items #1134
through #1137 only.

That bootstrap may register the selected-repository GitHub App, place its
private key under Platform custody, mint a short-lived installation token, and
author the exact non-default review branches for those work items. It does not
activate shared runtime behavior, mutate a default branch, approve or merge a
pull request, expand repository scope, or permit human-credential fallback.

Normal Agent Gary activation remains disabled until Security accepts the exact
boundary in #1135, Platform commissions it in #1136, and OOS activates bounded
credential consumption in #1137.

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

The separate source-implementation path is also fail closed. Defining Agent
Gary in this contract does not activate normal provider use; its activation
requirements are recorded under `source_implementation.normal_activation`.

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
