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

from project_lifecycle_proof import (  # noqa: E402
    proof_suite_issues,
    render_markdown,
    run_proof,
)


def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class ProjectLifecycleProofTests(unittest.TestCase):
    def setUp(self) -> None:
        self.lifecycle = load_yaml(REPO_ROOT / "contracts/project-lifecycle.yaml")
        self.proof = load_yaml(REPO_ROOT / "contracts/project-lifecycle-proof.yaml")

    def test_canonical_proof_suite_passes_all_scenarios(self) -> None:
        report = run_proof(self.lifecycle, self.proof)

        self.assertEqual(proof_suite_issues(self.lifecycle, self.proof), [])
        self.assertEqual(report["summary"]["outcome"], "passed")
        self.assertEqual(report["summary"]["scenario_count"], 12)
        self.assertEqual(report["summary"]["positive_scenario_count"], 4)
        self.assertEqual(report["summary"]["negative_scenario_count"], 8)

    def test_receipts_are_deterministic(self) -> None:
        first = run_proof(self.lifecycle, self.proof)
        second = run_proof(self.lifecycle, self.proof)

        self.assertEqual(first, second)
        self.assertTrue(
            first["scenarios"][0]["steps"][0]["receipt_id"].startswith(
                "lifecycle-proof-receipt:"
            )
        )

    def test_negative_scenario_detects_a_weakened_authority_check(self) -> None:
        weakened = copy.deepcopy(self.proof)
        scenario = next(
            item
            for item in weakened["project_lifecycle_proof"]["scenarios"]
            if item["scenario_id"] == "reject-wrong-source-authority"
        )
        scenario["steps"][0]["source_authority_role"] = (
            "operator-workflow-authority"
        )

        issues = proof_suite_issues(self.lifecycle, weakened)

        self.assertIn(
            "proof scenario reject-wrong-source-authority did not pass",
            issues,
        )

    def test_generated_reports_match_the_canonical_run(self) -> None:
        report = run_proof(self.lifecycle, self.proof)
        outputs = self.proof["project_lifecycle_proof"]["report_outputs"]

        self.assertEqual(
            (REPO_ROOT / outputs["markdown"]).read_text(encoding="utf-8"),
            render_markdown(report),
        )
        self.assertEqual(
            load_yaml(REPO_ROOT / outputs["json"]),
            report,
        )

    def test_malformed_proof_returns_issues_instead_of_crashing(self) -> None:
        malformed = copy.deepcopy(self.proof)
        malformed["project_lifecycle_proof"]["scenarios"][0]["steps"][0].pop(
            "state_changes"
        )

        issues = proof_suite_issues(self.lifecycle, malformed)

        self.assertTrue(any("cannot execute" in issue for issue in issues), issues)


if __name__ == "__main__":
    unittest.main()
