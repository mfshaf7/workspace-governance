# Dev-Integration Runtime Composition

This is the workspace contract for composing already-admitted
`dev-integration` profiles. It does not launch runtimes and it does not own
credentials. The shared runner in `platform-engineering` consumes this contract
and remains the runtime authority.

Use a runtime composition when one profile cannot provide its operator workflow
without other registered profiles being ready at the same time. Source-repo
relationships remain in `shared_dependencies`; runtime startup and projection
relationships belong in `runtime_compositions`.

## Contract Shape

Each composition declares:

- one Platform-owned composition and root profile
- every participating profile and its required admitted lifecycle
- directed dependency edges from consumers to providers
- optional service endpoint projections for a dependency edge
- runtime-generated credential bindings and the environment variable projected
  into each participant

The registry contains names, ownership, service coordinates, and environment
variable targets only. Credential values must never be committed. Platform
generates and retains a binding for the composition lifetime, projects the same
value to the declared participants, and removes it when the composition is torn
down.

## Validation And Failure

Both workspace contract validation and dev-integration validation reject:

- unknown or undeclared profiles
- profile lifecycle mismatches
- dependency cycles or participants unreachable from the root
- duplicate dependency or environment projections
- composition ownership that disagrees with profile runtime ownership
- credential values or undeclared credential fields in tracked source

The runner must fail closed when a required profile, endpoint, or credential
projection is unavailable. It must not substitute fixture data or bypass the
declared provider.

## Work Design Composition

`work-design-advice` composes `accepted-idea-delivery` with
`context-governance-gateway` and `governed-ai-gateway`. The Console continues to
call only its same-origin server route, which calls OOS. OOS receives the two
declared service endpoints and one side of the CGG caller credential; CGG
receives the matching credential under its own environment variable.

The owner-repo landing order is:

1. workspace contract and validation
2. Platform dependency and credential projection
3. CGG active-profile caller admission
4. OOS composed advice proof
5. Security review before composed runtime activation

Independent profile launch remains valid. Removing the composition must disable
only the composed Work Design path, not the standalone profiles.
