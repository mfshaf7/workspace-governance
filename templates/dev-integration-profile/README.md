# Developer-Integration Profile Template

Use this template lane when a repo needs a reusable `dev-integration` profile
for fast local iteration before governed stage rehearsal.

Before a new profile becomes self-serve launchable, record a request first and
admit it through the workspace contract model.

Do not require a profile for every new project by default. Require a
runtime-lane decision first:

- `no-runtime` for governance records, schemas, contracts, or docs.
- `local-only` for CLI or library tooling with no shared runtime lane.
- `dev-integration-required` for API, worker, database-backed, operator
  workflow, broker adapter, cross-repo runtime, or evolving topology work.
- `stage-direct` only when mature platform deployment, security, smoke,
  rollback, and release ownership already exist.

When a repo class is governed as dev-integration-required, the profile may
start as `proposed` so the runtime shape is recorded before implementation
drifts into API, worker, storage, or service assumptions.

Move a profile to `build-admitted` when platform and security gates explicitly
authorize bounded owner-repo service implementation, but the profile is not yet
safe to launch from the shared runner. Do not skip from `proposed` to
implementation work by pretending the profile is `active`.

Current lifecycle:

- `proposed`
- `build-admitted`
- `active`
- `suspended`
- `retired`

Only `active` profiles are launchable from the shared runner. `build-admitted`
profiles may permit implementation work, but `up`, `access`, and shared smoke
must still fail closed until the profile becomes `active`.

The profile file must be owned by the repo that owns the concrete workflow,
not by `workspace-governance/`.

Each profile must declare `runtime.state_model` as either:

- `disposable`
- `persistent`

Use `persistent` only when the local lane is expected to hold a long-running
project tree whose data should survive normal `devint-down` / `devint-up`
cycles. `devint-reset` remains the destructive wipe path.

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
- `testing`
- `source_repos`
- `commands`
- `session`
- `stage_handoff`

`testing.smoke.mutation_mode` must declare one of:

- `read-only`
- `mutating`

Persistent profiles must keep shared `devint-smoke` read-only. If a workflow
still needs mutating smoke, create a separate disposable companion profile
instead of letting tests write into the persistent working lane.

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

Optional command ids:

- `access`
  - use when the profile exposes a primary inspection surface such as a local
    OpenProject UI port-forward that an operator is expected to keep open

The shared lane standard lives in:

- `contracts/developer-integration-policy.yaml`
- `contracts/developer-integration-profiles.yaml`

The registry entry for a real profile should also carry:

- `lifecycle`
- `purpose`
- `requested_by`
- `requested_on`
- `request_record`
- `build_admission` when the profile is accepted for bounded implementation
- `admission` once the profile is accepted for self-serve use
