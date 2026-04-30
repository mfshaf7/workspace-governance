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

## Named-Reference Proof

Treat specific names and references as claims that need proof before they are
used as facts.

This includes:

- deployment, pod, namespace, service, and route names
- work item IDs, subjects, parent links, and owner fields
- control names, validator names, and workflow gate IDs
- root-cause labels and completion facts

Use the authoritative source for the layer:

- live runtime APIs for deployed object names and state
- broker continuation context or planning reads for ART item truth
- owner-repo contracts and docs for workflow or control names
- local git status and PR metadata for source and merge state

If the reference has not been proven yet, say it is unverified. Do not turn a
wrapper failure, memory, or inference into a named root cause.

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

## Operator-Side Blockers

Some failures are not technical mysteries. They require an operator action
outside Codex's safe tool boundary.

Examples:

- host package installation
- sudo authentication
- credential, token, or account permission changes
- GUI or browser action
- approval that only the operator can grant

When that is the blocked next step, stop there. State the exact blocked step,
ask the operator for the required action immediately, and do not silently
replace the missing proof with weaker CI-only evidence, guesswork, or a
workaround. If the blocked step affects active ART work, record the blocker,
Defect, or Risk through the bounded ART path before adjacent mutation
continues.

## Self-Improvement Route

If the eventual root cause turns out to be a simpler precondition that should
have been checked earlier, that is a workspace learning signal.

Typical examples:

- missing role or membership found only after adapter debugging
- dead endpoint found only after code-level investigation
- read-only contract discovered only after mutation redesign work
- wrong environment or source state discovered late

In those cases:

1. run `scripts/check_self_improvement_escalation.py --signal late-root-cause-discovery`
2. if it fails closed, record or update the improvement candidate before
   continuing normal troubleshooting
3. classify it as a diagnostic-ordering miss when that fits
4. close it only through durable control changes, not chat memory

Primary operator surface:

- `docs/self-improvement-escalation.md`

## Output

A good troubleshooting result should say:

- which layer failed first
- what evidence proved it
- which owner repo holds the durable fix
- whether a self-improvement record was required

If that cannot be stated clearly, the diagnosis is not finished yet.
