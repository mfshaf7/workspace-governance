from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator, FormatChecker
import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "contracts" / "agent-source-implementation.yaml"
SCHEMA_PATH = (
    REPO_ROOT
    / "contracts"
    / "schemas"
    / "agent-source-implementation.schema.json"
)


class AgentSourceImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
        cls.validator = Draft202012Validator(
            schema,
            format_checker=FormatChecker(),
        )

    def assertContractInvalid(self, contract: dict) -> None:
        self.assertTrue(list(self.validator.iter_errors(contract)))

    def test_contract_validates(self) -> None:
        self.assertEqual(list(self.validator.iter_errors(self.contract)), [])

    def test_agent_gary_is_source_implementor_only(self) -> None:
        profile = self.contract["profiles"]["agent-gary"]

        self.assertEqual(profile["display_name"], "Agent Gary")
        self.assertEqual(profile["logical_agent_id"], "agent-gary")
        self.assertEqual(profile["role"], "source-implementor")
        self.assertEqual(profile["state"], "contract-defined")
        self.assertEqual(profile["provider_principal"], "mfshaf7-agent-gary[bot]")
        self.assertEqual(profile["git_author"]["name"], profile["display_name"])
        self.assertEqual(
            profile["git_author"]["email"],
            "327854141+mfshaf7-agent-gary[bot]@users.noreply.github.com",
        )

    def test_ambiguous_agent_name_is_rejected(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["profiles"]["agent-gary"]["display_name"] = "Gary"

        self.assertContractInvalid(contract)

    def test_provider_administration_is_rejected(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["provider_boundary"]["permissions"]["administration"] = "write"

        self.assertContractInvalid(contract)

    def test_unattributed_git_author_is_rejected(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["profiles"]["agent-gary"]["git_author"]["email"] = (
            "agent-gary@workspace.local"
        )

        self.assertContractInvalid(contract)

    def test_normal_activation_is_fail_closed(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["normal_activation"]["enabled"] = True

        self.assertContractInvalid(contract)

    def test_agent_authorship_cannot_replace_human_review(self) -> None:
        contract = copy.deepcopy(self.contract)
        contract["evidence"]["agent_authorship_as_human_review"] = "allowed"

        self.assertContractInvalid(contract)

    def test_session_and_completion_bindings_are_temporally_separate(self) -> None:
        bindings = self.contract["required_bindings"]

        self.assertNotIn("merged_head", bindings["session"])
        self.assertEqual(
            set(bindings["completion"]),
            {"pushed_head", "reviewed_head", "merged_head"},
        )

    def test_human_fallback_and_agent_merge_are_denied(self) -> None:
        denied = set(self.contract["provider_boundary"]["denied_powers"])

        self.assertIn("use-human-credential-fallback", denied)
        self.assertIn("approve-pull-request", denied)
        self.assertIn("merge-pull-request", denied)


if __name__ == "__main__":
    unittest.main()
