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


def complete_request(
    contract: dict,
    transition_id: str,
    current_state: dict[str, str],
    requested_state: dict[str, str],
    *,
    recovery: dict | None = None,
) -> dict:
    model = contract["project_lifecycle"]
    transition = model["transitions"][transition_id]
    envelope = {}
    for field in model["envelopes"][transition["required_envelope"]][
        "required_fields"
    ]:
        if field == "transition_id":
            envelope[field] = transition_id
        elif field == "expected_state_version":
            envelope[field] = 1
        elif field == "evidence_refs":
            envelope[field] = ["proof://evidence/1"]
        elif field == "recovery":
            envelope[field] = recovery
        else:
            envelope[field] = f"proof://{field}/1"
    return {
        "transition_id": transition_id,
        "current_state": current_state,
        "requested_state": requested_state,
        "source_authority_role": transition["source_authority_role"],
        "target_owner_role": transition["target_owner_role"],
        "implementation_maturity": transition["implementation_maturity"],
        "envelope_type": transition["required_envelope"],
        "envelope": envelope,
        "evidence_types": list(transition["required_evidence"]),
        "recovery": recovery,
    }


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
        request = complete_request(
            self.contract,
            "proposal-route-delivery",
            base_state(),
            base_state(**{"project-phase": "delivery-governed"}),
        )

        self.assertEqual(transition_request_issues(self.contract, request), [])

    def test_first_source_admission_uses_assignment_not_transfer(self) -> None:
        current = base_state(**{"project-phase": "incubating"})
        requested = base_state(
            **{
                "project-phase": "incubating",
                "source-custody": "incubation-repo",
            }
        )
        request = complete_request(
            self.contract,
            "source-admit-incubation",
            current,
            requested,
        )

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
        request = complete_request(
            self.contract,
            "retire-project",
            current,
            requested,
        )

        self.assertEqual(transition_request_issues(self.contract, request), [])

    def test_unknown_transition_is_rejected(self) -> None:
        request = {
            "transition_id": "prototype-skip-to-publication",
            "current_state": base_state(),
            "requested_state": base_state(),
            "source_authority_role": "operator-workflow-authority",
            "target_owner_role": "operator-workflow-authority",
            "implementation_maturity": "contract-only",
            "envelope_type": "project-handoff",
            "envelope": {},
            "evidence_types": [],
            "recovery": None,
        }

        self.assertEqual(
            transition_request_issues(self.contract, request),
            ["unsupported transition 'prototype-skip-to-publication'"],
        )

    def test_transition_cannot_hide_an_extra_axis_change(self) -> None:
        request = complete_request(
            self.contract,
            "proposal-route-incubation",
            base_state(),
            base_state(
                **{
                    "project-phase": "incubating",
                    "source-custody": "incubation-repo",
                }
            ),
        )

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
        request = complete_request(
            self.contract,
            "proposal-route-delivery",
            base_state(),
            base_state(**{"project-phase": "delivery-governed"}),
            recovery={
                "decision": "defer",
                "justification": "Target capacity is unavailable.",
            },
        )

        issues = transition_request_issues(self.contract, request)

        self.assertTrue(any("owner, review_at" in issue for issue in issues), issues)

    def test_wrong_transition_authority_is_rejected(self) -> None:
        request = complete_request(
            self.contract,
            "proposal-route-delivery",
            base_state(),
            base_state(**{"project-phase": "delivery-governed"}),
        )
        request["source_authority_role"] = "console-projection"

        issues = transition_request_issues(self.contract, request)

        self.assertTrue(any("requires source authority" in issue for issue in issues), issues)

    def test_incomplete_typed_envelope_is_rejected(self) -> None:
        request = complete_request(
            self.contract,
            "proposal-route-delivery",
            base_state(),
            base_state(**{"project-phase": "delivery-governed"}),
        )
        del request["envelope"]["target_owner_ref"]

        issues = transition_request_issues(self.contract, request)

        self.assertTrue(any("target_owner_ref" in issue for issue in issues), issues)

    def test_implementation_maturity_cannot_be_overstated(self) -> None:
        request = complete_request(
            self.contract,
            "proposal-route-delivery",
            base_state(),
            base_state(**{"project-phase": "delivery-governed"}),
        )
        request["implementation_maturity"] = "dev-integration"

        issues = transition_request_issues(self.contract, request)

        self.assertTrue(any("exceeds contract maturity" in issue for issue in issues), issues)


if __name__ == "__main__":
    unittest.main()
