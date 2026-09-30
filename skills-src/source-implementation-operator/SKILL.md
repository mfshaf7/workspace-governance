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

4. Run working-tree validators before committing. Commit under the prepared
   Agent Gary identity, then run every base-aware validator that compares
   `<base-ref>...HEAD`. A `HEAD`-based validator run before the commit does not
   prove the pending working-tree change.
5. After the committed local CI-equivalent validation passes, run the same
   command with `publish`. It resolves the protected hashed credential slot,
   verifies exact provider scope and commit identity, pushes without force,
   opens or reuses the Agent Gary PR, and requests human review.
6. Verify the PR author is `app/mfshaf7-agent-gary` before using the delegated
   human identity for approval and merge.
7. Use the exact review, merge, credential-revocation, and cleanup commands in
   the next section after required checks pass.

Do not manually locate credential files, run `git push`, or invoke `gh pr
create` as a fallback. If the bounded command fails, diagnose that workflow
instead of bypassing it.

## Review, Merge, And Cleanup

Use the delegated human identity only after proving the PR author, exact head,
required checks, and review state:

```bash
gh pr review <pr-number> --repo mfshaf7/<owner-repo> \
  --approve --body "<validation summary>"
gh pr checks <pr-number> --repo mfshaf7/<owner-repo> --watch --interval 5
```

For the current single-human-reviewer repositories whose rulesets allow the
accountable reviewer to bypass after approval, use the known merge command
directly. Do not first try a normal merge and do not fall back to unsupported
auto-merge:

```bash
gh pr merge <pr-number> --repo mfshaf7/<owner-repo> \
  --squash --delete-branch --admin
```

After proving the PR is merged, revoke the exact Landing Unit credential:

```bash
make -C /home/mfshaf7/projects/platform-engineering agent-source-identity \
  ACTION=revoke \
  ARGS="--landing-unit-id <landing-unit-id> \
    --repository mfshaf7/<owner-repo> \
    --receipt <operator-private-revocation-receipt-path> \
    --workspace-repo-inventory /home/mfshaf7/projects/workspace-governance/contracts/repos.yaml"
```

Then return the owner repo to current `main`, retire the local branch, prune
deleted remote refs, and run the exact strict audit:

```bash
git -C <owner-repo-root> switch main
git -C <owner-repo-root> pull --ff-only origin main
git -C <owner-repo-root> branch -d <branch>
git -C <owner-repo-root> fetch --prune origin
python3 /home/mfshaf7/projects/workspace-governance/scripts/audit_branch_lifecycle.py \
  --workspace-root /home/mfshaf7/projects \
  --repo-root <owner-repo-root> \
  --include-remote \
  --check-clean
```

Do not use command-help discovery for these normal-path steps. If one of these
exact commands stops matching the implementation, repair this skill in the same
work rather than relying on session memory.

## Completion

Apply the `done-criteria-enforcer` cleanup and evidence checks before reporting
the Landing Unit complete.
