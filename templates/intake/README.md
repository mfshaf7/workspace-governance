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

Use:

```bash
python3 scripts/scaffold_intake.py repo --name <repo> --status proposed --notes "<why>"
python3 scripts/scaffold_intake.py product --name <product> --status proposed --notes "<why>"
python3 scripts/scaffold_intake.py component --name <component> --status proposed --notes "<why>"
```
