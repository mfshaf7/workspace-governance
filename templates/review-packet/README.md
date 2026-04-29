# Review Packet Template

Use this template when one landed or explicitly accepted evidence packet covers
one or more ART items.

A Review Packet is not a new system of record. It is the evidence bridge
between:

- ART items for work-state truth
- Landing Units for source review, merge, deployment, and rollback truth
- live or non-source evidence when no source landing exists

Copy `TEMPLATE.md` into the owning repo or ART evidence location that the
current work uses. Keep the packet close to the source PR, release evidence, or
completion evidence it supports.

Use one packet for several ART children when they share the same review and
rollback boundary. Split packets when repo ownership, validation, security
posture, deployment timing, or rollback scope differs.
