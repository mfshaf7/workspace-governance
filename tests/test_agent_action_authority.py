from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "agent-action-authority.yaml"
CONTRACT_SCHEMA_PATH = (
    REPO_ROOT / "contracts" / "schemas" / "agent-action-authority.schema.json"
)
FIXTURE_ROOT = REPO_ROOT / "contracts" / "fixtures" / "agent-action-authority"
SCHEMA_ROOT = REPO_ROOT / "contracts" / "schemas"
FORMAT_CHECKER = FormatChecker()

ARTIFACT_CASES = {
    "request": (
        SCHEMA_ROOT / "agent-action-request.schema.json",
        FIXTURE_ROOT / "request.valid.json",
    ),
    "policy_decision": (
        SCHEMA_ROOT / "agent-action-policy-decision.schema.json",
        FIXTURE_ROOT / "policy-decision.valid.json",
    ),
    "action_receipt": (
        SCHEMA_ROOT / "agent-action-receipt.schema.json",
        FIXTURE_ROOT / "action-receipt.valid.json",
    ),
    "owner_receipt": (
        SCHEMA_ROOT / "agent-action-owner-receipt.schema.json",
        FIXTURE_ROOT / "owner-receipt.valid.json",
    ),
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validator_for(path: Path) -> Draft202012Validator:
    schema = load_json(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema, format_checker=FORMAT_CHECKER)


class AgentActionAuthorityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validators = {
            name: validator_for(schema_path)
            for name, (schema_path, _) in ARTIFACT_CASES.items()
        }
        cls.fixtures = {
            name: load_json(fixture_path)
            for name, (_, fixture_path) in ARTIFACT_CASES.items()
        }

    def assertValid(self, artifact_name: str, instance: dict) -> None:
        errors = sorted(
            self.validators[artifact_name].iter_errors(instance),
            key=lambda error: list(error.absolute_path),
        )
        self.assertEqual([error.message for error in errors], [])

    def assertInvalid(self, artifact_name: str, instance: dict) -> None:
        self.assertTrue(
            list(self.validators[artifact_name].iter_errors(instance)),
            f"{artifact_name} unexpectedly passed validation",
        )

    def test_canonical_contract_and_examples_validate(self) -> None:
        contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        contract_validator = validator_for(CONTRACT_SCHEMA_PATH)

        self.assertEqual(list(contract_validator.iter_errors(contract)), [])
        for artifact_name, fixture in self.fixtures.items():
            with self.subTest(artifact_name=artifact_name):
                self.assertValid(artifact_name, fixture)

    def test_each_action_class_has_a_valid_request_shape(self) -> None:
        base = self.fixtures["request"]
        for action_class in ("read", "advise", "draft", "mutate"):
            request = copy.deepcopy(base)
            request["action_class"] = action_class
            if action_class == "read":
                request["model_invocation_ref"] = None
                request["context"] = {"packet_ref": None, "receipt_ref": None}
                request["authority"]["approval_ref"] = None
            elif action_class in {"advise", "draft"}:
                request["authority"]["approval_ref"] = None
            else:
                request["model_invocation_ref"] = None

            with self.subTest(action_class=action_class):
                self.assertValid("request", request)

    def test_each_action_class_has_a_valid_terminal_receipt_shape(self) -> None:
        base = self.fixtures["action_receipt"]
        for action_class in ("read", "advise", "draft", "mutate"):
            receipt = copy.deepcopy(base)
            receipt["action_class"] = action_class
            if action_class != "mutate":
                receipt["approval_ref"] = None
                receipt["owner_receipt_ref"] = None
                receipt["mutation_state"] = "not-applicable"
                receipt["target"]["after_version"] = None

            with self.subTest(action_class=action_class):
                self.assertValid("action_receipt", receipt)

    def test_agent_identity_cannot_replace_operator_delegation(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["action_class"] = "read"
        request["authority"]["delegation_ref"] = None

        self.assertInvalid("request", request)

    def test_context_is_required_for_model_assisted_actions(self) -> None:
        for action_class in ("advise", "draft", "mutate"):
            request = copy.deepcopy(self.fixtures["request"])
            request["action_class"] = action_class
            request["context"]["packet_ref"] = None
            if action_class != "mutate":
                request["authority"]["approval_ref"] = None

            with self.subTest(action_class=action_class):
                self.assertInvalid("request", request)

    def test_mutation_requires_exact_approval(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["authority"]["approval_ref"] = None
        self.assertInvalid("request", request)

        decision = copy.deepcopy(self.fixtures["policy_decision"])
        decision["bindings"]["approval_ref"] = None
        self.assertInvalid("policy_decision", decision)

        decision = copy.deepcopy(self.fixtures["policy_decision"])
        decision["obligations"].remove("require-owner-receipt-after-invocation")
        self.assertInvalid("policy_decision", decision)

    def test_applied_mutation_requires_owner_receipt_and_after_version(self) -> None:
        receipt = copy.deepcopy(self.fixtures["action_receipt"])
        receipt["owner_receipt_ref"] = None
        self.assertInvalid("action_receipt", receipt)

        owner_receipt = copy.deepcopy(self.fixtures["owner_receipt"])
        owner_receipt["target"]["after_version"] = None
        self.assertInvalid("owner_receipt", owner_receipt)

    def test_raw_context_cannot_enter_authority_envelopes(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["raw_context"] = "secret material"

        self.assertInvalid("request", request)

    def test_unknown_action_class_is_rejected(self) -> None:
        request = copy.deepcopy(self.fixtures["request"])
        request["action_class"] = "autonomous"

        self.assertInvalid("request", request)


if __name__ == "__main__":
    unittest.main()
