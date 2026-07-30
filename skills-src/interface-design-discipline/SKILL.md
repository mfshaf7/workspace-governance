---
name: interface-design-discipline
description: Use when designing or changing UI/UX for operator consoles, dashboards, product prototypes, client apps, workflow surfaces, modals, tables, forms, visual baselines, or reusable interface patterns.
---

# Interface Design Discipline

Use this skill when work affects what a human sees, clicks, scans, edits,
approves, or reviews in a visual interface.

This skill governs the design method. It does not impose one visual style.
Each project owns its own design profile, pattern inventory, and baseline.

## Pair With

- `operator-workflow-design` when the UI changes workflow meaning, approvals,
  lifecycle, status visibility, or operator action paths.
- `security-governance-review` when the UI exposes identity, secrets, real
  data, client data, AI-assisted actions, or mutable system operations.
- `context-admission-operator` when the UI shows large logs, command output,
  traces, model context, or operational evidence that may need redaction or
  budgeted projection.

## Required Pre-Edit Discipline

Before editing UI source:

1. Identify the project design profile or state that none exists yet.
2. Identify the user job for the surface being changed.
3. Identify the source of truth for the data shown in the surface.
4. Inspect the closest existing pattern before inventing a new one.
5. Decide whether the work is exploration, baseline hardening, or post-baseline
   maintenance.
6. Change one coherent surface at a time unless the operator explicitly asks
   for a broader redesign.

If there is no design profile, create or update one before treating the UI as
baseline-ready.

## Project Design Profile

Each UI project should define, at minimum:

- audience and operating context
- visual direction and personality
- typography direction
- color and status semantics
- density and spacing rules
- responsive policy
- accessibility expectations
- primary components and reusable patterns
- data modes and source-of-truth assumptions
- baseline states that must be reviewed

Keep project profiles local to the product or prototype. Do not force unrelated
projects to inherit the same aesthetic.

## Pattern-First Editing

Reuse before inventing. For repeated interface elements, locate or define the
named pattern first:

- panel
- tray
- status card
- connected card or tab
- registry table
- detail panel
- modal
- guard or confirmation dialog
- workflow draft surface
- action button
- status pill
- resource or telemetry graph
- agent or assistant console

If an existing pattern is inadequate, extend the pattern deliberately instead
of creating a visually similar one-off.

## State And Interaction Checks

For every changed surface, consider whether it needs:

- empty, loading, ready, warning, blocked, error, offline, and stale states
- selected and unselected behavior
- hover, focus, disabled, and active behavior
- guard behavior for unsaved or unsafe transitions
- compact and expanded views
- source, receipt, or evidence visibility
- keyboard and screen-reader affordance when the surface is not purely visual

Do not reuse the same color or badge semantics for materially different states.

## Fast Iteration Rules

During exploration:

- keep iteration local and fast
- do not promote every visual tweak through heavyweight delivery flow
- avoid premature PRs that make an unsettled design look official
- preserve a rollback point before broad refactors
- use mock or synthetic data unless the project profile allows otherwise

During baseline hardening:

- consolidate one-off CSS into named patterns
- remove filler content that would not appear in the live product
- verify the target viewport policy
- verify key states, modals, tables, and guard flows
- run the project's focused type/lint/check command

After baseline:

- protect the baseline with regression checks appropriate to the project
- prefer screenshot or component-state checks for high-risk visual surfaces
- require explicit design-profile updates for deliberate visual direction
  changes

## Guardrails

- Do not treat a UI as complete because it compiles.
- Do not let filler text, marketing-style mock panels, or disconnected buttons
  stand in for real operator behavior.
- Do not redesign a shared pattern in one place without checking its other
  usages.
- Do not let status, lifecycle, approval, or blocker meaning live only in color.
- Do not hide the source of truth for important operational data.
- Do not collapse desktop, tablet, and mobile into one layout if the project
  has not designed each viewport class.
- Do not call a design baseline approved from chat memory alone; record it in
  the owning project surface.
