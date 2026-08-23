#!/usr/bin/env node

import { readFile } from "node:fs/promises";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";


function reference(uri, digit) {
  return { uri, digest: `sha256:${digit.repeat(64)}` };
}


function actionReceiptReference(receipt) {
  const token = receipt.receipt_id.split(":", 2)[1];
  return {
    uri: `oos://agent-actions/receipts/${token}`,
    digest: receipt.integrity.content_digest,
  };
}


async function main() {
  const inputPath = process.argv[2];
  const oosRepo = process.argv[3];
  if (!inputPath || !oosRepo) {
    throw new Error("usage: agent_action_conformance_adapter.mjs <input.json> <oos-repo>");
  }

  const input = JSON.parse(await readFile(inputPath, "utf8"));
  const contracts = await import(pathToFileURL(
    path.join(oosRepo, "src/agent-action/contracts.js"),
  ));
  const enforcement = await import(pathToFileURL(
    path.join(oosRepo, "src/agent-action/enforcement.js"),
  ));

  const results = [];
  for (const testCase of input.cases) {
    const receipts = [];
    let executionInvocations = 0;
    let ownerMutationInvocations = 0;
    let returned = null;
    let error = null;

    const enforcer = enforcement.createAgentActionEnforcer({
      audit: {
        emit() {
          if (testCase.failure_injection === "audit") {
            throw new Error("conformance-audit-failure");
          }
        },
      },
      clock: () => input.execution_time,
      evaluatorClient: {
        async evaluate() {
          return {
            decision: structuredClone(testCase.decision),
            ledger_event: structuredClone(testCase.ledger_event),
          };
        },
      },
      async recordReceipt(receipt) {
        if (testCase.failure_injection === "receipt-store") {
          throw new Error("conformance-receipt-store-failure");
        }
        receipts.push(structuredClone(receipt));
      },
    });

    try {
      returned = await enforcer.execute({
        request: testCase.request,
        async resolveCurrent() {
          return structuredClone(testCase.current);
        },
        async execute({ decision, request }) {
          executionInvocations += 1;
          if (request.action_class !== "mutate") {
            return {
              backend_executor_id: `conformance-${request.action_class}-adapter-v1`,
              outcome: "succeeded",
              result_ref: reference(
                `oos://agent-actions/results/${testCase.case_id}`,
                "d",
              ),
            };
          }

          ownerMutationInvocations += 1;
          const ownerReceipt = {
            schema_version: 1,
            artifact_type: "agent_action_owner_receipt",
            receipt_id: `agent-action-owner-receipt:${testCase.case_id}`,
            request_ref: contracts.agentActionRequestRef(request),
            decision_ref: contracts.agentActionDecisionRef(decision),
            action_class: "mutate",
            owner: {
              repo: request.target.owner_repo,
              adapter: "synthetic-conformance-owner-v1",
              authority_ref: reference(
                "proof://authorities/synthetic-conformance-owner-v1",
                "e",
              ),
            },
            target: {
              resource_id: request.target.resource_id,
              before_version: request.target.source_version,
              after_version: `${request.target.source_version}:after`,
            },
            mutation_outcome: "applied",
            result_ref: reference(
              `proof://results/${testCase.case_id}`,
              "f",
            ),
            audit_ref: reference(
              `proof://audit/${testCase.case_id}`,
              "1",
            ),
            executed_at: input.execution_time,
            idempotency_key: request.idempotency_key,
            failure: null,
            integrity: {
              canonicalization: "RFC8785",
              algorithm: "sha256",
              content_digest: "",
            },
          };
          ownerReceipt.integrity.content_digest =
            contracts.agentActionArtifactDigest(ownerReceipt);
          return {
            backend_executor_id: "synthetic-conformance-owner-v1",
            owner_receipt: ownerReceipt,
            owner_receipt_ref: {
              uri: `proof://owner-receipts/${testCase.case_id}`,
              digest: ownerReceipt.integrity.content_digest,
            },
          };
        },
      });
    } catch (caught) {
      error = caught;
    }

    const terminalReceipt = returned?.action_receipt ?? receipts.at(-1) ?? null;
    results.push({
      case_id: testCase.case_id,
      policy_outcome: testCase.decision.outcome,
      policy_reason_codes: [...testCase.decision.reason_codes],
      execution_outcome: error
        ? "error"
        : returned.action_receipt.outcome,
      execution_invocations: executionInvocations,
      owner_mutation_invocations: ownerMutationInvocations,
      terminal_receipts: receipts.length,
      decision_ref: contracts.agentActionDecisionRef(testCase.decision),
      action_receipt_ref: terminalReceipt
        ? actionReceiptReference(terminalReceipt)
        : null,
      owner_receipt_ref: returned?.action_receipt?.owner_receipt_ref ?? null,
      owner_receipt_returned: returned?.owner_receipt !== null && returned?.owner_receipt !== undefined,
      success_returned: returned?.action_receipt?.outcome === "succeeded",
      error_code: error?.code ?? error?.message ?? null,
    });
  }

  process.stdout.write(`${JSON.stringify({ results }, null, 2)}\n`);
}


main().catch((error) => {
  process.stderr.write(`${error.stack ?? error.message}\n`);
  process.exitCode = 1;
});
