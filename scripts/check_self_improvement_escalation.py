#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys

import yaml

from contracts_lib import load_contracts


VALID_STATUSES = {"new", "triaged", "accepted", "dismissed", "closed"}
VALID_SOURCE_TYPES = {"conversation", "machine-audit", "manual", "review", "rehearsal"}


def write_yaml(path: Path, payload: dict) -> None:
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate whether a self-improvement signal requires immediate candidate capture "
            "and optionally scaffold that candidate."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="workspace-governance repository root",
    )
    parser.add_argument("--signal", required=True, help="signal id from contracts/self-improvement-policy.yaml")
    parser.add_argument("--owner-repo", required=True, help="active repo that owns the candidate")
    parser.add_argument("--candidate-id", help="candidate record id / filename stem when writing a candidate")
    parser.add_argument("--title", help="candidate title when writing a candidate")
    parser.add_argument("--summary", help="candidate summary when writing a candidate")
    parser.add_argument("--finding", help="signal finding text when writing a candidate")
    parser.add_argument("--recorded-on", help="override recorded_on date (YYYY-MM-DD)")
    parser.add_argument("--source-type", choices=sorted(VALID_SOURCE_TYPES), help="override source type")
    parser.add_argument("--trigger", help="override trigger")
    parser.add_argument("--failure-class", action="append", default=[], dest="failure_classes")
    parser.add_argument("--related-repo", action="append", default=[], dest="related_repos")
    parser.add_argument("--related-product", action="append", default=[], dest="related_products")
    parser.add_argument("--related-component", action="append", default=[], dest="related_components")
    parser.add_argument("--change-class", action="append", default=[], dest="change_classes")
    parser.add_argument("--source-ref", action="append", default=[], dest="source_refs")
    parser.add_argument("--regression-of", help="closed candidate or after-action path when this signal is a regression")
    parser.add_argument("--status", choices=sorted(VALID_STATUSES), default="triaged")
    parser.add_argument("--follow-up-owner")
    parser.add_argument("--follow-up-due-on")
    parser.add_argument("--follow-up-note")
    parser.add_argument("--write-candidate", action="store_true", help="scaffold the candidate immediately")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    contracts = load_contracts(repo_root)
    active_repos = set(contracts["repos"]["repos"].keys())
    triggers = contracts["improvement_triggers"]["triggers"]
    failure_classes = set(contracts["failure_taxonomy"]["failure_classes"].keys())
    policy = contracts["self_improvement_policy"]
    signal_catalog = policy["signal_catalog"]
    runtime_gate = policy["runtime_gate"]

    if args.owner_repo not in active_repos:
        raise SystemExit(f"--owner-repo must be an active repo, got {args.owner_repo!r}")
    if args.signal not in signal_catalog:
        raise SystemExit(f"--signal must exist in contracts/self-improvement-policy.yaml, got {args.signal!r}")
    signal = signal_catalog[args.signal]

    if args.regression_of and not signal["supports_regression_link"]:
        raise SystemExit(f"signal {args.signal!r} does not support regression linkage")

    effective_trigger = args.trigger or (
        "closed-lesson-regression" if args.regression_of else signal["default_trigger"]
    )
    if effective_trigger not in triggers:
        raise SystemExit(f"trigger {effective_trigger!r} is not declared in contracts/improvement-triggers.yaml")

    effective_failure_classes = list(args.failure_classes or signal["default_failure_classes"])
    if args.regression_of and "learning-closure-regression" not in effective_failure_classes:
        effective_failure_classes.append("learning-closure-regression")
    for failure_class in effective_failure_classes:
        if failure_class not in failure_classes:
            raise SystemExit(
                f"failure class {failure_class!r} is not declared in contracts/failure-taxonomy.yaml"
            )
    effective_failure_classes = sorted(set(effective_failure_classes))

    requires_candidate_before_continue = args.signal in set(
        runtime_gate["require_candidate_before_continue_for"]
    )
    pause_before_continue = bool(runtime_gate["pause_before_continue"])

    output = {
        "signal": args.signal,
        "description": signal["description"],
        "requires_candidate_before_continue": requires_candidate_before_continue,
        "pause_before_continue": pause_before_continue,
        "effective_source_type": args.source_type or signal["default_source_type"],
        "effective_trigger": effective_trigger,
        "effective_failure_classes": effective_failure_classes,
        "candidate_created": False,
        "candidate_path": None,
    }

    if not args.write_candidate:
        print(json.dumps(output, indent=2, sort_keys=False))
        return 2 if requires_candidate_before_continue and pause_before_continue else 0

    missing = [
        name
        for name, value in (
            ("--candidate-id", args.candidate_id),
            ("--title", args.title),
            ("--summary", args.summary),
            ("--finding", args.finding),
        )
        if not value
    ]
    if missing:
        raise SystemExit(f"--write-candidate requires {', '.join(missing)}")

    output_path = repo_root / "reviews" / "improvement-candidates" / f"{args.candidate_id}.yaml"
    if output_path.exists():
        raise SystemExit(f"improvement candidate already exists: {output_path}")

    if args.status in {"new", "triaged", "accepted"}:
        due_on = args.follow_up_due_on or (
            date.fromisoformat(args.recorded_on) + timedelta(days=runtime_gate["default_follow_up_days"])
            if args.recorded_on
            else date.today() + timedelta(days=runtime_gate["default_follow_up_days"])
        )
        if not isinstance(due_on, str):
            due_on = due_on.isoformat()
        follow_up = {
            "owner_repo": args.follow_up_owner or args.owner_repo,
            "due_on": due_on,
            "note": args.follow_up_note
            or "Review and approve the strongest durable control before treating this lesson as closed.",
        }
    else:
        follow_up = {"owner_repo": None, "due_on": None, "note": None}

    payload = {
        "schema_version": 1,
        "id": args.candidate_id,
        "title": args.title,
        "recorded_on": args.recorded_on or date.today().isoformat(),
        "owner_repo": args.owner_repo,
        "summary": args.summary,
        "regression_of": args.regression_of,
        "status": args.status,
        "source_type": args.source_type or signal["default_source_type"],
        "scope": {
            "related_repos": sorted(set(args.related_repos)),
            "related_products": sorted(set(args.related_products)),
            "related_components": sorted(set(args.related_components)),
            "change_classes": sorted(set(args.change_classes)),
        },
        "signals": [
            {
                "id": args.signal,
                "title": signal["description"],
                "trigger": effective_trigger,
                "failure_classes": effective_failure_classes,
                "finding": args.finding,
                "source_refs": list(args.source_refs or ["replace-with-concrete-signal-ref"]),
            }
        ],
        "resolution": {
            "after_action_ref": None,
            "control_refs": [],
            "note": None,
        },
        "follow_up": follow_up,
    }

    write_yaml(output_path, payload)
    output["candidate_created"] = True
    output["candidate_path"] = str(output_path.relative_to(repo_root))
    print(json.dumps(output, indent=2, sort_keys=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
