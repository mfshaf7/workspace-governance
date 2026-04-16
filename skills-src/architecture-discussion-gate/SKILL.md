---
name: architecture-discussion-gate
description: Use when a request introduces a new product, shared component, ingress or service-mesh layer, identity/secrets/observability subsystem, or other architecture-shaping feature that requires framing before implementation.
---

# Architecture Discussion Gate

Use this skill before implementation when the request could change the long-term
platform shape.

## Read First

- `contracts/task-types.yaml`
- `contracts/products.yaml`
- `contracts/components.yaml`
- `contracts/review-obligations.yaml`
- `workspace-root/AGENTS.md`

## Trigger Conditions

Stop and discuss first when the request introduces:

- a new product
- a new shared component or control plane
- a new ingress, gateway, service-mesh, or network authority layer
- a new identity, secret-delivery, storage, messaging, or observability subsystem
- a new privileged host-control capability
- any feature with multiple plausible long-term architectures

## Discussion Outputs

Make these explicit before implementation:

- target role in the platform
- owner repo and control plane
- trust-boundary impact
- workflow maturity after the change
- operator surface and visibility model
- rollout and rollback shape

Do not begin implementation until those are narrowed enough to choose the owner.
