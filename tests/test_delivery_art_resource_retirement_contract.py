from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from delivery_art_resource_retirement_contract import (  # noqa: E402
    CLEANUP_RECEIPT_FIXTURE,
    CLEANUP_RECEIPT_SCHEMA,
    RESOURCE_MANIFEST_FIXTURE,
    RESOURCE_MANIFEST_SCHEMA,
    cleanup_receipt_semantic_issues,
    contract_fixture_issues,
    manifest_receipt_pair_issues,
    resource_manifest_semantic_issues,
    resource_retirement_definition_issues,
)


def load_json(relative_path: Path) -> dict:
    return json.loads((REPO_ROOT / relative_path).read_text(encoding="utf-8"))


class DeliveryArtResourceRetirementContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest_schema = load_json(RESOURCE_MANIFEST_SCHEMA)
        self.manifest = load_json(RESOURCE_MANIFEST_FIXTURE)
        self.receipt_schema = load_json(CLEANUP_RECEIPT_SCHEMA)
        self.receipt = load_json(CLEANUP_RECEIPT_FIXTURE)
        operator_contract = yaml.safe_load(
            (REPO_ROOT / "contracts/delivery-art-operator-path.yaml").read_text(
                encoding="utf-8"
            )
        )
        self.retirement = operator_contract["delivery_art_operator_path"][
            "work_session_lifecycle"
        ]["resource_retirement"]

    def schema_errors(self, schema: dict, payload: dict) -> list:
        return list(
            Draft202012Validator(
                schema,
                format_checker=FormatChecker(),
            ).iter_errors(payload)
        )

    def test_canonical_contract_and_fixtures_are_valid(self) -> None:
        self.assertEqual(contract_fixture_issues(REPO_ROOT), [])
        self.assertEqual(resource_retirement_definition_issues(self.retirement), [])

    def test_manifest_rejects_absolute_and_parent_traversal_paths(self) -> None:
        absolute = copy.deepcopy(self.manifest)
        absolute["resources"][0]["locator"]["workspace_relative_path"] = (
            "/tmp/unowned"
        )
        traversal = copy.deepcopy(self.manifest)
        traversal["resources"][0]["locator"]["workspace_relative_path"] = (
            ".worktrees/../unowned"
        )

        self.assertTrue(resource_manifest_semantic_issues(absolute))
        self.assertTrue(resource_manifest_semantic_issues(traversal))

    def test_manifest_rejects_unowned_resource_deletion_eligibility(self) -> None:
        invalid = copy.deepcopy(self.manifest)
        invalid["resources"][-1]["retention_class"] = "retire-on-terminal-close"
        invalid["resources"][-1]["outcome"] = "eligible"

        issues = resource_manifest_semantic_issues(invalid)

        self.assertTrue(any("unowned resources" in issue for issue in issues), issues)

    def test_manifest_rejects_wrong_ownership_marker(self) -> None:
        invalid = copy.deepcopy(self.manifest)
        invalid["resources"][0]["locator"]["ownership_marker"] = (
            "work-session:delivery-999:delivery-999-work-item-999"
        )

        issues = resource_manifest_semantic_issues(invalid)

        self.assertTrue(any("ownership_marker" in issue for issue in issues), issues)

    def test_cleanup_receipt_rejects_nonterminal_resource_outcome(self) -> None:
        invalid = copy.deepcopy(self.receipt)
        invalid["resources"][0]["outcome"] = "blocked"

        self.assertTrue(self.schema_errors(self.receipt_schema, invalid))

    def test_cleanup_receipt_rejects_false_complete_result(self) -> None:
        invalid = copy.deepcopy(self.receipt)
        invalid["outcome"] = "complete"

        issues = cleanup_receipt_semantic_issues(invalid)

        self.assertTrue(any("cannot contain retained" in issue for issue in issues), issues)

    def test_cleanup_receipt_rejects_unowned_resource_removal(self) -> None:
        invalid = copy.deepcopy(self.receipt)
        invalid["resources"][-1]["outcome"] = "removed"
        invalid["resources"][-1]["reason"] = None

        issues = cleanup_receipt_semantic_issues(invalid)

        self.assertTrue(any("unowned resource" in issue for issue in issues), issues)

    def test_cleanup_receipt_requires_reason_for_retained_resource(self) -> None:
        invalid = copy.deepcopy(self.receipt)
        invalid["resources"][-1]["reason"] = None

        self.assertTrue(self.schema_errors(self.receipt_schema, invalid))

    def test_cleanup_receipt_binds_exact_final_manifest_resources(self) -> None:
        self.assertEqual(manifest_receipt_pair_issues(self.manifest, self.receipt), [])
        invalid = copy.deepcopy(self.receipt)
        invalid["resources"].pop()

        issues = manifest_receipt_pair_issues(self.manifest, invalid)

        self.assertTrue(any("resource set exactly" in issue for issue in issues), issues)

    def test_runtime_claim_cannot_downgrade_after_activation(self) -> None:
        invalid = copy.deepcopy(self.retirement)
        invalid["state"] = "contract-ready-pending-owner-implementation"

        issues = resource_retirement_definition_issues(invalid)

        self.assertTrue(any("must remain active" in issue for issue in issues), issues)


if __name__ == "__main__":
    unittest.main()
