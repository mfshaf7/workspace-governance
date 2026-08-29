from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "repository-custody.yaml"
SCHEMA_ROOT = REPO_ROOT / "contracts" / "schemas"
FIXTURE_ROOT = REPO_ROOT / "contracts" / "fixtures" / "repository-custody"
FORMAT_CHECKER = FormatChecker()

ARTIFACT_CASES = {
    "request": ("repository-custody-request.schema.json", "request.valid.json"),
    "decision": ("repository-custody-decision.schema.json", "decision.valid.json"),
    "provider_readback": (
        "repository-provider-readback.schema.json",
        "provider-readback.valid.json",
    ),
    "custody_receipt": (
        "repository-custody-receipt.schema.json",
        "receipt.valid.json",
    ),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


class RepositoryCustodyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        cls.validators = {
            name: validator_for(SCHEMA_ROOT / schema_name)
            for name, (schema_name, _) in ARTIFACT_CASES.items()
        }
        cls.fixtures = {
            name: load_json(FIXTURE_ROOT / fixture_name)
            for name, (_, fixture_name) in ARTIFACT_CASES.items()
        }

    def assertValid(self, artifact_name: str, payload: dict) -> None:
        errors = sorted(
            self.validators[artifact_name].iter_errors(payload),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual([error.message for error in errors], [])

    def assertInvalid(self, artifact_name: str, payload: dict) -> None:
        self.assertTrue(list(self.validators[artifact_name].iter_errors(payload)))

    def test_contract_and_artifact_fixtures_validate(self) -> None:
        contract_validator = validator_for(
            SCHEMA_ROOT / "repository-custody.schema.json"
        )
        self.assertEqual(list(contract_validator.iter_errors(self.contract)), [])
        for name, payload in self.fixtures.items():
            with self.subTest(artifact=name):
                self.assertValid(name, payload)

    def test_repository_identity_uses_provider_id_not_coordinates(self) -> None:
        self.assertEqual(
            self.contract["repository_identity"]["immutable_key"]["fields"],
            ["provider", "provider_repository_id"],
        )
        readback = copy.deepcopy(self.fixtures["provider_readback"])
        readback["repository_identity"].pop("provider_repository_id")
        self.assertInvalid("provider_readback", readback)

    def test_existing_repository_actions_require_provider_identity(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["target"]["provider_repository_id"] = None
        self.assertInvalid("request", request)

    def test_provider_mutation_requires_exact_approval(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["action"] = "archive-provider"
        request["authority"]["approval_ref"] = None
        self.assertInvalid("request", request)

    def test_linking_custody_requires_exact_approval(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["authority"]["approval_ref"] = None
        self.assertInvalid("request", request)

    def test_successful_link_requires_readback_and_identity(self) -> None:
        receipt = copy.deepcopy(self.fixtures["custody_receipt"])
        receipt["provider_readback_ref"] = None
        self.assertInvalid("custody_receipt", receipt)

        receipt = copy.deepcopy(self.fixtures["custody_receipt"])
        receipt["repository_identity"] = None
        self.assertInvalid("custody_receipt", receipt)

    def test_custody_receipt_does_not_claim_downstream_mutation(self) -> None:
        downstream = self.fixtures["custody_receipt"]["downstream_handoffs"]
        self.assertEqual(downstream["workspace_intake"], "request-available")
        self.assertEqual(downstream["active_inventory"], "separate-action-required")
        self.assertEqual(downstream["delivery_catalog"], "separate-action-required")
        self.assertEqual(downstream["product_admission"], "separate-action-required")

    def test_secret_values_are_rejected_as_unknown_fields(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["authority"]["token"] = "not-allowed"
        self.assertInvalid("request", request)


if __name__ == "__main__":
    unittest.main()
