# Context Admission Governance

This is the primary operator surface for workspace context admission adoption.

Machine-readable contracts:

- [contracts/context-behavior.yaml](../contracts/context-behavior.yaml)
- [contracts/raw-context-retirement.yaml](../contracts/raw-context-retirement.yaml)

## Purpose

Operational context is not harmless text. Terminal output, CI logs, runtime
diagnostics, ART payloads, review packets, and security evidence can contain
secrets, topology, account identifiers, internal hostnames, private IPs, or
authority-store details.

The workspace rule is:

1. Capture raw context.
2. Normalize and classify it.
3. Redact or suppress risky material.
4. Slice and budget it.
5. Project only a model-safe or operator-safe packet.
6. Preserve digest, receipt, and artifact custody evidence when required.

`context-governance-gateway` implements that context admission behavior.
`workspace-governance` owns the declaration and retirement contracts.
`workspace-governance-control-fabric` may consume CGG receipts, but it does not
replace CGG. `operator-orchestration-service` remains the Delivery ART mutation
authority. `platform-engineering` remains deployment and profile authority.
`security-architecture` remains security acceptance authority.

## When To Use This

Use this workflow when a repo, component, product source, CI job, operator
workflow, runtime diagnostic, or ART path emits context that could be sent to an
agent, model, operator packet, CI automation, review packet, or debugging tool.

Do not use this workflow to justify sending raw output directly to a model.
Token reduction is a benefit, not the authority boundary. The authority boundary
is context admission control.

## Operator Flow

1. Identify the context source.

   Examples: terminal output, CI logs, repo snapshots, ART work-item context,
   platform runtime logs, operator payloads, or security review context.

2. Check whether the repo has a declaration in
   [contracts/context-behavior.yaml](../contracts/context-behavior.yaml).

   If the repo is active and missing, the contract is incomplete. If the repo is
   proposed or admitted through intake, the intake decision must say whether
   context behavior is required before the entrant becomes active.

3. If a direct raw-output path exists, check or add it in
   [contracts/raw-context-retirement.yaml](../contracts/raw-context-retirement.yaml).

   Record the owner repo, covered repos, current raw path, current risk, target
   CGG path, state, next action, rollback requirement, and evidence refs.

4. Use CGG packet output for model or automation context.

   The admitted context should be a packet, receipt, digest, safe excerpt,
   failure summary, and redaction summary. The full raw artifact stays local or
   in approved enterprise custody when retention is required.

5. Prove parity before retiring a legacy raw path.

   Parity means the packet preserves the diagnostic signal needed for the
   workflow while being safer than the raw path. Smaller output alone is not
   parity.

6. Close through ART evidence when the work is part of an accepted initiative.

   Source-backed closeout needs a finalized Review Packet that maps the landed
   PR or approved source evidence to the covered ART children.

## Status Model

- `declared`: workspace-level behavior is declared; owner-native adoption may
  still be pending.
- `native-provider`: the repo implements CGG behavior directly.
- `packet-consumer`: the repo consumes CGG packets or receipts.
- `parity-required`: legacy raw-output path remains until packet parity is
  proven.
- `retirement-eligible`: the legacy path may be removed after evidence and
  owner closeout.
- `retired`: legacy path is removed and must not return without a new
  exception.
- `not-required`: no operational context projection path exists.

## Intake Rule

New repos, products, components, and runtime profiles are not forced to become
CGG consumers by default. They are forced to make an explicit decision.

The intake decision must identify whether operational context is emitted,
consumed, stored, or projected. If yes, the entrant needs a context-behavior
declaration and any legacy raw-output path must enter the retirement inventory.

If no, record `not-required` with a reason. Silent omission is not a valid
state for an active governed repo.

## Retirement Rule

Do not delete a raw-output path just because CGG exists. Retire only after:

- the owner repo and current path are recorded
- the target CGG packet path is recorded
- the packet preserves the needed diagnostic signal
- redactions, suppressed content, artifact custody, digest, and receipt are
  recorded
- rollback remains until the entry reaches `retired`
- security and platform gates are current when the path crosses those
  authorities
- ART Review Packet evidence covers the work when the retirement is initiative
  work

After an entry reaches `retired`, legacy fallback is denied. Reintroducing it
requires a new exception with owner, rationale, expiry, and audit reference.

## Denied Shortcuts

- Do not paste raw terminal, CI, Kubernetes, ART, or security output into model
  prompts because it is faster.
- Do not treat a shorter summary as packet parity when diagnostic signal is
  missing.
- Do not use CI-only evidence when operator-side proof was blocked but the
  blocker was not recorded.
- Do not let CGG replace WGCF, OOS, platform release authority, or security
  acceptance.
- Do not retire legacy raw-output paths before packet parity and rollback
  evidence exist.

## Evidence Checklist

Before closing context adoption or retirement work, evidence should name:

- ART items covered
- owner repo and branch or PR evidence
- affected context source classes
- legacy raw path and target CGG packet path
- packet digest or receipt evidence
- redaction and suppression behavior
- artifact custody and rollback posture
- validation commands and results
- security or platform gate references when applicable
