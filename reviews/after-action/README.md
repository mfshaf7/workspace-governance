# After-Action Reviews

Use this directory for governed learning records.

This is the closure layer, not the first signal layer.

If the system has only recognized a likely repeated miss or late discovery and
the durable control shape is not ready yet, record an improvement candidate
first under `../improvement-candidates/`.

An after-action review should capture:

- what was discovered too late
- the failure class and trigger
- the operational or architecture impact
- whether the lesson is still open or closed
- the durable controls that were added, or the explicit follow-up owner and due date

These are not free-form notes.

Validate them with:

```bash
python3 scripts/validate_learning_closure.py --workspace-root /home/mfshaf7/projects
```

Use [TEMPLATE.yaml](TEMPLATE.yaml) or `scripts/record_after_action.py` to start
new records.
