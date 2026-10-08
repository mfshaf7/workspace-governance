---
name: context-admission-operator
description: Use when command output, CI logs, ART packets, runtime diagnostics, repo context, or other operational context may be large or sensitive and should be captured, redacted, packetized, budgeted, or admitted through Context Governance Gateway instead of pasted raw.
---

# Context Admission Operator

Use this when operational context is large, sensitive, repetitive, or likely to
burn tokens if pasted raw.

## Read First

- `docs/context-admission-governance.md`
- `contracts/context-behavior.yaml`
- `contracts/raw-context-retirement.yaml`
- `context-governance-gateway/AGENTS.md`
- `context-governance-gateway/README.md`
- `workspace-root/AGENTS.md`

## Workflow

1. Classify the context source: terminal, CI, ART, runtime, repo, security, or
   operator packet.
2. Preserve full raw artifacts locally or in the approved custody path.
3. Project only model-safe/operator-safe packets into agent or operator
   context.
4. Redact secret-like values, private IPs, hostnames, tokens, env dumps, and
   uncertain sensitive material by default.
5. Prefer compact ART packet commands first for ART work; use CGG packet refs
   for oversized output or context that should not be raw-projected.
6. Keep WGCF, OOS, platform, and security authority boundaries intact. CGG
   governs context admission; it does not approve work or mutate authority
   stores.
7. Record packet refs, digests, receipts, and redaction decisions in evidence
   when the packet is used for completion or review.

## Process Environment Diagnostics

- Inspect environment variable names first and keep values suppressed. Do not
  use `env`, `printenv`, `/proc/<pid>/environ`, Kubernetes Secret data, or a
  credential file as raw diagnostic output.
- Never expand captured `NAME=value` entries into a command's arguments. A
  parser or command error can echo its argument list and disclose every value.
- When reproducing a child process, prefer a minimal allowlist. If exact
  environment inheritance is genuinely required, pass entries through the
  child process environment without printing them or converting them to argv,
  and keep command output behind the normal context-admission boundary.
- Treat any accidental environment-value output as credential exposure:
  stop the affected runtime path, rotate every exposed credential, reconcile
  the registered composition, and retain only secret-free evidence.

## Guardrails

- Do not paste raw terminal, CI, ART, Kubernetes, OpenProject, or security
  output into model context when packet parity exists or the material is
  sensitive.
- Do not use CGG as a custom LLM gateway, scanner, observability backend,
  object store, WGCF replacement, or ART mutation authority.
- Default uncertain sensitive material to denied raw model projection.
- Do not use argument-building forms such as `xargs ... env` on captured
  process environments; environment entries must never become argv.
- If CGG is unavailable, use the documented rollback path and record the
  limitation instead of pretending the context was governed.
