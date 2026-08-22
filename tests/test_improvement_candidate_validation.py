from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
VALIDATOR_PATH = SCRIPTS_ROOT / "validate_improvement_candidates.py"


def load_validator():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "validate_improvement_candidates_worktree_paths",
        VALIDATOR_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class ImprovementCandidatePathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_validator()

    def test_canonical_checkout_uses_canonical_repo_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root = workspace_root / "workspace-governance"
            record_path = repo_root / "reviews" / "improvement-candidates" / "record.yaml"

            result = self.validator.workspace_relative_path(
                record_path,
                repo_root=repo_root,
                workspace_root=workspace_root,
            )

        self.assertEqual(
            result,
            "workspace-governance/reviews/improvement-candidates/record.yaml",
        )

    def test_worktree_checkout_keeps_canonical_repo_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root = workspace_root / ".worktrees" / "workspace-governance-961"
            record_path = repo_root / "reviews" / "improvement-candidates" / "record.yaml"

            result = self.validator.workspace_relative_path(
                record_path,
                repo_root=repo_root,
                workspace_root=workspace_root,
            )

        self.assertEqual(
            result,
            "workspace-governance/reviews/improvement-candidates/record.yaml",
        )

    def test_same_repo_reference_resolves_to_active_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root = workspace_root / ".worktrees" / "workspace-governance-961"

            result = self.validator.resolve_workspace_reference(
                "workspace-governance/tests/new-branch-test.py",
                repo_root=repo_root,
                workspace_root=workspace_root,
            )

        self.assertEqual(result, repo_root / "tests" / "new-branch-test.py")

    def test_other_repo_reference_resolves_to_workspace_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root = workspace_root / ".worktrees" / "workspace-governance-961"

            result = self.validator.resolve_workspace_reference(
                "operator-orchestration-service/src/app.js",
                repo_root=repo_root,
                workspace_root=workspace_root,
            )

        self.assertEqual(
            result,
            workspace_root / "operator-orchestration-service" / "src" / "app.js",
        )


if __name__ == "__main__":
    unittest.main()
