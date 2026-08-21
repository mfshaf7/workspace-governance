from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from project_lifecycle_contract import (  # noqa: E402
    contract_issues,
    state_vector_issues,
    transition_request_issues,
)


CONTRACT_PATH = REPO_ROOT / "contracts" / "project-lifecycle.yaml"


def load_contract() -> dict:
    return yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))


def base_state(**overrides: str) -> dict[str, str]:
    state = {
        "project-phase": "proposed",
        "source-custody": "none",
        "runtime-environment": "none",
        "release-posture": "unreleased",
        "publication-posture": "unlisted",
    }
    state.update(overrides)
    return state


class ProjectLifecycleContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load_contract()
        self.known_repos = {
            role["owner_ref"]
            for role in self.contract["project_lifecycle"]["ownership_roles"].values()
            if role["owner_kind"] == "repo"
        }

    def test_canonical_contract_has_no_semantic_issues(self) -> None:
        self.assertEqual(
            contract_issues(self.contract, known_repos=self.known_repos),
            [],
        )

    def test_contradictory_ownership_is_rejected(self) -> None:
        invalid = copy.deepcopy(self.contract)
        invalid["project_lifecycle"]["ownership_roles"]["console-projection"][
            "responsibilities"
        ].append("project-workflow-record")

        issues = contract_issues(invalid, known_repos=self.known_repos)

        self.assertTrue(
            any("contradictory owners" in issue for issue in issues),
            issues,
        )
        self.assertTrue(
            any("projection role" in issue for issue in issues),
            issues,
        )

    def test_supported_transition_with_complete_evidence_passes(self) -> None:
        request = {
            "transition_id": "proposal-route-delivery",
            "current_state": base_state(),
            "requested_state": base_state(**{"project-phase": "delivery-governed"}),
            "envelope_type": "project-handoff",
            "evidence_types": [
                "operator-decision",
                "target-admission",
                "owner-receipt",
            ],
            "recovery": None,
        }

        self.assertEqual(transition_request_issues(self.contract, request), [])

    def test_first_source_admission_uses_assignment_not_transfer(self) -> None:
        current = base_state(**{"project-phase": "incubating"})
        requested = base_state(
            **{
                "project-phase": "incubating",
                "source-custody": "incubation-repo",
            }
        )
        request = {
            "transition_id": "source-admit-incubation",
            "current_state": current,
            "requested_state": requested,
            "envelope_type": "source-custody-assignment",
            "evidence_types": ["incubation-source-record", "owner-receipt"],
            "recovery": None,
        }

        self.assertEqual(transition_request_issues(self.contract, request), [])

    def test_retirement_has_a_non_cyclic_cleanup_path(self) -> None:
        current = base_state(
            **{
                "project-phase": "operational",
                "source-custody": "dedicated-owner-repo",
                "release-posture": "withdrawn",
            }
        )
        requested = dict(current, **{"project-phase": "retired"})
        request = {
            "transition_id": "retire-project",
            "current_state": current,
            "requested_state": requested,
            "envelope_type": "retirement-decision",
            "evidence_types": ["operator-decision", "validation-receipt"],
            "recovery": None,
        }

        self.assertEqual(transition_request_issues(self.contract, request), [])

    def test_unknown_transition_is_rejected(self) -> None:
        request = {
            "transition_id": "prototype-skip-to-publication",
            "current_state": base_state(),
            "requested_state": base_state(),
            "envelope_type": "project-handoff",
            "evidence_types": [],
            "recovery": None,
        }

        self.assertEqual(
            transition_request_issues(self.contract, request),
            ["unsupported transition 'prototype-skip-to-publication'"],
        )

    def test_transition_cannot_hide_an_extra_axis_change(self) -> None:
        request = {
            "transition_id": "proposal-route-incubation",
            "current_state": base_state(),
            "requested_state": base_state(
                **{
                    "project-phase": "incubating",
                    "source-custody": "incubation-repo",
                }
            ),
            "envelope_type": "project-handoff",
            "evidence_types": [
                "operator-decision",
                "target-admission",
                "owner-receipt",
            ],
            "recovery": None,
        }

        issues = transition_request_issues(self.contract, request)

        self.assertTrue(any("must change only project-phase" in issue for issue in issues), issues)

    def test_state_vector_invariants_reject_false_operational_posture(self) -> None:
        invalid = base_state(
            **{
                "project-phase": "operational",
                "release-posture": "not-applicable",
            }
        )

        issues = state_vector_issues(self.contract, invalid)

        self.assertTrue(
            any("operational-source-is-durable" in issue for issue in issues),
            issues,
        )

    def test_non_removal_recovery_requires_governed_fields(self) -> None:
        request = {
            "transition_id": "proposal-route-delivery",
            "current_state": base_state(),
            "requested_state": base_state(**{"project-phase": "delivery-governed"}),
            "envelope_type": "project-handoff",
            "evidence_types": [
                "operator-decision",
                "target-admission",
                "owner-receipt",
            ],
            "recovery": {
                "decision": "defer",
                "justification": "Target capacity is unavailable.",
            },
        }

        issues = transition_request_issues(self.contract, request)

        self.assertTrue(any("owner, review_at" in issue for issue in issues), issues)


if __name__ == "__main__":
    unittest.main()
