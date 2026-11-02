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
- requested runtime state model:
  - `disposable`
  - `persistent`
- participating repos
- runtime dependencies
- expected canonical backend writes, if any
- whether identity, secrets, runtime privilege, or AI review is involved
- requested by (derived from the verified operator)
- request record system and ref (returned by OOS, not manually entered)

Additional required information for `persistent` requests:

- persistence justification
  - why a disposable lane is insufficient
- retained data scope
  - what data must survive normal `devint-down` / `devint-up`
- suspend/resume semantics
  - what operators expect `devint-down` and `devint-up` to preserve
- storage size or class
  - expected PVC size, storage class, or other local-runtime assumptions
- destructive reset semantics
  - exactly what `devint-reset` is allowed to wipe
- cutover plan when upgrading
  - required when an existing disposable profile is being turned into a
    persistent project-backed lane
- smoke mutation mode
  - persistent profiles must keep shared `devint-smoke` read-only
- disposable companion profile, if mutating smoke is still required
  - mutating smoke must move to a separate disposable profile instead of
    writing test artifacts into the persistent working lane

Minimum decision path:

1. request recorded
2. owner repo confirms the profile shape belongs there
3. `platform-engineering` accepts or rejects the shared-lane fit
4. `security-architecture` reviews it when the request widens risky boundaries
5. `workspace-governance` records the admitted lifecycle state

For `persistent` requests, the decision path should also confirm:

1. the retained data scope is acceptable for a local ungoverned lane
2. the storage model is acceptable for the shared local-k3s implementation
3. the destructive reset boundary is documented before launch

Lifecycle targets:

- `proposed`
  - request exists but the profile is not self-serve launchable
- `build-admitted`
  - platform and security gates authorize bounded owner-repo implementation,
    but the profile is not self-serve launchable
- `active`
  - admitted and launchable on the shared runner
- `suspended`
  - admitted before, but temporarily blocked
- `retired`
  - no longer part of the active profile set

Use `build-admitted` for the bootstrap gap where service code and profile-owned
runtime wiring must be built before `active` smoke can honestly pass. Do not
use it as launch evidence.

## Current request workflow

Use **Dev Integration → Request Profile** in the Console. OOS owns the durable
request, exact operator attribution, receipt and original-request recovery.
Submission and status remain in Dev Integration. Routine profile requests do
not create Proposal or Delivery ART items.

After owner review, reference the exact original request in the profile record:

- `request_record.system: oos`
- `request_record.ref: oos://dev-integration/requests/<request_id>`

Recording a request does not admit, implement or start the profile. Workspace
Governance retains admission, Platform retains runtime execution, and Security
retains its applicable review. Existing OpenProject or document references on
older profiles remain historical provenance and do not require replacement.

The generic `request_record.system` and `request_record.ref` fields remain
adapter-neutral. A future workflow change must reconcile the operator procedure,
selected adapter and implementation together. Contract selection alone does not
prove that the runtime adapter is activated; unavailable submission must remain
visible in the Console until commissioning passes.
