#!/usr/bin/env python3
"""Turn code_review + optional security_scanner JSON into human-readable fix hints."""

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


def load_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return None


def suggest_from_code_review(report: dict) -> list[str]:
    hints: list[str] = []
    summary = report.get("summary") or {}
    if summary.get("hardcoded_secret_pattern_hits", 0):
        hints.append(
            "Move secrets to environment variables or a secret manager; "
            "remove literals matching password/secret/api_key assignments."
        )
    if summary.get("console_log_hits", 0):
        hints.append(
            "Replace console.log with a structured logger; gate debug logs "
            "behind NODE_ENV !== 'production'."
        )
    if summary.get("todo_hits", 0):
        hints.append(
            "Resolve or ticket TODO comments; prioritize security-related TODOs."
        )
    return hints


def suggest_from_security(findings: list) -> list[str]:
    hints: list[str] = []
    for item in findings:
        issue = item.get("issue")
        if issue == "dangerous_call":
            hints.append(
                f"Avoid {item.get('detail')} in {item.get('path')}:{item.get('line')} "
                "— refactor to safer APIs."
            )
        elif issue == "risky_js_pattern":
            hints.append(
                f"Review risky JS in {item.get('path')}:{item.get('line')} "
                "for XSS / code injection."
            )
    return list(dict.fromkeys(hints))


def main() -> int:
    parser = argparse.ArgumentParser(description="Print fix suggestions from scan JSON.")
    parser.add_argument(
        "--code-review",
        default="",
        help="Path to ai_report.txt (default: repo root ai_report.txt).",
    )
    parser.add_argument(
        "--security",
        default="",
        help="Optional path to security_scanner JSON saved to a file.",
    )
    args = parser.parse_args()

    root = find_repo_root()
    cr_path = Path(args.code_review) if args.code_review else root / "ai_report.txt"
    sec_path = Path(args.security) if args.security else None

    cr = load_json(cr_path)
    sec = load_json(sec_path) if sec_path else None

    all_hints: list[str] = []
    if cr:
        all_hints.extend(suggest_from_code_review(cr))
    else:
        all_hints.append(f"No readable code review JSON at {cr_path}.")

    if sec:
        findings = sec.get("findings") or []
        all_hints.extend(suggest_from_security(findings))

    print("=== Suggested fixes ===")
    for h in all_hints:
        print(f"- {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
