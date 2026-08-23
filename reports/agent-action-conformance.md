# Agent Action Conformance

This generated report proves the merged WGCF evaluator and OOS enforcer against the workspace-owned action contract.

## Result

- Outcome: `passed`
- Cases: `11/11` passed
- Positive cases: `4`
- Negative cases: `7`
- Runtime activation: `disabled`
- Authority contract: `sha256:8ed8aee6b03e42d02d5621e650d4488ee3a043e55b38cbd9e4018e4b9bf8d0c3`
- Conformance contract: `sha256:a7f5734c1036865dec69c18153fa3f56562aea140a989ed962dc813bea0a557c`

The owner mutation adapter is synthetic. This proof does not mutate a canonical backend or activate shared runtime behavior.

## Source Revisions

| Role | Repository | Revision | Manifest |
| --- | --- | --- | --- |
| `enforcer` | `operator-orchestration-service` | `61c037fdd5368863681f6582970bc7f976d40b22` | `sha256:5ae4d4abc6bfa51211f176dd06eeae5031eb704824c508291b6389da32e0f890` |
| `evaluator` | `workspace-governance-control-fabric` | `8b83ba7a2fc0dbbe52ed2892e1b190d2ce0e5de9` | `sha256:a82e94f8a5650eb7fdeacfa2096298fb43d3cca729e6132596de12ed428436d1` |

## Cases

| Case | Class | Action | Policy | Execution | Dispatch | Owner mutation | Terminal receipts | Result |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| `read-allow` | `positive` | `read` | `allow` | `succeeded` | 1 | 0 | 1 | `passed` |
| `read-caller-mismatch` | `negative` | `read` | `deny` | `denied` | 0 | 0 | 1 | `passed` |
| `advise-allow` | `positive` | `advise` | `allow` | `succeeded` | 1 | 0 | 1 | `passed` |
| `advise-context-mismatch` | `negative` | `advise` | `deny` | `denied` | 0 | 0 | 1 | `passed` |
| `draft-allow` | `positive` | `draft` | `allow` | `succeeded` | 1 | 0 | 1 | `passed` |
| `draft-source-version-mismatch` | `negative` | `draft` | `deny` | `denied` | 0 | 0 | 1 | `passed` |
| `mutate-allow` | `positive` | `mutate` | `allow` | `succeeded` | 1 | 1 | 1 | `passed` |
| `mutate-approval-mismatch` | `negative` | `mutate` | `deny` | `denied` | 0 | 0 | 1 | `passed` |
| `mutate-replay-consumed` | `negative` | `mutate` | `deny` | `denied` | 0 | 0 | 1 | `passed` |
| `mutate-receipt-store-failure` | `negative` | `mutate` | `allow` | `error` | 1 | 1 | 0 | `passed` |
| `mutate-audit-failure` | `negative` | `mutate` | `allow` | `error` | 1 | 1 | 1 | `passed` |

## Excluded Capabilities

- `console-agent-mutation`
- `shared-runtime-exposure`
- `stage-execution`
- `production-execution`
- `direct-model-provider-access`
- `canonical-backend-mutation`

## Receipt References

- `read-allow`: decision `wgcf://agent-actions/decisions/ce76a2263f606bb0e0cf04dd`; action `oos://agent-actions/receipts/6b491a3c38cf54b8b9ef13d7`
- `read-caller-mismatch`: decision `wgcf://agent-actions/decisions/4b81116c755973833681d87e`; action `oos://agent-actions/receipts/ecec0d17087a0a2671352727`
- `advise-allow`: decision `wgcf://agent-actions/decisions/9abb96e65f5a287f9cff6deb`; action `oos://agent-actions/receipts/ec3037dc4265b10a9f9ec132`
- `advise-context-mismatch`: decision `wgcf://agent-actions/decisions/392c3c512cdc1ccb26e39b5e`; action `oos://agent-actions/receipts/b0fadb7107a29f60de647ee2`
- `draft-allow`: decision `wgcf://agent-actions/decisions/7a3eb432b9441827857d63ea`; action `oos://agent-actions/receipts/e70fea0a7ca3675672ec770f`
- `draft-source-version-mismatch`: decision `wgcf://agent-actions/decisions/42c41a322671a079041a7ecc`; action `oos://agent-actions/receipts/75d9bef2d8c84f4d9b9a1533`
- `mutate-allow`: decision `wgcf://agent-actions/decisions/d4e8baecab2e7bf0bc050588`; action `oos://agent-actions/receipts/7b3e386201766c0ec0b48022`; owner `proof://owner-receipts/mutate-allow`
- `mutate-approval-mismatch`: decision `wgcf://agent-actions/decisions/88b9692529e69b25445baea7`; action `oos://agent-actions/receipts/b5e1d269b784455975a041ae`
- `mutate-replay-consumed`: decision `wgcf://agent-actions/decisions/2c30ce1b307608cba75d677c`; action `oos://agent-actions/receipts/49e7e902c3003282203b7395`
- `mutate-receipt-store-failure`: decision `wgcf://agent-actions/decisions/3637e232eeb017cdfc255a20`
- `mutate-audit-failure`: decision `wgcf://agent-actions/decisions/81bb35146562ee9b2f8acbca`; action `oos://agent-actions/receipts/34012241c3de98d713c38bb2`
