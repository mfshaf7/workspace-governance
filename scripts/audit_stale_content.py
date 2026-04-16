#!/usr/bin/env python3
import argparse
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Rule:
    description: str
    pattern: str
    repo_names: tuple[str, ...]
    exclude_substrings: tuple[str, ...] = ()


ACTIVE_DOC_RULES = (
    Rule(
        description="retired openclaw-isolated-deployment repo reference in active platform docs",
        pattern=r"openclaw-isolated-deployment",
        repo_names=("platform-engineering",),
    ),
    Rule(
        description="retired Telegram copy-sync workflow",
        pattern=r"sync-telegram-build-copy\.sh",
        repo_names=(
            "workspace-governance",
            "platform-engineering",
            "openclaw-runtime-distribution",
            "openclaw-telegram-enhanced",
            "openclaw-host-bridge",
            "security-architecture",
        ),
    ),
    Rule(
        description="retired workspace-sync verifier",
        pattern=r"verify-workspace-sync\.sh",
        repo_names=(
            "workspace-governance",
            "platform-engineering",
            "openclaw-runtime-distribution",
            "openclaw-telegram-enhanced",
            "openclaw-host-bridge",
            "security-architecture",
        ),
    ),
    Rule(
        description="retired gateway image recorder entrypoint",
        pattern=r"record_gateway_image\.py",
        repo_names=("workspace-governance", "platform-engineering"),
    ),
    Rule(
        description="retired stage readiness entrypoint",
        pattern=r"stage_promotion_readiness\.py",
        repo_names=("workspace-governance", "platform-engineering"),
    ),
    Rule(
        description="retired environment contract validator path",
        pattern=r"validate_environment_contract\.py",
        repo_names=("workspace-governance", "platform-engineering"),
    ),
)


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
    errors: list[str] = []
    compiled_rules = [(rule, re.compile(rule.pattern)) for rule in ACTIVE_DOC_RULES]

    for rule, pattern in compiled_rules:
        repo_names = tuple(args.repo_names) if args.repo_names else rule.repo_names
        for repo_name in repo_names:
            if repo_name not in rule.repo_names:
                continue
            repo_root = workspace_root / repo_name
            if not repo_root.exists():
                errors.append(f"missing repo for stale-content audit: {repo_root}")
                continue
            for path in iter_markdown_files(repo_root):
                path_str = str(path)
                if any(marker in path_str for marker in rule.exclude_substrings):
                    continue
                text = path.read_text()
                if pattern.search(text):
                    errors.append(
                        f"{path}: found stale-content pattern for {rule.description!r} matching /{rule.pattern}/"
                    )

    if errors:
        raise SystemExit("\n".join(errors))

    print("stale-content audit clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
