---
name: self-improvement-review
description: Use after meaningful misses, late discoveries, repeated operator pain, or when the user asks what the system learned and which durable controls should be added next.
---

# Self-Improvement Review

Use this skill when a task exposed a weakness in routing, workflow design,
evidence, host drift detection, testing seams, or operator reliability.

## Read First

- `contracts/README.md`
- `contracts/failure-taxonomy.yaml`
- `contracts/improvement-triggers.yaml`
- `reviews/improvement-candidates/README.md`
- `reviews/after-action/README.md`
- `scripts/README.md`

## Workflow

1. Identify what was discovered too late or failed repeatedly.
2. Classify it with one or more `failure-taxonomy` classes.
3. Choose the trigger that explains the signal.
4. Record or update an improvement candidate immediately when:
   - the user explicitly says this is a repeated mistake
   - the same workflow needs a corrective follow-up in the same task
   - a machine-visible audit flags a doctrine or completion miss
5. Decide whether the lesson is:
   - still only a candidate that needs triage, or
   - strong enough for a full after-action review now
6. If a full after-action is required, choose the trigger that explains why.
7. Decide whether the lesson is:
   - closed by durable controls already added, or
   - still open with a real owner and due date
8. Record the review under `reviews/after-action/` when warranted.
9. Validate both the candidate layer and learning closure:

```bash
python3 scripts/validate_improvement_candidates.py --workspace-root /home/mfshaf7/projects
python3 scripts/validate_learning_closure.py --workspace-root /home/mfshaf7/projects
```

## Guardrails

- Do not leave a major miss only in chat.
- Do not wait for a user to restate the same problem twice before recording a
  candidate.
- If the user explicitly calls out a repeated mistake, open or update a
  candidate even if the final after-action shape is not ready yet.
- Do not close a lesson without linking the actual control changes that landed.
- Do not bury architecture or workflow doctrine changes in the record alone; add
  the ADR, contract, validator, runbook, or skill update too.
- Open lessons are allowed, but only with an explicit owner, due date, and next
  control to land.
