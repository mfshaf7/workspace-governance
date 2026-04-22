---
name: project-delivery-operator
description: Use when work is being delivered through the OpenProject ART and Codex must treat the ART as the primary work-state source, classify uncovered work correctly, and keep PI, stretch, and completion-evidence discipline intact.
---

# Project Delivery Operator

Use this skill when a serious initiative is already running inside
`Workspace Delivery ART`.

## Read First

- `platform-engineering/products/openproject/AGENTS.md`
- `platform-engineering/products/openproject/README.md`
- `platform-engineering/products/openproject/delivery-art-contract.md`
- `platform-engineering/products/openproject/runbooks/show-delivery-initiatives.md`
- `platform-engineering/products/openproject/runbooks/show-delivery-execution.md`
- `platform-engineering/products/openproject/runbooks/check-delivery-art-quality.md`
- `workspace-governance/docs/delegated-execution.md`
- `workspace-governance/docs/self-improvement-escalation.md`

## Workflow

1. Start from the ART, not from chat memory.
   - if the active `Epic` is already known, start with its fast active-front
     read and a scoped ART-quality check for that `Epic`
   - use the deep execution read only when the full evidence-grade tree is
     actually needed
   - use the portfolio initiative summary only when the active `Epic` is not
     yet known or when PI/portfolio replanning is happening
   - identify the committed front, stretch work, PI objective state, and ART
     risk state before reading repo code
2. Keep the truth split explicit:
   - ART = work-state truth
   - owner repos = implementation and design truth
   - `workspace-governance` = workspace-control truth
3. If the request is not already covered by the active ART, classify it before
   doing the work:
   - tiny same-slice patch: absorb it into the active work item
   - meaningful work in the same initiative: add a new item under the active
     `Epic`
   - different business outcome: route it through `Workspace Proposals`
   - repeated process or control miss: record or update an improvement
     candidate
   - security or trust-boundary judgment: route it through
     `security-architecture` and reflect any blocking impact back in the ART
   - pure owner-repo maintenance outside the initiative: track it in the owner
     repo only
4. Keep PI honesty explicit.
   - do not leave work marked committed when it is really stretch or deferred
   - replan the PI when the active front changes materially
5. Update the ART when work-state changes:
   - status
   - blocker or risk state
   - PI commitment
   - completion evidence
6. Close work only through the supported evidence-backed completion path.
7. Raise active-slice narrative weakness explicitly.
   - if the ART-quality check reports `rewrite-required` or
     `discussion-required` findings on active or next-up work, bring that to
     the operator before continuing that item
   - propose the rewrite shape clearly instead of silently working around weak
     content
8. If active work becomes half-finished or the operator explicitly calls out a
   repeated mistake, half-baked state, or missed catch:
   - run `python3 /home/mfshaf7/projects/workspace-governance/scripts/check_self_improvement_escalation.py ...`
   - record the candidate before continuing normal execution when the signal is
     in the fail-closed set
9. When using delegated execution for ART-backed work:
   - keep ART mutation, live proof, security closure, and final completion
     with the main agent
   - create a bounded packet before spawn
   - keep delegated write scopes disjoint
   - record the delegated run in the delegation journal when delegated write is
     used
   - classify any newly discovered scope through the ART before treating it as
     accepted work

## Guardrails

- Do not let meaningful uncovered work live only in chat.
- Do not reconstruct the work queue from handoff prose when the ART already
  exists.
- Do not treat repo code or contracts as the work queue; they are the
  implementation truth, not the planning truth.
- Do not leave stretch work looking committed just because it still exists in
  the same PI.
- Do not silently continue on active work whose narrative contract is too weak
  to operate safely.
- Do not continue active delivery work normally after a fail-closed
  self-improvement signal.
- Do not let delegated workers mutate the ART, live environments, security
  closure, or final proof surfaces.
