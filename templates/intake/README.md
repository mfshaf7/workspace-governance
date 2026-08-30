# Intake Template

Use the intake layer when a new repo, product, or component appears in the
workspace and you need to decide whether it should become part of the governed
system.

The intake decision is explicit:

- `out-of-scope`
  - tracked so workspace audit knows the entrant is deliberate, but it does not
    join the governed control plane
- `proposed`
  - candidate for governance, with owner and scope discussion still open
- `admitted`
  - accepted into the governed path and ready to be promoted into the active
    contracts once the owning surface is prepared

Read the current digest and version bindings before constructing the v2
request and decision artifacts:

```bash
python3 scripts/workspace_intake.py state --kind <repo|product|component> --name <name>
```

Follow [`docs/workspace-intake.md`](../../docs/workspace-intake.md) for the
artifact chain, deterministic apply command, review boundary, and validation.
`scaffold_intake.py` is a temporary compatibility front end, not a separate
authority writer.
