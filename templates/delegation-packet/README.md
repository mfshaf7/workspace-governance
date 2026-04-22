# Delegation Packet Template

Use this template when the main agent is preparing a bounded delegated write.

The packet is the durable execution contract for a delegated worker. It should
be created before the worker starts, then copied into the delegation-journal
record once the run is active.

Required fields are governed by
[contracts/delegation-policy.yaml](../../contracts/delegation-policy.yaml).
