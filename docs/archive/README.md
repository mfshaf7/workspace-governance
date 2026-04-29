# Archive

This directory holds workspace-governance historical notes that are useful for
continuity and audit but are not active operator guidance.

Use this for:

- historical implementation notes
- contextual records that should survive chat resets

## Session Handoff Lifecycle

Session handoffs are local-only restart continuity state, not durable archive
records.

Rules:

- use only `session-handoff-current.md`
- keep zero or one handoff at a time
- remove the current handoff when it is no longer accurate or needed
- do not commit session handoffs
- do not create dated `session-handoff-YYYY-MM-DD.md` files

Do not treat files here as the primary operator procedure or governance truth.
Those still belong in:

- `README.md`
- `AGENTS.md`
- `contracts/`
- `reviews/`
- `workspace-root/`
