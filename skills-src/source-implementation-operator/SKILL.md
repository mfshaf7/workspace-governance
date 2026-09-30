---
name: source-implementation-operator
description: Use whenever a git-tracked workspace change will be committed, pushed, opened for review, merged, or cleaned up so Agent Gary authors implementation while the human identity remains reviewer and merger across ART and owner-repo maintenance paths.
---

# Source Implementation Operator

Use this skill before the first source mutation that is intended to land.

## Route First

- For accepted ART work, use the OOS `work start`, `work continue`, `work
  merge`, and `work close` path. Do not reproduce its source actions manually.
- For owner-repo maintenance outside accepted ART scope, keep the normal
  owner-repo tracking decision and use the OOS maintenance source command. Do
  not invent an ART item only to obtain source identity.

## Identity Boundary

- Agent Gary is the source author, committer, branch pusher, and pull-request
  opener.
- `mfshaf7` is the delegated accountable reviewer, approver, and merger.
- Never use ambient human GitHub credentials for implementation publication.
- Never use Agent Gary credentials for approval, merge, branch deletion,
  repository administration, or installation-scope changes.

## Owner-Repo Maintenance Path

1. Prove the owner repo, exact branch, fetched `origin/main` commit, Landing
   Unit id, and tracking reference.
2. Use Platform's `agent-source-identity deliver` target. Its default Vault
   address is the cataloged persistent operator endpoint
   `http://127.0.0.1:32200`. Use the documented `vault-ui` port-forward at
   `http://127.0.0.1:8220` only after proving the primary endpoint is
   unavailable from the current WSL network mode. Do not improvise another
   address or start the fallback for normal operation.

   ```bash
   make -C /home/mfshaf7/projects/platform-engineering agent-source-identity \
     ACTION=deliver \
     ARGS="--landing-unit-id <landing-unit-id> \
       --repository mfshaf7/<owner-repo> \
       --branch <branch> \
       --fetched-base <fetched-origin-main-commit> \
       --human-reviewer-id mfshaf7 \
       --receipt <operator-private-receipt-path> \
       --workspace-repo-inventory /home/mfshaf7/projects/workspace-governance/contracts/repos.yaml"
   ```

   When the primary endpoint is unavailable, establish the fallback first and
   explicitly override `AGENT_SOURCE_VAULT_ADDR` for that invocation:

   ```bash
   k3s kubectl -n vault port-forward svc/vault-ui 8220:8200

   AGENT_SOURCE_VAULT_ADDR=http://127.0.0.1:8220 \
     make -C /home/mfshaf7/projects/platform-engineering agent-source-identity \
       ACTION=deliver \
       ARGS="<same bounded arguments>"
   ```
3. Before committing, run:

   ```bash
   npm --prefix /home/mfshaf7/projects/operator-orchestration-service run source -- \
     maintenance prepare \
     --repo-root <owner-repo-root> \
     --landing-unit-id <landing-unit-id> \
     --base-commit <fetched-origin-main-commit> \
     --tracking-ref <owner-record-or-candidate-ref>
   ```

4. After committing and local CI-equivalent validation, run the same command
   with `publish`. It resolves the protected hashed credential slot, verifies
   exact provider scope and commit identity, pushes without force, opens or
   reuses the Agent Gary PR, and requests human review.
5. Verify the PR author is `app/mfshaf7-agent-gary` before using the delegated
   human identity for approval and merge.
6. Revoke the Landing Unit credential and complete exact owner-repo branch and
   worktree cleanup after merge.

Do not manually locate credential files, run `git push`, or invoke `gh pr
create` as a fallback. If the bounded command fails, diagnose that workflow
instead of bypassing it.

## Completion

Apply the `done-criteria-enforcer` cleanup and evidence checks before reporting
the Landing Unit complete.
