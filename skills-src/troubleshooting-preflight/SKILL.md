---
name: troubleshooting-preflight
description: Use when diagnosing a real failure or unexpected behavior and Codex must prove preconditions, live truth, contract truth, and code truth in the right order before workaround analysis.
---

# Troubleshooting Preflight

Use this skill when the root cause is still unproven.

## Read First

- `docs/troubleshooting-preflight.md`
- `docs/self-improvement-escalation.md`
- `contracts/failure-taxonomy.yaml`
- `contracts/improvement-triggers.yaml`
- `skills-src/self-improvement-review/SKILL.md`

## Workflow

1. Frame the target operation and the actual failure signal.
2. Prove preflight first:
   - identity, permissions, and membership
   - secrets, config, flags, readiness, and reachability
   - environment or lane selection
3. Prove live truth from the authoritative backend.
4. Prove named references before using them as facts:
   - deployment, pod, namespace, service, and route names
   - work item IDs, subjects, parent links, and owners
   - control names, validator names, workflow gate IDs, and root-cause labels
   - completion facts, branch names, PR numbers, and merge state
   - if a reference is not proven from the authoritative source for that
     layer, state that it is unverified instead of using it as fact
5. Prove contract truth:
   - writable fields
   - allowed values
   - supported mutation shape
   - operator doctrine
   - for OpenProject broker mutation changes, prove the live form schema and
     smallest faithful contract fixture before implementation or merge
6. Only then inspect code truth.
7. Do not expand into workaround or redesign analysis before those earlier
   layers are checked.
8. If the blocked next step requires operator-side credentials, package
   installation, sudo, a GUI action, approval, or account permission outside
   Codex's safe tool boundary:
   - stop at that layer and state the exact blocked step
   - prompt the operator immediately for the required action
   - do not silently substitute weaker CI-only proof, guesswork, or workaround
     evidence
   - if active ART work is affected, record the blocker, Defect, or Risk before
     adjacent mutation continues
9. If the root cause turns out to be a skipped simpler earlier-layer check:
   - treat it as a self-improvement signal
   - run `python3 scripts/check_self_improvement_escalation.py --signal late-root-cause-discovery ...`
   - if it fails closed, record or update the candidate before continuing
     normal troubleshooting

## Guardrails

- Do not start with code just because the symptom appears in code.
- Do not call backend or permission reality an adapter mystery before proving
  the live state.
- Do not turn a wrapper failure, memory, or inference into a named root-cause
  claim.
- Do not implement broker/OpenProject mutation changes before proving whether
  the target live form field is writable or read-only.
- Do not represent late discovery of a simpler precondition as normal bad luck.
- Do not continue workaround analysis once an earlier failed layer is proven.
- Do not downgrade an operator-side blocker into CI-only proof or a workaround
  without explicit operator acceptance recorded in the affected workflow.
