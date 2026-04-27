#!/usr/bin/env python3
"""Rule-based deploy recommendation from ai_report.json (code_review output)."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def find_repo_root() -> Path:
    env = os.environ.get("WORKSPACE") or os.environ.get("CI_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    return Path(__file__).resolve().parent.parent


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def _norm_path(p: str) -> str:
    return p.replace("\\", "/")


def _findings(report: dict, key: str) -> list[dict]:
    findings = report.get("findings") or {}
    raw = findings.get(key)
    return raw if isinstance(raw, list) else []


def count_in_backend(report: dict, key: str) -> int:
    return sum(
        1
        for item in _findings(report, key)
        if "/backend/" in _norm_path(str(item.get("path", "")))
    )


def decide(report: dict) -> dict:
    summary = report.get("summary") or {}
    secrets = count_in_backend(report, "hardcoded_password_secret_api_key")
    todos = count_in_backend(report, "todo_comments")
    logs = count_in_backend(report, "console_log")
    total_todos = int(summary.get("todo_hits", 0))
    total_logs = int(summary.get("console_log_hits", 0))

    blockers: list[str] = []
    if secrets > 0:
        blockers.append("hardcoded_secret_pattern_hits_in_backend > 0")

    if blockers:
        decision = "NO_DEPLOY"
        confidence = 0.95
    elif todos > 5 or logs > 10 or total_todos > 8 or total_logs > 15:
        decision = "REVIEW_REQUIRED"
        confidence = 0.7
    else:
        decision = "DEPLOY_OK"
        confidence = 0.85

    return {
        "decision": decision,
        "confidence": confidence,
        "blockers": blockers,
        "metrics": {
            "secrets_backend": secrets,
            "todos_backend": todos,
            "console_logs_backend": logs,
            "todos_repo": total_todos,
            "console_logs_repo": total_logs,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit deploy gate JSON from ai_report.")
    parser.add_argument(
        "--report",
        default="",
        help="Path to ai_report.txt JSON (default: <repo>/ai_report.txt).",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit 1 when decision is NO_DEPLOY.",
    )
    args = parser.parse_args()

    root = find_repo_root()
    report_path = Path(args.report) if args.report else root / "ai_report.txt"
    if not report_path.is_file():
        out = {
            "decision": "REVIEW_REQUIRED",
            "confidence": 0.5,
            "blockers": [f"missing_report:{report_path}"],
            "metrics": {},
        }
        print(json.dumps(out, indent=2))
        return 0

    report = load_report(report_path)
    out = decide(report)
    print(json.dumps(out, indent=2))

    if args.strict and out["decision"] == "NO_DEPLOY":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
