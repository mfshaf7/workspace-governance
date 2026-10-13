# Console Operational Capability Contract

This is the primary Workspace Governance surface for deciding whether the
Governance Operations Console has a complete idea-to-product plan and whether
one capability is genuinely available in live operation.

The machine-readable authority is
[`contracts/console-operational-capabilities.yaml`](../contracts/console-operational-capabilities.yaml).
The generated review view is
[`generated/console-operational-capabilities.json`](../generated/console-operational-capabilities.json).

## What The Contract Prevents

Three facts must never be collapsed into one claim:

- a capability is defined in a contract
- source implementing that capability exists
- a live runtime can execute it against its canonical authority

A fixture, Storybook story, or disconnected preview may prove presentation and
interaction behavior. It cannot prove live availability or completion. Live
mode must use owner-backed state and fail visibly when that owner is
unavailable; it must not substitute fixture data.

## Capability Status

Every status projection keeps five independent dimensions:

- contract state
- implementation state
- runtime state
- evidence state
- demonstration source

Only the `operational-live` profile is terminal capability evidence. It means
the contract is defined, implementation exists, the runtime is available,
evidence is validated, and the demonstration source is the live authority.
`planned`, `implemented-uncommissioned`, fixture, disconnected-preview, and
degraded profiles remain truthful non-terminal postures.

## Plan Completeness

An idea-to-product plan is complete only when every ordered journey stage has:

- a canonical authority reference and workflow owner
- a Console read model and explicit operator intents
- lifecycle, failure, and recovery states
- positive, negative, and terminal proof obligations
- accepted activation work and current authority references

The required journey is idea and proposal, prototype incubation, Delivery ART
planning, architecture decision, source realization, exact-head human review,
distinct Security acceptance, governed source merge, Workspace Intake and
Active Inventory, runtime and release, Product Portfolio, and interruption
recovery and audit.

The Console remains an adapter. OOS owns durable cross-domain orchestration,
domain owners retain canonical state, WGCF evaluates and stores bounded
governance evidence, Security decides trust acceptance, Platform owns runtime
composition, Git owns source truth, and OpenProject owns proposal and Delivery
ART work state.

## Validation

Run:

```bash
python3 scripts/validate_contracts.py --repo-root .
python3 -m unittest tests.test_console_operational_capabilities
python3 scripts/validate_cross_repo_truth.py --workspace-root /home/mfshaf7/projects --check-generated
```

The first command validates the schema and semantic separation rules. The unit
tests exercise positive and negative cases. The generated-view check proves
that the compact operator review view still matches the canonical contract.
