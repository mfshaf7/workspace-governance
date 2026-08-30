from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from agent_action_conformance import (  # noqa: E402
    REQUIRED_EXCLUSIONS,
    _materialize_pinned_source,
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

    def test_pinned_source_uses_merged_revision_not_mutable_head(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source_repo = root / "source"
            source_repo.mkdir()
            subprocess.run(
                ["git", "init", "--initial-branch=main"],
                cwd=source_repo,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "Conformance Test"],
                cwd=source_repo,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "conformance@example.invalid"],
                cwd=source_repo,
                check=True,
            )
            source_file = source_repo / "source.txt"
            source_file.write_text("pinned\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=source_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "pinned source"],
                cwd=source_repo,
                check=True,
                capture_output=True,
            )
            pinned_revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=source_repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            source_file.write_text("new main\n", encoding="utf-8")
            subprocess.run(["git", "add", "."], cwd=source_repo, check=True)
            subprocess.run(
                ["git", "commit", "-m", "advance main"],
                cwd=source_repo,
                check=True,
                capture_output=True,
            )
            main_revision = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=source_repo,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            source_file.write_text("dirty checkout\n", encoding="utf-8")

            snapshot, observed_main = _materialize_pinned_source(
                source_repo,
                pinned_revision,
                root / "snapshot",
            )

            self.assertEqual(observed_main, main_revision)
            self.assertEqual(
                (snapshot / "source.txt").read_text(encoding="utf-8"),
                "pinned\n",
            )


if __name__ == "__main__":
    unittest.main()
