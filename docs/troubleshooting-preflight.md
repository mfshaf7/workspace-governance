# Troubleshooting Preflight

This is the primary operator surface for serious troubleshooting in the
workspace.

Use it when a failure is real but the root cause is not yet proven.

## Scope

Use this workflow for:

- live environment drift
- failing operator workflows
- broken delivery paths
- unexpected permission or identity failures
- backend behavior that does not match the contract
- adapter or runtime failures where the real fault location is still unclear

This workflow is not product-specific. It applies across owner repos.

## Order Of Operations

1. Frame the target operation first.
   - what should happen
   - what actually happened
   - which operator or system path is affected
   - which environment or lane is in scope
2. Run preflight before deeper debugging.
3. Prove live truth from the authoritative backend.
4. Prove contract truth.
5. Only then inspect code truth.
6. Do not expand into workaround or redesign analysis until those earlier
   layers are proven.

## Preflight

Check the simple prerequisites first:

- identity, membership, and permissions
- secrets, tokens, config, and feature flags
- environment shape, lane selection, mounted source state, and readiness
- endpoint reachability and health
- target object existence and current state

If one of these is already broken, stop there and correct the diagnosis before
moving deeper.

## Live Truth

Use the authoritative system to prove the current behavior directly:

- backend response
- actual status from the target system
- direct mutation or read behavior when supported
- minimal reproduction against the active lane or environment

Do not substitute documentation, memory, or assumed behavior for live truth.

## Contract Truth

After preflight and live truth are proven, check the declared interface:

- writable vs read-only fields
- allowed values and principal scope
- supported relation or mutation shape
- required headers, tokens, or approval boundaries
- explicit workflow rules and operator doctrine

If the contract already says the operation is not allowed, stop calling it an
adapter mystery.

## Code Truth

Inspect code only after the earlier layers are proven:

- broker or adapter mapping
- client behavior
- serialization or request-shape bugs
- retry and error handling
- workflow orchestration logic

Code inspection is the last proof layer, not the first reflex.

## Workaround Gate

Do not invent workarounds, redesigns, or alternate flows until:

- preflight is complete
- live truth is proven
- contract truth is checked

If those layers were skipped, the troubleshooting sequence is incomplete.

## Self-Improvement Route

If the eventual root cause turns out to be a simpler precondition that should
have been checked earlier, that is a workspace learning signal.

Typical examples:

- missing role or membership found only after adapter debugging
- dead endpoint found only after code-level investigation
- read-only contract discovered only after mutation redesign work
- wrong environment or source state discovered late

In those cases:

1. record or update an improvement candidate
2. classify it as a diagnostic-ordering miss when that fits
3. use trigger `late-root-cause-discovery`
4. close it only through durable control changes, not chat memory

Use the workspace skill:

- `self-improvement-review`

## Output

A good troubleshooting result should say:

- which layer failed first
- what evidence proved it
- which owner repo holds the durable fix
- whether a self-improvement record was required

If that cannot be stated clearly, the diagnosis is not finished yet.
