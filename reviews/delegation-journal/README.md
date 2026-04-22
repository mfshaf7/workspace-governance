# Delegation Journal

Use this directory for governed delegated-execution audit records.

A delegation journal record is required when:

- delegated work writes to a repo
- delegated work is security-significant

The journal is not a narrative handoff note. It is the durable record of:

- which work item was being executed
- which task class allowed delegation
- what the main agent retained
- what each delegated packet was allowed to change
- whether the result was integrated or rejected

Use [TEMPLATE.yaml](TEMPLATE.yaml) to start a new record.

Validate records with:

```bash
python3 scripts/validate_delegation_journal.py --workspace-root /home/mfshaf7/projects
```
