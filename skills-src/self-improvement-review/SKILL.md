---
name: self-improvement-review
description: Use after meaningful misses, late discoveries, repeated operator pain, or when the user asks what the system learned and which durable controls should be added next.
---

# Self-Improvement Review

Use this skill when a task exposed a weakness in routing, workflow design,
evidence, host drift detection, testing seams, or operator reliability.

## Read First

- `contracts/README.md`
- `docs/self-improvement-escalation.md`
- `contracts/failure-taxonomy.yaml`
- `contracts/improvement-triggers.yaml`
- `contracts/self-improvement-policy.yaml`
- `reviews/improvement-candidates/README.md`
- `reviews/after-action/README.md`
- `scripts/README.md`

## Workflow

1. Identify what was discovered too late or failed repeatedly.
2. Classify it with one or more `failure-taxonomy` classes.
3. Choose the trigger that explains the signal.
4. Run the signal check from `docs/self-improvement-escalation.md` first.
   - use `python3 scripts/check_self_improvement_escalation.py ...`
   - if it exits `2`, candidate capture is mandatory before normal work
     continues
5. Record or update an improvement candidate immediately when:
   - the user explicitly says this is a repeated mistake
   - the user calls the work half-baked, incomplete, sloppy, or says a miss
     should have been caught already
   - the same workflow needs a corrective follow-up in the same task
   - an active work transition is left incomplete, such as closing one
     feature/task/phase without explicitly recording the next committed
     work-state
   - a machine-visible audit flags a doctrine or completion miss
   - the control-plane summary or review-control validator flags repeated drift
   - an active `dev-integration` profile's stage-handoff contract, README, or
     promote-check expectations lag behind the landed workflow surface
   - the eventual root cause turns out to be a skipped simpler precondition,
     environment truth, permission truth, or contract truth check that should
     have been proven before workaround analysis
   - delegated execution crossed packet scope, write-scope, live-control, or
     work-tracking boundaries
6. If the miss regresses a lesson that was already treated as closed:
   - record it as a regression candidate, not as a vague new issue
   - set `regression_of` to the earlier closed candidate or after-action
   - use trigger `closed-lesson-regression`
   - treat this as evidence that the earlier closure controls were too weak or
     too narrow
7. Propose the best fix shape for the candidate, justify why that fix is the
   best option, and get operator approval before landing the durable control.
8. Decide whether the lesson is:
   - still only a candidate that needs triage, or
   - strong enough for a full after-action review now
9. If a full after-action is required, choose the trigger that explains why.
10. Decide whether the lesson is:
   - closed by durable controls already added, or
   - still open with a real owner and due date
11. Record the review under `reviews/after-action/` when warranted.
12. Validate both the candidate layer and learning closure:

```bash
python3 scripts/validate_improvement_candidates.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_learning_closure.py --workspace-root /home/mfshaf7/projects
```

## Guardrails

- Do not leave a major miss only in chat.
- Do not rely on memory alone when the signal is in the governed runtime gate;
  run the escalation check.
- Do not wait for a user to restate the same problem twice before recording a
  candidate.
- If the user explicitly calls out a repeated mistake, open or update a
  candidate even if the final after-action shape is not ready yet.
- If a simpler root cause is discovered late because earlier troubleshooting
  layers were skipped, use trigger `late-root-cause-discovery` and classify it
  as a diagnostic-ordering miss when that matches the case.
- If active work becomes half-finished at the planning, control, or completion
  layer, do not continue normally. Record the candidate first and surface the
  miss.
- If a supposedly closed lesson regresses, do not represent it as a brand-new
  unrelated miss. Link the regression explicitly.
- If delegated execution crosses main-agent-only authority, overlaps write
  scope, or leaves meaningful scope outside the work system, record that as a
  control miss instead of treating it as normal task churn.
- Do not make the operator invent the fix from scratch when the likely control
  improvement is clear. Propose the best fix yourself and explain the
  reasoning.
- Do not auto-land the durable control after opening a candidate. The operator
  still approves the chosen fix shape before closure work starts.
- Treat stale `dev-integration -> stage` closure doctrine as a first-class
  self-improvement signal. If source-landed work is being mistaken for workflow
  closure, add a validator, runbook update, and skill update rather than only
  recording the miss.
- Do not close a lesson without linking the actual control changes that landed.
- Do not bury architecture or workflow doctrine changes in the record alone; add
  the ADR, contract, validator, runbook, or skill update too.
- Open lessons are allowed, but only with an explicit owner, due date, and next
  control to land.
