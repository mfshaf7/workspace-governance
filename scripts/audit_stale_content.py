#!/usr/bin/env python3
import argparse
import re
from pathlib import Path

from contracts_lib import load_contracts

DEFAULT_EXCLUDES = (
    "/.git/",
    "/docs/archive/",
    "/docs/records/change-records/",
    "/docs/decisions/adr/",
)


def iter_markdown_files(repo_root: Path):
    for path in repo_root.rglob("*.md"):
        path_str = str(path)
        if any(marker in path_str for marker in DEFAULT_EXCLUDES):
            continue
        yield path


def resolve_contract_repo(workspace_root: Path) -> Path:
    direct_repo = workspace_root
    nested_repo = workspace_root / "workspace-governance"
    if (direct_repo / "contracts").exists():
        return direct_repo
    if (nested_repo / "contracts").exists():
        return nested_repo
    return nested_repo


def resolve_repo_root(workspace_root: Path, repo_name: str, contract_repo: Path) -> Path:
    nested_repo = workspace_root / repo_name
    if nested_repo.exists():
        return nested_repo
    if repo_name == "workspace-governance" and contract_repo.exists():
        return contract_repo
    return nested_repo


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit active docs for known stale-content patterns."
    )
    parser.add_argument(
        "--workspace-root",
        default=Path(__file__).resolve().parents[2],
        type=Path,
        help="workspace root containing the active repos",
    )
    parser.add_argument(
        "--repo-name",
        action="append",
        dest="repo_names",
        help="limit the audit to one or more specific repo names",
    )
    args = parser.parse_args()

    workspace_root = args.workspace_root.resolve()
    contract_repo = resolve_contract_repo(workspace_root)
    contracts = load_contracts(contract_repo)
    errors: list[str] = []

    retired_terms = contracts["vocabulary"]["retired_terms"]
    repo_rules = contracts["repo_rules"]
    selected_repo_names = set(args.repo_names or [])

    for entry in retired_terms:
        pattern = re.compile(entry["pattern"])
        for repo_name in entry["repo_names"]:
            if selected_repo_names and repo_name not in selected_repo_names:
                continue
            repo_root = resolve_repo_root(workspace_root, repo_name, contract_repo)
            if not repo_root.exists():
                errors.append(f"missing repo for stale-content audit: {repo_root}")
                continue
            for path in iter_markdown_files(repo_root):
                path_str = str(path)
                if any(marker in path_str for marker in entry.get("exclude_paths", [])):
                    continue
                text = path.read_text()
                if pattern.search(text):
                    errors.append(
                        f"{path}: found stale-content pattern for retired term {entry['id']!r} matching /{entry['pattern']}/"
                    )

    for repo_name, rule in repo_rules.items():
        if selected_repo_names and repo_name not in selected_repo_names:
            continue
        repo_root = resolve_repo_root(workspace_root, repo_name, contract_repo)
        for filename, pattern_list in (
            ("README.md", rule["forbidden_patterns"]["readme"]),
            ("AGENTS.md", rule["forbidden_patterns"]["agents"]),
        ):
            path = repo_root / filename
            if not path.exists():
                errors.append(f"missing ownership doc for stale-content audit: {path}")
                continue
            text = path.read_text()
            for pattern_text in pattern_list:
                pattern = re.compile(pattern_text)
                if pattern.search(text):
                    errors.append(
                        f"{path}: found repo-rule stale-content pattern matching /{pattern_text}/"
                    )

    if errors:
        raise SystemExit("\n".join(errors))

    print("stale-content audit clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
