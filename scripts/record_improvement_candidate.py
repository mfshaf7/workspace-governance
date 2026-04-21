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
        description="Create a scaffolded improvement candidate record in workspace-governance."
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    parser.add_argument("--record-id", required=True, help="record id and filename stem")
    parser.add_argument("--title", required=True, help="candidate title")
    parser.add_argument("--owner-repo", required=True, help="active repo that owns the candidate")
    parser.add_argument("--summary", required=True, help="short summary of the candidate")
    parser.add_argument(
        "--regression-of",
        help="workspace-relative path to the earlier closed candidate or after-action if this record is a regression",
    )
    parser.add_argument("--status", choices=("new", "triaged", "accepted", "dismissed", "closed"), default="new")
    parser.add_argument(
        "--source-type",
        choices=("conversation", "machine-audit", "manual", "review", "rehearsal"),
        default="conversation",
    )
    parser.add_argument("--related-repo", action="append", default=[], dest="related_repos")
    parser.add_argument("--related-product", action="append", default=[], dest="related_products")
    parser.add_argument("--related-component", action="append", default=[], dest="related_components")
    parser.add_argument("--change-class", action="append", default=[], dest="change_classes")
    parser.add_argument("--signal-id", default="signal-1")
    parser.add_argument("--signal-title", default="Initial signal")
    parser.add_argument("--trigger", default="repeated-manual-retrospective")
    parser.add_argument("--failure-class", action="append", default=["workflow-doctrine-gap"], dest="failure_classes")
    parser.add_argument("--finding", default="Replace this scaffold signal with the concrete repeated miss or late discovery.")
    parser.add_argument("--source-ref", action="append", default=[], dest="source_refs")
    parser.add_argument("--after-action-ref")
    parser.add_argument(
        "--control-ref",
        action="append",
        default=[],
        dest="control_refs",
        help="repeatable control ref in the form type:path:owner_repo[:note]",
    )
    parser.add_argument("--resolution-note")
    parser.add_argument("--follow-up-owner", help="required when status is new, triaged, or accepted")
    parser.add_argument("--follow-up-due-on", help="ISO date, required when status is new, triaged, or accepted")
    parser.add_argument("--follow-up-note", help="required when status is new, triaged, or accepted")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    contracts = load_contracts(repo_root)
    active_repos = set(contracts["repos"]["repos"].keys())

    if args.owner_repo not in active_repos:
        raise SystemExit(f"--owner-repo must be an active repo, got {args.owner_repo!r}")
    if args.trigger not in contracts["improvement_triggers"]["triggers"]:
        raise SystemExit(f"--trigger must be declared in contracts/improvement-triggers.yaml, got {args.trigger!r}")
    for failure_class in args.failure_classes:
        if failure_class not in contracts["failure_taxonomy"]["failure_classes"]:
            raise SystemExit(f"--failure-class must be declared in contracts/failure-taxonomy.yaml, got {failure_class!r}")

    output_path = repo_root / "reviews" / "improvement-candidates" / f"{args.record_id}.yaml"
    if output_path.exists():
        raise SystemExit(f"improvement candidate already exists: {output_path}")

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

    if args.status in {"new", "triaged", "accepted"}:
        due_on = args.follow_up_due_on or (date.today() + timedelta(days=14)).isoformat()
        follow_up = {
            "owner_repo": args.follow_up_owner or args.owner_repo,
            "due_on": due_on,
            "note": args.follow_up_note or "Replace this scaffold follow-up note with the real next triage or control step.",
        }
    else:
        follow_up = {"owner_repo": None, "due_on": None, "note": None}

    payload = {
        "schema_version": 1,
        "id": args.record_id,
        "title": args.title,
        "recorded_on": date.today().isoformat(),
        "owner_repo": args.owner_repo,
        "summary": args.summary,
        "regression_of": args.regression_of,
        "status": args.status,
        "source_type": args.source_type,
        "scope": {
            "related_repos": sorted(set(args.related_repos)),
            "related_products": sorted(set(args.related_products)),
            "related_components": sorted(set(args.related_components)),
            "change_classes": sorted(set(args.change_classes)),
        },
        "signals": [
            {
                "id": args.signal_id,
                "title": args.signal_title,
                "trigger": args.trigger,
                "failure_classes": sorted(set(args.failure_classes)),
                "finding": args.finding,
                "source_refs": list(args.source_refs or ["replace-with-chat-thread-pr-or-audit-ref"]),
            }
        ],
        "resolution": {
            "after_action_ref": args.after_action_ref,
            "control_refs": control_refs,
            "note": args.resolution_note,
        },
        "follow_up": follow_up,
    }

    write_yaml(output_path, payload)
    print(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
