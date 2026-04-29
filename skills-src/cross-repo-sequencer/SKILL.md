---
name: cross-repo-sequencer
description: Use when one repo's validator, contract, or operator surface depends on changes landing in another repo first so the merge and validation order is handled deliberately.
---

# Cross-Repo Sequencer

Use this skill when a change spans multiple repos and one repo's validation or
doctrine depends on another repo being merged first.

## Read First

- `contracts/repos.yaml`
- `contracts/repo-rules/`
- the relevant owner repo `AGENTS.md` files

## Workflow

1. Identify the primary owner repo and every dependency repo whose `main`
   branch must move first.
2. Separate:
   - owner alignments
   - control-plane changes
   - shared audits that read remote `main`
3. Merge dependency repos first when a later repo's CI or validation reads
   those repos from remote `main`.
4. When an owner-repo change record declares `security_evidence`, treat the
   generated `security-architecture/registers/security-change-record-index.yaml`
   update as a required dependency landing unit. Run the structured-record
   preflight for the change record and merge the security-architecture update
   before claiming workspace audit or closure is clean.
5. If a dependent PR already failed for sequencing reasons, retrigger it only
   after the dependency repos are actually merged.
6. State the merge order explicitly in the user-facing progress updates and the
   final close-out.

## Guardrails

- Do not assume multi-repo PRs can merge in arbitrary order.
- Do not treat a no-op rerun commit as a real fix when the real issue was merge
  sequencing.
- Do not hide dependency ordering in chat memory only; make it explicit while
  the work is in flight.
- Do not treat a security-evidenced owner-repo record as complete while the
  security-architecture generated change-record index is stale or unmerged.
