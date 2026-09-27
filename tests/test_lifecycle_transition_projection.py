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

from project_lifecycle_contract import (  # noqa: E402
    PROJECTION_ROUTES,
    contract_issues,
    projection_issues,
)


CONTRACT_PATH = REPO_ROOT / "contracts" / "project-lifecycle.yaml"
SCHEMA_PATH = (
    REPO_ROOT
    / "contracts"
    / "schemas"
    / "lifecycle-transition-projection.schema.json"
)
FIXTURE_PATH = (
    REPO_ROOT
    / "contracts"
    / "fixtures"
    / "lifecycle-transition-projection"
    / "prototype-to-delivery.current.valid.json"
)


class LifecycleTransitionProjectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.validator = Draft202012Validator(
            self.schema,
            format_checker=FormatChecker(),
        )

    def schema_errors(self, artifact: dict) -> list[str]:
        return [error.message for error in self.validator.iter_errors(artifact)]

    def test_contract_and_canonical_fixture_are_valid(self) -> None:
        known_repos = {
            role["owner_ref"]
            for role in self.contract["project_lifecycle"]["ownership_roles"].values()
            if role["owner_kind"] == "repo"
        }
        self.assertEqual(contract_issues(self.contract, known_repos=known_repos), [])
        self.assertEqual(self.schema_errors(self.fixture), [])
        self.assertEqual(projection_issues(self.contract, self.fixture), [])

    def test_routes_bind_existing_canonical_transitions(self) -> None:
        model = self.contract["project_lifecycle"]
        routes = model["projection_contract"]["locked_routes"]
        self.assertEqual(routes, PROJECTION_ROUTES)
        self.assertEqual(
            {route["canonical_transition_id"] for route in routes.values()},
            {
                "proposal-route-delivery",
                "proposal-route-incubation",
                "incubation-promote-delivery",
            },
        )
        self.assertTrue(
            all(
                route["canonical_transition_id"] in model["transitions"]
                for route in routes.values()
            )
        )

    def test_unknown_route_and_state_are_rejected(self) -> None:
        artifact = copy.deepcopy(self.fixture)
        artifact["projection"]["route_id"] = "portfolio-to-delivery"
        self.assertTrue(self.schema_errors(artifact))

        artifact = copy.deepcopy(self.fixture)
        artifact["projection"]["state"] = "waiting"
        self.assertTrue(self.schema_errors(artifact))

    def test_projection_rejects_raw_or_unmodeled_owner_data(self) -> None:
        artifact = copy.deepcopy(self.fixture)
        artifact["projection"]["raw_owner_artifact"] = {"output": "not allowed"}
        self.assertTrue(self.schema_errors(artifact))

    def test_non_terminal_state_requires_exact_owned_next_action(self) -> None:
        artifact = copy.deepcopy(self.fixture)
        artifact["projection"]["next_action"]["owner_ref"] = ""
        self.assertTrue(self.schema_errors(artifact))
        self.assertIn(
            "lifecycle transition next action requires an owner",
            projection_issues(self.contract, artifact),
        )

        artifact = copy.deepcopy(self.fixture)
        artifact["projection"]["next_action"]["action"] = "record-admission"
        self.assertIn(
            "lifecycle transition state prepared requires next action start-validation",
            projection_issues(self.contract, artifact),
        )

        artifact = copy.deepcopy(self.fixture)
        artifact["projection"]["next_action"]["owner_ref"] = "prototype"
        self.assertIn(
            "lifecycle transition state prepared requires next-action owner "
            "workspace-governance-control-fabric",
            projection_issues(self.contract, artifact),
        )

    def test_terminal_state_cannot_expose_a_next_action(self) -> None:
        artifact = copy.deepcopy(self.fixture)
        artifact["projection"]["state"] = "cancelled"
        artifact["projection"]["cancelled_reason_code"] = "operator-cancelled"
        self.assertIn(
            "terminal lifecycle transition must not expose a next action",
            projection_issues(self.contract, artifact),
        )

    def test_route_source_and_target_must_match(self) -> None:
        artifact = copy.deepcopy(self.fixture)
        artifact["projection"]["source"]["domain"] = "proposal"
        artifact["projection"]["target"]["home_ref"] = "workspace-prototype-studio"
        issues = projection_issues(self.contract, artifact)
        self.assertIn(
            "projection source does not match locked route prototype-to-delivery",
            issues,
        )
        self.assertIn(
            "projection target does not match locked route prototype-to-delivery",
            issues,
        )

    def test_applied_state_requires_the_route_completion_receipt(self) -> None:
        artifact = copy.deepcopy(self.fixture)
        artifact["projection"]["state"] = "applied"
        artifact["projection"]["next_action"] = None
        artifact["projection"]["application"]["state"] = "applied"
        self.assertIn(
            "applied lifecycle transition requires its route completion receipt",
            projection_issues(self.contract, artifact),
        )

    def test_history_is_bounded_and_matches_revision(self) -> None:
        artifact = copy.deepcopy(self.fixture)
        artifact["revision"]["event_sequence"] = 2
        self.assertIn(
            "projection revision must match the latest history sequence",
            projection_issues(self.contract, artifact),
        )


if __name__ == "__main__":
    unittest.main()
