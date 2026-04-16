#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
import sys

import yaml

from contracts_lib import load_contracts


def write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Create a scaffolded after-action review record in workspace-governance."
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    parser.add_argument("--record-id", required=True, help="record id and filename stem, for example 2026-04-17-example")
    parser.add_argument("--title", required=True, help="after-action title")
    parser.add_argument("--owner-repo", required=True, help="active repo that owns the learning record")
    parser.add_argument("--summary", required=True, help="short summary of what the review is about")
    parser.add_argument("--related-repo", action="append", default=[], dest="related_repos")
    parser.add_argument("--related-product", action="append", default=[], dest="related_products")
    parser.add_argument("--related-component", action="append", default=[], dest="related_components")
    parser.add_argument("--change-class", action="append", default=[], dest="change_classes")
    parser.add_argument("--source-ref", action="append", default=[], dest="source_refs")
    parser.add_argument("--lesson-id", default="lesson-1")
    parser.add_argument("--lesson-title", default="Initial lesson")
    parser.add_argument("--failure-class", default="workflow-doctrine-gap")
    parser.add_argument("--trigger", default="repeated-manual-retrospective")
    parser.add_argument("--finding", default="Replace this scaffold finding with the concrete miss or late discovery.")
    parser.add_argument("--impact", default="Replace this scaffold impact with the real operational or architecture cost.")
    parser.add_argument("--status", choices=("open", "closed"), default="open")
    parser.add_argument(
        "--expected-control-type",
        action="append",
        default=["contract"],
        dest="expected_control_types",
        help="repeatable expected control type for the lesson",
    )
    parser.add_argument(
        "--control-ref",
        action="append",
        default=[],
        dest="control_refs",
        help="repeatable control ref in the form type:path:owner_repo[:note]",
    )
    parser.add_argument("--follow-up-owner", help="required when status=open")
    parser.add_argument("--follow-up-due-on", help="ISO date, required when status=open")
    parser.add_argument("--follow-up-note", help="required when status=open")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    contracts = load_contracts(repo_root)
    active_repos = set(contracts["repos"]["repos"].keys())

    if args.owner_repo not in active_repos:
        raise SystemExit(f"--owner-repo must be an active repo, got {args.owner_repo!r}")

    if args.failure_class not in contracts["failure_taxonomy"]["failure_classes"]:
        raise SystemExit(f"--failure-class must be declared in contracts/failure-taxonomy.yaml, got {args.failure_class!r}")

    if args.trigger not in contracts["improvement_triggers"]["triggers"]:
        raise SystemExit(f"--trigger must be declared in contracts/improvement-triggers.yaml, got {args.trigger!r}")

    output_path = repo_root / "reviews" / "after-action" / f"{args.record_id}.yaml"
    if output_path.exists():
        raise SystemExit(f"after-action record already exists: {output_path}")

    control_refs: list[dict] = []
    for raw in args.control_refs:
        parts = raw.split(":", 3)
        if len(parts) < 3:
            raise SystemExit(f"invalid --control-ref {raw!r}; expected type:path:owner_repo[:note]")
        control_type, path, owner_repo = parts[:3]
        note = parts[3] if len(parts) == 4 else ""
        control_refs.append(
            {
                "type": control_type,
                "path": path,
                "owner_repo": owner_repo,
                **({"note": note} if note else {}),
            }
        )

    if args.status == "closed":
        if not control_refs:
            raise SystemExit("closed scaffold lessons require at least one --control-ref")
        follow_up = {"owner_repo": None, "due_on": None, "note": None}
    else:
        due_on = args.follow_up_due_on or (date.today() + timedelta(days=14)).isoformat()
        follow_up = {
            "owner_repo": args.follow_up_owner or args.owner_repo,
            "due_on": due_on,
            "note": args.follow_up_note or "Replace this scaffold follow-up note with the real next control to land.",
        }

    payload = {
        "schema_version": 1,
        "id": args.record_id,
        "title": args.title,
        "recorded_on": date.today().isoformat(),
        "owner_repo": args.owner_repo,
        "summary": args.summary,
        "scope": {
            "related_repos": sorted(set(args.related_repos)),
            "related_products": sorted(set(args.related_products)),
            "related_components": sorted(set(args.related_components)),
            "change_classes": sorted(set(args.change_classes)),
        },
        "source_refs": list(args.source_refs or ["replace-with-pr-or-incident-ref"]),
        "lessons": [
            {
                "id": args.lesson_id,
                "title": args.lesson_title,
                "failure_class": args.failure_class,
                "trigger": args.trigger,
                "finding": args.finding,
                "impact": args.impact,
                "status": args.status,
                "expected_control_types": sorted(set(args.expected_control_types)),
                "control_refs": control_refs,
                "follow_up": follow_up,
            }
        ],
    }

    write_yaml(output_path, payload)
    print(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
