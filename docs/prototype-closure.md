# Prototype Closure

The [closure contract](../contracts/prototype-closure.yaml) defines the exit
boundary for a landed Prototype. Workspace Prototype Studio remains the source
authority until a durable owner has accepted the exact source. The Console is
an operator projection; OOS coordinates the workflow, WGCF evaluates readiness,
Platform owns runtime cleanup, and Security reviews the trust boundary.

## Operator Path

1. Confirm the Prototype's current lifecycle, source revision, accepted
   baseline, and desired exit action. A Delivery application is available only
   after baseline approval. Retirement is available for active incubation work.
2. For Delivery, apply the existing target workflow and inspect its accepted
   target receipt. This advances project phase to `delivery-governed`; it does
   **not** graduate Studio source.
3. To graduate source, identify a durable owner repo and prove either an
   accepted transfer of the exact Studio revision or that the source is already
   present under that owner. The new-repository route remains unavailable until
   Repository custody is actually active.
4. Review readiness and approve the exact action. OOS prepares a reviewable
   source change; Studio records the transition only after merged readback and
   the owner receipts agree. A denial preserves the prior state.
5. Inspect the terminal receipt and append-only history. Platform revokes only
   exact active incubation resources. Portfolio publication and governed
   release are separate later decisions.

Retirement ends the Prototype's local incubation, not an accepted Delivery
item or product. Reopen requires an explicit decision and the prior retirement
receipt; it returns to exploration without resurrecting a preview server or
erasing history. A graduated Prototype cannot be reopened into Studio custody
through this path.

The request, receipt, and history schemas live under
[`contracts/schemas/`](../contracts/schemas/). Source and target owners must
retain separate receipts so the project phase, source custody, runtime, release,
and publication axes remain independently auditable.
