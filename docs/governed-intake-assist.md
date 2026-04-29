# Governed Intake Assist

This is the primary operator surface for AI-assisted workspace intake.

The current state is source-defined only. Do not record `decision_source:
ai-suggested` in `contracts/intake-register.yaml` until the platform profile is
active and the governed access-plane activation gates are proven.

## Purpose

Governed intake assist may help classify a new repo, product, or component as:

- `out-of-scope`
- `proposed`
- `admitted`

The model is never the authority. It produces a bounded suggestion through the
platform-owned governed AI access plane. The operator remains the decision
authority and must explicitly accept or override the suggestion before workspace
truth changes.

## Control Split

- `workspace-governance` owns the consumer contract, output schema, intake
  register, scaffold command, and validation.
- `platform-engineering` owns the model profile registry, governed access
  plane, provider credential custody, and activation gates.
- `security-architecture` owns the security review and findings that approve or
  block live activation.

The workspace consumer contract is:

- `contracts/governed-intake-assist.yaml`

The platform contracts it consumes are:

- `platform-engineering/security/governed-ai-model-profiles.yaml`
- `platform-engineering/security/governed-ai-access-plane.yaml`
- `platform-engineering/security/governed-ai-runtime-assist-contract.yaml`

## Current Allowed Path

Use operator-only intake today:

```bash
python3 scripts/scaffold_intake.py component \
  --name example-component \
  --status proposed \
  --decision-source operator \
  --component-class shared-platform \
  --owner-repo platform-engineering \
  --security-owner security-architecture \
  --notes "Operator-classified intake entry."
python3 scripts/validate_intake.py --workspace-root /home/mfshaf7/projects
```

## Future AI-Suggested Path

Only after live activation gates are proven, the AI-assisted flow is:

1. Invoke the platform governed access plane as caller
   `workspace-governance/intake-assist`.
2. Require profile `intake-classifier-v1`, purpose `workspace-intake-assist`,
   and output schema `contracts/schemas/intake-ai-suggestion.schema.json`.
3. Review the suggestion as an operator.
4. Record the final intake decision only after acceptance or override.
5. Validate the intake model before merging the workspace truth update.

Example accepted suggestion shape:

```bash
python3 scripts/scaffold_intake.py component \
  --name example-component \
  --status proposed \
  --decision-source ai-suggested \
  --component-class shared-platform \
  --owner-repo platform-engineering \
  --security-owner security-architecture \
  --notes "Operator accepted governed AI intake suggestion." \
  --ai-profile-id intake-classifier-v1 \
  --ai-policy-status active \
  --ai-decision-id intake-example-20260429 \
  --ai-generated-at 2026-04-29T00:00:00Z \
  --ai-confidence medium \
  --ai-suggested-decision proposed \
  --accepted-by operator-login \
  --accepted-at 2026-04-29T00:05:00Z
python3 scripts/validate_intake.py --workspace-root /home/mfshaf7/projects
```

Example operator override:

```bash
python3 scripts/scaffold_intake.py component \
  --name example-component \
  --status out-of-scope \
  --decision-source ai-suggested \
  --notes "Operator overrode governed AI intake suggestion." \
  --ai-profile-id intake-classifier-v1 \
  --ai-policy-status active \
  --ai-decision-id intake-example-override-20260429 \
  --ai-generated-at 2026-04-29T00:00:00Z \
  --ai-confidence low \
  --ai-suggested-decision proposed \
  --operator-decision out-of-scope \
  --acceptance-state overridden \
  --override-reason "The entrant is not intended to join this workspace." \
  --accepted-by operator-login \
  --accepted-at 2026-04-29T00:05:00Z
python3 scripts/validate_intake.py --workspace-root /home/mfshaf7/projects
```

## Denied Paths

- Do not put provider credentials in `workspace-governance`.
- Do not call a provider directly from the intake workflow.
- Do not let model output mutate canonical contracts directly.
- Do not write rejected suggestions into `intake-register.yaml`; rejected
  suggestions stay in the future audit trail, not workspace truth.
- Do not record `ai-suggested` entries while
  `contracts/governed-intake-assist.yaml` has
  `activation_state.live_consumption_allowed: false`.

## Validation

Run these after changing the contract, schema, scaffold command, or intake
register:

```bash
python3 scripts/validate_structured_record.py contracts/governed-intake-assist.yaml --workspace-root /home/mfshaf7/projects
python3 scripts/validate_structured_record.py contracts/intake-policy.yaml --workspace-root /home/mfshaf7/projects
python3 scripts/validate_contracts.py --repo-root .
python3 scripts/validate_intake.py --workspace-root /home/mfshaf7/projects
```
