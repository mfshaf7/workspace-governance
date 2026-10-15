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

The contract also records one dated operating observation for every capability.
That observation is not inferred from feature presence: it names the exact
five-dimensional profile seen in the local `dev-integration` composition and
cites the source packet that captured the audit. A dependency may be reused
only when fresh authority evidence still resolves it as `operational-live`.
Missing or stale evidence makes it non-reusable; it does not inherit the last
successful claim.

## Plan Completeness

An idea-to-product plan is complete only when every ordered journey stage has:

- a canonical authority reference and workflow owner
- a Console read model and explicit operator intents
- lifecycle, failure, and recovery states
- positive, negative, and terminal proof obligations
- accepted activation work and current authority references

The required journey is idea and proposal, prototype incubation, Delivery ART
planning, architecture decision, repository custody, source realization,
exact-head human review, distinct Security acceptance, governed source merge,
Workspace Intake and Active Inventory, runtime and release, Product Portfolio,
and interruption recovery and audit.

Repository custody is explicit because a new-product journey cannot enter
source realization until the real repository, provider policy, dedicated
credential, reconciliation, revocation, and rollback path are operational. A
contract-only or uncommissioned adapter is therefore visible as
`implemented-uncommissioned`, not silently treated as reusable infrastructure.

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
