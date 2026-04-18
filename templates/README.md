# Templates

These templates are scaffolds for new governance objects.

Use `templates/intake/` first when a repo, product, or component is new enough
that the workspace still needs to decide whether it is out-of-scope or should
enter the governed control plane.

Use `templates/dev-integration-profile/` when an owner repo needs a reusable
fast-iteration profile for the shared local-k3s `dev-integration` lane.

Use `templates/dev-integration-request/` when a team needs to request a new
profile before it becomes an `active` self-serve option.

Use `templates/improvement-candidate/` when the system has a real signal for a
repeated miss or late discovery, but the durable control shape is not ready for
a full after-action review yet.

They are not source of truth and must not become an alternate policy layer.
