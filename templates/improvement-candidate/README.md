# Improvement Candidate Template

Use this template when a likely repeated miss or late discovery has been
recognized, but the workspace is not yet ready to write a full after-action
record.

This is the fast triage layer for the self-improvement system.

Use it when:

- the user explicitly says something is a repeated mistake
- the same workflow needs a corrective follow-up in the same session
- a machine-visible audit flags a doctrine or completion miss

Use a full after-action instead when:

- the lesson and control shape are already clear
- the failure class is important enough that direct closure is justified now

Required candidate information:

- candidate id
- owner repo
- status
- source type
- one or more concrete signals
- trigger
- one or more failure classes
- follow-up owner and due date while the candidate is still open

Close a candidate only when it links either:

- a real after-action review, or
- direct durable controls that resolved the signal cleanly
