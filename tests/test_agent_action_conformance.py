from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from agent_action_conformance import (  # noqa: E402
    REQUIRED_EXCLUSIONS,
    contract_issues,
    render_markdown,
    report_issues,
)


class AgentActionConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = yaml.safe_load(
            (REPO_ROOT / "contracts/agent-action-conformance.yaml").read_text(
                encoding="utf-8"
            )
        )
        cls.report = json.loads(
            (REPO_ROOT / "reports/agent-action-conformance.json").read_text(
                encoding="utf-8"
            )
        )

    def test_case_map_covers_each_class_and_failure_boundary(self) -> None:
        self.assertEqual(contract_issues(self.contract), [])
        self.assertEqual(len(self.contract["cases"]), 11)
        self.assertEqual(
            set(self.contract["excluded_capabilities"]), REQUIRED_EXCLUSIONS
        )

    def test_generated_report_passes_without_runtime_activation(self) -> None:
        self.assertEqual(report_issues(self.report), [])
        self.assertEqual(self.report["summary"]["passed_case_count"], 11)
        self.assertEqual(self.report["summary"]["runtime_activation"], "disabled")

    def test_replay_and_post_dispatch_failures_never_return_success(self) -> None:
        cases = {case["case_id"]: case for case in self.report["cases"]}
        replay = cases["mutate-replay-consumed"]["observed"]
        self.assertEqual(replay["owner_mutation_invocations"], 0)
        self.assertFalse(replay["success_returned"])

        for case_id in (
            "mutate-receipt-store-failure",
            "mutate-audit-failure",
        ):
            with self.subTest(case_id=case_id):
                observed = cases[case_id]["observed"]
                self.assertEqual(observed["execution_outcome"], "error")
                self.assertEqual(observed["owner_mutation_invocations"], 1)
                self.assertFalse(observed["success_returned"])

    def test_generated_markdown_matches_report(self) -> None:
        markdown_path = REPO_ROOT / self.contract["report_outputs"]["markdown"]
        self.assertEqual(
            markdown_path.read_text(encoding="utf-8"),
            render_markdown(self.report),
        )


if __name__ == "__main__":
    unittest.main()
