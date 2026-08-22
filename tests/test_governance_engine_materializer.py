from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_ROOT = REPO_ROOT / "scripts"
MATERIALIZER_PATH = SCRIPTS_ROOT / "governance_engine_materializer.py"


def load_materializer():
    if str(SCRIPTS_ROOT) not in sys.path:
        sys.path.insert(0, str(SCRIPTS_ROOT))
    spec = importlib.util.spec_from_file_location(
        "governance_engine_materializer_worktree_skills",
        MATERIALIZER_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load {MATERIALIZER_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class SkillMaterializationSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.materializer = load_materializer()

    def test_workspace_governance_skill_uses_active_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_root = Path(temp_dir)
            repo_root = workspace_root / ".worktrees" / "workspace-governance-961"
            main_repo = workspace_root / "workspace-governance"
            source_relative = Path("skills-src/project-delivery-operator")
            target_root = workspace_root / "installed"
            for source_root, content in (
                (repo_root, "worktree source\n"),
                (main_repo, "main source\n"),
            ):
                source_dir = source_root / source_relative
                source_dir.mkdir(parents=True)
                (source_dir / "SKILL.md").write_text(content, encoding="utf-8")
            contracts = {
                "skills": {
                    "skills": {
                        "project-delivery-operator": {
                            "owner_repo": "workspace-governance",
                            "source_path": source_relative.as_posix(),
                            "scope": "workspace",
                        }
                    }
                },
                "governance_engine_output_manifest": {
                    "governance_engine_output_manifest": {
                        "emission_families": [
                            {
                                "id": "installed-skills",
                                "managed_manifest_filename": ".manifest.json",
                            }
                        ]
                    }
                },
            }

            skill_names, errors = self.materializer.install_registered_skills(
                repo_root,
                workspace_root,
                target_root,
                contracts=contracts,
                selected_skill_names={"project-delivery-operator"},
            )

            installed = (
                target_root / "project-delivery-operator" / "SKILL.md"
            ).read_text(encoding="utf-8")

        self.assertEqual(skill_names, ["project-delivery-operator"])
        self.assertEqual(errors, [])
        self.assertEqual(installed, "worktree source\n")


if __name__ == "__main__":
    unittest.main()
