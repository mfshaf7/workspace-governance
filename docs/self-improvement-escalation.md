# Self-Improvement Escalation

This is the primary operator surface for in-session self-improvement
escalation in the workspace.

Use it when a meaningful miss becomes visible during active work and normal
execution should not continue until the learning signal is recorded.

## Scope

Use this workflow when any of these happen:

- the operator explicitly says the miss is a repeated mistake
- the operator explicitly says the work is half-baked, incomplete, sloppy, or
  should have been caught already
- active work changes phase or status without the next committed work-state
  being recorded cleanly
- the same workflow needs another corrective follow-up in the same task or
  session
- a validator, quality gate, or structured read model exposes workflow drift
- a live ART mutation, closeout, or review seam fails and the exact blocker is
  not yet recorded in ART
- a simpler root cause is discovered late after deeper analysis had already
  expanded
- delegated execution crosses packet scope, write scope, live-control, or
  work-tracking boundaries

## Rule

If the signal is in the governed runtime gate, pause normal execution first.

Do not keep implementing, debugging, or closing work as if the miss is only
chat commentary.

Record the candidate first, then decide the durable fix.

## Signal Check

Run the signal check before continuing:

```bash
python3 scripts/check_self_improvement_escalation.py \
  --repo-root . \
  --signal <signal-id> \
  --owner-repo workspace-governance
```

If the command exits with code `2`, the signal is in the fail-closed set and a
candidate must be created before normal work continues.

The governed signal catalog lives in:

- `contracts/self-improvement-policy.yaml`

## Candidate Capture

When the signal requires capture, scaffold the candidate immediately:

```bash
python3 scripts/check_self_improvement_escalation.py \
  --repo-root . \
  --signal operator-repeated-mistake-callout \
  --owner-repo workspace-governance \
  --candidate-id 2026-04-22-example-self-improvement-signal \
  --title "Replace with candidate title" \
  --summary "Replace with candidate summary" \
  --finding "Replace with the concrete signal and why work must pause" \
  --source-ref "conversation: operator explicitly said this is a repeated mistake" \
  --related-repo workspace-governance \
  --change-class architecture-shaping \
  --write-candidate
```

Use `--regression-of <closed-record-path>` when the same lesson was already
treated as closed and has clearly regressed again.

## Recommended Signal IDs

- `operator-repeated-mistake-callout`
- `operator-half-baked-callout`
- `active-work-transition-incomplete`
- `repeated-corrective-follow-up`
- `machine-visible-workflow-drift`
- `live-art-mutation-proof-gap`
- `late-root-cause-discovery`
- `delegated-execution-control-breach`

## Follow-On

After the candidate exists:

1. explain the miss clearly
2. propose the strongest durable fix
3. get operator approval for that fix
4. land the control change
5. close through an after-action when warranted

## ART Blocker Honesty

When the signal is an active ART blocker rather than only a workflow lesson:

1. stop adjacent ART mutation on the same initiative
2. state the exact blocked step and exact blocker
3. record the blocker in ART on the affected work item
4. open or update a real `Defect` when the blocker is caused by a live system
   or control bug
5. open or update a `Risk` when the exposure is broader than one blocked item

Do not keep the blocker only in chat, only in a candidate record, or only in a
status label.

## Guardrails

- Do not leave a major miss only in chat.
- Do not continue active delivery work normally after a fail-closed signal.
- Do not wait for the operator to restate the same complaint twice.
- Do not close a regression signal as if it were a brand-new unrelated lesson.
- Do not treat candidate capture as the durable fix. It is the stop-and-record
  layer, not the closure layer.
