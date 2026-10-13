from __future__ import annotations

from pathlib import Path
import sys
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from preflight_touched_records import owner_repo_root  # noqa: E402


class TouchedRecordPreflightTests(unittest.TestCase):
    def test_workspace_governance_uses_selected_repo_root(self) -> None:
        workspace_root = Path("/workspace")
        selected_worktree = Path("/worktrees/workspace-governance")

        self.assertEqual(
            owner_repo_root(
                "workspace-governance",
                workspace_root=workspace_root,
                repo_root=selected_worktree,
            ),
            selected_worktree,
        )

    def test_other_owners_remain_under_workspace_root(self) -> None:
        workspace_root = Path("/workspace")

        self.assertEqual(
            owner_repo_root(
                "operator-orchestration-service",
                workspace_root=workspace_root,
                repo_root=Path("/worktrees/workspace-governance"),
            ),
            workspace_root / "operator-orchestration-service",
        )


if __name__ == "__main__":
    unittest.main()
