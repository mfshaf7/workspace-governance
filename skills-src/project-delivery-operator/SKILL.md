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
   - when planning surfaces a `ready` `PI Objective`, `Feature`, or another
     umbrella item such as a `Feature` or `User story` classified as
     `Enabler`, do not present it as the next executable work from planning
     alone; fetch that item's
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
   - before `create` or `update` sets `assignee_login` or
     `responsible_login`, read the live assignable-principal list first from
     the active devint broker pod:
     `k3s kubectl -n <active-devint-namespace> exec deploy/operator-orchestration-service -- node scripts/show_delivery_art_assignables.mjs`
   - choose the exact login from that list; do not infer assignee or
     responsible from repo names, board labels, or Rails-admin pages
   - when the active implementation repo is `operator-orchestration-service`
     and the route already exists, use the documented broker contract first:
     `docs/api/openapi.json` or
     `npm run api:contract -- <METHOD> <PATH>`
   - before `POST /v1/delivery-work-items/{work_item_id}/complete`, run the
     local completion-evidence preflight in
     `operator-orchestration-service`:
     `npm run validate:completion-evidence -- <payload.json>`
   - do not let the live broker completion write be the first place malformed
     completion evidence fails
   - completion-evidence preflight is necessary but not sufficient for done
     work; the broker now also fail-closes on weak done-state narrative
     structure
   - before `complete`, and before `update` when the work item will remain
     `done`, confirm the description still keeps the required narrative
     headings for that type and a flat `Execution Context` that matches the
     stored owner repo, parent item, delivery team, and iteration values when
     those fields apply
   - use execution-summary `done_narrative_contract_*` fields as the fast read
     model for done-state narrative drift instead of rediscovering it from raw
     OpenProject markdown
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
   - if the operator asks for a broad stage/prod rehearsal, temporary prod
     activation, or restore-to-baseline exercise, classify the scope as a
     governed drill before assuming product scope:
     - `product-runtime-drill` for one governed product lane
     - `active-stack-runtime-drill` for multi-product or shared-component
       mixed-lane bring-up plus restore
     - `environment-complete-runtime-drill` only when every admitted lane and
       product environment in scope is actually exercised
     - `lifecycle-control-drill` for lifecycle-state exercises without full
       runtime bring-up
   - route broad runtime drills through the shared platform workflow in
     `platform-engineering/docs/runbooks/active-stack-runtime-drill.md`
     instead of defaulting to the most mature product-only path
   - do not treat a broad platform rehearsal as OpenClaw-only just because
     OpenClaw already has the most mature governed promotion path
   - before creating a new item, choose the smallest ART structure that still
     preserves real owner, review, and validation boundaries
   - one task is only acceptable when the work is genuinely one execution slice
     with one primary owner path and one materially shared done boundary
   - if the work changes a shared control plane, introduces a new operator
     workflow, or spans multiple repos with distinct deliverables, do not
     compress it into one task
   - represent that class of work as a parent `Feature` plus
     child tasks for the concrete owner slices such as:
     - workflow model or design decision
     - platform or source implementation
     - security review
     - governance closure or skill/routing updates
   - when the slice is enabling or runway-focused, express that through the
     real machine metadata:
     - structural delivery types are:
       `Epic`, `PI Objective`, `Feature`, `User story`, `Defect`, `Task`,
       `Milestone`, and `Risk`
     - use structural `Feature` or `User story`
     - set `Execution Classification = Enabler`
     - use structural `Defect` for true defect work instead of title-only
       tagging it as a `Task`
     - let visible subject prefixes be derived from machine metadata:
       `Risk:` from type `Risk`, `Defect:` from type `Defect`,
       `Enabler:` or `Improvement:` from `Execution Classification`
     - do not invent a structural `Enabler` type or rely on title-only prefixes
   - if a stopgap placeholder item was created just to avoid leaving the work
     untracked, replace or retire it before normal implementation continues
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
   - when new accepted work enters ART, do not skip straight to deep execution
     structure
   - the default planning path is:
     1. consume into one `Epic` shell
     2. frame the initiative while it stays backlog-shaped
     3. create PI objectives and committed features during PI planning
     4. elaborate user stories only for committed features
     5. create tasks only under active user stories or defects
     6. review carryover and decommit work deliberately at PI boundaries
   - treat backlog as mostly `Epic` + `Feature`
   - do not create `User story` or `Task` forests before PI commitment
   - `PI Objective`, `User story`, `Task`, and `Milestone` work must carry
     `Target PI`
   - PI-committed non-`Epic` work must also carry non-backlog `Iteration`
   - backlog `Feature` work may exist without `Target PI`, but it must stay
     umbrella-shaped until commitment
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
- Do not hide a cross-repo control-plane or workflow change inside one coarse
  ART task when the real work has distinct owner, review, or validation slices.
- Do not leave a temporary placeholder item as the lasting execution model once
  the proper parent-plus-children structure is clear.
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
- Do not guess ART assignee or responsible values; read the live assignable
  principal list first and use the exact login it returns.
- Do not leave stretch work looking committed just because it still exists in
  the same PI.
- Do not silently continue on active work whose narrative contract is too weak
  to operate safely.
- Do not continue active delivery work normally after a fail-closed
  self-improvement signal.
- Do not let delegated workers mutate the ART, live environments, security
  closure, or final proof surfaces.
- Do not assume valid completion-evidence bullets mean the done record is
  acceptable; the done-state narrative contract is a separate hard gate now.
