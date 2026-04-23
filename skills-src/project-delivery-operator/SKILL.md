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
- `operator-orchestration-service/docs/operations/delivery-workflow-operator-surface.md`
- `platform-engineering/products/openproject/runbooks/check-delivery-art-quality.md`
- `workspace-governance/docs/delegated-execution.md`
- `workspace-governance/docs/self-improvement-escalation.md`

## Workflow

1. Start from the ART, not from chat memory.
   - if the active `Epic` is already known, start with its fast active-front
     read and a scoped ART-quality check for that `Epic`
   - if the target work item is already known, use the broker work-item
     continuation read before scanning the full execution tree
   - use the deep execution read only when the full evidence-grade tree is
     actually needed
   - use the portfolio initiative summary only when the active `Epic` is not
     yet known or when PI/portfolio replanning is happening
   - identify the committed front, stretch work, PI objective state, and ART
     risk state before reading repo code
   - inside local `dev-integration`, default ART reads and writes to direct
     top-level `k3s kubectl` broker calls against the active profile namespace
   - use `GET /v1/delivery-work-items/{work_item_id}/continuation-context`
     as the default ART resume read for one known item
   - when the active item is not yet known, use
     `GET /v1/delivery-initiatives/{delivery_id}/planning` first to identify
     the active front, then fetch continuation context for the chosen item
   - when planning surfaces a `ready` `PI Objective`, `Feature`, `Enabler`, or
     other umbrella item as the candidate next front, do not present it as the
     next executable work from planning alone; fetch that item's
     `continuation-context` first
   - if that continuation packet shows `open_child_count=0` and the related
     completed scope already satisfies the item, treat it as a stale-open
     closeout candidate rather than the next active front
   - when the broker image does not carry `curl`, use the broker pod runtime
     itself with `node` and `fetch(...)` rather than falling back to another
     access path
   - source `x-oos-caller-id` from the first allowed id in
     `CALLER_ALLOWED_IDS`, and source `x-oos-caller-secret` from
     `CALLER_AUTH_SHARED_SECRET`
   - when the active implementation repo is `operator-orchestration-service`
     and the route already exists, use the documented broker contract first:
     `docs/api/openapi.json` or
     `npm run api:contract -- <METHOD> <PATH>`
   - when live broker truth matters for an existing documented route in
     `operator-orchestration-service`, use
     `npm run api:probe -- <METHOD> <PATH>` before falling back to handler
     tracing
   - treat `src/app.js` and service code as runtime-confirmation or drift
     sources after the contract read, not as the default first read for an
     existing broker route
   - do not default to Python wrappers, Rails paths, or ad hoc background
     localhost bridges when a direct broker call can do the job
   - use local parsing only after the broker response is captured; parsing is
     not the access path
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
- Do not reconstruct prior-done sibling context by manually scanning a giant
  execution-summary payload when the continuation-context read is available.
- Do not present a `ready` umbrella item as the next ART front from planning
  alone; confirm it still has open execution scope through its own
  continuation-context first.
- Do not treat repo code or contracts as the work queue; they are the
  implementation truth, not the planning truth.
- Do not turn broker access into a wrapper-first workflow; use direct
  `k3s kubectl` broker read and write calls by default in local delivery work.
- Do not guess broker caller auth headers during delivery work; reuse the
  broker pod's own allowed caller id and shared secret from environment.
- Do not leave stretch work looking committed just because it still exists in
  the same PI.
- Do not silently continue on active work whose narrative contract is too weak
  to operate safely.
- Do not continue active delivery work normally after a fail-closed
  self-improvement signal.
- Do not let delegated workers mutate the ART, live environments, security
  closure, or final proof surfaces.
