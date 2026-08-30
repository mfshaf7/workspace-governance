# Workspace Intake

Workspace Intake classifies a new repository, product, or component before it
enters active workspace inventory. The canonical policy is
[`contracts/workspace-intake.yaml`](../contracts/workspace-intake.yaml); the
canonical records are in
[`contracts/intake-register.yaml`](../contracts/intake-register.yaml).

## What Intake Decides

Intake records one of three classifications:

- `out-of-scope`: known to the workspace and intentionally not governed here
- `proposed`: worth evaluating, but not admitted to active inventory
- `admitted`: accepted by intake, pending a separate reviewed inventory change

These classifications are not runtime or lifecycle status. `active`,
`suspended`, and `retired` belong to active inventory. Product maturity such as
`owner-managed`, `platform-integrated`, or `fully-governed` is a third,
independent axis.

An entrant may exist in intake or active inventory, never both.

## Authority Chain

1. A `workspace-intake-request` binds source, target, requested classification,
   owner route, desired record, current register digest, and idempotency key.
2. A `workspace-intake-decision` binds that exact request and records explicit
   operator acceptance. AI output remains suggestion-only.
3. The Workspace Governance mutation command changes exactly one record on a
   non-default review branch.
4. A pull request carries the source change through exact-head review and
   merge. The mutation command does not open or merge it.
5. Merged canonical readback is the success authority. Mutation, receipt, and
   readback artifacts preserve the evidence chain.

WGCF evaluates readiness without writing contracts. OOS owns the durable
workflow and merge wait. Platform owns the exact-repository application
identity. Security owns trust-boundary acceptance. Console projects the OOS
workflow and never writes these files directly.

## Current Owner Commands

Read the current optimistic-concurrency bindings before creating a request:

```bash
python3 scripts/workspace_intake.py state \
  --kind component \
  --name example-component
```

Apply one schema-valid, digest-bound request and decision on a review branch:

```bash
python3 scripts/workspace_intake.py apply \
  --request .art/workspace-intake/request.json \
  --decision .art/workspace-intake/decision.json \
  --output-dir .art/workspace-intake/result
```

The command emits `mutation.json`, a `review-branch` readback, and a
`source-preparation` receipt. It
rejects default-branch writes, detached heads, stale digests, mismatched
identity, reused idempotency keys with changed content, active-inventory
overlap, denied decisions, and implicit AI acceptance.

The request, decision, mutation, receipt, and readback schemas are under
`contracts/schemas/workspace-intake-*.schema.json`.

Decision findings are structured as `info`, `warning`, or `blocking`.
Blocking findings require a `remove`, `workaround`, `accept-risk`, or `defer`
disposition with justification and evidence. `workaround` and `defer` also
require an accountable owner and review date. `accept-risk` requires Security
evidence and explicit operator acceptance. `defer` produces `requires-action`
and can never authorize the mutation.

## Compatibility Add Command

`scripts/scaffold_intake.py` remains temporarily for existing callers. It now
builds v2 request and decision artifacts and delegates to
`workspace_intake.py`; it is not a second writer. New OOS and Console adapters
must consume the v2 artifact contract directly. Retire the wrapper only after
those adapters have operating proof.

## Validation

Run the owner checks before opening the pull request:

```bash
python3 scripts/validate_contracts.py --repo-root .
python3 scripts/validate_intake.py \
  --workspace-root /home/mfshaf7/projects \
  --repo-root .
python3 -m unittest tests.test_workspace_intake tests.test_governed_intake_assist
python3 scripts/validate_repo_structure.py --repo-root .
```

After merge, OOS must emit a `merged-authority` readback and bind it into the
terminal `succeeded` workflow receipt. A source-preparation receipt, local
artifact, or unmerged branch is not completion.

## Unsupported Shortcuts

- direct writes on `main` or `master`
- automatic merge
- Console or WGCF mutation of canonical contracts
- hard deletion of intake history
- treating intake admission as runtime activation or product maturity
- accepting model output without an explicit operator disposition
