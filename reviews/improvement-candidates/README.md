# Improvement Candidates

Use this directory for fast triage records when the system sees a likely miss
before it is ready to become a full after-action review.

This is the missing middle layer between:

- a conversational or machine-visible signal
- a governed after-action review with closure controls

Use an improvement candidate when:

- a user explicitly calls out a repeated mistake
- the same workflow needs a corrective follow-up in the same session
- a machine-visible audit detects a doctrine or completion miss
- the eventual root cause turns out to be a skipped simpler prerequisite or
  live-truth check that should have been proven before workaround analysis
- the miss looks real, but the durable control is not decided yet

If the miss is a regression of a lesson that was already treated as closed:

- record it as a regression candidate, not as a vague new note
- set `regression_of` to the earlier closed candidate or after-action record
- use trigger `closed-lesson-regression`
- treat that as an automatic signal that the earlier closure was too weak or too
  narrow

Expected handling:

- record the candidate automatically once the signal is real
- propose the best fix shape instead of waiting for the operator to invent one
- explain why that fix is the best option
- do not implement the durable control until the operator approves the fix
  shape
- close the candidate only after the approved control lands or an after-action
  review links the open follow-up explicitly
- when the candidate is a regression, prefer closing it through a new
  after-action so the stronger replacement controls are explicit

Lifecycle:

- `new`
  - signal captured, needs triage
- `triaged`
  - real signal, owner and next step assigned
- `accepted`
  - will become a real after-action or direct control change
- `dismissed`
  - signal was reviewed and should not continue
- `closed`
  - resolved by a linked after-action record or direct durable controls

These are not free-form notes.

Validate them with:

```bash
python3 scripts/validate_improvement_candidates.py --workspace-root /home/mfshaf7/projects
```

Run the proactive machine-visible signal audit with:

```bash
python3 scripts/audit_improvement_signals.py --workspace-root /home/mfshaf7/projects
```
