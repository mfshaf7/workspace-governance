# Developer-Integration Profile Request Template

This template is supporting material, not the primary operator procedure.

For the current operator-facing request and usage path, use:

- [platform-engineering/docs/runbooks/dev-integration-profiles.md](https://github.com/mfshaf7/platform-engineering/blob/main/docs/runbooks/dev-integration-profiles.md)

Use this template when a team needs a new `dev-integration` profile and there
is no suitable `active` profile already available.

The request model is generic. It should work whether the current request
surface is OpenProject, Git, a portal, or another future adapter.

Required request information:

- requested profile id
- owner repo
- purpose
- participating repos
- runtime dependencies
- expected canonical backend writes, if any
- whether identity, secrets, runtime privilege, or AI review is involved
- requested by
- request record system
- request record ref

Minimum decision path:

1. request recorded
2. owner repo confirms the profile shape belongs there
3. `platform-engineering` accepts or rejects the shared-lane fit
4. `security-architecture` reviews it when the request widens risky boundaries
5. `workspace-governance` records the admitted lifecycle state

Lifecycle targets:

- `proposed`
  - request exists but the profile is not self-serve launchable
- `active`
  - admitted and launchable on the shared runner
- `suspended`
  - admitted before, but temporarily blocked
- `retired`
  - no longer part of the active profile set

Current implementation note:

- the current request surface adapter may be OpenProject
- the contract should still record only:
  - `request_record.system`
  - `request_record.ref`

That keeps the model reusable if the request surface changes later.
