from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from console_operational_capabilities_contract import (  # noqa: E402
    contract_issues,
    generated_view,
)


CONTRACT_PATH = REPO_ROOT / "contracts" / "console-operational-capabilities.yaml"
GENERATED_PATH = REPO_ROOT / "generated" / "console-operational-capabilities.json"


def load_contract() -> dict:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


class ConsoleOperationalCapabilitiesTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()
        self.known_repos = {
            "workspace-governance",
            "workspace-governance-control-fabric",
            "workspace-prototype-studio",
            "governance-operations-console",
            "operator-orchestration-service",
            "platform-engineering",
            "security-architecture",
        }

    def assertInvalid(self, contract: dict, expected: str) -> None:
        issues = contract_issues(
            contract,
            known_repos=self.known_repos,
            repo_root=REPO_ROOT,
        )
        self.assertTrue(any(expected in issue for issue in issues), issues)

    def test_canonical_contract_is_complete(self) -> None:
        self.assertEqual(
            contract_issues(
                self.contract,
                known_repos=self.known_repos,
                repo_root=REPO_ROOT,
            ),
            [],
        )

    def test_feature_presence_cannot_claim_live_runtime(self) -> None:
        invalid = copy.deepcopy(self.contract)
        invalid["console_operational_capabilities"]["status_profiles"]["planned"][
            "runtime_state"
        ] = "available"

        self.assertInvalid(invalid, "status_profiles must preserve truthful")

    def test_fixture_demonstration_cannot_be_terminal_completion(self) -> None:
        invalid = copy.deepcopy(self.contract)
        invalid["console_operational_capabilities"]["plan_completeness"][
            "terminal_completion_profile"
        ] = "fixture-demonstration"

        self.assertInvalid(invalid, "terminal completion must require")

    def test_live_mode_cannot_fall_back_to_fixtures(self) -> None:
        invalid = copy.deepcopy(self.contract)
        invalid["console_operational_capabilities"]["fixture_boundary"][
            "fixture_live_fallback_allowed"
        ] = True

        self.assertInvalid(invalid, "fixture fallback cannot be enabled")

    def test_missing_journey_stage_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.contract)
        invalid["console_operational_capabilities"]["capabilities"].pop(1)

        self.assertInvalid(invalid, "capability journey_order must be contiguous")
        self.assertInvalid(invalid, "capabilities must cover each required journey stage")

    def test_console_cannot_become_canonical_workflow_owner(self) -> None:
        invalid = copy.deepcopy(self.contract)
        invalid["console_operational_capabilities"]["capabilities"][0][
            "workflow_owner_repo"
        ] = "governance-operations-console"

        self.assertInvalid(invalid, "cannot assign canonical workflow ownership")

    def test_every_capability_requires_negative_and_terminal_proof(self) -> None:
        invalid = copy.deepcopy(self.contract)
        invalid["console_operational_capabilities"]["capabilities"][0][
            "proof_classes"
        ] = ["positive"]

        self.assertInvalid(invalid, "must require positive, negative, and terminal proof")

    def test_missing_authority_reference_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.contract)
        invalid["console_operational_capabilities"]["capabilities"][0][
            "authority_refs"
        ] = ["contracts/does-not-exist.yaml"]

        self.assertInvalid(invalid, "references missing authority file")

    def test_generated_view_is_current(self) -> None:
        expected = generated_view(self.contract)
        actual = json.loads(GENERATED_PATH.read_text(encoding="utf-8"))

        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
