# Developer-Integration Profile Template

Use this template lane when a repo needs a reusable `dev-integration` profile
for fast local iteration before governed stage rehearsal.

Before a new profile becomes self-serve launchable, record a request first and
admit it through the workspace contract model.

Current lifecycle:

- `proposed`
- `active`
- `suspended`
- `retired`

Only `active` profiles are launchable from the shared runner.

The profile file must be owned by the repo that owns the concrete workflow,
not by `workspace-governance/`.

Profile-owned docs should include, at minimum:

- `## Smoke Scope`
- `## Stage Handoff Checks`

The `## Stage Handoff Checks` list must mirror
`stage_handoff.required_checks` from both the repo-owned `profile.yaml` and the
workspace registry entry in `contracts/developer-integration-profiles.yaml`.

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

`stage_handoff` must include:

- `owner_repo`
- `governed_surface`
- `required_checks`

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

The registry entry for a real profile should also carry:

- `lifecycle`
- `purpose`
- `requested_by`
- `requested_on`
- `request_record`
- `admission` once the profile is accepted for self-serve use
