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

- its own lifecycle; only `active` compositions may be launched
- one Platform-owned composition and root profile
- every participating profile and its required admitted lifecycle
- directed dependency edges from consumers to providers
- optional URL or host-and-port projections for a dependency edge
- optional non-secret caller identity bindings across an exact dependency edge
- runtime-generated credential bindings and the environment variable projected
  into each participant
- profile-owned non-secret literal or service bindings
- one dependency-first startup, profile-owned readiness, reverse-order
  teardown, rollback, and state-preservation contract

The registry contains names, ownership, service coordinates, and environment
variable targets only. Credential values must never be committed. Platform
generates and retains a binding for the composition lifetime, projects the same
value to the declared participants, and removes it when the composition is torn
down.

`proposed` and `build-admitted` compositions may name the lifecycle each
participant must reach, but they are not launchable. Their target lifecycle may
therefore be ahead of a participant's current lifecycle. Once a composition is
`active`, every participant must exactly match its required lifecycle.

Readiness remains profile-owned. A composition invokes the declared
`readiness_action` for every participant instead of duplicating HTTP paths or
component-specific health logic. Teardown uses the declared action in reverse
startup order, rolls back only profiles started by the failed composition, and
preserves persistent profile state.

## Validation And Failure

Both workspace contract validation and dev-integration validation reject:

- unknown or undeclared profiles
- profile lifecycle mismatches
- dependency cycles or participants unreachable from the root
- duplicate dependency or environment projections
- composition ownership that disagrees with profile runtime ownership
- active-composition lifecycle mismatches
- caller bindings that do not follow a declared dependency
- startup, readiness, or teardown actions absent from any participant
- cleanup ownership that differs from composition runtime ownership
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

## Refinement And Catalog Composition

`refinement-catalog` is registered as `proposed`. It cannot launch until the
separate Security review and Platform activation work make the exact
composition active.

Its root remains `accepted-idea-delivery`. The root depends on:

- `context-governance-gateway` for receipt-bound Refinement projection
- `governed-ai-gateway` for suggestion-only Refinement advice
- `governance-control-fabric` for digest-bound repository readiness
- `temporal` for recoverable Refinement apply execution

The contract binds the exact OOS caller identities and generated CGG, WGCF, and
Catalog-control credentials, projects URL endpoints and the Temporal
host-and-port address, and names the profile-owned Catalog endpoint, Refinement
activation flags, and Temporal namespace. It does not reuse the general
OpenProject API token and stores no secret value.

The Governance Operations Console is deliberately not a composition profile.
Its browser continues to call same-origin Console routes only; the Console
server's authenticated OOS integration belongs to the later Console Landing
Unit. The composition therefore exposes no browser path to CGG, WGCF, the AI
gateway, Temporal, or OpenProject and requires no visual change.
