from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "workspace-intake-inventory-operation.yaml"
SCHEMA_PATH = (
    REPO_ROOT
    / "contracts"
    / "schemas"
    / "workspace-intake-inventory-operation.schema.json"
)


class WorkspaceIntakeInventoryOperationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(self.schema)

    def errors(self, contract: dict) -> list[str]:
        return [error.message for error in self.validator.iter_errors(contract)]

    def test_contract_locks_the_approved_activation_order(self) -> None:
        self.assertEqual(self.errors(self.contract), [])
        self.assertEqual(
            [entry["owner_repo"] for entry in self.contract["authority_sequence"]],
            [
                "workspace-governance",
                "workspace-governance-control-fabric",
                "operator-orchestration-service",
                "governance-operations-console",
                "security-architecture",
                "platform-engineering",
            ],
        )
        self.assertEqual(
            self.contract["ordered_work_item_refs"],
            [
                f"openproject://work_packages/{work_item_id}"
                for work_item_id in (1206, 1207, 1208, 1209, 1216, 1217, 1210)
            ],
        )

    def test_source_completion_cannot_claim_operating_readiness(self) -> None:
        self.assertEqual(
            self.contract["evidence_posture"]["baseline"],
            "source-complete-conformance-only",
        )
        self.assertIn(
            "source-complete-treated-as-operating-ready",
            self.contract["denied_shortcuts"],
        )
        self.assertEqual(
            self.contract["status_projection"]["source"],
            "operator-orchestration-service",
        )

    def test_schema_rejects_owner_order_drift(self) -> None:
        drifted = copy.deepcopy(self.contract)
        drifted["authority_sequence"].append(
            {
                "order": 7,
                "owner_repo": "governance-operations-console",
                "capability": "claim-operating-readiness",
                "evidence": "local UI state",
            }
        )
        self.assertNotEqual(self.errors(drifted), [])


if __name__ == "__main__":
    unittest.main()
