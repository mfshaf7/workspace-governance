# Governed Intake Assist

This is the primary operator surface for AI-assisted workspace intake.

Local `dev-integration` consumption is active through the platform-owned
governed AI gateway and the reviewed `intake-classifier-v1` profile. The model
only produces a suggestion. An operator must separately accept or override it
before `contracts/intake-register.yaml` can change.

## Purpose

Governed intake assist may suggest that a new repo, product, or component is:

- `out-of-scope`
- `proposed`
- `admitted`

The active dev-integration binding is local Ollama `qwen3:8b`. Consumers remain
provider-neutral and request the logical profile, so the future paid OpenAI
binding can be activated without changing this workflow.

## Control Split

- `workspace-governance` owns the consumer, candidate and accepted-record
  schemas, intake register, controlled apply command, and validation.
- `platform-engineering` owns the gateway, provider binding, runtime integrity,
  network boundary, and audit ledger.
- `security-architecture` owns the binding review and activation findings.

The model cannot write canonical workspace truth, carry provider credentials,
or bypass the governed endpoint.

## Prerequisites

1. Start and verify the platform profile:

   ```bash
   cd /home/mfshaf7/projects/platform-engineering
   make devint-up PROFILE=governed-ai-gateway
   make devint-smoke PROFILE=governed-ai-gateway
   ```

2. Keep the loopback access process running in a separate terminal:

   ```bash
   make devint-access PROFILE=governed-ai-gateway
   ```

The workspace client defaults to `http://127.0.0.1:18290`. Plain HTTP is
rejected for any non-loopback endpoint.

## Request A Suggestion

Run from `workspace-governance`:

```bash
python3 scripts/governed_intake_assist.py \
  --notes "A shared component that validates workspace contract ownership." \
  --operator-id operator-login \
  --output .art/intake-assist/example-component.json
```

The command:

- validates the active workspace and platform contracts
- sends only operator-supplied notes to the governed gateway
- validates caller, profile, decision, and schema identity on the response
- stores the note digest rather than the note in the local candidate artifact
- confines candidate output to the ignored `.art/intake-assist/` directory
- preserves the gateway audit reference
- does not modify `contracts/intake-register.yaml`

Review the candidate before proceeding. To reject it, stop here; rejected
suggestions never enter workspace truth.

## Accept A Suggestion

The recorded `--status` and `--operator-decision` must agree. Acceptance must
also be explicit. Each gateway `decision_id` may be applied only once:

```bash
python3 scripts/scaffold_intake.py component \
  --name example-component \
  --status proposed \
  --decision-source ai-suggested \
  --component-class shared-platform \
  --owner-repo platform-engineering \
  --security-owner security-architecture \
  --notes "Operator accepted the governed intake suggestion." \
  --ai-suggestion-file .art/intake-assist/example-component.json \
  --operator-decision proposed \
  --acceptance-state accepted \
  --accepted-by operator-login \
  --accepted-at 2026-08-20T12:05:00Z
```

## Override A Suggestion

An override requires a different operator decision and a reason:

```bash
python3 scripts/scaffold_intake.py component \
  --name example-component \
  --status out-of-scope \
  --decision-source ai-suggested \
  --notes "Operator overrode the governed intake suggestion." \
  --ai-suggestion-file .art/intake-assist/example-component.json \
  --operator-decision out-of-scope \
  --acceptance-state overridden \
  --override-reason "The component is not intended to join this workspace." \
  --accepted-by operator-login \
  --accepted-at 2026-08-20T12:05:00Z
```

## Validate The Result

After an accepted or overridden decision changes workspace truth, run:

```bash
python3 scripts/validate_structured_record.py contracts/intake-register.yaml \
  --workspace-root /home/mfshaf7/projects
python3 scripts/validate_intake.py --workspace-root /home/mfshaf7/projects
```

## Failure And Rollback

- Gateway denial, timeout, malformed output, identity mismatch, or inactive
  contracts fail without changing workspace truth.
- If caller attribution, audit emission, provider isolation, or security posture
  regresses, set `activation_state.source_contract_status` to `suspended` and
  `activation_state.live_consumption_allowed` to `false`, stop using the
  client, preserve the audit reference, and suspend the platform profile
  through its owner workflow.
- Revert the workspace activation pull request to restore the source-defined
  disabled consumer path without changing provider runtime state.

## Denied Paths

- provider credentials in `workspace-governance`
- direct Ollama or external-provider clients
- model output written directly to canonical contracts
- manually fabricated profile, decision, or audit metadata
- replay of a gateway decision already applied to another intake entry
- unaccepted or rejected suggestions in `intake-register.yaml`
- stage or production claims from dev-integration evidence
