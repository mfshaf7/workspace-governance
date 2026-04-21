---
name: troubleshooting-preflight
description: Use when diagnosing a real failure or unexpected behavior and Codex must prove preconditions, live truth, contract truth, and code truth in the right order before workaround analysis.
---

# Troubleshooting Preflight

Use this skill when the root cause is still unproven.

## Read First

- `docs/troubleshooting-preflight.md`
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
4. Prove contract truth:
   - writable fields
   - allowed values
   - supported mutation shape
   - operator doctrine
5. Only then inspect code truth.
6. Do not expand into workaround or redesign analysis before those earlier
   layers are checked.
7. If the root cause turns out to be a skipped simpler earlier-layer check:
   - treat it as a self-improvement signal
   - use trigger `late-root-cause-discovery`
   - record or update an improvement candidate

## Guardrails

- Do not start with code just because the symptom appears in code.
- Do not call backend or permission reality an adapter mystery before proving
  the live state.
- Do not represent late discovery of a simpler precondition as normal bad luck.
- Do not continue workaround analysis once an earlier failed layer is proven.
