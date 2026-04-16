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
- `reviews/after-action/README.md`
- `scripts/README.md`

## Workflow

1. Identify what was discovered too late or failed repeatedly.
2. Classify it with one or more `failure-taxonomy` classes.
3. Choose the trigger that explains why an after-action is required now.
4. Decide whether the lesson is:
   - closed by durable controls already added, or
   - still open with a real owner and due date
5. Record the review under `reviews/after-action/`.
6. Validate learning closure:

```bash
python3 scripts/validate_learning_closure.py --workspace-root /home/mfshaf7/projects
```

## Guardrails

- Do not leave a major miss only in chat.
- Do not close a lesson without linking the actual control changes that landed.
- Do not bury architecture or workflow doctrine changes in the record alone; add
  the ADR, contract, validator, runbook, or skill update too.
- Open lessons are allowed, but only with an explicit owner, due date, and next
  control to land.
