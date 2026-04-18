# Developer-Integration Profile Template

Use this template lane when a repo needs a reusable `dev-integration` profile
for fast local iteration before governed stage rehearsal.

The profile file must be owned by the repo that owns the concrete workflow,
not by `workspace-governance/`.

Expected layout:

```text
<owner-repo>/
`-- dev-integration/
    `-- profiles/
        `-- <profile-id>/
            |-- profile.yaml
            |-- README.md
            `-- scripts/
                |-- up.sh
                |-- status.sh
                |-- smoke.sh
                |-- down.sh
                |-- reset.sh
                `-- promote-check.sh
```

Required profile keys:

- `schema_version`
- `profile_id`
- `summary`
- `runtime`
- `source_repos`
- `commands`
- `session`
- `stage_handoff`

Required command ids:

- `up`
- `status`
- `smoke`
- `down`
- `reset`
- `promote_check`

The shared lane standard lives in:

- `contracts/developer-integration-policy.yaml`
- `contracts/developer-integration-profiles.yaml`
